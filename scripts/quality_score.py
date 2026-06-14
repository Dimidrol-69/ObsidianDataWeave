"""quality_score.py - Score Obsidian notes for maintenance triage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from scripts.audit_vault import NoteRecord, iter_notes
    from scripts.config import load_config
    from scripts.export_graph import build_graph
except ModuleNotFoundError:
    from audit_vault import NoteRecord, iter_notes
    from config import load_config
    from export_graph import build_graph


def _graph_lookup(graph: dict) -> dict[str, dict]:
    return {node["title"]: node for node in graph.get("nodes", [])}


def _relative_path(path: Path, root: Path | None = None) -> str:
    if root is None:
        return path.as_posix()
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def score_note(note: NoteRecord, graph_node: dict | None = None, *, root: Path | None = None) -> dict:
    """Return a 0-100 quality score and issue tags for one note."""
    score = 100
    issues: list[str] = []
    graph_node = graph_node or {}

    if not note.frontmatter:
        score -= 15
        issues.append("no_frontmatter")
    if not note.tags:
        score -= 15
        issues.append("no_tags")
    if note.note_type == "atomic" and note.words < 80:
        score -= 20
        issues.append("thin")
    if not note.links:
        score -= 15
        issues.append("no_outlinks")
    if graph_node.get("in_degree", 0) == 0:
        score -= 15
        issues.append("orphan")
    if note.note_type in {"atomic", "source", "contact"} and not note.source_doc:
        score -= 10
        issues.append("missing_source")

    return {
        "title": note.title,
        "path": _relative_path(note.path, root),
        "score": max(score, 0),
        "words": note.words,
        "note_type": note.note_type,
        "in_degree": graph_node.get("in_degree", 0),
        "out_degree": graph_node.get("out_degree", len(note.links)),
        "issues": issues,
    }


def score_vault(notes: list[NoteRecord], graph: dict, *, root: Path | None = None) -> list[dict]:
    """Score all notes, weakest first."""
    nodes = _graph_lookup(graph)
    scores = [score_note(note, nodes.get(note.title), root=root) for note in notes]
    return sorted(scores, key=lambda item: (item["score"], item["title"]))


def render_markdown(scores: list[dict], *, limit: int = 25) -> str:
    lines = [
        "# Quality Score",
        "",
        "| Score | Note | Issues |",
        "|---:|---|---|",
    ]
    for item in scores[:limit]:
        issues = ", ".join(item["issues"]) if item["issues"] else "ok"
        lines.append(f"| {item['score']} | [[{item['title']}]] | {issues} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Score vault note quality.")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--output", help="Optional output file path")
    args = parser.parse_args()

    config = load_config(strict=True)
    vault_path = Path(config["vault"]["vault_path"])
    if not vault_path.exists():
        print(f"ERROR: Vault path does not exist: {vault_path}", file=sys.stderr)
        sys.exit(1)

    scores = score_vault(iter_notes(vault_path), build_graph(vault_path), root=vault_path)
    output = (
        render_markdown(scores, limit=args.limit)
        if args.format == "markdown"
        else json.dumps(scores[: args.limit], ensure_ascii=False, indent=2)
    )
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
