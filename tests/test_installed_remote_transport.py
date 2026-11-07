"""Explicit transport survives installation and full configuration conversion."""

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from pydantic import ValidationError

from mcpm.clients.managers.claude_desktop import ClaudeDesktopManager
from mcpm.schemas.full_server_config import FullServerConfig


class InstalledRemoteTransportTests(unittest.TestCase):
    def _install(self, transport):
        """Run the real install callback with registry and persistence isolated."""
        method = {
            "type": "http",
            "url": "https://example.invalid/mcp",
            "recommended": True,
            "headers": {"X-Example": "synthetic-value"},
        }
        if transport is not None:
            method["transport"] = transport
        metadata = {"name": "transport-example", "installations": {"http": method}}
        # Load only this command, avoiding commands/__init__ and unrelated CLIs.
        command_path = Path(__file__).parents[1] / "src/mcpm/commands/install.py"
        spec = importlib.util.spec_from_file_location("install_transport_under_test", command_path)
        command = importlib.util.module_from_spec(spec)
        with (
            patch("mcpm.global_config.GlobalConfigManager"),
            patch("mcpm.profile.profile_config.ProfileConfigManager"),
            patch("mcpm.utils.repository.RepositoryManager"),
            patch("requests.get", side_effect=AssertionError("Network access is forbidden")),
            tempfile.TemporaryDirectory() as directory,
        ):
            spec.loader.exec_module(command)
            command.repo_manager.get_server_metadata.return_value = metadata
            command.global_add_server = Mock(return_value=True)
            command.get_data_directory = lambda: Path(directory) / "metadata"
            command.install.callback("transport-example", force=True)
            remote = command.global_add_server.call_args.args[0]
            saved = type(remote).model_validate(remote.to_dict())
            manager = ClaudeDesktopManager(config_path_override=str(Path(directory) / "desktop.json"))
            return manager.to_client_format(saved), remote.to_dict()

    def test_installer_preserves_streamable_http_and_headers(self):
        """A recommended HTTP method reaches Desktop with explicit transport."""
        config, _ = self._install("streamablehttp")
        self.assertEqual(
            config,
            {
                "command": "uvx",
                "args": [
                    "mcp-proxy",
                    "--transport",
                    "streamablehttp",
                    "https://example.invalid/mcp",
                    "--headers",
                    "X-Example",
                    "synthetic-value",
                ],
            },
        )

    def test_installer_preserves_explicit_sse(self):
        """Explicit SSE remains SSE through the same installation path."""
        config, _ = self._install("sse")
        self.assertEqual(config["args"][1:3], ["--transport", "sse"])

    def test_legacy_installation_keeps_arguments_and_saved_shape(self):
        """An omitted transport preserves the previous arguments and fields."""
        config, saved = self._install(None)
        self.assertEqual(
            config["args"],
            ["mcp-proxy", "https://example.invalid/mcp", "--headers", "X-Example", "synthetic-value"],
        )
        self.assertNotIn("transport", saved)

    def test_installer_rejects_unknown_transport(self):
        """An invalid explicit value is rejected rather than silently dropped."""
        with self.assertRaises(ValidationError):
            self._install("grpc")

    def test_full_config_round_trip_preserves_transport(self):
        """Full configuration serialization retains the explicit selection."""
        config = FullServerConfig(
            name="docs", installation="http", url="https://example.invalid/mcp", transport="streamablehttp"
        )
        restored = FullServerConfig.model_validate(config.to_dict())
        self.assertEqual(restored.to_server_config().to_mcp_proxy_stdio().args[1:3], ["--transport", "streamablehttp"])

    def test_full_config_keeps_legacy_stdio(self):
        """Adding HTTP transport does not change a command-based server."""
        config = FullServerConfig(name="local", command="example", args=["stdio"])
        self.assertEqual(config.to_server_config().args, ["stdio"])
        self.assertNotIn("transport", config.to_dict())


if __name__ == "__main__":
    unittest.main()
