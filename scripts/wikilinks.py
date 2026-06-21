"""Obsidian wikilink parsing helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
import re


WIKILINK_RE = re.compile(r"(!?)\[\[([^\]]+)\]\]")


@dataclass(frozen=True)
class WikiLink:
    raw: str
    target: str
    alias: str
    heading: str
    is_embed: bool


def normalize_wikilink_target(raw_target: str) -> tuple[str, str]:
    """Return normalized page target and optional heading/block reference."""
    target = raw_target.split("|", 1)[0].strip()
    page, sep, heading = target.partition("#")
    page = page.strip()
    heading = heading.strip() if sep else ""
    if "/" in page:
        page = PurePosixPath(page).name
    if page.endswith(".md"):
        page = page[:-3]
    return page, heading


def extract_wikilinks(text: str, *, include_embeds: bool = False) -> list[WikiLink]:
    """Extract normalized Obsidian wikilinks from Markdown text."""
    links: list[WikiLink] = []
    for marker, raw in WIKILINK_RE.findall(text):
        is_embed = marker == "!"
        if is_embed and not include_embeds:
            continue
        target, heading = normalize_wikilink_target(raw)
        alias = raw.split("|", 1)[1].strip() if "|" in raw else ""
        if not target:
            continue
        links.append(
            WikiLink(
                raw=raw,
                target=target,
                alias=alias,
                heading=heading,
                is_embed=is_embed,
            )
        )
    return links


def extract_wikilink_targets(text: str, *, include_embeds: bool = False) -> set[str]:
    """Extract normalized wikilink page targets."""
    return {link.target for link in extract_wikilinks(text, include_embeds=include_embeds)}
