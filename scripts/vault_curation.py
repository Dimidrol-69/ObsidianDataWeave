"""Deterministic helpers for vault curation commands."""

from __future__ import annotations

import re
from pathlib import Path

try:
    from scripts.audit_vault import NoteRecord
except ModuleNotFoundError:
    from audit_vault import NoteRecord


TOKEN_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9]{3,}")
RELATED_HEADERS = ("## Связи", "## Related", "## Related Notes", "## Связанные заметки")


def note_tokens(note: NoteRecord) -> set[str]:
    """Extract coarse tokens from title, tags, and body."""
    text = " ".join([note.title, " ".join(note.tags), note.body])
    return {match.group(0).lower() for match in TOKEN_RE.finditer(text)}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def related_score(note: NoteRecord, candidate: NoteRecord) -> float:
    """Score candidate relatedness without LLM calls."""
    note_title = set(TOKEN_RE.findall(note.title.lower()))
    cand_title = set(TOKEN_RE.findall(candidate.title.lower()))
    tag_score = _jaccard(set(note.tags), set(candidate.tags))
    title_score = _jaccard(note_title, cand_title)
    body_score = _jaccard(note_tokens(note), note_tokens(candidate))
    folder_bonus = 0.05 if note.path.parent == candidate.path.parent else 0.0
    return min(1.0, 0.45 * tag_score + 0.20 * title_score + 0.30 * body_score + folder_bonus)


def rank_related_candidates(
    note: NoteRecord,
    candidates: list[NoteRecord],
    *,
    min_score: float = 0.12,
    max_links: int = 4,
) -> list[dict]:
    """Return the best related note candidates for one note."""
    ranked: list[dict] = []
    existing = set(note.links)
    for candidate in candidates:
        if candidate.path == note.path or candidate.title in existing:
            continue
        if candidate.note_type in {"digest", "source"}:
            continue
        score = related_score(note, candidate)
        if score < min_score:
            continue
        ranked.append({
            "title": candidate.title,
            "path": candidate.path,
            "score": round(score, 3),
        })
    ranked.sort(key=lambda item: (-item["score"], item["title"]))
    return ranked[:max_links]


def append_related_section(content: str, targets: list[str], *, header: str = "## Связи") -> str:
    """Append wikilinks to an existing related section, or create one."""
    missing = [target for target in targets if f"[[{target}]]" not in content]
    if not missing:
        return content

    block = "\n".join(f"- [[{target}]]" for target in missing)
    stripped = content.rstrip()
    for existing_header in RELATED_HEADERS:
        marker = f"{existing_header}\n"
        index = stripped.find(marker)
        if index == -1:
            continue
        insert_at = index + len(marker)
        return f"{stripped[:insert_at]}{block}\n{stripped[insert_at:]}\n"
    return f"{stripped}\n\n{header}\n{block}\n"


def write_text_if_changed(path: Path, content: str) -> bool:
    """Write content only if it changed."""
    old = path.read_text(encoding="utf-8")
    if old == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True
