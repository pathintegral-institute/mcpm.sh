"""
Tests for Docker integration functionality.
"""

import json
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from mcpm.commands.docker import DockerIntegration
from mcpm.commands.target_operations.docker_sync import DockerSyncOperations
from mcpm.core.schema import STDIOServerConfig


class TestDockerIntegration:
    """Test Docker integration functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.compose_file = self.temp_dir / "docker-compose.yml"
        self.integration = DockerIntegration(str(self.compose_file))
        
    def test_detect_server_type_postgresql(self):
        """Test PostgreSQL server type detection."""
        server = STDIOServerConfig(
            name="postgresql",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-postgres", "postgresql://..."],
            env={}
        )
        
        server_type = self.integration.detect_server_type(server)
        assert server_type == "postgresql"
        
    def test_detect_server_type_context7(self):
        """Test Context7 server type detection."""
        server = STDIOServerConfig(
            name="context7",
            command="npx",
            args=["-y", "@upstash/context7-mcp@latest"],
            env={}
        )
        
        server_type = self.integration.detect_server_type(server)
        assert server_type == "context7"
        
    def test_detect_server_type_github(self):
        """Test GitHub server type detection.""" 
        server = STDIOServerConfig(
            name="github",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_PERSONAL_ACCESS_TOKEN": "token"}
        )
        
        server_type = self.integration.detect_server_type(server)
        assert server_type == "github"
        
    def test_generate_docker_service_postgresql(self):
        """Test Docker service generation for PostgreSQL."""
        server = STDIOServerConfig(
            name="postgresql",
            command="npx", 
            args=["-y", "@modelcontextprotocol/server-postgres"],
            env={}
        )
        
        docker_service = self.integration.generate_docker_service(server)
        
        assert docker_service is not None
        assert docker_service["image"] == "postgres:16-alpine"
        assert docker_service["container_name"] == "mcp-postgresql"
        assert docker_service["restart"] == "unless-stopped"
        assert "5432:5432" in docker_service["ports"]
        assert "mcp-network" in docker_service["networks"]
        
    def test_generate_docker_service_context7(self):
        """Test Docker service generation for Context7."""
        server = STDIOServerConfig(
            name="context7",
            command="npx",
            args=["-y", "@upstash/context7-mcp@latest"],
            env={}
        )
        
        docker_service = self.integration.generate_docker_service(server)
        
        assert docker_service is not None
        assert docker_service["image"] == "node:20-alpine"
        assert docker_service["container_name"] == "mcp-context7"
        assert docker_service["working_dir"] == "/app"
        assert "3000:3000" in docker_service["ports"]
        
    def test_load_compose_file_not_exists(self):
        """Test loading non-existent compose file creates base structure."""
        compose_data = self.integration.load_compose_file()
        
        assert "services" in compose_data
        assert "networks" in compose_data
        assert "volumes" in compose_data
        assert "mcp-network" in compose_data["networks"]
        assert "postgres-data" in compose_data["volumes"]
        
    def test_save_compose_file(self):
        """Test saving Docker Compose file."""
        compose_data = {
            "services": {
                "test": {
                    "image": "test:latest"
                }
            },
            "networks": self.integration.standard_networks,
            "volumes": self.integration.standard_volumes
        }
        
        self.integration.save_compose_file(compose_data)
        
        assert self.compose_file.exists()
        
        # Verify content
        import yaml
        with open(self.compose_file) as f:
            loaded_data = yaml.safe_load(f)
            
        assert "services" in loaded_data
        assert "test" in loaded_data["services"]
        assert loaded_data["services"]["test"]["image"] == "test:latest"
        
    @patch('mcpm.commands.docker.subprocess.run')
    def test_get_docker_status_success(self, mock_run):
        """Test successful Docker status retrieval."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"Name": "test", "State": "running", "Ports": "3000:3000"}\n'
        )
        
        status = self.integration.get_docker_status()
        
        assert status["status"] == "success"
        assert len(status["services"]) == 1
        assert status["services"][0]["Name"] == "test"
        
    @patch('mcpm.commands.docker.subprocess.run')
    def test_get_docker_status_error(self, mock_run):
        """Test Docker status error handling."""
        mock_run.side_effect = Exception("Docker not available")
        
        status = self.integration.get_docker_status()
        
        assert status["status"] == "error"
        assert "Docker not available" in status["message"]
        
    @patch('mcpm.commands.docker.subprocess.run')
    def test_deploy_services_success(self, mock_run):
        """Test successful service deployment."""
        mock_run.return_value = MagicMock(returncode=0)
        
        result = self.integration.deploy_services(["postgresql", "context7"])
        
        assert result is True
        mock_run.assert_called_once()
        
    @patch('mcpm.commands.docker.subprocess.run')
    def test_deploy_services_error(self, mock_run):
        """Test service deployment error handling."""
        mock_run.side_effect = Exception("Deployment failed")
        
        result = self.integration.deploy_services()
        
        assert result is False


