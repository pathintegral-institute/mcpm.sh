"""Tests for the `mcpm doctor` command — both default Rich output and `--json`."""

import json
from unittest.mock import patch

from click.testing import CliRunner

from mcpm.commands.doctor import (
    _check_cli_tool_status,
    _collect_findings,
    doctor,
)


class TestCollectFindings:
    """The structured findings dict is the public contract for `--json`.

    These tests pin the keys / shape so adding a new check (non-breaking)
    or removing one (breaking) is caught at test time. Implementation
    details of individual checks are mocked in test_render_json to keep
    these tests fast and deterministic.
    """

    def test_findings_has_all_section_keys(self):
        findings = _collect_findings()
        assert set(findings.keys()) == {
            "mcpm",
            "python",
            "node",
            "config",
            "cache",
            "clients",
            "profiles",
            "summary",
        }

    def test_summary_rolls_up_issues_found(self):
        findings = _collect_findings()
        # `summary.issues_found` equals the sum of every section's
        # `issues` field (excluding the summary itself, which doesn't have
        # an `issues` field). Pre-PR behavior matched this — mirrored here.
        per_section_total = sum(
            int(section.get("issues", 0)) for key, section in findings.items() if key != "summary"
        )
        assert findings["summary"]["issues_found"] == per_section_total

    def test_summary_all_healthy_matches_zero_issues(self):
        findings = _collect_findings()
        assert findings["summary"]["all_healthy"] == (findings["summary"]["issues_found"] == 0)

    def test_python_section_always_succeeds(self):
        # Python is always available — the test is running in Python — so
        # `python.issues` should always be 0. Pins the invariant the
        # `_check_python()` helper documents.
        findings = _collect_findings()
        assert findings["python"]["issues"] == 0
        assert isinstance(findings["python"]["version"], str)
        assert isinstance(findings["python"]["executable"], str)


class TestCheckCliToolStatus:
    """Lower-level helper used by `_check_node()`. Pins the failure shapes
    so the JSON contract for the `node` / `npm` sub-objects stays stable."""

    def test_returns_not_found_when_tool_missing(self):
        with patch("mcpm.commands.doctor.shutil.which", return_value=None):
            version, error, issues = _check_cli_tool_status("nonexistent-binary-12345")
        assert version is None
        assert error == "not_found"
        assert issues == 1

    def test_returns_version_when_tool_succeeds(self):
        with patch("mcpm.commands.doctor.shutil.which", return_value="/usr/bin/fake-tool"):
            with patch(
                "mcpm.commands.doctor.subprocess.check_output",
                return_value=b"fake-tool 1.2.3\n",
            ):
                version, error, issues = _check_cli_tool_status("fake-tool")
        assert version == "fake-tool 1.2.3"
        assert error is None
        assert issues == 0

    def test_returns_version_check_failed_on_subprocess_error(self):
        import subprocess

        with patch("mcpm.commands.doctor.shutil.which", return_value="/usr/bin/fake-tool"):
            with patch(
                "mcpm.commands.doctor.subprocess.check_output",
                side_effect=subprocess.CalledProcessError(1, "fake-tool"),
            ):
                version, error, issues = _check_cli_tool_status("fake-tool")
        assert version is None
        assert error == "version_check_failed"
        assert issues == 1


class TestDoctorJsonOutput:
    """End-to-end tests of the `--json` flag emitting valid JSON to stdout."""

    def test_json_output_is_valid_json(self):
        runner = CliRunner()
        result = runner.invoke(doctor, ["--json"])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        # Sanity: top-level keys present.
        assert "summary" in parsed
        assert "issues_found" in parsed["summary"]
        assert "all_healthy" in parsed["summary"]

    def test_json_output_does_not_emit_rich_text(self):
        # The Rich output uses `console.print` which goes to stderr in
        # CliRunner. The `--json` path skips _render_text entirely, so
        # stdout should contain ONLY the JSON payload — no banner emoji,
        # no section headers.
        runner = CliRunner()
        result = runner.invoke(doctor, ["--json"])
        assert result.exit_code == 0
        # No Rich headers should leak into the JSON output.
        assert "📦 MCPM Installation" not in result.output
        assert "🩺 MCPM System Health Check" not in result.output
        # Output should be parseable as JSON without trailing prose.
        parsed = json.loads(result.output)
        assert isinstance(parsed, dict)

    def test_json_includes_all_check_section_keys(self):
        runner = CliRunner()
        result = runner.invoke(doctor, ["--json"])
        parsed = json.loads(result.output)
        # The full contract — every section the rendered text output
        # surfaces is also surfaced in the JSON.
        for key in ("mcpm", "python", "node", "config", "cache", "clients", "profiles", "summary"):
            assert key in parsed, f"--json output missing top-level key {key}"

    def test_json_summary_is_well_typed(self):
        runner = CliRunner()
        result = runner.invoke(doctor, ["--json"])
        parsed = json.loads(result.output)
        assert isinstance(parsed["summary"]["issues_found"], int)
        assert isinstance(parsed["summary"]["all_healthy"], bool)


class TestDoctorTextOutput:
    """The default (no `--json`) path still emits the same Rich-formatted
    output as before this change. This is the back-compat guarantee."""

    def test_text_output_includes_known_banner(self):
        runner = CliRunner()
        result = runner.invoke(doctor)
        assert result.exit_code == 0
        # Banner emoji from the original implementation stays in place.
        # Rich strips terminal colors when the output is captured by
        # CliRunner so the test asserts on plain-text fragments only.
        assert "MCPM System Health Check" in result.output

    def test_text_output_does_not_emit_json(self):
        runner = CliRunner()
        result = runner.invoke(doctor)
        # Without `--json`, the output is human-readable text; it should
        # NOT be parseable as JSON (would imply the JSON path leaked).
        try:
            json.loads(result.output)
            json_parsed = True
        except json.JSONDecodeError:
            json_parsed = False
        assert not json_parsed
