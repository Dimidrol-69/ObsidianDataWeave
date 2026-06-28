"""Tests for vault observability: changelog and digest."""

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


def test_format_changelog_row_escapes_markdown_table_cells():
    from scripts.vault_writer import format_changelog_row

    row = format_changelog_row(
        timestamp="2026-06-14T10:00:00+03:00",
        operation="create",
        title="A | B\nC",
        note_type="atomic",
        source_doc="source | doc.md",
        relative_path="Notes/A | B.md",
    )

    assert "\n" not in row.rstrip("\n")
    assert r"[[A \| B C]]" in row
    assert r"source \| doc.md" in row
    assert r"Notes/A \| B.md" in row


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
            "links": {
                "summary": {"total_links": 1, "orphan_count": 1},
                "top_orphans": [{"title": "Gamma", "path": "Research/Gamma.md", "in_degree": 0}],
                "top_connected": [{"title": "Beta", "links": 2}],
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

    assert markdown.startswith("# Daily Digest")
    assert "| Total notes | 3 |" in markdown
    assert "| Wikilinks | 1 |" in markdown
    assert "[[Gamma]]" in markdown
    assert "Top Connected Notes" in markdown
    assert "create" in markdown
    assert "Thin atomic notes" in markdown
