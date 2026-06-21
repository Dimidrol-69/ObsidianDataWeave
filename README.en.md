<div align="center">

# ObsidianDataWeave

**NotebookLM, Google Drive `.docx`, Zettelkasten atomization, LLM Wiki, and FTS5 memory for your Obsidian vault. The Dimidrol fork adds a unified CLI, dry-run/diff writes, observability, quality checks, Russian command aliases, and Windows-safe paths.**

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-blueviolet)
![Codex](https://img.shields.io/badge/Codex-AGENTS.md-green)
![NotebookLM](https://img.shields.io/badge/NotebookLM-API%20Control-orange)
![LLM Wiki](https://img.shields.io/badge/LLM%20Wiki-Compiled%20Knowledge-teal)
![FTS5 Memory](https://img.shields.io/badge/FTS5-Vault%20Memory-9cf)
![Unified CLI](https://img.shields.io/badge/CLI-dw.py-2ea44f)
![Dry Run](https://img.shields.io/badge/Writes-dry--run%20%2B%20diff-blue)
![Windows CI](https://img.shields.io/badge/CI-Windows%20%2B%20Linux-informational)

---

🇷🇺 **[Читать по-русски → README.md](README.md)**

</div>

---

## What is this

ObsidianDataWeave turns Claude Code and Codex into a programmable control plane for NotebookLM and your Obsidian vault.

The upstream project idea is preserved:

- run NotebookLM research and manage sources programmatically;
- import `.docx` documents from Google Drive;
- atomize documents and notes into Zettelkasten-style notes;
- generate MOCs, tags, and `[[wikilinks]]`;
- maintain a separate **LLM Wiki** layer as a compiled knowledge base;
- search the vault through a local SQLite **FTS5 memory** index.

The Dimidrol fork adds an operational layer for day-to-day vault maintenance:

- unified CLI: `python scripts/dw.py ...`;
- safe `--dry-run --diff` for write operations;
- append-only changelog, graph export, and daily digest;
- link health checker, quality score, and inbox triage;
- Russian command aliases for agents;
- Windows-safe path normalization for wiki/memory/link tooling;
- GitHub Actions matrix for Linux and Windows.

## What this fork adds

| Layer | Added behavior |
|---|---|
| Unified CLI | `dw.py` delegates to `write`, `graph`, `digest`, `links`, `quality`, `inbox`, `audit` |
| Write safety | `vault_writer.py --dry-run --diff` previews writes without changing the vault |
| Observability | `vault-changelog.md`, wikilink graph export, daily digest |
| Ops checks | Link health, note quality scoring, Inbox triage |
| Russian commands | Ready-to-use Russian phrases for Codex / Claude Code |
| Windows compatibility | POSIX-style paths for Obsidian links and Windows tests |
| CI | GitHub Actions: Ubuntu + Windows, Python 3.10-3.13 |

## Quick start

```bash
git clone https://github.com/Dimidrol-69/ObsidianDataWeave.git
cd ObsidianDataWeave
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
copy config.example.toml config.toml
python scripts/doctor.py
```

On Linux/macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
cp config.example.toml config.toml
python3 scripts/doctor.py
```

After copying `config.toml`, set your vault path:

```toml
[vault]
vault_path = "D:/Obsidian"
```

## Installation via install.sh

The upstream installer is preserved:

```bash
bash install.sh --vault-path "/path/to/your/vault"
```

Modes:

| Mode | Flag | Behavior |
|---|---|---|
| Claude | `--mode claude` | Dependencies, config, global skill in `~/.claude/` |
| Codex | `--mode codex` | Dependencies, config, `AGENTS.md` validation |
| Local | `--mode local` | Dependencies and config only |

Upgrade:

```bash
git pull
bash install.sh
python scripts/migrate.py
```

`migrate.py` idempotently adds missing `[memory]`, `[observability]`, `[inbox]`, and `[quality]` sections and refreshes the FTS5 index when enabled.

## Two ways to run

You can work through an agent or call scripts directly.

| Task | Agent phrase | CLI |
|---|---|---|
| Check setup | `проверь настройку проекта` | `python scripts/doctor.py` |
| Import `.docx` | `обработай документ "Document.docx"` | `python scripts/process.py "Document.docx"` |
| Import `.docx` without prompts | `обработай документ "Document.docx" без вопросов` | `python scripts/process.py "Document.docx" --non-interactive --on-conflict skip` |
| Process a note | `обработай заметку "Title"` | `python scripts/process_note.py "Title"` |
| Atomize a note | `атомизируй заметку "Title" без вопросов` | `python scripts/process_note.py "Title" --mode atomize --non-interactive --on-conflict skip` |
| Show duplicate candidates | `покажи кандидатов на дубли` | `python scripts/dedup_vault.py --dry-run --skip-claude` |
| Preview write diff | `покажи diff перед записью из staging "<dir>"` | `python scripts/dw.py write --staging "<dir>" --dry-run --diff --non-interactive` |
| Export graph | `покажи граф vault` | `python scripts/dw.py graph --format json` |
| Export GraphML | `экспортируй граф vault в graphml` | `python scripts/dw.py graph --format graphml --output graph.graphml` |
| Daily digest | `создай дайджест vault` | `python scripts/dw.py digest --write` |
| Check links | `проверь ссылки в vault` | `python scripts/dw.py links --format markdown` |
| Score quality | `оцени качество заметок` | `python scripts/dw.py quality --format markdown --limit 25` |
| Triage Inbox | `разбери inbox` | `python scripts/dw.py inbox --format markdown` |
| NotebookLM research | `запусти ресерч в notebook "<id>" по запросу "<query>"` | `python scripts/research_notebook.py run "<notebook_id>" "<query>"` |
| Import NotebookLM | `импортируй notebook "<id>" в Obsidian` | `python scripts/process_notebook.py "<notebook_id>"` |
| Create LLM Wiki | `создай wiki "demo"` | `python scripts/wiki_init.py demo --mode project --title "Demo"` |
| Compile LLM Wiki | `собери wiki "demo"` | `python scripts/wiki_compile.py demo --since-last-compile` |
| Lint LLM Wiki | `проверь wiki "demo"` | `python scripts/wiki_lint.py demo --strict` |

Phrases do not have to match exactly. The agent contract lives in [AGENTS.md](AGENTS.md).

## Unified CLI

`dw.py` is a thin wrapper around the main operational commands:

```bash
python scripts/dw.py write --staging "<dir>" --dry-run --diff
python scripts/dw.py graph --format graphml --output graph.graphml
python scripts/dw.py digest --write
python scripts/dw.py links --format markdown
python scripts/dw.py quality --format markdown --limit 25
python scripts/dw.py inbox --format markdown
python scripts/dw.py audit
```

Mapping:

| `dw` command | Script |
|---|---|
| `write` | `vault_writer.py` |
| `graph` | `export_graph.py` |
| `digest` | `vault_digest.py` |
| `links` | `link_health.py` |
| `quality` | `quality_score.py` |
| `inbox` | `inbox_triage.py` |
| `audit` | `audit_vault.py` |

## Write safety

All vault writes must go through `vault_writer.py`.

Before writing, preview the plan:

```bash
python scripts/vault_writer.py --staging "<dir>" --dry-run --diff --non-interactive
```

Dry-run does not:

- copy files into the vault;
- update `processed.json`;
- append to the changelog;
- refresh the FTS5 index.

## NotebookLM

NotebookLM automation uses `notebooklm-py` as a library, not the CLI. This matters because the raw CLI command `notebooklm source add-research --import-all` can duplicate sources on timeout.

Initial setup:

```bash
python -m venv .venv
.venv/Scripts/python scripts/notebooklm_setup.py --skip-login
```

Login is done separately in an interactive terminal:

```bash
.venv/Scripts/notebooklm login
```

After login, the session is stored in `~/.notebooklm/storage_state.json`.

Main commands:

```bash
python scripts/research_notebook.py run "<notebook_id>" "<query>"
python scripts/research_notebook.py dedupe "<notebook_id>" --dry-run
python scripts/process_notebook.py "<notebook_id>"
python scripts/process_notebook.py "<notebook_id>" --include-sources --include-mindmap
python scripts/fetch_notebook.py "<notebook_id>"
```

## LLM Wiki

LLM Wiki is an isolated compiled-knowledge layer inside the vault:

```text
<vault>/<wiki_folder>/<slug>/
```

Modes:

- `project` - fixed core pages: overview, architecture, components, workflows, goals-and-roadmap, glossary, open-questions;
- `corpus` - wiki around entities, concepts, comparisons, and queries.

Commands:

```bash
python scripts/wiki_init.py demo --mode project --title "Demo" --lang ru
python scripts/wiki_ingest.py demo path/to/article.md --kind articles
python scripts/wiki_compile.py demo --since-last-compile
python scripts/wiki_lint.py demo --strict
```

Safety properties:

- wiki is isolated from atomic notes, MOCs, and contacts;
- `wiki_folder` is protected against traversal, absolute paths, and path separators;
- compile preserves existing `[[wikilinks]]`;
- lost links fail with `WIKI_LINKS_LOST`.

## FTS5 memory

FTS5 memory is a local full-text index of the entire vault on stdlib SQLite. The database lives outside the vault so Obsidian sync does not touch it.

```bash
python scripts/memory_index.py status
python scripts/memory_index.py build
python scripts/memory_index.py search "query" --json
python scripts/memory_index.py update
```

If the index does not exist yet, `vault_writer.py` does not create it automatically. The first build is explicit:

```bash
python scripts/memory_index.py build
```

After that, `[memory].auto_update = true` keeps it fresh after writes.

## Observability

The fork adds three observability layers:

| Layer | Command | Purpose |
|---|---|---|
| Changelog | `vault_writer.py` | append-only write journal |
| Graph export | `python scripts/dw.py graph` | JSON/GraphML wikilink graph, PageRank |
| Digest | `python scripts/dw.py digest --write` | daily summary from changelog, graph, and audit |

Examples:

```bash
python scripts/export_graph.py --format json --output graph.json
python scripts/export_graph.py --format graphml --output graph.graphml
python scripts/export_graph.py --metric pagerank --top 10
python scripts/vault_digest.py --write
```

## Vault checks

```bash
python scripts/link_health.py --format markdown
python scripts/quality_score.py --format markdown --limit 25
python scripts/inbox_triage.py --format markdown
```

`link_health.py` understands Obsidian wikilink variants:

- `[[Page|Alias]]`
- `[[Page#Heading]]`
- `[[Page#^block-id]]`
- `[[Folder/Page]]`
- `![[Embed.png]]`

## Configuration

Key `config.toml` sections:

```toml
[vault]
vault_path = "D:/Obsidian"
notes_folder = "Research & Insights"
moc_folder = "Guides & Overviews"
source_folder = "Sources"
contacts_folder = "Networking"

[observability]
enabled = true
changelog_file = "vault-changelog.md"
digest_folder = "Daily Digest"

[inbox]
folder = "Inbox"

[quality]
min_atomic_words = 80

[wiki]
wiki_folder = "LLM Wiki"
default_mode = "project"
default_lang = "en"

[memory]
enabled = true
tokenizer = "unicode61"
auto_update = true
```

Full example: [config.example.toml](config.example.toml).

## Development

```bash
python -m pip install -r requirements-dev.txt
pytest -q
python -m py_compile scripts/*.py
```

CI runs tests on:

- Ubuntu latest;
- Windows latest;
- Python 3.10, 3.11, 3.12, 3.13.

## Syncing with upstream

Upstream: [howdeploy/ObsidianDataWeave](https://github.com/howdeploy/ObsidianDataWeave)  
Fork: [Dimidrol-69/ObsidianDataWeave](https://github.com/Dimidrol-69/ObsidianDataWeave)

Recommended flow:

```bash
git fetch origin
git fetch dimidrol
git checkout main
git merge origin/main
pytest -q
```

If an upstream patch has already been cherry-picked, use a normal merge or `-s ours` only deliberately, to mark the upstream commit as merged without overwriting fork-specific changes.
