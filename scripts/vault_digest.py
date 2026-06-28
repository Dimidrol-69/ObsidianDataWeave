"""vault_digest.py - Build a daily Markdown digest for an Obsidian vault."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import json
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from scripts.audit_vault import audit_notes, iter_notes
    from scripts.config import load_config
    from scripts.quality_score import compute_link_degrees
    from scripts.vault_writer import get_observability_config
except ModuleNotFoundError:
    from audit_vault import audit_notes, iter_notes
    from config import load_config
    from quality_score import compute_link_degrees
    from vault_writer import get_observability_config


def _relative_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def parse_changelog_rows(changelog_text: str, *, limit: int = 10) -> list[dict]:
    """Parse recent rows from the Markdown changelog table."""
    rows: list[dict] = []
    for line in changelog_text.splitlines():
        if not line.startswith("| "):
            continue
        if "Timestamp" in line or "---" in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 6:
            continue
        title = cells[2]
        if title.startswith("[[") and title.endswith("]]"):
            title = title[2:-2]
        rows.append({
            "timestamp": cells[0],
            "operation": cells[1],
            "title": title,
            "note_type": cells[3],
            "source_doc": cells[4],
            "path": cells[5],
        })
    return list(reversed(rows[-limit:]))


def collect_recent_changes(config: dict, *, limit: int = 10) -> list[dict]:
    obs_cfg = get_observability_config(config)
    vault_path = Path(config["vault"]["vault_path"])
    changelog_path = vault_path / obs_cfg["changelog_file"]
    if not changelog_path.exists():
        return []
    try:
        return parse_changelog_rows(changelog_path.read_text(encoding="utf-8"), limit=limit)
    except OSError:
        return []


def collect_digest_data(config: dict, digest_date: str) -> dict:
    """Collect scan, link, audit, and changelog summaries for a digest."""
    vault_path = Path(config["vault"]["vault_path"])
    notes = iter_notes(vault_path)
    audit = audit_notes(notes)
    degrees = compute_link_degrees(notes)

    folders = Counter()
    note_types = Counter()
    for note in notes:
        parent = _relative_path(vault_path, note.path.parent)
        folders[parent or "."] += 1
        note_types[note.note_type or "(none)"] += 1

    total_links = sum(item["out_degree"] for item in degrees.values())
    orphan_notes = sorted(
        (
            {
                "title": note.title,
                "path": _relative_path(vault_path, note.path),
                "in_degree": degrees.get(note.title, {}).get("in_degree", 0),
            }
            for note in notes
            if degrees.get(note.title, {}).get("in_degree", 0) == 0
        ),
        key=lambda item: (item["path"], item["title"]),
    )[:5]
    top_connected = sorted(
        (
            {
                "title": note.title,
                "links": (
                    degrees.get(note.title, {}).get("in_degree", 0)
                    + degrees.get(note.title, {}).get("out_degree", 0)
                ),
            }
            for note in notes
        ),
        key=lambda item: (-item["links"], item["title"]),
    )[:5]

    return {
        "date": digest_date,
        "summary": {
            "total_notes": len(notes),
            "folders": dict(sorted(folders.items())),
            "note_types": dict(sorted(note_types.items())),
        },
        "links": {
            "summary": {
                "total_links": total_links,
                "orphan_count": len([
                    note for note in notes
                    if degrees.get(note.title, {}).get("in_degree", 0) == 0
                ]),
            },
            "top_orphans": orphan_notes,
            "top_connected": top_connected,
        },
        "audit": {"summary": audit["summary"]},
        "recent_changes": collect_recent_changes(config),
    }


def _table_from_mapping(mapping: dict) -> str:
    if not mapping:
        return "_No data._\n"
    lines = ["| Key | Count |", "|---|---:|"]
    for key, value in mapping.items():
        lines.append(f"| {key} | {value} |")
    return "\n".join(lines) + "\n"


def render_digest(data: dict) -> str:
    """Render collected digest data to Markdown."""
    summary = data["summary"]
    link_summary = data["links"]["summary"]
    audit_summary = data["audit"]["summary"]

    lines = [
        f"# Daily Digest — {data['date']}",
        "",
        "## Overview",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Total notes | {summary['total_notes']} |",
        f"| Wikilinks | {link_summary['total_links']} |",
        f"| Orphan notes | {link_summary['orphan_count']} |",
        "",
        "## Note Types",
        "",
        _table_from_mapping(summary["note_types"]).rstrip(),
        "",
        "## Folders",
        "",
        _table_from_mapping(summary["folders"]).rstrip(),
        "",
        "## Top Orphans",
        "",
    ]

    orphans = data["links"]["top_orphans"]
    if orphans:
        lines.extend(
            f"- [[{item['title']}]] - {item['path']}" for item in orphans
        )
    else:
        lines.append("_No orphan notes._")

    lines.extend(["", "## Top Connected Notes", ""])
    connected = data["links"]["top_connected"]
    if connected:
        lines.extend(
            f"- [[{item['title']}]] - {item['links']} links" for item in connected
        )
    else:
        lines.append("_No linked notes._")

    lines.extend([
        "",
        "## Audit",
        "",
        "| Check | Count |",
        "|---|---:|",
        f"| Empty notes | {audit_summary['empty_notes']} |",
        f"| Thin atomic notes | {audit_summary['thin_atomic_notes']} |",
        f"| Atomic notes without links | {audit_summary['atomic_notes_without_links']} |",
        f"| Unlinked similar pairs | {audit_summary['unlinked_similar_pairs']} |",
        "",
        "## Recent Changes",
        "",
    ])

    changes = data["recent_changes"]
    if changes:
        lines.extend([
            "| Timestamp | Operation | Note | Type | Source | Path |",
            "|---|---|---|---|---|---|",
        ])
        for change in changes:
            lines.append(
                f"| {change['timestamp']} | {change['operation']} | "
                f"[[{change['title']}]] | {change['note_type']} | "
                f"{change['source_doc']} | {change['path']} |"
            )
    else:
        lines.append("_No recent changelog entries._")

    lines.append("")
    return "\n".join(lines)


def _staged_digest(markdown: str, digest_date: str) -> str:
    return (
        "---\n"
        "note_type: digest\n"
        f"date: {digest_date}\n"
        "source_doc: vault_digest\n"
        "tags:\n"
        "  - vault/digest\n"
        "---\n"
        f"{markdown}"
    )


def write_digest_via_vault_writer(markdown: str, digest_date: str) -> None:
    """Write the digest through vault_writer.py to preserve the write boundary."""
    writer = Path(__file__).with_name("vault_writer.py")
    with tempfile.TemporaryDirectory(prefix="vault_digest_") as tmp:
        staging = Path(tmp)
        digest_file = staging / f"{digest_date}.md"
        digest_file.write_text(_staged_digest(markdown, digest_date), encoding="utf-8")
        subprocess.run(
            [
                sys.executable,
                str(writer),
                "--staging",
                str(staging),
                "--non-interactive",
                "--on-conflict",
                "overwrite",
            ],
            check=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a daily Markdown digest for the configured vault."
    )
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--write", action="store_true", help="Write via vault_writer.py")
    parser.add_argument("--output", help="Write Markdown to this path instead of stdout")
    parser.add_argument("--json", action="store_true", help="Print collected data as JSON")
    args = parser.parse_args()

    config = load_config(strict=True)
    vault_path = Path(config["vault"]["vault_path"])
    if not vault_path.exists():
        print(f"ERROR: Vault path does not exist: {vault_path}", file=sys.stderr)
        sys.exit(1)

    data = collect_digest_data(config, args.date)
    if args.json:
        output = json.dumps(data, ensure_ascii=False, indent=2)
    else:
        output = render_digest(data)

    if args.write:
        write_digest_via_vault_writer(output, args.date)
    elif args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
