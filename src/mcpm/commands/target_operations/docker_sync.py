"""
Docker synchronization target operations.

This module provides Docker-specific target operations for bidirectional sync
between MCPM profiles and Docker Compose services.
"""

import json
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

import yaml
from rich.console import Console

from mcpm.core.schema import ServerConfig, STDIOServerConfig
from mcpm.profile.profile_config import ProfileConfigManager

console = Console()


class DockerSyncOperations:
    """Docker synchronization operations for MCPM targets."""
    
    def __init__(self):
        self.profile_manager = ProfileConfigManager()
        
        # Mapping from Docker service patterns to MCP server types
        self.docker_to_mcp_mapping = {
            'postgresql': 'postgresql',
            'postgres': 'postgresql', 
            'context7': 'context7',
            'github': 'github',
            'obsidian': 'obsidian'
        }
        
        # Mapping from MCP server types to Docker service templates
        self.mcp_to_docker_mapping = {
            'postgresql': {
                'image': 'postgres:16-alpine',
                'environment': [
                    'POSTGRES_USER=${POSTGRES_USER:-mcpuser}',
                    'POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-password}',
                    'POSTGRES_DB=${POSTGRES_DB:-mcpdb}'
                ],
                'ports': ['5432:5432'],
                'volumes': ['postgres-data:/var/lib/postgresql/data'],
                'networks': ['mcp-network'],
                'healthcheck': {
                    'test': ['CMD-SHELL', 'pg_isready -U ${POSTGRES_USER:-mcpuser}'],
                    'interval': '10s',
                    'timeout': '5s',
                    'retries': 3,
                    'start_period': '30s'
                }
            },
            'context7': {
                'image': 'node:20-alpine',
                'working_dir': '/app',
                'command': 'sh -c "npm install -g @upstash/context7-mcp@latest && npx @upstash/context7-mcp@latest"',
                'ports': ['3000:3000'],
                'volumes': ['./volumes/context7:/data'],
                'networks': ['mcp-network'],
                'environment': [
                    'MCP_SERVER_NAME=context7',
                    'MCP_SERVER_PORT=3000'
                ]
            },
            'github': {
                'image': 'node:20-alpine',
                'working_dir': '/app', 
                'command': 'sh -c "npm install -g @modelcontextprotocol/server-github && mcp-server-github"',
                'ports': ['3000:3000'],
                'volumes': ['./volumes/github:/data'],
                'networks': ['mcp-network'],
                'environment': [
                    'GITHUB_PERSONAL_ACCESS_TOKEN=${GITHUB_PERSONAL_ACCESS_TOKEN}'
                ]
            },
            'obsidian': {
                'image': 'node:20-alpine',
                'working_dir': '/app',
                'command': 'sh -c "npm install -g obsidian-mcp-server && obsidian-mcp-server"',
                'ports': ['3000:3000'],
                'volumes': ['./volumes/obsidian:/data'],
                'networks': ['mcp-network'],
                'environment': [
                    'OBSIDIAN_API_KEY=${OBSIDIAN_API_KEY}',
                    'OBSIDIAN_URL=${OBSIDIAN_URL:-http://localhost:27123}'
                ]
            }
        }

    def sync_profile_to_docker(self, profile_name: str, compose_file: Path, auto_deploy: bool = False) -> bool:
        """Sync MCPM profile to Docker Compose file."""
        console.print(f"[cyan]🔄 Syncing profile '{profile_name}' to Docker...[/]")
        
        # Get profile servers
        profile_servers = self.profile_manager.get_profile(profile_name)
        if not profile_servers:
            console.print(f"[red]❌ Profile '{profile_name}' not found[/]")
            return False
            
        # Load or create compose structure
        compose_data = self._load_compose_file(compose_file)
        
        # Generate Docker services from profile
        services_added = []
        for server_config in profile_servers:
            docker_service = self._generate_docker_service(server_config)
            if docker_service:
                service_name = server_config.name
                compose_data['services'][service_name] = docker_service
                services_added.append(service_name)
                console.print(f"[green]✅ Added service:[/] {service_name}")
                
        if services_added:
            self._save_compose_file(compose_file, compose_data)
            
            if auto_deploy:
                console.print("[cyan]🚀 Auto-deploying services...[/]")
                self._deploy_services(compose_file, services_added)
                
            console.print(f"[green]🎉 Synced {len(services_added)} services to Docker[/]")
            return True
        else:
            console.print("[yellow]⚠️  No compatible services found in profile[/]")
            return False

    def sync_docker_to_profile(self, compose_file: Path, profile_name: str, auto_restart_router: bool = False) -> bool:
        """Sync Docker Compose services to MCPM profile."""
        console.print(f"[cyan]🔄 Syncing Docker services to profile '{profile_name}'...[/]")
        
        # Load compose file
        compose_data = self._load_compose_file(compose_file)
        services = compose_data.get('services', {})
        
        if not services:
            console.print(f"[yellow]⚠️  No services found in {compose_file}[/]")
            return False
            
        # Create or update profile
        servers_added = []
        for service_name, service_config in services.items():
            mcp_server = self._generate_mcp_server(service_name, service_config)
            if mcp_server:
                # Add to profile
                success = self.profile_manager.set_profile(profile_name, mcp_server)
                if success:
                    servers_added.append(service_name)
                    console.print(f"[green]✅ Added to profile:[/] {service_name}")
                    
        if servers_added:
            if auto_restart_router:
                console.print("[cyan]🔄 Restarting MCPM router...[/]")
                self._restart_mcpm_router()
                
            console.print(f"[green]🎉 Synced {len(servers_added)} services to profile '{profile_name}'[/]")
            return True
        else:
            console.print("[yellow]⚠️  No compatible Docker services found[/]")
            return False

    def bidirectional_sync(self, profile_name: str, compose_file: Path, conflict_resolution: str = 'profile_wins') -> bool:
        """Perform bidirectional sync with conflict resolution."""
        console.print(f"[cyan]🔄 Running bidirectional sync for profile '{profile_name}'...[/]")
        
        # Check what has changed since last sync
        profile_changed = self._has_profile_changed(profile_name)
        docker_changed = self._has_docker_changed(compose_file)
        
        if profile_changed and docker_changed:
            console.print("[yellow]⚠️  Conflict detected: both profile and Docker have changed[/]")
            
            if conflict_resolution == 'profile_wins':
                console.print("[cyan]📋 Profile takes precedence - syncing to Docker[/]")
                return self.sync_profile_to_docker(profile_name, compose_file, auto_deploy=True)
            elif conflict_resolution == 'docker_wins':
                console.print("[cyan]🐳 Docker takes precedence - syncing to profile[/]")
                return self.sync_docker_to_profile(compose_file, profile_name, auto_restart_router=True)
            else:
                console.print("[red]❌ Manual conflict resolution required[/]")
                return False
                
        elif profile_changed:
            console.print("[cyan]📋 Profile changed - syncing to Docker[/]")
            return self.sync_profile_to_docker(profile_name, compose_file, auto_deploy=True)
            
        elif docker_changed:
            console.print("[cyan]🐳 Docker changed - syncing to profile[/]")
            return self.sync_docker_to_profile(compose_file, profile_name, auto_restart_router=True)
            
        else:
            console.print("[green]✅ No changes detected - sync not needed[/]")
            return True

    def _generate_docker_service(self, server_config: ServerConfig) -> Optional[Dict[str, Any]]:
        """Generate Docker service from MCP server config."""
        server_type = self._detect_server_type(server_config)
        if not server_type or server_type not in self.mcp_to_docker_mapping:
            return None
            
        template = self.mcp_to_docker_mapping[server_type].copy()
        
        # Add container name and restart policy
        container_name = f"mcp-{server_config.name}"
        template['container_name'] = container_name
        template['restart'] = 'unless-stopped'
        
        # Merge environment variables
        if hasattr(server_config, 'env') and server_config.env:
            template_env = template.get('environment', [])
            for key, value in server_config.env.items():
                template_env.append(f"{key}={value}")
            template['environment'] = template_env
            
        return template

    def _generate_mcp_server(self, service_name: str, service_config: Dict[str, Any]) -> Optional[ServerConfig]:
        """Generate MCP server config from Docker service."""
        server_type = self._detect_docker_service_type(service_name, service_config)
        if not server_type:
            return None
            
        # Create base server config
        if server_type == 'postgresql':
            # Extract connection details from Docker service
            env_vars = service_config.get('environment', [])
            user = 'mcpuser'
            password = 'password'
            db = 'mcpdb'
            host = service_name  # Use service name as hostname in Docker network
            
            for env_var in env_vars:
                if isinstance(env_var, str):
                    if env_var.startswith('POSTGRES_USER='):
                        user = env_var.split('=', 1)[1].replace('${POSTGRES_USER}', 'mcpuser').replace('${POSTGRES_USER:-', '').replace('}', '')
                    elif env_var.startswith('POSTGRES_PASSWORD='):
                        password = env_var.split('=', 1)[1].replace('${POSTGRES_PASSWORD}', 'password').replace('${POSTGRES_PASSWORD:-', '').replace('}', '')
                    elif env_var.startswith('POSTGRES_DB='):
                        db = env_var.split('=', 1)[1].replace('${POSTGRES_DB:-', '').replace('}', '')
            
            connection_string = f'postgresql://{user}:{password}@{host}:5432/{db}'
            return STDIOServerConfig(
                name=service_name,
                command='npx',
                args=['-y', '@modelcontextprotocol/server-postgres', connection_string],
                env={}
            )
        elif server_type == 'context7':
            return STDIOServerConfig(
                name=service_name,
                command='npx',
                args=['-y', '@upstash/context7-mcp@latest'],
                env={}
            )
        elif server_type == 'github':
            return STDIOServerConfig(
                name=service_name,
                command='npx',
                args=['-y', '@modelcontextprotocol/server-github'],
                env={'GITHUB_PERSONAL_ACCESS_TOKEN': '${GITHUB_PERSONAL_ACCESS_TOKEN}'}
            )
        elif server_type == 'obsidian':
            return STDIOServerConfig(
                name=service_name,
                command='npx',
                args=['-y', 'obsidian-mcp-server'],
                env={
                    'OBSIDIAN_API_KEY': '${OBSIDIAN_API_KEY}',
                    'OBSIDIAN_URL': '${OBSIDIAN_URL:-http://localhost:27123}'
                }
            )
            
        return None

    def _detect_server_type(self, server_config: ServerConfig) -> Optional[str]:
        """Detect server type from MCP config."""
        if not isinstance(server_config, STDIOServerConfig):
            return None
            
        name = server_config.name.lower()
        
        # Direct name mapping
        if name in self.mcp_to_docker_mapping:
            return name
            
        # Package-based detection
        for arg in server_config.args:
            if 'server-postgres' in str(arg):
                return 'postgresql'
            elif 'context7-mcp' in str(arg):
                return 'context7'
            elif 'server-github' in str(arg):
                return 'github'
            elif 'obsidian-mcp' in str(arg):
                return 'obsidian'
                
        return None

    def _detect_docker_service_type(self, service_name: str, service_config: Dict[str, Any]) -> Optional[str]:
        """Detect Docker service type."""
        name = service_name.lower()
        image = service_config.get('image', '').lower()
        command = service_config.get('command', '').lower()
        
        # Direct name mapping
        if name in self.docker_to_mcp_mapping:
            return self.docker_to_mcp_mapping[name]
            
        # Image-based detection
        if 'postgres' in image:
            return 'postgresql'
        elif 'node' in image:
            if 'context7' in command:
                return 'context7'
            elif 'github' in command:
                return 'github'
            elif 'obsidian' in command:
                return 'obsidian'
                
        return None

    def _load_compose_file(self, compose_file: Path) -> Dict[str, Any]:
        """Load Docker Compose file."""
        if not compose_file.exists():
            return {
                'services': {},
                'networks': {
                    'mcp-network': {
                        'driver': 'bridge',
                        'ipam': {'config': [{'subnet': '10.200.0.0/16'}]}
                    }
                },
                'volumes': {'postgres-data': {}}
            }
            
        try:
            with open(compose_file) as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            console.print(f"[yellow]Warning: Error loading {compose_file}: {e}[/]")
            return {'services': {}}

    def _save_compose_file(self, compose_file: Path, compose_data: Dict[str, Any]):
        """Save Docker Compose file."""
        try:
            with open(compose_file, 'w') as f:
                yaml.dump(compose_data, f, default_flow_style=False, indent=2)
        except Exception as e:
            console.print(f"[red]❌ Error saving compose file: {e}[/]")

    def _deploy_services(self, compose_file: Path, services: List[str] = None):
        """Deploy Docker services."""
        try:
            cmd = ['docker-compose', '-f', str(compose_file), 'up', '-d']
            if services:
                cmd.extend(services)
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            stderr_output = e.stderr if e.stderr else "No error output"
            console.print(f"[red]❌ Error deploying services: {stderr_output}[/]")

    def _restart_mcpm_router(self):
        """Restart MCPM router."""
        try:
            subprocess.run(['mcpm', 'router', 'restart'], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            console.print("[yellow]⚠️  Could not restart MCPM router[/]")

    def _has_profile_changed(self, profile_name: str) -> bool:
        """Check if profile has changed since last sync."""
        current_hash = self._get_profile_hash(profile_name)
        last_hash = self.last_state.get('profiles_hash', '')
        return current_hash != last_hash

    def _has_docker_changed(self, compose_file: Path) -> bool:
        """Check if Docker compose has changed since last sync."""
        if not compose_file.exists():
            return False
            
        current_hash = self._get_file_hash(compose_file)
        last_hash = self.last_state.get('compose_hashes', {}).get(str(compose_file), '')
        return current_hash != last_hash
        
    def _get_profile_hash(self, profile_name: str) -> str:
        """Get hash of profile configuration."""
        profile_servers = self.profile_manager.get_profile(profile_name)
        if not profile_servers:
            return ""
        
        # Create deterministic string representation
        profile_data = []
        for server in profile_servers:
            profile_data.append(f"{server.name}:{server.command}:{':'.join(server.args)}")
        
        import hashlib
        return hashlib.md5("|".join(sorted(profile_data)).encode()).hexdigest()
        
    def _get_file_hash(self, file_path: Path) -> str:
        """Get hash of file contents."""
        if not file_path.exists():
            return ""
        
        import hashlib
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()