"""link_health.py - Check Obsidian wikilink health."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import sys
from pathlib import Path

try:
    from scripts.audit_vault import iter_notes
    from scripts.config import load_config
except ModuleNotFoundError:
    from audit_vault import iter_notes
    from config import load_config


def _relative_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def check_link_health(vault_path: Path) -> dict:
    """Return broken link, self-link, and duplicate-title issues."""
    notes = iter_notes(vault_path)
    by_title: dict[str, list] = defaultdict(list)
    for note in notes:
        by_title[note.title].append(note)

    known_titles = set(by_title)
    broken_links = []
    self_links = []

    for note in notes:
        for target in sorted(note.links):
            if target == note.title:
                self_links.append({
                    "title": note.title,
                    "path": _relative_path(vault_path, note.path),
                    "target": target,
                })
            elif target not in known_titles:
                broken_links.append({
                    "title": note.title,
                    "path": _relative_path(vault_path, note.path),
                    "target": target,
                })

    duplicate_titles = [
        {
            "title": title,
            "paths": [_relative_path(vault_path, note.path) for note in notes_with_title],
        }
        for title, notes_with_title in sorted(by_title.items())
        if len(notes_with_title) > 1
    ]

    return {
        "summary": {
            "notes": len(notes),
            "broken_links": len(broken_links),
            "self_links": len(self_links),
            "duplicate_titles": len(duplicate_titles),
        },
        "broken_links": broken_links,
        "self_links": self_links,
        "duplicate_titles": duplicate_titles,
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Link Health",
        "",
        "| Check | Count |",
        "|---|---:|",
        f"| Notes | {report['summary']['notes']} |",
        f"| Broken links | {report['summary']['broken_links']} |",
        f"| Self-links | {report['summary']['self_links']} |",
        f"| Duplicate titles | {report['summary']['duplicate_titles']} |",
        "",
        "## Broken Links",
        "",
    ]
    if report["broken_links"]:
        lines.extend(
            f"- [[{item['title']}]] -> [[{item['target']}]] ({item['path']})"
            for item in report["broken_links"]
        )
    else:
        lines.append("_No broken links._")

    lines.extend(["", "## Self Links", ""])
    if report["self_links"]:
        lines.extend(
            f"- [[{item['title']}]] links to itself ({item['path']})"
            for item in report["self_links"]
        )
    else:
        lines.append("_No self-links._")

    lines.extend(["", "## Duplicate Titles", ""])
    if report["duplicate_titles"]:
        lines.extend(
            f"- {item['title']}: {', '.join(item['paths'])}"
            for item in report["duplicate_titles"]
        )
    else:
        lines.append("_No duplicate titles._")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Check vault wikilink health.")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", help="Optional output file path")
    args = parser.parse_args()

    config = load_config(strict=True)
    vault_path = Path(config["vault"]["vault_path"])
    if not vault_path.exists():
        print(f"ERROR: Vault path does not exist: {vault_path}", file=sys.stderr)
        sys.exit(1)

    report = check_link_health(vault_path)
    output = (
        render_markdown(report)
        if args.format == "markdown"
        else json.dumps(report, ensure_ascii=False, indent=2)
    )
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