class TestDockerSyncOperations:
    """Test Docker synchronization operations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.compose_file = self.temp_dir / "docker-compose.yml"
        self.sync_ops = DockerSyncOperations()
        
    def test_detect_server_type_postgresql(self):
        """Test PostgreSQL server type detection."""
        server = STDIOServerConfig(
            name="postgresql",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-postgres"],
            env={}
        )
        
        server_type = self.sync_ops._detect_server_type(server)
        assert server_type == "postgresql"
        
    def test_detect_docker_service_type_postgresql(self):
        """Test PostgreSQL Docker service type detection."""
        service_config = {
            "image": "postgres:16-alpine",
            "environment": ["POSTGRES_USER=test"],
            "ports": ["5432:5432"]
        }
        
        service_type = self.sync_ops._detect_docker_service_type("postgresql", service_config)
        assert service_type == "postgresql"
        
    def test_detect_docker_service_type_context7(self):
        """Test Context7 Docker service type detection."""
        service_config = {
            "image": "node:20-alpine",
            "command": "sh -c \"npm install -g @upstash/context7-mcp@latest && npx @upstash/context7-mcp@latest\"",
            "ports": ["3000:3000"]
        }
        
        service_type = self.sync_ops._detect_docker_service_type("context7", service_config)
        assert service_type == "context7"
        
    def test_generate_docker_service_postgresql(self):
        """Test Docker service generation for PostgreSQL."""
        server = STDIOServerConfig(
            name="postgresql",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-postgres"],
            env={}
        )
        
        docker_service = self.sync_ops._generate_docker_service(server)
        
        assert docker_service is not None
        assert docker_service["image"] == "postgres:16-alpine"
        assert docker_service["container_name"] == "mcp-postgresql"
        assert "5432:5432" in docker_service["ports"]
        
    def test_generate_mcp_server_postgresql(self):
        """Test MCP server generation from PostgreSQL Docker service."""
        service_config = {
            "image": "postgres:16-alpine",
            "environment": ["POSTGRES_USER=test"],
            "ports": ["5432:5432"]
        }
        
        mcp_server = self.sync_ops._generate_mcp_server("postgresql", service_config)
        
        assert mcp_server is not None
        assert mcp_server.name == "postgresql"
        assert mcp_server.command == "npx"
        assert "@modelcontextprotocol/server-postgres" in mcp_server.args
        
    def test_generate_mcp_server_context7(self):
        """Test MCP server generation from Context7 Docker service."""
        service_config = {
            "image": "node:20-alpine",
            "command": "sh -c \"npm install -g @upstash/context7-mcp@latest && npx @upstash/context7-mcp@latest\"",
            "ports": ["3000:3000"]
        }
        
        mcp_server = self.sync_ops._generate_mcp_server("context7", service_config)
        
        assert mcp_server is not None
        assert mcp_server.name == "context7"
        assert mcp_server.command == "npx"
        assert "@upstash/context7-mcp@latest" in mcp_server.args
        
    def test_load_compose_file_creates_base_structure(self):
        """Test loading compose file creates base structure when file doesn't exist."""
        compose_data = self.sync_ops._load_compose_file(self.compose_file)
        
        assert "services" in compose_data
        assert "networks" in compose_data
        assert "volumes" in compose_data
        assert "mcp-network" in compose_data["networks"]
        
    def test_save_compose_file(self):
        """Test saving compose file."""
        compose_data = {
            "services": {"test": {"image": "test:latest"}},
            "networks": {"mcp-network": {"driver": "bridge"}},
            "volumes": {"postgres-data": {}}
        }
        
        self.sync_ops._save_compose_file(self.compose_file, compose_data)
        
        assert self.compose_file.exists()
        
        # Verify content
        import yaml
        with open(self.compose_file) as f:
            loaded_data = yaml.safe_load(f)
            
        assert loaded_data["services"]["test"]["image"] == "test:latest"


