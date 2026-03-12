from __future__ import annotations

from struct import pack

import pytest

from PySide6.QtGui import QVector3D
from PySide6.QtWidgets import QListWidget, QPushButton, QCheckBox, QLabel, QTabWidget

from fl_editor.cmp_loader import load_native_freelancer_model
from fl_editor.dialogs import MeshPreviewDialog
from fl_editor.qt3d_compat import QT3D_AVAILABLE


def test_mesh_preview_dialog_shows_native_model_lists(qapp, tmp_path):
    if not QT3D_AVAILABLE:
        pytest.skip("Qt3D not available")

    cmp_path = tmp_path / "sample.cmp"
    (tmp_path / "diffuse.dds").write_bytes(b"DDS ")
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            [r"\\", "VMeshLibrary", "Part_Core", "File name", "Object name", "mesh0.vms", "Part_Wing", "mesh1.vms", "VMeshData", "Cmpnd", "Cons", "Fix", "Index", "diffuse.dds"],
            [
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("VMeshLibrary", 0x10, 0, 0, 0, 88, 0, None),
                ("Part_Core", 0x10, 0, 0, 0, 132, 0, None),
                ("File name", 0x80, 0, 11, 11, 176, 0, "mesh0.vms"),
                ("Object name", 0x80, 0, 10, 10, 220, 0, "core_mesh"),
                ("mesh0.vms", 0x80, 128, 64, 64, 264, 0, None),
                ("VMeshData", 0x80, 0, 64, 64, 308, 0, b"0123456789abcdef" * 4),
                ("VMeshRef", 0x80, 0, 60, 60, 352, 0, _build_vmesh_ref_blob()),
                ("Part_Wing", 0x10, 0, 0, 0, 396, 440, None),
                ("Index", 0x80, 0, 4, 4, 484, 0, pack("<I", 0)),
                ("mesh1.vms", 0x80, 256, 64, 64, 528, 0, None),
                ("Cmpnd", 0x10, 0, 0, 0, 572, 616, None),
                ("Cons", 0x10, 0, 0, 0, 660, 704, None),
                ("Fix", 0x80, 0, 352, 352, 748, 0, pack("<88f", *[float(index) for index in range(88)])),
                ("diffuse.dds", 0x10, 0, 0, 0, 0, 0, None),
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
    model_nodes_list = dialog.findChild(QListWidget, "native_model_nodes_list")
    vmesh_data_list = dialog.findChild(QListWidget, "native_vmesh_data_list")
    preview_mesh_list = dialog.findChild(QListWidget, "native_preview_mesh_list")
    geometry_candidate_list = dialog.findChild(QListWidget, "native_geometry_candidate_list")
    submesh_list = dialog.findChild(QListWidget, "native_submesh_list")
    geometry_source_list = dialog.findChild(QListWidget, "native_geometry_source_list")
    layout_guess_list = dialog.findChild(QListWidget, "native_layout_guess_list")
    buffer_slice_list = dialog.findChild(QListWidget, "native_buffer_slice_list")
    material_reference_list = dialog.findChild(QListWidget, "native_material_reference_list")
    material_binding_list = dialog.findChild(QListWidget, "native_material_binding_list")
    material_group_list = dialog.findChild(QListWidget, "native_material_group_list")
    resolved_texture_label = dialog.findChild(QLabel, "native_resolved_texture_label")
    cmp_fix_list = dialog.findChild(QListWidget, "native_cmp_fix_list")
    cmp_transform_hint_list = dialog.findChild(QListWidget, "native_cmp_transform_hint_list")
    reference_check_list = dialog.findChild(QListWidget, "native_reference_check_list")
    reference_summary_label = dialog.findChild(QLabel, "native_reference_summary_label")

    assert nodes_list is not None
    assert nodes_list.count() == 10
    assert parts_list is not None
    assert parts_list.count() == 2
    assert "Part_Core -> mesh0.vms" in parts_list.item(0).text()
    assert "file=mesh0.vms" in parts_list.item(0).text()
    assert "object=core_mesh" in parts_list.item(0).text()
    assert "idx=0" in parts_list.item(1).text()
    assert vmesh_list is not None
    assert vmesh_list.count() == 2
    assert vmesh_data_list is not None
    assert vmesh_data_list.count() == 1
    assert "bytes=64" in vmesh_data_list.item(0).text()
    assert model_nodes_list is not None
    assert model_nodes_list.count() == 1
    assert "r=6.50" in model_nodes_list.item(0).text()
    assert "blocks=1" in model_nodes_list.item(0).text()
    assert "bytes=64" in model_nodes_list.item(0).text()
    assert preview_mesh_list is not None
    assert preview_mesh_list.count() == 1
    assert "verts=10" in preview_mesh_list.item(0).text()
    assert "tris=6" in preview_mesh_list.item(0).text()
    assert geometry_candidate_list is not None
    assert geometry_candidate_list.count() == 1
    assert "stage=single-block-header" in geometry_candidate_list.item(0).text()
    assert "render=yes" in geometry_candidate_list.item(0).text()
    assert submesh_list is not None
    assert submesh_list.count() == 1
    assert "v=0+10" in submesh_list.item(0).text()
    assert "i=0+18" in submesh_list.item(0).text()
    assert geometry_source_list is not None
    assert geometry_source_list.count() == 1
    assert "resolved=yes" in geometry_source_list.item(0).text()
    assert "via=single-block-fallback" in geometry_source_list.item(0).text()
    assert layout_guess_list is not None
    assert layout_guess_list.count() == 1
    assert "conf=no-fit" in layout_guess_list.item(0).text()
    assert buffer_slice_list is None
    assert material_reference_list is not None
    assert material_reference_list.count() == 1
    assert "texture: diffuse.dds" in material_reference_list.item(0).text()
    assert material_binding_list is not None
    assert material_binding_list.count() == 1
    assert "g=0+1" in material_binding_list.item(0).text()
    assert "tex=diffuse.dds" in material_binding_list.item(0).text()
    assert "texs=1" in material_binding_list.item(0).text()
    assert material_group_list is not None
    assert material_group_list.count() == 1
    assert "groups=0+1" in material_group_list.item(0).text()
    assert "tex=diffuse.dds" in material_group_list.item(0).text()
    assert "texs=1" in material_group_list.item(0).text()
    assert resolved_texture_label is not None
    assert resolved_texture_label.text().endswith("diffuse.dds")
    assert cmp_fix_list is not None
    assert cmp_fix_list.count() == 2
    assert "Part_Core" in cmp_fix_list.item(1).text()
    assert "idx=0" in cmp_fix_list.item(0).text()
    assert "rows=4x11" in cmp_fix_list.item(0).text()
    assert "bytes=176" in cmp_fix_list.item(0).text()
    assert cmp_transform_hint_list is not None
    assert cmp_transform_hint_list.count() == 2
    assert "t=(" in cmp_transform_hint_list.item(0).text()
    assert "|t|=" in cmp_transform_hint_list.item(0).text()
    assert reference_check_list is not None
    assert reference_check_list.count() == 1
    assert "mesh0.vms" in reference_check_list.item(0).text()
    assert "idx=0" in reference_check_list.item(0).text()
    assert "tex=yes" in reference_check_list.item(0).text()
    assert "| d=" in reference_check_list.item(0).text()
    assert "| ok=" in reference_check_list.item(0).text()
    assert "| sev=" in reference_check_list.item(0).text()
    assert "| t-src=" in reference_check_list.item(0).text()
    assert "| lc=(" in reference_check_list.item(0).text()
    assert reference_summary_label is not None
    assert "rows=1" in reference_summary_label.text()
    assert "hints=1" in reference_summary_label.text()
    assert "high=1" in reference_summary_label.text()
    assert "rot=" in reference_summary_label.text()
    assert "t-local=1" in reference_summary_label.text()
    assert native_model.bounds is not None
    assert round(native_model.bounds.radius or 0.0, 2) == 6.5
    assert dialog._preview_bounds == native_model.bounds


def test_mesh_preview_dialog_accepts_native_geometry_path(qapp, tmp_path):
    if not QT3D_AVAILABLE:
        pytest.skip("Qt3D not available")

    cmp_path = tmp_path / "native_exact.cmp"
    vertex_blob = pack("<9f", 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    index_blob = pack("<3H", 0, 1, 2)
    block = (b"H" * 16) + vertex_blob + index_blob
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            [r"\\", "VMeshLibrary", "mesh0.vms", "VMeshData", "mesh0.3db", "MultiLevel", "Level0", "VMeshPart", "VMeshRef"],
            [
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("VMeshLibrary", 0x10, 0, 0, 0, 88, 176, None),
                ("mesh0.vms", 0x10, 0, 0, 0, 132, 0, None),
                ("VMeshData", 0x80, 0, len(block), len(block), 0, 0, block),
                ("mesh0.3db", 0x10, 0, 0, 0, 220, 0, None),
                ("MultiLevel", 0x10, 0, 0, 0, 264, 0, None),
                ("Level0", 0x10, 0, 0, 0, 308, 0, None),
                ("VMeshPart", 0x10, 0, 0, 0, 352, 0, None),
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob(vertex_count=3, index_count=3, group_count=1)),
            ],
        )
    )
    native_model = load_native_freelancer_model(cmp_path)

    dialog = MeshPreviewDialog(
        None,
        None,
        "Native Geometry Preview",
        primitive="cube",
        native_model=native_model,
    )

    assert hasattr(dialog, "_mesh")
    tabs = dialog.findChild(QTabWidget, "native_preview_tabs")
    assert tabs is not None
    assert tabs.count() == 2
    assert tabs.currentIndex() == 0
    assert tabs.tabText(0) == "Preview"
    assert tabs.tabText(1) == "Details"
    render_summary_label = dialog.findChild(QLabel, "native_preview_render_summary_label")
    assert render_summary_label is not None
    assert "Render path: native geometry" in render_summary_label.text()
    assert "geometries=1" in render_summary_label.text()
    assert "confidence=exact" in render_summary_label.text()


