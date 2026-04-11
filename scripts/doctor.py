"""doctor.py — Validate local setup for ObsidianDataWeave."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

try:
    from scripts.config import PROJECT_ROOT, REGISTRY_PATH, load_config
    from scripts.rebuild_processed import rebuild_registry
except ModuleNotFoundError:
    from config import PROJECT_ROOT, REGISTRY_PATH, load_config
    from rebuild_processed import rebuild_registry


def check_path(label: str, path: Path, *, must_exist: bool = True) -> bool:
    """Print a status line for a filesystem path."""
    exists = path.exists()
    status = "OK" if (exists or not must_exist) else "MISSING"
    print(f"{status:<8} {label}: {path}")
    return exists or not must_exist


def check_command(name: str) -> bool:
    """Print a status line for a shell command."""
    resolved = shutil.which(name)
    status = "OK" if resolved else "MISSING"
    location = resolved or "not in PATH"
    print(f"{status:<8} command `{name}`: {location}")
    return resolved is not None


def check_python_import(module: str, install_hint: str) -> bool:
    """Print a status line for a Python module import."""
    try:
        __import__(module)
        print(f"OK       python module `{module}`")
        return True
    except ImportError:
        print(f"MISSING  python module `{module}` — install with: {install_hint}")
        return False


def check_notebooklm_auth() -> None:
    """Best-effort check that notebooklm-py storage exists.

    Non-fatal: prints an informational line only. The actual storage path
    is profile-dependent, so we just look for the default location.
    """
    candidates = [
        Path.home() / ".notebooklm" / "storage_state.json",
        Path.home() / ".config" / "notebooklm" / "storage_state.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            print(f"OK       notebooklm auth: {candidate}")
            return
    print(
        "WARN     notebooklm auth: storage_state.json not found in default locations. "
        "Run `notebooklm login` once before using process_notebook.py."
    )


def main() -> None:
    ok = True

    print("ObsidianDataWeave doctor")
    print(f"Project root: {PROJECT_ROOT}")

    ok &= check_path("config.example.toml", PROJECT_ROOT / "config.example.toml")
    ok &= check_path("AGENTS.md", PROJECT_ROOT / "AGENTS.md")
    ok &= check_path("SKILL.md", PROJECT_ROOT / "SKILL.md")
    ok &= check_path("SKILL_PERSONAL.md", PROJECT_ROOT / "SKILL_PERSONAL.md")
    ok &= check_path("SKILL_CONTACTS.md", PROJECT_ROOT / "SKILL_CONTACTS.md")
    ok &= check_path("rules/atomization.md", PROJECT_ROOT / "rules" / "atomization.md")
    ok &= check_path("rules/taxonomy.md", PROJECT_ROOT / "rules" / "taxonomy.md")
    ok &= check_path("rules/personal_notes.md", PROJECT_ROOT / "rules" / "personal_notes.md")
    ok &= check_path("rules/contacts.md", PROJECT_ROOT / "rules" / "contacts.md")
    ok &= check_path("tags.yaml", PROJECT_ROOT / "tags.yaml")

    config_path = PROJECT_ROOT / "config.toml"
    ok &= check_path("config.toml", config_path)

    if config_path.exists():
        cfg = load_config(strict=True)
        vault_path = Path(cfg["vault"]["vault_path"])
        ok &= check_path("vault_path", vault_path)
        if vault_path.exists():
            rebuilt = rebuild_registry(vault_path)
            if REGISTRY_PATH.exists():
                try:
                    current = REGISTRY_PATH.read_text(encoding="utf-8")
                    current_count = len(__import__("json").loads(current))
                except Exception:
                    current_count = -1
                rebuilt_count = len(rebuilt)
                status = "OK" if current_count == rebuilt_count else "WARN"
                print(
                    f"{status:<8} processed.json coverage: file={current_count} rebuilt={rebuilt_count}",
                )
            else:
                print("WARN     processed.json coverage: file missing, rebuild recommended")

    ok &= check_command("python3")
    ok &= check_command("claude")
    ok &= check_command("codex")
    ok &= check_command("rclone")

    # NotebookLM integration (optional: only needed for process_notebook.py)
    check_python_import("notebooklm", 'pip install "notebooklm-py[browser]"')
    check_notebooklm_auth()

    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
