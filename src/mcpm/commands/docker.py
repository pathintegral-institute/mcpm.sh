"""
Docker integration commands for MCPM.

This module provides Docker orchestration capabilities, allowing MCPM to manage
Docker Compose services alongside MCP server profiles with bidirectional sync.
"""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

import click
import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from mcpm.core.schema import ServerConfig, STDIOServerConfig
from mcpm.profile.profile_config import ProfileConfigManager

console = Console()


class DockerIntegration:
    """Manages Docker integration for MCPM profiles."""
    
    def __init__(self, compose_file: str = "docker-compose.yml"):
        self.compose_file = Path(compose_file)
        self.profile_manager = ProfileConfigManager()
        
        # Server-to-Docker service mappings
        self.server_mappings = {
            'postgresql': {
                'image': 'postgres:16-alpine',
                'environment': [
                    'POSTGRES_USER=${POSTGRES_USER}',
                    'POSTGRES_PASSWORD=${POSTGRES_PASSWORD}',
                    'POSTGRES_DB=${POSTGRES_DB:-mcpdb}'
                ],
                'ports': ['5432:5432'],
                'volumes': [
                    'postgres-data:/var/lib/postgresql/data'
                ],
                'networks': ['mcp-network'],
                'healthcheck': {
                    'test': ['CMD-SHELL', 'pg_isready -U ${POSTGRES_USER}'],
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
        
        # Standard Docker Compose structure
        self.standard_networks = {
            'mcp-network': {
                'driver': 'bridge',
                'ipam': {
                    'config': [{'subnet': '10.200.0.0/16'}]
                }
            }
        }
        
        self.standard_volumes = {
            'postgres-data': {}
        }
        
        # Required environment variables for security
        self.required_env_vars = {
            'postgresql': ['POSTGRES_USER', 'POSTGRES_PASSWORD'],
            'github': ['GITHUB_PERSONAL_ACCESS_TOKEN'],
            'obsidian': ['OBSIDIAN_API_KEY']
        }

    def detect_server_type(self, server_config: ServerConfig) -> Optional[str]:
        """Detect Docker service type from MCP server configuration."""
        if not isinstance(server_config, STDIOServerConfig):
            return None
            
        name = server_config.name.lower()
        
        # Direct name mapping
        if name in self.server_mappings:
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

    def validate_environment_variables(self, server_type: str) -> List[str]:
        """Validate required environment variables for server type."""
        missing_vars = []
        required_vars = self.required_env_vars.get(server_type, [])
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
                
        return missing_vars

    def generate_docker_service(self, server_config: ServerConfig) -> Optional[Dict[str, Any]]:
        """Generate Docker service definition from MCP server config."""
        server_type = self.detect_server_type(server_config)
        if not server_type or server_type not in self.server_mappings:
            return None
            
        template = self.server_mappings[server_type].copy()
        
        # Generate container name
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

    def sync_profile_to_docker(self, profile_name: str) -> bool:
        """Sync MCPM profile to Docker Compose."""
        profile_servers = self.profile_manager.get_profile(profile_name)
        if not profile_servers:
            console.print(f"[bold red]Error:[/] Profile '{profile_name}' not found.")
            return False
            
        # Load or create compose structure
        compose_data = self.load_compose_file()
        
        # Generate services
        services_added = []
        warnings = []
        for server_config in profile_servers:
            server_type = self.detect_server_type(server_config)
            if server_type:
                # Validate environment variables
                missing_vars = self.validate_environment_variables(server_type)
                if missing_vars:
                    warnings.append(f"{server_config.name}: Missing environment variables: {', '.join(missing_vars)}")
                
            docker_service = self.generate_docker_service(server_config)
            if docker_service:
                service_name = server_config.name
                compose_data['services'][service_name] = docker_service
                services_added.append(service_name)
                
        # Show warnings for missing environment variables
        for warning in warnings:
            console.print(f"[yellow]⚠️  {warning}[/]")
            
        if services_added:
            self.save_compose_file(compose_data)
            console.print(f"[green]✅ Added services:[/] {', '.join(services_added)}")
            if warnings:
                console.print("[yellow]💡 Set missing environment variables before deployment[/]")
            return True
        else:
            console.print("[yellow]No compatible services found in profile.[/]")
            return False

    def load_compose_file(self) -> Dict[str, Any]:
        """Load existing Docker Compose file or create base structure."""
        if not self.compose_file.exists():
            return {
                'services': {},
                'networks': self.standard_networks,
                'volumes': self.standard_volumes
            }
            
        try:
            with open(self.compose_file) as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            console.print(f"[yellow]Warning: Error loading {self.compose_file}: {e}[/]")
            return {
                'services': {},
                'networks': self.standard_networks, 
                'volumes': self.standard_volumes
            }

    def save_compose_file(self, compose_data: Dict[str, Any]):
        """Save Docker Compose file."""
        try:
            with open(self.compose_file, 'w') as f:
                yaml.dump(compose_data, f, default_flow_style=False, indent=2)
            console.print(f"[green]✅ Saved Docker Compose:[/] {self.compose_file}")
        except Exception as e:
            console.print(f"[bold red]Error saving compose file: {e}[/]")

    def get_docker_status(self) -> Dict[str, Any]:
        """Get status of Docker services."""
        try:
            result = subprocess.run(
                ['docker-compose', '-f', str(self.compose_file), 'ps', '--format', 'json'],
                capture_output=True,
                text=True,
                check=True
            )
            
            services = []
            if result.stdout.strip():
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        try:
                            services.append(json.loads(line))
                        except json.JSONDecodeError:
                            console.print(f"[yellow]⚠️  Failed to parse JSON line: {line}[/]")
                            continue
                        
            return {'status': 'success', 'services': services}
        except subprocess.CalledProcessError as e:
            return {'status': 'error', 'message': str(e)}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def deploy_services(self, services: List[str] = None) -> bool:
        """Deploy Docker services."""
        try:
            cmd = ['docker-compose', '-f', str(self.compose_file), 'up', '-d']
            if services:
                cmd.extend(services)
                
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            console.print("[green]✅ Services deployed successfully[/]")
            return True
        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]Error deploying services: {e.stderr}[/]")
            return False
        except Exception as e:
            console.print(f"[bold red]Error deploying services: {e}[/]")
            return False


@click.group()
@click.help_option("-h", "--help")
def docker():
    """Docker integration commands for MCPM.
    
    Example:
    
    \b
        mcpm docker sync my-profile
        mcpm docker status
        mcpm docker deploy postgresql
    """
    pass


@docker.command()
@click.argument('profile_name')
@click.option('--compose-file', '-f', default='docker-compose.yml', 
              help='Docker Compose file to generate/update')
@click.option('--deploy', is_flag=True, help='Deploy services after sync')
def sync(profile_name: str, compose_file: str, deploy: bool):
    """Sync MCPM profile to Docker Compose services."""
    console.print(f"[bold cyan]🔄 Syncing profile '{profile_name}' to Docker...[/]")
    
    integration = DockerIntegration(compose_file)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Syncing profile to Docker...", total=None)
        
        success = integration.sync_profile_to_docker(profile_name)
        
        if success and deploy:
            progress.update(task, description="Deploying services...")
            integration.deploy_services()
            
        progress.stop()
    
    if success:
        console.print(f"[green]🎉 Profile '{profile_name}' synced successfully![/]")
    else:
        console.print(f"[bold red]❌ Failed to sync profile '{profile_name}'[/]")


@docker.command()
@click.option('--compose-file', '-f', default='docker-compose.yml',
              help='Docker Compose file to check')
def status(compose_file: str):
    """Show Docker integration status."""
    console.print("[bold cyan]🐳 Docker Integration Status[/]")
    console.print("=" * 50)
    
    integration = DockerIntegration(compose_file)
    
    # Check if compose file exists
    if not integration.compose_file.exists():
        console.print(f"[bold red]❌ Compose file not found:[/] {compose_file}")
        return
        
    # Get Docker status
    docker_status = integration.get_docker_status()
    
    if docker_status['status'] == 'success':
        services = docker_status['services']
        
        console.print(f"\n[bold green]📦 Services ({len(services)} found):[/]")
        
        if services:
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Service", style="cyan")
            table.add_column("State", style="green")
            table.add_column("Ports", style="yellow")
            
            for service in services:
                name = service.get('Name', 'Unknown')
                state = service.get('State', 'Unknown')
                ports = service.get('Ports', '')
                
                state_color = "green" if state == "running" else "red"
                table.add_row(name, f"[{state_color}]{state}[/]", ports)
                
            console.print(table)
        else:
            console.print("  [yellow]No services running[/]")
    else:
        console.print(f"[bold red]❌ Error checking Docker status:[/] {docker_status.get('message', 'Unknown error')}")


@docker.command()
@click.option('--compose-file', '-f', default='docker-compose.yml',
              help='Docker Compose file to deploy')
@click.argument('services', nargs=-1)
def deploy(compose_file: str, services: tuple):
    """Deploy Docker services."""
    integration = DockerIntegration(compose_file)
    
    if services:
        console.print(f"[bold cyan]🚀 Deploying services:[/] {', '.join(services)}")
    else:
        console.print("[bold cyan]🚀 Deploying all services...[/]")
    
    success = integration.deploy_services(list(services) if services else None)
    
    if success:
        console.print("[green]🎉 Deployment completed![/]")
    else:
        console.print("[bold red]❌ Deployment failed![/]")


@docker.command()
@click.argument('profile_name')
@click.option('--compose-file', '-f', default='docker-compose.yml',
              help='Docker Compose file to generate')
def generate(profile_name: str, compose_file: str):
    """Generate Docker Compose file from MCPM profile."""
    console.print(f"[bold cyan]📝 Generating Docker Compose from profile '{profile_name}'...[/]")
    
    integration = DockerIntegration(compose_file)
    success = integration.sync_profile_to_docker(profile_name)
    
    if success:
        console.print(f"[green]✅ Generated:[/] {compose_file}")
    else:
        console.print("[bold red]❌ Generation failed![/]")


if __name__ == "__main__":
    docker()