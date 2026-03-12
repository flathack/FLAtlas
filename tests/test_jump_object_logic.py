from fl_editor.jump_object_logic import classify_jump_connection_kind


def test_classify_jump_connection_kind_detects_gate_by_archetype():
    assert classify_jump_connection_kind(archetype="jumpgate", msg_id_prefix="", reputation="") == "gate"


def test_classify_jump_connection_kind_detects_hole_by_archetype():
    assert classify_jump_connection_kind(archetype="jumphole_red", msg_id_prefix="", reputation="") == "hole"


def test_classify_jump_connection_kind_detects_custom_gate_from_msg_and_reputation():
    assert classify_jump_connection_kind(
        archetype="domgate",
        msg_id_prefix="gcs_refer_system_CF94",
        reputation="fc_cf6_grp",
    ) == "gate"


def test_classify_jump_connection_kind_ignores_custom_gate_without_reputation():
    assert classify_jump_connection_kind(
        archetype="domgate",
        msg_id_prefix="gcs_refer_system_CF94",
        reputation="",
    ) == ""


def test_classify_jump_connection_kind_detects_alien_gate_from_jump_effect_and_goto():
    assert classify_jump_connection_kind(
        archetype="domgate",
        msg_id_prefix="",
        reputation="",
        jump_effect="jump_effect_crossfirehyperspace",
        goto_value="CF94, CF94_to_CF89, gate_tunnel_crossfirehyperspace",
    ) == "alien_gate"


def test_classify_jump_connection_kind_prefers_gate_filters_over_alien_gate_fallback():
    assert classify_jump_connection_kind(
        archetype="jumpgate",
        msg_id_prefix="",
        reputation="",
        jump_effect="jump_effect_crossfirehyperspace",
        goto_value="CF94, CF94_to_CF89, gate_tunnel_crossfirehyperspace",
    ) == "gate"
