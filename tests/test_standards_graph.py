from ai.standards_graph.graph_builder import StandardsGraphBuilder
from ai.standards_graph.graph_queries import StandardsGraphQueryEngine


def build_query_engine():
    builder = StandardsGraphBuilder(
        standards_path="data/standards.json",
        relations_path="data/relations.json",
    )
    return builder, StandardsGraphQueryEngine(builder)


def test_graph_loads():
    builder, _ = build_query_engine()

    graph = builder.get_graph()

    assert graph is not None
    assert len(graph.nodes) > 0


def test_graph_contains_expected_core_standards():
    builder, _ = build_query_engine()

    graph = builder.get_graph()

    assert "IS 14220" in graph.nodes
    assert "IS 9283" in graph.nodes
    assert "IS 12615" in graph.nodes


def test_outgoing_relationships_from_is14220():
    _, query = build_query_engine()

    results = query.get_outgoing_relationships("IS 14220")

    assert len(results) == 2

    targets = {item["target"] for item in results}

    assert targets == {"IS 9283", "IS 8034"}

    for item in results:
        assert item["source"] == "IS 14220"
        assert item["source_resolved"] is True
        assert item["target_resolved"] is True
        assert item["provenance"] == "data/relations.json"


def test_normative_reference_is14220_to_is9283():
    _, query = build_query_engine()

    results = query.get_outgoing_relationships("IS 14220")

    normative = [
        item
        for item in results
        if item["relationship_type"] == "NORMATIVE_REFERENCE"
    ]

    assert len(normative) == 1
    assert normative[0]["target"] == "IS 9283"


def test_incoming_relationship_to_is14220():
    _, query = build_query_engine()

    results = query.get_incoming_relationships("IS 14220")

    assert len(results) >= 1

    superseding = [
        item
        for item in results
        if item["relationship_type"] == "SUPERSEDED_BY"
    ]

    assert len(superseding) == 1

    item = superseding[0]

    assert item["source"] == "IS 14220:1994"
    assert item["target"] == "IS 14220"
    assert item["source_status"] == "SUPERSEDED"
    assert item["target_status"] == "CURRENT"
    assert item["source_resolved"] is True
    assert item["target_resolved"] is True


def test_related_standards_contains_real_standard_ids_only():
    _, query = build_query_engine()

    result = query.get_related_standards("IS 14220")

    related = result["related_standards"]

    assert "IS 14220:1994" in related
    assert "IS 8034" in related
    assert "IS 9283" in related

    # Provenance/data paths must never appear as standards.
    assert "data/relations.json" not in related

    for item in related:
        assert item.startswith("IS ")


def test_dependency_tree_follows_normative_chain():
    _, query = build_query_engine()

    tree = query.get_dependency_tree("IS 14220", max_depth=2)

    assert tree["is_number"] == "IS 14220"
    assert tree["status"] == "CURRENT"
    assert tree["verification_status"] == "VERIFIED_OFFICIAL"

    normative_refs = tree["normative_references"]

    assert len(normative_refs) >= 1

    is9283_ref = next(
        item
        for item in normative_refs
        if item["target"] == "IS 9283"
    )

    assert is9283_ref["target_resolved"] is True
    assert "dependencies" in is9283_ref

    level_1 = is9283_ref["dependencies"]

    assert level_1["is_number"] == "IS 9283"

    level_2 = level_1["normative_references"]

    assert any(
        item["target"] == "IS 12615"
        for item in level_2
    )


def test_relationship_path_is14220_to_is12615():
    _, query = build_query_engine()

    path = query.get_relationship_path(
        "IS 14220",
        "IS 12615",
    )

    assert path is not None

    # The method returns relationship edges, not nodes.
    # IS 14220 -> IS 9283 -> IS 12615 = 2 edges.
    assert len(path) == 2

    assert path[0]["source"] == "IS 14220"
    assert path[0]["target"] == "IS 9283"

    assert path[1]["source"] == "IS 9283"
    assert path[1]["target"] == "IS 12615"


def test_unresolved_references_are_not_fabricated():
    _, query = build_query_engine()

    results = query.get_outgoing_relationships(
        "IS 14220",
        include_unresolved=True,
    )

    for item in results:
        if item["target_resolved"] is False:
            assert item["target"].startswith("IS ")


def test_graph_query_for_unknown_standard():
    _, query = build_query_engine()

    results = query.get_outgoing_relationships("IS 99999")

    assert isinstance(results, list)
    assert results == []