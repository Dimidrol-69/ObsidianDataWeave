"""Tests for vault observability: changelog, graph export, and digest."""

from pathlib import Path


def write_note(path: Path, body: str, *, note_type: str = "atomic", tags=None) -> None:
    if tags is None:
        tags = []
    tag_lines = "\n".join(f"  - {tag}" for tag in tags)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nnote_type: {note_type}\ntags:\n{tag_lines}\n---\n# {path.stem}\n\n{body}\n",
        encoding="utf-8",
    )


def test_format_changelog_row_links_note_and_source():
    from scripts.vault_writer import format_changelog_row

    row = format_changelog_row(
        timestamp="2026-06-14T10:00:00+03:00",
        operation="create",
        title="Vector Search",
        note_type="atomic",
        source_doc="research.docx",
        relative_path="Research & Insights/Vector Search.md",
    )

    assert row == (
        "| 2026-06-14T10:00:00+03:00 | create | [[Vector Search]] | "
        "atomic | research.docx | Research & Insights/Vector Search.md |\n"
    )


def test_build_graph_reports_edges_orphans_and_pagerank(tmp_path):
    from scripts.export_graph import build_graph

    write_note(tmp_path / "Research" / "Alpha.md", "Links to [[Beta]].", tags=["ai/llm"])
    write_note(tmp_path / "Research" / "Beta.md", "Target note.", tags=["ai/llm"])
    write_note(tmp_path / "Research" / "Gamma.md", "No incoming links.", tags=["data/graph"])

    graph = build_graph(tmp_path)

    assert graph["summary"]["node_count"] == 3
    assert graph["summary"]["edge_count"] == 1
    assert graph["edges"] == [{"source": "Alpha", "target": "Beta"}]

    nodes = {node["id"]: node for node in graph["nodes"]}
    assert nodes["Alpha"]["out_degree"] == 1
    assert nodes["Beta"]["in_degree"] == 1
    assert nodes["Gamma"]["is_orphan"] is True
    assert nodes["Beta"]["pagerank"] > nodes["Alpha"]["pagerank"]


def test_graphml_export_contains_nodes_and_edges(tmp_path):
    from scripts.export_graph import build_graph, graph_to_graphml

    write_note(tmp_path / "Alpha.md", "[[Beta]]")
    write_note(tmp_path / "Beta.md", "Target")

    xml = graph_to_graphml(build_graph(tmp_path))

    assert "<graphml" in xml
    assert 'id="Alpha"' in xml
    assert 'source="Alpha" target="Beta"' in xml


def test_render_digest_includes_core_sections():
    from scripts.vault_digest import render_digest

    markdown = render_digest(
        {
            "date": "2026-06-14",
            "summary": {
                "total_notes": 3,
                "folders": {"Research": 2, "Sources": 1},
                "note_types": {"atomic": 2, "source": 1},
            },
            "graph": {
                "summary": {"node_count": 3, "edge_count": 1, "orphan_count": 1},
                "top_orphans": [{"title": "Gamma", "path": "Research/Gamma.md", "in_degree": 0}],
                "top_pagerank": [{"title": "Beta", "pagerank": 0.52}],
            },
            "audit": {
                "summary": {
                    "empty_notes": 0,
                    "thin_atomic_notes": 1,
                    "atomic_notes_without_links": 1,
                    "unlinked_similar_pairs": 0,
                }
            },
            "recent_changes": [
                {
                    "timestamp": "2026-06-14T10:00:00+03:00",
                    "operation": "create",
                    "title": "Alpha",
                    "note_type": "atomic",
                    "source_doc": "research.docx",
                    "path": "Research/Alpha.md",
                }
            ],
        }
    )

    assert markdown.startswith("# Daily Digest — 2026-06-14")
    assert "| Total notes | 3 |" in markdown
    assert "[[Gamma]]" in markdown
    assert "create" in markdown
    assert "Thin atomic notes" in markdown
