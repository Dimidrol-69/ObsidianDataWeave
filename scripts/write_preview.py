"""write_preview.py - Dry-run write planning and diff rendering helpers."""

from __future__ import annotations

import difflib
from pathlib import Path


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def plan_write(
    source_path: Path,
    dest_path: Path,
    *,
    operation: str,
    title: str,
    note_type: str,
    source_doc: str = "",
) -> dict:
    """Describe a pending write without touching the destination."""
    source_text = _read_text(source_path)
    dest_exists = dest_path.exists()
    dest_text = _read_text(dest_path) if dest_exists else ""
    return {
        "operation": operation,
        "title": title,
        "note_type": note_type or "",
        "source_doc": source_doc or "",
        "source_path": str(source_path),
        "dest_path": str(dest_path),
        "dest_exists": dest_exists,
        "would_write": operation in {"create", "overwrite"},
        "source_text": source_text,
        "dest_text": dest_text,
    }


def render_unified_diff(plan: dict) -> str:
    """Render a unified diff for one write plan."""
    if not plan.get("would_write"):
        return ""
    before = plan.get("dest_text", "").splitlines(keepends=True)
    after = plan.get("source_text", "").splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(
            before,
            after,
            fromfile=plan["dest_path"],
            tofile=plan["source_path"],
        )
    )


def render_write_plan(plans: list[dict], *, include_diff: bool = False) -> str:
    """Render a human-readable dry-run report."""
    lines = ["# Write Preview", ""]
    for plan in plans:
        lines.append(
            f"- {plan['operation']}: {plan['title']} "
            f"({plan['note_type']}) -> {plan['dest_path']}"
        )
        if include_diff:
            diff = render_unified_diff(plan)
            if diff:
                lines.extend(["", "```diff", diff.rstrip(), "```", ""])
    return "\n".join(lines).rstrip() + "\n"