@pytest.fixture
def sample_profile_servers():
    """Sample servers for testing."""
    return [
        STDIOServerConfig(
            name="postgresql",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-postgres", "postgresql://..."],
            env={}
        ),
        STDIOServerConfig(
            name="context7",
            command="npx", 
            args=["-y", "@upstash/context7-mcp@latest"],
            env={}
        )
    ]


@pytest.fixture
def sample_docker_compose():
    """Sample Docker Compose data for testing."""
    return {
        "services": {
            "postgresql": {
                "image": "postgres:16-alpine",
                "environment": ["POSTGRES_USER=test"],
                "ports": ["5432:5432"],
                "networks": ["mcp-network"]
            },
            "context7": {
                "image": "node:20-alpine",
                "command": "sh -c \"npm install -g @upstash/context7-mcp@latest && npx @upstash/context7-mcp@latest\"",
                "ports": ["3000:3000"],
                "networks": ["mcp-network"]
            }
        },
        "networks": {
            "mcp-network": {
                "driver": "bridge",
                "ipam": {"config": [{"subnet": "10.200.0.0/16"}]}
            }
        },
        "volumes": {
            "postgres-data": {}
        }
    }


class TestSecurityAndValidation:
    """Test security and validation features."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.compose_file = self.temp_dir / "docker-compose.yml"
        self.integration = DockerIntegration(str(self.compose_file))
        
    @patch.dict(os.environ, {}, clear=True)
    def test_validate_environment_variables_missing(self):
        """Test validation when environment variables are missing."""
        missing_vars = self.integration.validate_environment_variables('postgresql')
        
        assert 'POSTGRES_USER' in missing_vars
        assert 'POSTGRES_PASSWORD' in missing_vars
        
    @patch.dict(os.environ, {'POSTGRES_USER': 'test', 'POSTGRES_PASSWORD': 'secret'})
    def test_validate_environment_variables_present(self):
        """Test validation when environment variables are present."""
        missing_vars = self.integration.validate_environment_variables('postgresql')
        
        assert len(missing_vars) == 0
        
    def test_validate_environment_variables_unknown_server(self):
        """Test validation for unknown server type."""
        missing_vars = self.integration.validate_environment_variables('unknown')
        
        assert len(missing_vars) == 0  # No requirements for unknown servers


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def setup_method(self):
        """Set up test fixtures.""" 
        self.temp_dir = Path(tempfile.mkdtemp())
        self.compose_file = self.temp_dir / "docker-compose.yml"
        self.integration = DockerIntegration(str(self.compose_file))
        
    @patch('mcpm.commands.docker.subprocess.run')
    def test_get_docker_status_malformed_json(self, mock_run):
        """Test JSON parsing error handling."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"valid": "json"}\n{invalid json\n{"another": "valid"}\n'
        )
        
        with patch('mcpm.commands.docker.console') as mock_console:
            status = self.integration.get_docker_status()
            
            assert status["status"] == "success"
            assert len(status["services"]) == 2  # Only valid JSON entries
            mock_console.print.assert_called_once()  # Warning printed for malformed JSON


