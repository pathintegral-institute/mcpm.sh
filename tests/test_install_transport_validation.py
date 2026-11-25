"""Invalid registry transport must fail before installation has side effects."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from click.testing import CliRunner
from jsonschema import Draft7Validator


class InstallTransportValidationTests(unittest.TestCase):
    def _invoke(self, method):
        """Exercise the real CLI with only registry and persistence isolated."""
        root = Path(__file__).parents[1]
        spec = importlib.util.spec_from_file_location(
            "install_validation_under_test", root / "src/mcpm/commands/install.py"
        )
        command = importlib.util.module_from_spec(spec)
        with (
            patch("mcpm.global_config.GlobalConfigManager"),
            patch("mcpm.profile.profile_config.ProfileConfigManager"),
            patch("mcpm.utils.repository.RepositoryManager"),
            patch("requests.get", side_effect=AssertionError("Network access is forbidden")),
            tempfile.TemporaryDirectory() as directory,
        ):
            spec.loader.exec_module(command)
            command.repo_manager.get_server_metadata.return_value = {
                "name": "transport-example",
                "installations": {"selected": method},
            }
            command.global_add_server = Mock(return_value=True)
            data_dir = Path(directory) / "data"
            command.get_data_directory = lambda: data_dir
            result = CliRunner().invoke(command.install, ["transport-example", "--force"])
            return result, data_dir.exists(), command.global_add_server.called

    def _validator(self):
        """Validate the real registry installation fragment, not a test copy."""
        path = Path(__file__).parents[1] / "mcp-registry/schema/server-schema.json"
        schema = json.loads(path.read_text())
        return Draft7Validator(schema["properties"]["installations"]["additionalProperties"])

    def test_http_invalid_transport_leaves_no_files(self):
        """A malformed explicit value gets a CLI error without partial state."""
        for transport in ("grpc", None, 7):
            with self.subTest(transport=transport):
                result, files_created, persisted = self._invoke(
                    {"type": "http", "url": "https://example.invalid/mcp", "transport": transport}
                )
                self.assertEqual(result.exit_code, 1)
                self.assertIn("transport", result.output.lower())
                self.assertNotIn("Traceback", result.output)
                self.assertIsInstance(result.exception, SystemExit)
                self.assertFalse(files_created)
                self.assertFalse(persisted)

    def test_non_http_transport_leaves_no_files(self):
        """A command-based method cannot silently discard HTTP transport."""
        result, files_created, persisted = self._invoke(
            {"type": "cli", "command": "example", "args": [], "transport": "sse"}
        )
        self.assertEqual(result.exit_code, 1)
        self.assertIn("transport", result.output.lower())
        self.assertIsInstance(result.exception, SystemExit)
        self.assertFalse(files_created)
        self.assertFalse(persisted)

    def test_legacy_stdio_still_installs(self):
        """A command method without transport retains its existing behavior."""
        result, files_created, persisted = self._invoke({"type": "cli", "command": "example", "args": []})
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertTrue(files_created)
        self.assertTrue(persisted)

    def test_registry_rejects_transport_for_each_non_http_type(self):
        """All six command-based registry types reject HTTP-only metadata."""
        validator = self._validator()
        for kind in ("npm", "python", "docker", "cli", "uvx", "custom"):
            with self.subTest(kind=kind):
                self.assertFalse(
                    validator.is_valid({"type": kind, "command": "example", "args": [], "transport": "sse"})
                )
                self.assertTrue(validator.is_valid({"type": kind, "command": "example", "args": []}))

    def test_registry_http_legacy_and_explicit_values(self):
        """HTTP still accepts omission and both documented transport values."""
        validator = self._validator()
        method = {"type": "http", "url": "https://example.invalid/mcp"}
        self.assertTrue(validator.is_valid(method))
        for transport in ("sse", "streamablehttp"):
            self.assertTrue(validator.is_valid({**method, "transport": transport}))
        for transport in ("grpc", None, 7):
            self.assertFalse(validator.is_valid({**method, "transport": transport}))


if __name__ == "__main__":
    unittest.main()
