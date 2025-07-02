from collections import deque

from click import Group
from click.testing import CliRunner

from mcpm.cli import main


def test_cli_help():
    """Test that all commands have help options."""
    runner = CliRunner()

    def bfs(cmd):
        queue = deque([cmd])
        commands = []
        while queue:
            cmd = queue.popleft()
            sub_cmds = cmd.commands.values()
            for sub_cmd in sub_cmds:
                commands.append(sub_cmd)
                if isinstance(sub_cmd, Group):
                    queue.append(sub_cmd)
        return commands

    # List of deprecated commands that should fail
    deprecated_commands = {"stash", "pop", "mv", "cp", "target"}

    all_commands = bfs(main)
    for cmd in all_commands:
        result = runner.invoke(cmd, ["--help"])
        if cmd.name in deprecated_commands:
            # Deprecated commands should fail
            assert result.exit_code == 1
            assert "removed in MCPM v2.0" in result.output
        else:
            assert result.exit_code == 0
            assert "Usage:" in result.output

    for cmd in all_commands:
        result = runner.invoke(cmd, ["-h"])
        if cmd.name in deprecated_commands:
            # Deprecated commands should fail with -h too
            assert result.exit_code == 1
            assert "removed in MCPM v2.0" in result.output
        else:
            assert result.exit_code == 0
            assert "Usage:" in result.output
