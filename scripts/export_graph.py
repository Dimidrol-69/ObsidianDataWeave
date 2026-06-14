"""export_graph.py - Export an Obsidian wikilink graph as JSON or GraphML."""

from __future__ import annotations

import argparse
from html import escape
import json
import sys
from pathlib import Path

try:
    from scripts.audit_vault import extract_wikilink_targets
    from scripts.config import load_config
    from scripts.scan_vault import SKIP_DIRS
    from scripts.vault_writer import parse_frontmatter
except ModuleNotFoundError:
    from audit_vault import extract_wikilink_targets
    from config import load_config
    from scan_vault import SKIP_DIRS
    from vault_writer import parse_frontmatter


def _body_after_frontmatter(text: str) -> str:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return text.strip()


def _title_from_text(path: Path, text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem


def _relative_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _iter_note_files(vault_path: Path) -> list[Path]:
    files: list[Path] = []
    for md_file in vault_path.rglob("*.md"):
        rel = md_file.relative_to(vault_path)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        files.append(md_file)
    return sorted(files, key=lambda p: p.as_posix())


def _compute_pagerank(
    node_ids: list[str],
    edges: list[dict],
    *,
    damping: float = 0.85,
    iterations: int = 30,
) -> dict[str, float]:
    if not node_ids:
        return {}

    count = len(node_ids)
    ranks = {node_id: 1.0 / count for node_id in node_ids}
    outlinks = {node_id: set() for node_id in node_ids}
    incoming = {node_id: set() for node_id in node_ids}

    for edge in edges:
        source = edge["source"]
        target = edge["target"]
        outlinks[source].add(target)
        incoming[target].add(source)

    for _ in range(iterations):
        dangling = sum(ranks[node_id] for node_id in node_ids if not outlinks[node_id])
        next_ranks = {}
        for node_id in node_ids:
            rank = (1.0 - damping) / count
            rank += damping * dangling / count
            for source in incoming[node_id]:
                rank += damping * ranks[source] / len(outlinks[source])
            next_ranks[node_id] = rank
        ranks = next_ranks

    return {node_id: round(ranks[node_id], 6) for node_id in node_ids}


def build_graph(vault_path: Path) -> dict:
    """Build a graph dict from Markdown notes under vault_path."""
    records: dict[str, dict] = {}
    raw_links: dict[str, set[str]] = {}

    for md_file in _iter_note_files(vault_path):
        try:
            text = md_file.read_text(encoding="utf-8")
        except OSError:
            continue

        title = _title_from_text(md_file, text)
        frontmatter = parse_frontmatter(text)
        tags = frontmatter.get("tags", [])
        if not isinstance(tags, list):
            tags = []

        records[title] = {
            "id": title,
            "title": title,
            "path": _relative_path(vault_path, md_file),
            "note_type": str(frontmatter.get("note_type", "")),
            "tags": sorted(str(tag) for tag in tags),
        }
        raw_links[title] = extract_wikilink_targets(_body_after_frontmatter(text))

    node_ids = sorted(records)
    node_set = set(node_ids)
    edges = sorted(
        (
            {"source": source, "target": target}
            for source, targets in raw_links.items()
            for target in targets
            if target in node_set and source != target
        ),
        key=lambda edge: (edge["source"], edge["target"]),
    )

    in_degree = {node_id: 0 for node_id in node_ids}
    out_degree = {node_id: 0 for node_id in node_ids}
    for edge in edges:
        out_degree[edge["source"]] += 1
        in_degree[edge["target"]] += 1

    pagerank = _compute_pagerank(node_ids, edges)
    nodes = []
    for node_id in node_ids:
        node = dict(records[node_id])
        node["in_degree"] = in_degree[node_id]
        node["out_degree"] = out_degree[node_id]
        node["is_orphan"] = in_degree[node_id] == 0
        node["pagerank"] = pagerank[node_id]
        nodes.append(node)

    return {
        "summary": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "orphan_count": sum(1 for node in nodes if node["is_orphan"]),
        },
        "nodes": nodes,
        "edges": edges,
    }


def graph_to_graphml(graph: dict) -> str:
    """Render graph data to a small GraphML document."""
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
        '  <graph id="vault" edgedefault="directed">',
    ]
    for node in graph["nodes"]:
        node_id = escape(node["id"], quote=True)
        lines.append(f'    <node id="{node_id}">')
        lines.append(f'      <data key="path">{escape(node["path"])}</data>')
        lines.append(f'      <data key="note_type">{escape(node["note_type"])}</data>')
        lines.append(f'      <data key="pagerank">{node["pagerank"]}</data>')
        lines.append("    </node>")
    for index, edge in enumerate(graph["edges"]):
        source = escape(edge["source"], quote=True)
        target = escape(edge["target"], quote=True)
        lines.append(f'    <edge id="e{index}" source="{source}" target="{target}" />')
    lines.extend(["  </graph>", "</graphml>", ""])
    return "\n".join(lines)


def _top_pagerank(graph: dict, limit: int) -> list[dict]:
    return sorted(
        (
            {"title": node["title"], "pagerank": node["pagerank"], "path": node["path"]}
            for node in graph["nodes"]
        ),
        key=lambda item: (-item["pagerank"], item["title"]),
    )[:limit]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export the configured Obsidian vault wikilink graph."
    )
    parser.add_argument("--format", choices=("json", "graphml"), default="json")
    parser.add_argument("--output", help="Optional output file path")
    parser.add_argument("--metric", choices=("pagerank",), help="Print a metric table")
    parser.add_argument("--top", type=int, default=10, help="Metric limit")
    args = parser.parse_args()

    config = load_config(strict=True)
    vault_path = Path(config["vault"]["vault_path"])
    if not vault_path.exists():
        print(f"ERROR: Vault path does not exist: {vault_path}", file=sys.stderr)
        sys.exit(1)

    graph = build_graph(vault_path)
    if args.metric == "pagerank":
        output = json.dumps(_top_pagerank(graph, args.top), ensure_ascii=False, indent=2)
    elif args.format == "graphml":
        output = graph_to_graphml(graph)
    else:
        output = json.dumps(graph, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
