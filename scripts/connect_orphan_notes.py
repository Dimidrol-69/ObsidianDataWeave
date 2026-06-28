"""connect_orphan_notes.py - Add related links to notes without outgoing links."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from scripts.audit_vault import NoteRecord, iter_notes
    from scripts.config import load_config
    from scripts.vault_curation import append_related_section, rank_related_candidates
except ModuleNotFoundError:
    from audit_vault import NoteRecord, iter_notes
    from config import load_config
    from vault_curation import append_related_section, rank_related_candidates


SKIP_NOTE_TYPES = {"moc", "source", "digest", "wiki"}


def _relative_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def is_orphan_candidate(note: NoteRecord) -> bool:
    """Return true for notes that should receive outgoing related links."""
    return note.note_type not in SKIP_NOTE_TYPES and not note.links and note.words > 0


def build_connection_plan(
    notes: list[NoteRecord],
    *,
    min_score: float = 0.12,
    min_links: int = 2,
    max_links: int = 4,
    limit: int | None = None,
) -> list[dict]:
    """Build a deterministic plan for adding related links."""
    plan: list[dict] = []
    candidates = [note for note in notes if note.note_type not in SKIP_NOTE_TYPES]
    for note in notes:
        if not is_orphan_candidate(note):
            continue
        related = rank_related_candidates(
            note,
            candidates,
            min_score=min_score,
            max_links=max_links,
        )
        if len(related) < min_links:
            continue
        plan.append({
            "title": note.title,
            "path": note.path,
            "links": related,
        })
        if limit is not None and len(plan) >= limit:
            break
    return plan


def apply_connection_plan(plan: list[dict]) -> int:
    """Apply planned related-link additions in place."""
    changed = 0
    for item in plan:
        path = Path(item["path"])
        content = path.read_text(encoding="utf-8")
        targets = [link["title"] for link in item["links"]]
        updated = append_related_section(content, targets)
        if updated != content:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    return changed


def render_markdown(plan: list[dict], *, root: Path) -> str:
    lines = ["# Orphan Note Connection Plan", ""]
    if not plan:
        lines.append("_No notes with enough related candidates found._")
        return "\n".join(lines) + "\n"
    for item in plan:
        lines.append(f"## [[{item['title']}]]")
        lines.append("")
        lines.append(f"Path: `{_relative_path(root, Path(item['path']))}`")
        lines.append("")
        for link in item["links"]:
            lines.append(f"- [[{link['title']}]] ({link['score']})")
        lines.append("")
    return "\n".join(lines)


def plan_to_json(plan: list[dict], *, root: Path) -> list[dict]:
    return [
        {
            "title": item["title"],
            "path": _relative_path(root, Path(item["path"])),
            "links": [
                {
                    "title": link["title"],
                    "path": _relative_path(root, Path(link["path"])),
                    "score": link["score"],
                }
                for link in item["links"]
            ],
        }
        for item in plan
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Suggest or apply 2-4 related links for notes without outgoing links."
    )
    parser.add_argument("--apply", action="store_true", help="Modify notes in place")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--min-score", type=float, default=0.12)
    parser.add_argument("--min-links", type=int, default=2)
    parser.add_argument("--max-links", type=int, default=4)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    if args.min_links < 1 or args.max_links < args.min_links:
        print("ERROR: require 1 <= --min-links <= --max-links", file=sys.stderr)
        sys.exit(1)

    config = load_config(strict=True)
    vault_path = Path(config["vault"]["vault_path"])
    if not vault_path.exists():
        print(f"ERROR: Vault path does not exist: {vault_path}", file=sys.stderr)
        sys.exit(1)

    plan = build_connection_plan(
        iter_notes(vault_path),
        min_score=args.min_score,
        min_links=args.min_links,
        max_links=args.max_links,
        limit=args.limit,
    )
    changed = apply_connection_plan(plan) if args.apply else 0

    if args.format == "json":
        print(json.dumps({
            "summary": {
                "planned_notes": len(plan),
                "changed_notes": changed,
                "dry_run": not args.apply,
            },
            "notes": plan_to_json(plan, root=vault_path),
        }, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(plan, root=vault_path))
        if args.apply:
            print(f"Changed notes: {changed}", file=sys.stderr)


if __name__ == "__main__":
    main()
