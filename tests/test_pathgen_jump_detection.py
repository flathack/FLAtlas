from fl_editor import pathgen


class _ParserStub:
    def __init__(self, objects_by_path):
        self._objects_by_path = dict(objects_by_path)

    def parse(self, path):
        return self._objects_by_path.get(path, [])

    def get_objects(self, sections):
        return list(sections)


def test_build_connection_graph_detects_custom_gate_from_msg_and_reputation(monkeypatch):
    systems = [
        {"nickname": "CF89", "path": "cf89.ini"},
        {"nickname": "CF94", "path": "cf94.ini"},
    ]
    objects_by_path = {
        "cf89.ini": [
            {
                "nickname": "CF89_to_CF94",
                "archetype": "domgate",
                "msg_id_prefix": "gcs_refer_system_CF94",
                "reputation": "fc_cf6_grp",
                "goto": "CF94, CF94_to_CF89, gate_tunnel_crossfirehyperspace",
            }
        ],
        "cf94.ini": [],
    }
    parser = _ParserStub(objects_by_path)
    monkeypatch.setattr(pathgen, "find_all_systems", lambda *args, **kwargs: systems)

    graph_all, graph_legal, graph_illegal = pathgen._build_connection_graph("game", parser)

    assert graph_all["CF89"] == {"CF94"}
    assert graph_legal["CF89"] == {"CF94"}
    assert graph_illegal["CF89"] == set()
