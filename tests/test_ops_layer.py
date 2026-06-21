"""Tests for the unified operations layer."""

from pathlib import Path


def write_note(
    path: Path,
    body: str,
    *,
    title: str | None = None,
    note_type: str = "atomic",
    tags=None,
    source_doc: str = "source.md",
) -> None:
    if tags is None:
        tags = []
    tag_lines = "\n".join(f"  - {tag}" for tag in tags)
    title = title or path.stem
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        f"note_type: {note_type}\n"
        f"source_doc: {source_doc}\n"
        "tags:\n"
        f"{tag_lines}\n"
        "---\n"
        f"# {title}\n\n"
        f"{body}\n",
        encoding="utf-8",
    )


def test_write_preview_create_and_overwrite_diff(tmp_path):
    from scripts.write_preview import plan_write, render_write_plan, render_unified_diff

    source = tmp_path / "staged.md"
    dest = tmp_path / "vault" / "Note.md"
    source.write_text("# Note\n\nNew body\n", encoding="utf-8")
    dest.parent.mkdir()
    dest.write_text("# Note\n\nOld body\n", encoding="utf-8")

    plan = plan_write(source, dest, operation="overwrite", title="Note", note_type="atomic")

    assert plan["operation"] == "overwrite"
    assert plan["would_write"] is True
    assert "overwrite" in render_write_plan([plan])
    diff = render_unified_diff(plan)
    assert "-Old body" in diff
    assert "+New body" in diff


def test_link_health_detects_broken_self_and_duplicate_titles(tmp_path):
    from scripts.link_health import check_link_health

    write_note(tmp_path / "Alpha.md", "Links to [[Missing]] and [[Alpha]].", title="Alpha")
    write_note(tmp_path / "Folder" / "Alpha copy.md", "Duplicate title.", title="Alpha")
    write_note(tmp_path / "Beta.md", "Links to [[Alpha]].", title="Beta")

    report = check_link_health(tmp_path)

    assert report["summary"]["broken_links"] == 1
    assert report["summary"]["self_links"] == 1
    assert report["summary"]["duplicate_titles"] == 1
    assert report["broken_links"][0]["target"] == "Missing"
    assert report["self_links"][0]["title"] == "Alpha"
    assert report["duplicate_titles"][0]["title"] == "Alpha"


def test_wikilink_parser_normalizes_obsidian_variants():
    from scripts.wikilinks import extract_wikilink_targets

    text = "\n".join(
        [
            "[[Note A|human alias]]",
            "[[Note A#Section]]",
            "[[Folder/Note A]]",
            "![[Image.png]]",
            "[[Note A#^block-id]]",
        ]
    )

    assert extract_wikilink_targets(text) == {"Note A"}


def test_link_health_accepts_obsidian_link_variants(tmp_path):
    from scripts.link_health import check_link_health

    write_note(tmp_path / "Folder" / "Note A.md", "Target note.", title="Note A")
    write_note(
        tmp_path / "Source.md",
        "\n".join(
            [
                "[[Note A|alias]]",
                "[[Note A#Section]]",
                "[[Folder/Note A]]",
                "![[Image.png]]",
                "[[Note A#^block-id]]",
            ]
        ),
        title="Source",
    )

    report = check_link_health(tmp_path)

    assert report["summary"]["broken_links"] == 0


def test_quality_score_ranks_connected_complete_note_higher(tmp_path):
    from scripts.audit_vault import iter_notes
    from scripts.export_graph import build_graph
    from scripts.quality_score import score_vault

    write_note(
        tmp_path / "Strong.md",
        ("A complete atomic note with enough words " * 12) + "[[Helper]].",
        title="Strong",
        tags=["ai/llm", "data/graph"],
    )
    write_note(tmp_path / "Helper.md", "Backlink to [[Strong]].", title="Helper", tags=["data/graph"])
    write_note(tmp_path / "Weak.md", "Tiny.", title="Weak", tags=[])

    scores = {item["title"]: item for item in score_vault(iter_notes(tmp_path), build_graph(tmp_path))}

    assert scores["Strong"]["score"] > scores["Weak"]["score"]
    assert "thin" in scores["Weak"]["issues"]
    assert "no_tags" in scores["Weak"]["issues"]


def test_quality_score_uses_configurable_atomic_word_threshold(tmp_path):
    from scripts.audit_vault import iter_notes
    from scripts.export_graph import build_graph
    from scripts.quality_score import score_vault

    write_note(
        tmp_path / "Borderline.md",
        "word " * 120,
        title="Borderline",
        tags=["ai/llm"],
    )

    default_scores = {
        item["title"]: item
        for item in score_vault(iter_notes(tmp_path), build_graph(tmp_path))
    }
    strict_scores = {
        item["title"]: item
        for item in score_vault(
            iter_notes(tmp_path),
            build_graph(tmp_path),
            min_atomic_words=200,
        )
    }

    assert "thin" not in default_scores["Borderline"]["issues"]
    assert "thin" in strict_scores["Borderline"]["issues"]
    assert strict_scores["Borderline"]["score"] < default_scores["Borderline"]["score"]


def test_inbox_triage_classifies_common_note_shapes(tmp_path):
    from scripts.inbox_triage import classify_note_text

    assert classify_note_text("Email: a@example.com\nTelegram: @alpha")["action"] == "contact"
    assert classify_note_text("Source: https://example.com/article")["action"] == "source"
    assert classify_note_text("One two three.")["action"] == "enrich"
    assert classify_note_text(("Long idea. " * 120) + "\n## Second idea")["action"] == "atomize"
    assert classify_note_text("")["action"] == "archive"


def test_dw_builds_expected_script_commands():
    from scripts.dw import build_command

    assert build_command(["graph", "--format", "graphml"]) == [
        "export_graph.py",
        "--format",
        "graphml",
    ]
    assert build_command(["digest", "--write"]) == ["vault_digest.py", "--write"]
    assert build_command(["links", "--format", "markdown"]) == [
        "link_health.py",
        "--format",
        "markdown",
    ]
