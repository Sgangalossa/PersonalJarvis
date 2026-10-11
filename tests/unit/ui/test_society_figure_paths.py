"""Path confinement for imported local society figures."""

from __future__ import annotations

from pathlib import Path

import pytest

from jarvis.ui.web import society_figure_routes as routes


@pytest.fixture
def figure_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(routes, "DATA_DIR", tmp_path)
    folder = routes.figures_dir()
    folder.mkdir(parents=True)
    return folder


def test_figure_path_accepts_a_plain_glb_component(figure_dir: Path) -> None:
    stored = figure_dir / "hero_01.glb"
    stored.write_bytes(b"glTF test")
    assert routes._figure_path(stored.name) == stored.resolve()


@pytest.mark.parametrize(
    "file_name",
    [
        "../outside.glb",
        "nested/inside.glb",
        r"C:outside.glb",
        ".hidden.glb",
        "bad-name.glb?query=1",
        "a" * 252 + ".glb",
    ],
)
def test_figure_path_rejects_non_component_names(figure_dir: Path, file_name: str) -> None:
    assert routes._figure_path(file_name) is None


def test_figure_path_rejects_a_symlink(figure_dir: Path, tmp_path: Path) -> None:
    outside = tmp_path / "outside.glb"
    outside.write_bytes(b"glTF test")
    link = figure_dir / "alias.glb"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is not permitted on this runner")
    assert routes._figure_path(link.name) is None
