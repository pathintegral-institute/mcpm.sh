from unittest.mock import Mock

from mcpm.commands.client import _client_config_for_global_server
from mcpm.core.schema import RemoteServerConfig, STDIOServerConfig


def test_client_config_prefers_remote_url(monkeypatch):
    remote = RemoteServerConfig(name="gh", url="https://mcp.example/mcp", headers={"A": "b"})
    monkeypatch.setattr(
        "mcpm.commands.client.global_config_manager.get_server",
        Mock(return_value=remote),
    )
    cfg = _client_config_for_global_server("gh", "mcpm_gh")
    assert isinstance(cfg, RemoteServerConfig)
    assert cfg.name == "mcpm_gh"
    assert cfg.url == "https://mcp.example/mcp"
    assert cfg.headers == {"A": "b"}


def test_client_config_falls_back_to_stdio_run(monkeypatch):
    monkeypatch.setattr(
        "mcpm.commands.client.global_config_manager.get_server",
        Mock(return_value=STDIOServerConfig(name="local", command="npx", args=["-y", "pkg"])),
    )
    cfg = _client_config_for_global_server("local", "mcpm_local")
    assert isinstance(cfg, STDIOServerConfig)
    assert cfg.command == "mcpm"
    assert cfg.args == ["run", "local"]
