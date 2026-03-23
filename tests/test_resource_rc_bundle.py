from pathlib import Path

from fl_editor.resource_rc_bundle import rc_escape, write_resource_rc_bundle


def test_rc_escape_escapes_slashes_quotes_and_newlines():
    assert rc_escape('a\\b"c\nd') == 'a\\\\b""c\\012d'


def test_rc_escape_escapes_unicode_for_rc_stringtable():
    assert rc_escape("WÃ¤hrend") == 'W\\x00C3\\x00A4hrend'


def test_write_resource_rc_bundle_writes_rc_and_info_files(tmp_path: Path):
    rc_path, res_path, tmp_dll = write_resource_rc_bundle(
        tmp_path,
        strings_by_local_id={10: 'Alpha "Beta"'},
        infos_by_local_id={20: "<RDL>Info</RDL>"},
    )

    rc_text = rc_path.read_text(encoding="utf-8-sig")
    info_text = (tmp_path / "ids_info_20.xml").read_text(encoding="utf-8")

    assert res_path == tmp_path / "resource.res"
    assert tmp_dll == tmp_path / "resource.dll"
    assert '10 L"Alpha ""Beta"""' in rc_text
    assert '20 23 "' in rc_text
    assert info_text == "<RDL>Info</RDL>"
