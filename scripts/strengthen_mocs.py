"""strengthen_mocs.py - Add structure and entry points to weak MOC notes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from scripts.audit_vault import NoteRecord, iter_notes
    from scripts.config import load_config
    from scripts.vault_curation import rank_related_candidates
except ModuleNotFoundError:
    from audit_vault import NoteRecord, iter_notes
    from config import load_config
    from vault_curation import rank_related_candidates


CONTEXT_HEADERS = ("## Контекст", "## Context")
START_HEADERS = ("## С чего начать", "## Start Here")
RELATED_HEADERS = ("## Связанные заметки", "## Related Notes", "## Related")


def _relative_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def is_moc(note: NoteRecord) -> bool:
    return note.note_type == "moc" or note.path.stem.endswith(" — MOC") or note.path.stem.endswith(" - MOC")


def has_any_header(content: str, headers: tuple[str, ...]) -> bool:
    return any(header in content for header in headers)


def build_moc_targets(
    moc: NoteRecord,
    notes: list[NoteRecord],
    *,
    min_score: float = 0.10,
    max_links: int = 8,
) -> list[str]:
    """Return existing MOC links plus related candidates."""
    by_title = {note.title: note for note in notes}
    existing = [title for title in sorted(moc.links) if title in by_title and title != moc.title]
    if len(existing) >= max_links:
        return existing[:max_links]

    candidates = [note for note in notes if not is_moc(note) and note.note_type not in {"digest", "source"}]
    ranked = rank_related_candidates(
        moc,
        candidates,
        min_score=min_score,
        max_links=max_links,
    )
    merged = list(existing)
    for item in ranked:
        if item["title"] not in merged:
            merged.append(item["title"])
        if len(merged) >= max_links:
            break
    return merged


def is_weak_moc(content: str, moc: NoteRecord, targets: list[str], *, min_links: int = 5) -> bool:
    """MOC is weak if it lacks structure or enough useful links."""
    return (
        len(targets) < min_links
        or not has_any_header(content, CONTEXT_HEADERS)
        or not has_any_header(content, START_HEADERS)
        or not has_any_header(content, RELATED_HEADERS)
    )


def build_moc_patch(content: str, moc: NoteRecord, targets: list[str]) -> str:
    """Append missing MOC sections without replacing existing content."""
    additions: list[str] = []
    title = moc.title.replace(" — MOC", "").replace(" - MOC", "").strip()

    if not has_any_header(content, CONTEXT_HEADERS):
        additions.extend([
            "## Контекст",
            "",
            (
                f"Эта карта объединяет заметки вокруг темы «{title}». "
                "Используйте ее как обзорный слой: сначала пройти ключевые входные точки, "
                "затем углубляться в отдельные атомарные заметки."
            ),
            "",
        ])

    if targets and not has_any_header(content, START_HEADERS):
        additions.extend(["## С чего начать", ""])
        for index, target in enumerate(targets[:3], start=1):
            additions.append(f"{index}. [[{target}]]")
        additions.append("")

    if targets and not has_any_header(content, RELATED_HEADERS):
        additions.extend(["## Связанные заметки", ""])
        for target in targets[:8]:
            additions.append(f"- [[{target}]]")
        additions.append("")

    if not additions:
        return content
    return content.rstrip() + "\n\n" + "\n".join(additions).rstrip() + "\n"


def build_moc_plan(
    notes: list[NoteRecord],
    *,
    min_score: float = 0.10,
    min_links: int = 5,
    max_links: int = 8,
    limit: int | None = None,
) -> list[dict]:
    """Build a plan for strengthening weak MOCs."""
    plan: list[dict] = []
    for moc in [note for note in notes if is_moc(note)]:
        content = moc.path.read_text(encoding="utf-8")
        targets = build_moc_targets(
            moc,
            notes,
            min_score=min_score,
            max_links=max_links,
        )
        if not is_weak_moc(content, moc, targets, min_links=min_links):
            continue
        updated = build_moc_patch(content, moc, targets)
        if updated == content:
            continue
        plan.append({
            "title": moc.title,
            "path": moc.path,
            "targets": targets,
            "updated": updated,
        })
        if limit is not None and len(plan) >= limit:
            break
    return plan


def apply_moc_plan(plan: list[dict]) -> int:
    changed = 0
    for item in plan:
        path = Path(item["path"])
        old = path.read_text(encoding="utf-8")
        if old != item["updated"]:
            path.write_text(item["updated"], encoding="utf-8")
            changed += 1
    return changed


def render_markdown(plan: list[dict], *, root: Path) -> str:
    lines = ["# MOC Strengthening Plan", ""]
    if not plan:
        lines.append("_No weak MOCs with useful targets found._")
        return "\n".join(lines) + "\n"
    for item in plan:
        lines.append(f"## [[{item['title']}]]")
        lines.append("")
        lines.append(f"Path: `{_relative_path(root, Path(item['path']))}`")
        lines.append("")
        for target in item["targets"][:8]:
            lines.append(f"- [[{target}]]")
        lines.append("")
    return "\n".join(lines)


def plan_to_json(plan: list[dict], *, root: Path) -> list[dict]:
    return [
        {
            "title": item["title"],
            "path": _relative_path(root, Path(item["path"])),
            "targets": item["targets"],
        }
        for item in plan
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add context, start-here, and related-note sections to weak MOCs."
    )
    parser.add_argument("--apply", action="store_true", help="Modify MOC notes in place")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--min-score", type=float, default=0.10)
    parser.add_argument("--min-links", type=int, default=5)
    parser.add_argument("--max-links", type=int, default=8)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    config = load_config(strict=True)
    vault_path = Path(config["vault"]["vault_path"])
    if not vault_path.exists():
        print(f"ERROR: Vault path does not exist: {vault_path}", file=sys.stderr)
        sys.exit(1)

    plan = build_moc_plan(
        iter_notes(vault_path),
        min_score=args.min_score,
        min_links=args.min_links,
        max_links=args.max_links,
        limit=args.limit,
    )
    changed = apply_moc_plan(plan) if args.apply else 0

    if args.format == "json":
        print(json.dumps({
            "summary": {
                "planned_mocs": len(plan),
                "changed_mocs": changed,
                "dry_run": not args.apply,
            },
            "mocs": plan_to_json(plan, root=vault_path),
        }, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(plan, root=vault_path))
        if args.apply:
            print(f"Changed MOCs: {changed}", file=sys.stderr)


if __name__ == "__main__":
    main()
