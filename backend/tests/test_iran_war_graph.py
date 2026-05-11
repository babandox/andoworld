from backend.app.iran_war.case_builder import build_case


def test_default_case_returns_precomputed_causal_spine_not_full_graph():
    case = build_case()

    assert case.graph_view.view == "spine"
    assert len(case.graph_view.nodes) <= 60
    assert all(edge.relation in {"triggers", "escalates", "justifies", "disrupts"} for edge in case.graph_view.edges)
    assert any(node.node_type == "proximate_trigger" for node in case.graph_view.nodes)


def test_market_series_contains_brent_sp500_and_markers():
    case = build_case()

    series_names = {point.series for point in case.market_series}
    marker_kinds = {marker.marker_type for marker in case.market_markers}

    assert {"Brent", "S&P 500"}.issubset(series_names)
    assert {"statement", "strike", "market_move"}.issubset(marker_kinds)
