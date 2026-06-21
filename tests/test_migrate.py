"""Tests for migrate.py — idempotent upgrade steps."""

from pathlib import Path

from scripts.migrate import ensure_config_sections, ensure_index, ensure_memory_section


def test_ensure_memory_section_added_once(tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    cfg.write_text('[vault]\nvault_path = "/tmp/v"\n', encoding="utf-8")

    assert ensure_memory_section(cfg) == "added"
    text = cfg.read_text(encoding="utf-8")
    assert "[memory]" in text and text.startswith("[vault]")  # original kept

    assert ensure_memory_section(cfg) == "present"  # idempotent
    assert text == cfg.read_text(encoding="utf-8")


def test_ensure_memory_section_no_config(tmp_path: Path) -> None:
    assert ensure_memory_section(tmp_path / "config.toml") == "no-config"


def test_ensure_config_sections_adds_ops_sections_once(tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        '[vault]\nvault_path = "/tmp/v"\n\n'
        "[quality]\nmin_atomic_words = 200\n",
        encoding="utf-8",
    )

    states = ensure_config_sections(cfg)
    text = cfg.read_text(encoding="utf-8")

    assert states["memory"] == "added"
    assert states["observability"] == "added"
    assert states["inbox"] == "added"
    assert states["quality"] == "present"
    assert "[memory]" in text
    assert "[observability]" in text
    assert "[inbox]" in text
    assert "min_atomic_words = 200" in text

    assert ensure_config_sections(cfg) == {
        "memory": "present",
        "observability": "present",
        "inbox": "present",
        "quality": "present",
    }
    assert text == cfg.read_text(encoding="utf-8")


def test_ensure_index_skips_gracefully(tmp_path: Path) -> None:
    # memory disabled
    out = ensure_index({"vault": {"vault_path": str(tmp_path)},
                        "memory": {"enabled": False}})
    assert out.startswith("skipped")
    # vault_path placeholder / missing
    out = ensure_index({"vault": {"vault_path": "/path/to/your/obsidian/vault"},
                        "memory": {"enabled": True, "db_dir": str(tmp_path)}})
    assert "vault_path not configured" in out


def test_ensure_index_builds_then_refreshes(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "note.md").write_text("# hello\n\nworld\n", encoding="utf-8")
    cfg = {"vault": {"vault_path": str(vault)},
           "memory": {"enabled": True, "db_dir": str(tmp_path / "cache"),
                      "tokenizer": "unicode61", "auto_update": True}}

    first = ensure_index(cfg)
    assert first.startswith("built: 1 notes")
    second = ensure_index(cfg)
    assert second.startswith("refreshed: 1 notes")