class TestChangeDetection:
    """Test change detection functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.compose_file = self.temp_dir / "docker-compose.yml"
        self.sync_ops = DockerSyncOperations()
        
    def test_get_file_hash_existing_file(self):
        """Test file hash calculation for existing file."""
        test_content = "test content"
        with open(self.compose_file, 'w') as f:
            f.write(test_content)
            
        hash1 = self.sync_ops._get_file_hash(self.compose_file)
        hash2 = self.sync_ops._get_file_hash(self.compose_file)
        
        assert hash1 == hash2  # Same content = same hash
        assert len(hash1) == 32  # MD5 hash length
        
    def test_get_file_hash_nonexistent_file(self):
        """Test file hash calculation for non-existent file."""
        nonexistent_file = self.temp_dir / "nonexistent.yml"
        
        hash_result = self.sync_ops._get_file_hash(nonexistent_file)
        
        assert hash_result == ""
        
    @patch('mcpm.commands.target_operations.docker_sync.ProfileConfigManager')
    def test_get_profile_hash(self, mock_profile_manager):
        """Test profile hash calculation."""
        mock_servers = [
            STDIOServerConfig(name="server1", command="cmd1", args=["arg1"], env={}),
            STDIOServerConfig(name="server2", command="cmd2", args=["arg2"], env={})
        ]
        mock_profile_manager.return_value.get_profile.return_value = mock_servers
        
        sync_ops = DockerSyncOperations()
        sync_ops.profile_manager = mock_profile_manager.return_value
        
        hash1 = sync_ops._get_profile_hash("test-profile")
        hash2 = sync_ops._get_profile_hash("test-profile")
        
        assert hash1 == hash2  # Same profile = same hash
        assert len(hash1) == 32  # MD5 hash length


class TestIntegrationWorkflows:
    """Test end-to-end integration workflows."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.compose_file = self.temp_dir / "docker-compose.yml"
        
    @patch('mcpm.commands.target_operations.docker_sync.ProfileConfigManager')
    def test_sync_profile_to_docker_workflow(self, mock_profile_manager, sample_profile_servers):
        """Test complete profile to Docker sync workflow."""
        # Mock profile manager
        mock_profile_manager.return_value.get_profile.return_value = sample_profile_servers
        
        sync_ops = DockerSyncOperations()
        sync_ops.profile_manager = mock_profile_manager.return_value
        
        # Test sync
        result = sync_ops.sync_profile_to_docker("test-profile", self.compose_file)
        
        assert result is True
        assert self.compose_file.exists()
        
        # Verify generated content
        import yaml
        with open(self.compose_file) as f:
            compose_data = yaml.safe_load(f)
            
        assert "postgresql" in compose_data["services"]
        assert "context7" in compose_data["services"]
        assert compose_data["services"]["postgresql"]["image"] == "postgres:16-alpine"
        assert compose_data["services"]["context7"]["image"] == "node:20-alpine"
        
    @patch('mcpm.commands.target_operations.docker_sync.ProfileConfigManager')
    def test_sync_docker_to_profile_workflow(self, mock_profile_manager, sample_docker_compose):
        """Test complete Docker to profile sync workflow."""
        # Create compose file
        import yaml
        with open(self.compose_file, 'w') as f:
            yaml.dump(sample_docker_compose, f)
            
        # Mock profile manager
        mock_profile_manager.return_value.set_profile.return_value = True
        
        sync_ops = DockerSyncOperations()
        sync_ops.profile_manager = mock_profile_manager.return_value
        
        # Test sync
        result = sync_ops.sync_docker_to_profile(self.compose_file, "test-profile")
        
        assert result is True
        
        # Verify profile manager was called to add servers
        assert mock_profile_manager.return_value.set_profile.call_count >= 2  # At least postgresql and context7


if __name__ == "__main__":
    pytest.main([__file__])