def test_mesh_preview_dialog_supports_jumpgate_fallback_primitive(qapp):
    if not QT3D_AVAILABLE:
        pytest.skip("Qt3D not available")

    dialog = MeshPreviewDialog(
        None,
        None,
        "Jumpgate Preview",
        primitive="jumpgate",
    )

    assert len(dialog._native_mesh_entities) >= 4


def test_mesh_preview_dialog_builds_multiple_native_geometry_entities(qapp, tmp_path):
    if not QT3D_AVAILABLE:
        pytest.skip("Qt3D not available")

    cmp_path = tmp_path / "native_multi.cmp"
    vertex_blob_a = pack("<9f", 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    index_blob_a = pack("<3H", 0, 1, 2)
    block_a = (b"H" * 16) + vertex_blob_a + index_blob_a
    vertex_blob_b = pack("<9f", 0.0, 0.0, 0.0, -1.0, 0.0, 0.0, 0.0, -1.0, 0.0)
    index_blob_b = pack("<3H", 0, 1, 2)
    block_b = (b"J" * 16) + vertex_blob_b + index_blob_b
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            [r"\\", "meshA.3db", "meshB.3db", "Level0", "VMeshPart", "VMeshRef", "VMeshLibrary", "mesh0.vms", "VMeshData", "mesh1.vms"],
            [
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("meshA.3db", 0x10, 0, 0, 0, 88, 0, None),
                ("Level0", 0x10, 0, 0, 0, 132, 0, None),
                ("VMeshPart", 0x10, 0, 0, 0, 176, 220, None),
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob(vertex_count=3, index_count=3, group_count=1)),
                ("meshB.3db", 0x10, 0, 0, 0, 264, 0, None),
                ("Level0", 0x10, 0, 0, 0, 308, 0, None),
                ("VMeshPart", 0x10, 0, 0, 0, 352, 396, None),
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob(vertex_count=3, index_count=3, group_count=1)),
                ("VMeshLibrary", 0x10, 0, 0, 0, 440, 572, None),
                ("mesh0.vms", 0x10, 0, 0, 0, 484, 0, None),
                ("VMeshData", 0x80, 0, len(block_a), len(block_a), 528, 0, block_a),
                ("mesh1.vms", 0x10, 0, 0, 0, 0, 0, None),
                ("VMeshData", 0x80, 0, len(block_b), len(block_b), 0, 0, block_b),
            ],
        )
    )
    native_model = load_native_freelancer_model(cmp_path)

    dialog = MeshPreviewDialog(
        None,
        None,
        "Native Multi Geometry Preview",
        primitive="cube",
        native_model=native_model,
    )

    assert hasattr(dialog, "_mesh")
    assert len(dialog._native_mesh_entities) == 1


