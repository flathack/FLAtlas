from __future__ import annotations

import pytest

from PySide6.QtWidgets import QListWidget

from fl_editor.cmp_loader import load_native_freelancer_model
from fl_editor.dialogs import MeshPreviewDialog
from fl_editor.qt3d_compat import QT3D_AVAILABLE


def test_mesh_preview_dialog_shows_native_model_lists(qapp, tmp_path):
    if not QT3D_AVAILABLE:
        pytest.skip("Qt3D not available")

    cmp_path = tmp_path / "sample.cmp"
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            [r"\\", "VMeshLibrary", "Part_Core", "File name", "Object name", "mesh0.vms", "Part_Wing", "mesh1.vms"],
            [
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("VMeshLibrary", 0x10, 0, 0, 0, 88, 0, None),
                ("Part_Core", 0x10, 0, 0, 0, 132, 0, None),
                ("File name", 0x80, 0, 11, 11, 176, 0, "mesh0.vms"),
                ("Object name", 0x80, 0, 10, 10, 220, 0, "core_mesh"),
                ("mesh0.vms", 0x80, 128, 64, 64, 264, 0, None),
                ("Part_Wing", 0x10, 0, 0, 0, 308, 0, None),
                ("mesh1.vms", 0x80, 256, 64, 64, 0, 0, None),
            ],
        )
    )
    native_model = load_native_freelancer_model(cmp_path)

    dialog = MeshPreviewDialog(
        None,
        None,
        "Native Preview",
        primitive="cube",
        info_text="info",
        native_model=native_model,
    )

    nodes_list = dialog.findChild(QListWidget, "native_nodes_list")
    parts_list = dialog.findChild(QListWidget, "native_parts_list")
    vmesh_list = dialog.findChild(QListWidget, "native_vmesh_list")

    assert nodes_list is not None
    assert nodes_list.count() == 8
    assert parts_list is not None
    assert parts_list.count() == 2
    assert "Part_Core -> mesh0.vms" in parts_list.item(0).text()
    assert "file=mesh0.vms" in parts_list.item(0).text()
    assert "object=core_mesh" in parts_list.item(0).text()
    assert vmesh_list is not None
    assert vmesh_list.count() == 2


def _build_fake_utf_with_nodes(
    names: list[str],
    nodes: list[tuple[str, int, int, int, int, int, int, str | None]],
) -> bytes:
    from struct import pack
    from fl_editor.cmp_loader import UTF_HEADER

    node_block_offset = UTF_HEADER.size
    node_entry_size = 44
    node_block_size = len(nodes) * node_entry_size
    names_blob = b"\x00".join(name.encode("latin-1") for name in names) + b"\x00"
    names_offset = node_block_offset + node_block_size
    data_offset = names_offset + len(names_blob)
    data_chunks: list[bytes] = []
    header = pack(
        "<4s13I",
        b"UTF ",
        257,
        node_block_offset,
        node_block_size,
        0,
        node_entry_size,
        names_offset,
        len(names_blob),
        len(names_blob),
        data_offset,
        0,
        0,
        0,
        0,
    )
    node_block = bytearray()
    name_offsets: dict[str, int] = {}
    current = 0
    for name in names:
        name_offsets[name] = current
        current += len(name.encode("latin-1")) + 1

    for name, flags, data_off, alloc, used, peer, aux, text_data in nodes:
        actual_data_off = data_off
        actual_alloc = alloc
        actual_used = used
        if text_data is not None:
            encoded = text_data.encode("latin-1") + b"\x00"
            actual_data_off = data_offset + sum(len(chunk) for chunk in data_chunks)
            actual_alloc = len(encoded)
            actual_used = len(encoded)
            data_chunks.append(encoded)
        lookup_name = name
        if lookup_name not in name_offsets and lookup_name == "\\" and "\\\\" in name_offsets:
            lookup_name = "\\\\"
        node_block.extend(
            pack(
                "<11I",
                aux,
                name_offsets[lookup_name],
                flags,
                0,
                peer,
                actual_data_off,
                actual_alloc,
                actual_used,
                0,
                0,
                0,
            )
        )
    return header + bytes(node_block) + names_blob + b"".join(data_chunks)
