"""inbox_triage.py - Classify notes from an Obsidian Inbox folder."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    from scripts.config import load_config
except ModuleNotFoundError:
    from config import load_config


URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b", re.IGNORECASE)


def classify_note_text(text: str) -> dict:
    """Classify note text into the next recommended action."""
    stripped = text.strip()
    lower = stripped.lower()
    words = stripped.split()
    heading_count = sum(1 for line in stripped.splitlines() if line.startswith("#"))

    if not stripped:
        return {"action": "archive", "confidence": 0.95, "reason": "empty_note"}
    if EMAIL_RE.search(stripped) or "telegram:" in lower or "linkedin" in lower:
        return {"action": "contact", "confidence": 0.85, "reason": "contact_fields"}
    if URL_RE.search(stripped) or lower.startswith("source:"):
        return {"action": "source", "confidence": 0.8, "reason": "source_reference"}
    if len(words) >= 180 or heading_count >= 2:
        return {"action": "atomize", "confidence": 0.75, "reason": "long_or_structured"}
    if len(words) < 80:
        return {"action": "enrich", "confidence": 0.7, "reason": "thin_note"}
    return {"action": "manual", "confidence": 0.5, "reason": "ambiguous"}


def scan_inbox(vault_path: Path, inbox_folder: str = "Inbox") -> dict:
    """Classify every Markdown note in the inbox folder."""
    inbox_path = vault_path / inbox_folder
    items = []
    if inbox_path.exists():
        for md_file in sorted(inbox_path.rglob("*.md"), key=lambda p: p.as_posix()):
            try:
                text = md_file.read_text(encoding="utf-8")
            except OSError:
                continue
            classification = classify_note_text(text)
            items.append({
                "path": md_file.relative_to(vault_path).as_posix(),
                "title": md_file.stem,
                **classification,
            })
    summary: dict[str, int] = {}
    for item in items:
        summary[item["action"]] = summary.get(item["action"], 0) + 1
    return {
        "summary": summary,
        "inbox_folder": inbox_folder,
        "items": items,
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Inbox Triage",
        "",
        "| Action | Count |",
        "|---|---:|",
    ]
    for action, count in sorted(report["summary"].items()):
        lines.append(f"| {action} | {count} |")
    lines.extend(["", "## Items", ""])
    if report["items"]:
        lines.extend(
            f"- {item['action']}: [[{item['title']}]] ({item['reason']}, {item['path']})"
            for item in report["items"]
        )
    else:
        lines.append("_Inbox is empty._")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify notes in the configured Inbox.")
    parser.add_argument("--folder", help="Inbox folder name relative to vault root")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", help="Optional output file path")
    args = parser.parse_args()

    config = load_config(strict=True)
    vault_path = Path(config["vault"]["vault_path"])
    inbox_cfg = config.get("inbox", {})
    inbox_folder = args.folder or inbox_cfg.get("folder", "Inbox")
    if not vault_path.exists():
        print(f"ERROR: Vault path does not exist: {vault_path}", file=sys.stderr)
        sys.exit(1)

    report = scan_inbox(vault_path, inbox_folder=inbox_folder)
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
