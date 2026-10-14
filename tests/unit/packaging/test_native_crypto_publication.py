"""The publication preflight gates expensive native dependency runners."""

from __future__ import annotations

import io
import urllib.error

import pytest

from scripts.ci import check_native_crypto_publication as check


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


@pytest.fixture
def records():
    return [
        {
            "target": "macos-x86_64",
            "filename": "mac.whl",
            "url": "https://packages.invalid/mac.whl",
            "sha256": "a" * 64,
        },
        {
            "target": "windows-arm64",
            "filename": "windows.whl",
            "url": "https://packages.invalid/windows.whl",
            "sha256": "b" * 64,
        },
    ]


def test_complete_index_checks_both_reviewed_artifacts(monkeypatch, records):
    page = "".join(
        f'<a href="{row["url"]}#sha256={row["sha256"]}">{row["filename"]}</a>'
        for row in records
    ).encode()
    fetched = []
    monkeypatch.setattr(check.index, "native_records", lambda: records)
    monkeypatch.setattr(check.urllib.request, "urlopen", lambda *_args, **_kwargs: _Response(page))
    monkeypatch.setattr(
        check.index,
        "fetch_native_wheel",
        lambda target, _directory: fetched.append(target),
    )

    check.check_publication()

    assert fetched == ["macos-x86_64", "windows-arm64"]


def test_missing_index_link_fails_before_artifact_download(monkeypatch, records):
    monkeypatch.setattr(check.index, "native_records", lambda: records)
    monkeypatch.setattr(
        check.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: _Response(
            f'<a href="{records[0]["url"]}#sha256={records[0]["sha256"]}"></a>'.encode()
        ),
    )
    monkeypatch.setattr(
        check.index,
        "fetch_native_wheel",
        lambda *_args: pytest.fail("artifact download must not start"),
    )

    with pytest.raises(ValueError, match="windows.whl"):
        check.check_publication()


def test_missing_pages_index_reports_exact_repository_action(monkeypatch, capsys):
    index_url = "https://sgangalossa.github.io/PersonalJarvis/native-crypto/"
    monkeypatch.setattr(check.index, "native_records", lambda: [])
    monkeypatch.setattr(check.index, "wheel_links_url", lambda: index_url)

    def missing_index(*_args, **_kwargs):
        raise urllib.error.HTTPError(index_url, 404, "Not Found", {}, None)

    monkeypatch.setattr(check.urllib.request, "urlopen", missing_index)

    assert check.main() == 1
    captured = capsys.readouterr()
    assert check.PAGES_SETTINGS_URL in captured.err
    assert "Source: GitHub Actions" in captured.err
    assert "Native cryptography wheels on jarvis-lab" in captured.err
    assert "complete and verified" not in captured.out


def test_non_404_index_error_does_not_claim_pages_is_disabled(monkeypatch, capsys):
    index_url = "https://sgangalossa.github.io/PersonalJarvis/native-crypto/"
    monkeypatch.setattr(check.index, "native_records", lambda: [])
    monkeypatch.setattr(check.index, "wheel_links_url", lambda: index_url)

    def unavailable_index(*_args, **_kwargs):
        raise urllib.error.HTTPError(index_url, 503, "Unavailable", {}, None)

    monkeypatch.setattr(check.urllib.request, "urlopen", unavailable_index)

    assert check.main() == 1
    captured = capsys.readouterr()
    assert "HTTP Error 503" in captured.err
    assert check.PAGES_SETTINGS_URL not in captured.err
