"""quality_score.py - Score Obsidian notes for maintenance triage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from scripts.audit_vault import NoteRecord, iter_notes
    from scripts.config import load_config
except ModuleNotFoundError:
    from audit_vault import NoteRecord, iter_notes
    from config import load_config


def compute_link_degrees(notes: list[NoteRecord]) -> dict[str, dict]:
    """Compute in/out degrees from wikilinks without producing export artifacts."""
    titles = {note.title for note in notes}
    degrees = {
        note.title: {"in_degree": 0, "out_degree": 0}
        for note in notes
    }
    for note in notes:
        targets = {target for target in note.links if target in titles and target != note.title}
        degrees[note.title]["out_degree"] = len(targets)
        for target in targets:
            degrees[target]["in_degree"] += 1
    return degrees


def _relative_path(path: Path, root: Path | None = None) -> str:
    if root is None:
        return path.as_posix()
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def score_note(
    note: NoteRecord,
    link_degrees: dict | None = None,
    *,
    root: Path | None = None,
    min_atomic_words: int = 80,
) -> dict:
    """Return a 0-100 quality score and issue tags for one note."""
    score = 100
    issues: list[str] = []
    link_degrees = link_degrees or {}

    if not note.frontmatter:
        score -= 15
        issues.append("no_frontmatter")
    if not note.tags:
        score -= 15
        issues.append("no_tags")
    if note.note_type == "atomic" and note.words < min_atomic_words:
        score -= 20
        issues.append("thin")
    if not note.links:
        score -= 15
        issues.append("no_outlinks")
    if link_degrees.get("in_degree", 0) == 0:
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
        "in_degree": link_degrees.get("in_degree", 0),
        "out_degree": link_degrees.get("out_degree", len(note.links)),
        "issues": issues,
    }


def score_vault(
    notes: list[NoteRecord],
    *,
    root: Path | None = None,
    min_atomic_words: int = 80,
) -> list[dict]:
    """Score all notes, weakest first."""
    degrees = compute_link_degrees(notes)
    scores = [
        score_note(
            note,
            degrees.get(note.title),
            root=root,
            min_atomic_words=min_atomic_words,
        )
        for note in notes
    ]
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

    min_atomic_words = int(config.get("quality", {}).get("min_atomic_words", 80))
    scores = score_vault(
        iter_notes(vault_path),
        root=vault_path,
        min_atomic_words=min_atomic_words,
    )
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
