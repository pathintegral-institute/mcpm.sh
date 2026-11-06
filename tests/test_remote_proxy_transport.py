"""Remote transport survives conversion into a stdio-only client configuration."""

import json
import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from mcpm.clients.managers.claude_desktop import ClaudeDesktopManager
from mcpm.core.schema import RemoteServerConfig


class RemoteProxyTransportTests(unittest.TestCase):
    def test_legacy_config_keeps_existing_proxy_arguments(self):
        """Omitted transport keeps the legacy proxy arguments and serialized shape."""
        remote = RemoteServerConfig(name="legacy", url="https://example.invalid/mcp")
        self.assertEqual(remote.to_mcp_proxy_stdio().args, ["mcp-proxy", remote.url])
        self.assertNotIn("transport", remote.to_dict())

    def test_explicit_sse_is_preserved(self):
        """An explicit SSE selection reaches the proxy command."""
        remote = RemoteServerConfig(name="events", url="https://example.invalid/events", transport="sse")
        self.assertEqual(remote.to_mcp_proxy_stdio().args, ["mcp-proxy", "--transport", "sse", remote.url])

    def test_http_transport_survives_parse_serialize_and_desktop_export(self):
        """Parsing and serialization retain HTTP transport in Desktop export."""
        with tempfile.TemporaryDirectory() as directory:
            manager = ClaudeDesktopManager(config_path_override=str(Path(directory) / "client.json"))
            remote = manager.from_client_format(
                "docs", {"url": "https://example.invalid/events", "transport": "streamablehttp"}
            )
            self.assertIsInstance(remote, RemoteServerConfig)
            restored = RemoteServerConfig.model_validate(remote.to_dict())
            self.assertEqual(
                manager.to_client_format(restored),
                {
                    "command": "uvx",
                    "args": ["mcp-proxy", "--transport", "streamablehttp", remote.url],
                },
            )

    def test_desktop_writes_transport_into_task_local_config(self):
        """Desktop configuration write and readback preserve HTTP transport."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "client.json"
            manager = ClaudeDesktopManager(config_path_override=str(path))
            remote = RemoteServerConfig(name="docs", url="https://example.invalid/mcp", transport="streamablehttp")
            self.assertTrue(manager.add_server(remote))
            saved = json.loads(path.read_text())["mcpServers"]["docs"]
            self.assertEqual(saved["args"], ["mcp-proxy", "--transport", "streamablehttp", remote.url])
            self.assertEqual(manager.get_server("docs").args, saved["args"])

    def test_transport_does_not_discard_headers(self):
        """Selecting transport retains the existing proxy header arguments."""
        remote = RemoteServerConfig(
            name="docs",
            url="https://example.invalid/mcp",
            headers={"X-Example": "synthetic-value"},
            transport="streamablehttp",
        )
        self.assertEqual(
            remote.to_mcp_proxy_stdio().args,
            ["mcp-proxy", "--transport", "streamablehttp", remote.url, "--headers", "X-Example", "synthetic-value"],
        )

    def test_unknown_transport_is_rejected(self):
        """Validation rejects transport values outside the supported vocabulary."""
        with self.assertRaises(ValidationError):
            RemoteServerConfig(name="invalid", url="https://example.invalid/mcp", transport="grpc")


if __name__ == "__main__":
    unittest.main()