def test_mesh_preview_dialog_supports_reset_camera_and_bounds_toggle(qapp, tmp_path):
    if not QT3D_AVAILABLE:
        pytest.skip("Qt3D not available")

    cmp_path = tmp_path / "native_controls.cmp"
    vertex_blob = pack("<9f", 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    index_blob = pack("<3H", 0, 1, 2)
    block = (b"H" * 16) + vertex_blob + index_blob
    cmp_path.write_bytes(
        _build_fake_utf_with_nodes(
            [r"\\", "VMeshLibrary", "mesh0.vms", "VMeshData", "mesh0.3db", "MultiLevel", "Level0", "VMeshPart", "VMeshRef"],
            [
                ("\\", 0x10, 0, 0, 0, 44, 0, None),
                ("VMeshLibrary", 0x10, 0, 0, 0, 88, 176, None),
                ("mesh0.vms", 0x10, 0, 0, 0, 132, 0, None),
                ("VMeshData", 0x80, 0, len(block), len(block), 0, 0, block),
                ("mesh0.3db", 0x10, 0, 0, 0, 220, 0, None),
                ("MultiLevel", 0x10, 0, 0, 0, 264, 0, None),
                ("Level0", 0x10, 0, 0, 0, 308, 0, None),
                ("VMeshPart", 0x10, 0, 0, 0, 352, 0, None),
                ("VMeshRef", 0x80, 0, 60, 60, 0, 0, _build_vmesh_ref_blob(vertex_count=3, index_count=3, group_count=1)),
            ],
        )
    )
    native_model = load_native_freelancer_model(cmp_path)

    dialog = MeshPreviewDialog(
        None,
        None,
        "Native Control Preview",
        primitive="cube",
        native_model=native_model,
    )

    reset_btn = dialog.findChild(QPushButton, "native_preview_reset_camera_btn")
    bounds_checkbox = dialog.findChild(QCheckBox, "native_preview_bounds_checkbox")
    wireframe_checkbox = dialog.findChild(QCheckBox, "native_preview_wireframe_checkbox")
    part_names_checkbox = dialog.findChild(QCheckBox, "native_preview_part_names_checkbox")
    part_names_label = dialog.findChild(QLabel, "native_preview_part_names_label")

    assert reset_btn is not None
    assert bounds_checkbox is not None
    assert wireframe_checkbox is not None
    assert part_names_checkbox is not None
    assert part_names_label is not None
    assert bounds_checkbox.isEnabled() is True
    assert wireframe_checkbox.isEnabled() is True
    assert part_names_checkbox.isEnabled() is True
    assert dialog._bounds_entity is not None
    assert dialog._bounds_entity.isEnabled() is False
    assert len(dialog._wireframe_entities) == 1
    assert dialog._wireframe_entities[0].isEnabled() is False
    assert part_names_label.isVisible() is False
    assert "mesh0.3db" in part_names_label.text()

    bounds_checkbox.setChecked(True)
    assert dialog._bounds_entity.isEnabled() is True
    bounds_checkbox.setChecked(False)
    assert dialog._bounds_entity.isEnabled() is False

    wireframe_checkbox.setChecked(True)
    assert dialog._wireframe_entities[0].isEnabled() is True
    wireframe_checkbox.setChecked(False)
    assert dialog._wireframe_entities[0].isEnabled() is False

    part_names_checkbox.setChecked(True)
    assert part_names_label.isVisible() is True
    part_names_checkbox.setChecked(False)
    assert part_names_label.isVisible() is False

    dialog._camera.setPosition(QVector3D(99.0, 99.0, 99.0))
    reset_btn.click()
    assert dialog._camera.position() != QVector3D(99.0, 99.0, 99.0)


def _build_fake_utf_with_nodes(
    names: list[str],
    nodes: list[tuple[str, int, int, int, int, int, int, str | bytes | None]],
) -> bytes:
    from struct import pack
    from fl_editor.cmp_loader import UTF_HEADER

    for name, *_ in nodes:
        if name not in names:
            names.append(name)
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
            if isinstance(text_data, bytes):
                encoded = text_data
            else:
                encoded = text_data.encode("latin-1") + b"\x00"
            actual_data_off = data_offset + sum(len(chunk) for chunk in data_chunks)
            actual_alloc = len(encoded)
            actual_used = len(encoded)
            data_chunks.append(encoded)
        lookup_name = name
        if lookup_name not in name_offsets and lookup_name == "\\" and "\\\\" in name_offsets:
            lookup_name = "\\\\"
        entry_or_peer = actual_data_off if (flags & 0x80) else peer
        entry_alloc = actual_alloc if (flags & 0x80) else actual_data_off
        entry_used = actual_used if (flags & 0x80) else actual_alloc
        node_block.extend(
            pack(
                "<11I",
                aux,
                name_offsets[lookup_name],
                flags,
                0,
                entry_or_peer,
                entry_alloc,
                entry_used,
                0,
                0,
                0,
                0,
            )
        )
    return header + bytes(node_block) + names_blob + b"".join(data_chunks)


def _build_vmesh_ref_blob() -> bytes:
    from struct import pack

    return pack(
        "<IIHHHHHH10f",
        60,
        0x12345678,
        0,
        10,
        0,
        18,
        0,
        1,
        5.0,
        -5.0,
        3.0,
        -3.0,
        2.0,
        -2.0,
        0.0,
        0.0,
        0.0,
        6.5,
    )
