"""dw.py - Unified CLI wrapper for ObsidianDataWeave operations."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


COMMANDS = {
    "write": "vault_writer.py",
    "graph": "export_graph.py",
    "digest": "vault_digest.py",
    "links": "link_health.py",
    "quality": "quality_score.py",
    "inbox": "inbox_triage.py",
    "audit": "audit_vault.py",
}


def build_command(argv: list[str]) -> list[str]:
    """Map a dw subcommand to a script command."""
    if not argv:
        raise ValueError("missing subcommand")
    subcommand = argv[0]
    if subcommand not in COMMANDS:
        raise ValueError(f"unknown subcommand: {subcommand}")
    return [COMMANDS[subcommand], *argv[1:]]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Unified wrapper for ObsidianDataWeave operations.",
        usage="python scripts/dw.py <command> [args...]",
    )
    parser.add_argument("command", choices=sorted(COMMANDS))
    parser.add_argument("args", nargs=argparse.REMAINDER)
    parsed = parser.parse_args()

    script_name, *script_args = build_command([parsed.command, *parsed.args])
    script_path = Path(__file__).with_name(script_name)
    result = subprocess.run([sys.executable, str(script_path), *script_args], check=False)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
