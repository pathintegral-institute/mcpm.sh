from scripts.utils import validate_arguments_in_installation


def test_arguments_in_installations():
    """
    Test validate_arguments_in_installation
    """

    # case 1: docker command with -e parameters
    installation1 = {
        "type": "docker",
        "command": "docker",
        "args": ["run", "-e", "API_KEY=value", "-e", "DB_PASSWORD=secret"],
        "env": {"API_KEY": "value", "DB_PASSWORD": "secret"},
    }
    arguments1 = {"API_KEY": "value", "DB_PASSWORD": "secret"}
    result1, replaced1 = validate_arguments_in_installation(installation1, arguments1)
    assert replaced1 is True
    assert result1["args"] == ["run", "-e", "API_KEY=${API_KEY}", "-e", "DB_PASSWORD=${DB_PASSWORD}"]
    assert result1["env"] == {"API_KEY": "${API_KEY}", "DB_PASSWORD": "${DB_PASSWORD}"}

    # case 2: docker command with --env parameters
    installation2 = {
        "type": "docker",
        "command": "docker",
        "args": ["run", "--env", "TOKEN=abc123", "--env", "URL"],
        "env": {"TOKEN": "abc123", "URL": "example.com"},
    }
    arguments2 = {"TOKEN": "abc123", "URL": "example.com"}
    result2, replaced2 = validate_arguments_in_installation(installation2, arguments2)
    assert replaced2 is True
    assert result2["args"] == ["run", "--env", "TOKEN=${TOKEN}", "--env", "URL"]
    assert result2["env"] == {"TOKEN": "${TOKEN}", "URL": "${URL}"}

    # case 3: npx command with --KEY=value parameters
    installation3 = {
        "type": "npm",
        "command": "npx",
        "args": ["some-package", "--API_KEY=value", "--DB_PASSWORD=secret"],
        "env": {},
    }
    arguments3 = {"API_KEY": "value", "DB_PASSWORD": "secret"}
    result3, replaced3 = validate_arguments_in_installation(installation3, arguments3)
    assert replaced3 is True
    assert result3["args"] == ["some-package", "--API_KEY=${API_KEY}", "--DB_PASSWORD=${DB_PASSWORD}"]

    # case 5: cli command with KEY=value parameters
    installation5 = {
        "type": "cli",
        "command": "cli-tool",
        "args": ["@user/command", "API_KEY=value", "DB_PASSWORD=secret"],
        "env": {},
    }
    arguments5 = {"API_KEY": "value", "DB_PASSWORD": "secret"}
    result5, replaced5 = validate_arguments_in_installation(installation5, arguments5)
    assert replaced5 is True
    assert result5["args"] == ["@user/command", "API_KEY=${API_KEY}", "DB_PASSWORD=${DB_PASSWORD}"]

    # case 6: python command with --KEY value parameters
    installation6 = {
        "type": "python",
        "command": "python",
        "args": ["path/to/script.py", "--API_KEY", "value", "--DB_PASSWORD", "secret"],
        "env": {},
    }
    arguments6 = {"API_KEY": "value", "DB_PASSWORD": "secret"}
    result6, replaced6 = validate_arguments_in_installation(installation6, arguments6)
    assert replaced6 is True
    assert result6["args"] == ["path/to/script.py", "--API_KEY", "${API_KEY}", "--DB_PASSWORD", "${DB_PASSWORD}"]

    # case 7: no arguments
    installation7 = {
        "type": "python",
        "command": "python",
        "args": ["path/to/script.py", "--argument", "value", "--argument2", "value2"],
        "env": {},
    }
    arguments7 = {"API_KEY": "value"}
    result7, replaced7 = validate_arguments_in_installation(installation7, arguments7)
    assert replaced7 is False
    assert result7["args"] == ["path/to/script.py", "--argument", "value", "--argument2", "value2"]

    # case 8: empty installation
    installation8 = {}
    arguments8 = {"API_KEY": "value"}
    result8, replaced8 = validate_arguments_in_installation(installation8, arguments8)
    assert replaced8 is False
    assert result8 == {}

    # case 9: already standard format
    installation9 = {
        "type": "docker",
        "command": "docker",
        "args": ["run", "-e", "API_KEY=${API_KEY}"],
        "env": {"API_KEY": "${API_KEY}"},
    }
    arguments9 = {"API_KEY": "value"}
    result9, replaced9 = validate_arguments_in_installation(installation9, arguments9)
    assert replaced9 is True
    assert result9["args"] == ["run", "-e", "API_KEY=${API_KEY}"]
    assert result9["env"] == {"API_KEY": "${API_KEY}"}
