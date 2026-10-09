"""CI bash-3.2 container mirror fallback."""

from __future__ import annotations

from types import SimpleNamespace

from scripts.ci import check_shell_bash32


def _result(*, returncode: int, stdout: str = "", stderr: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def test_parse_uses_public_ecr_before_docker_hub(monkeypatch, capsys) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **_kwargs):
        calls.append(cmd)
        return _result(returncode=0, stdout="@@ install/example.sh\n")

    monkeypatch.setattr(check_shell_bash32, "_run", fake_run)

    assert check_shell_bash32.parse_with_docker(["install/example.sh"]) == {}
    assert calls[0][5] == "public.ecr.aws/docker/library/bash:3.2"
    assert "public.ecr.aws" in capsys.readouterr().out


def test_parse_falls_back_when_public_mirror_cannot_start(monkeypatch, capsys) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **_kwargs):
        calls.append(cmd)
        if len(calls) == 1:
            return _result(returncode=125, stderr="mirror unavailable")
        return _result(returncode=0, stdout="@@ install/example.sh\n")

    monkeypatch.setattr(check_shell_bash32, "_run", fake_run)

    assert check_shell_bash32.parse_with_docker(["install/example.sh"]) == {}
    assert [call[5] for call in calls] == [
        "public.ecr.aws/docker/library/bash:3.2",
        "bash:3.2",
    ]
    assert "docker bash:3.2" in capsys.readouterr().out
