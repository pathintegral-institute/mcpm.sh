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

    all_commands = bfs(main)
    for cmd in all_commands:
        result = runner.invoke(cmd, ["--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output

    for cmd in all_commands:
        result = runner.invoke(cmd, ["-h"])
        assert result.exit_code == 0
        assert "Usage:" in result.output
