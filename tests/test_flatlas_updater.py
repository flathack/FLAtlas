from __future__ import annotations

from pathlib import Path

from flatlas_updater import _build_updater_args, _downloaded_file_looks_like_html, _resolve_source_root


def test_build_updater_args_includes_download_fields():
    args = _build_updater_args(
        mode="download-zip",
        wait_pid=123,
        install_root="C:/FLAtlas",
        exe_path="C:/FLAtlas/FLAtlas.exe",
        version="v0.6.8",
        download_url="https://example.com/FLAtlas.zip",
        asset_name="FLAtlas.zip",
    )

    assert "--mode" in args
    assert "download-zip" in args
    assert "https://example.com/FLAtlas.zip" in args
    assert "FLAtlas.zip" in args


def test_build_updater_args_includes_local_zip_source():
    args = _build_updater_args(
        mode="local-zip",
        wait_pid=321,
        install_root="C:/FLAtlas",
        exe_path="C:/FLAtlas/FLAtlas.exe",
        source_zip="C:/tmp/test.zip",
    )

    assert "local-zip" in args
    assert "C:/tmp/test.zip" in args


def test_downloaded_file_looks_like_html_detects_html(tmp_path: Path):
    path = tmp_path / "bad.zip"
    path.write_text("<html>oops</html>", encoding="utf-8")

    assert _downloaded_file_looks_like_html(path) is True


def test_resolve_source_root_prefers_single_nested_folder(tmp_path: Path):
    root = tmp_path / "extract"
    nested = root / "FLAtlas"
    nested.mkdir(parents=True)

    assert _resolve_source_root(root) == nested
