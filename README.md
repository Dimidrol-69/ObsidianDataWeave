<div align="center">

# ObsidianDataWeave

**NotebookLM, Google Drive `.docx`, Zettelkasten-атомизация, LLM Wiki и FTS5-память для Obsidian vault. Форк Dimidrol добавляет единый CLI, dry-run/diff для записей, observability-слой, проверки качества, русские команды и Windows-safe пути.**

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

🇬🇧 **[Read in English → README.en.md](README.en.md)**

</div>

---

## Что это

ObsidianDataWeave превращает Claude Code и Codex в программный пульт управления NotebookLM и Obsidian vault.

Основная идея upstream-проекта сохранена:

- запускать NotebookLM research и управлять источниками программно;
- импортировать `.docx` из Google Drive;
- превращать документы и заметки в атомарные Zettelkasten-заметки;
- строить MOC, теги и `[[wikilinks]]`;
- вести отдельный **LLM Wiki**-слой как compiled knowledge base;
- искать по vault через локальную **FTS5-память** на SQLite.

Форк добавляет операционный слой для ежедневной работы с vault:

- единый CLI `python scripts/dw.py ...`;
- безопасный `--dry-run --diff` для write-операций;
- append-only changelog, graph export и daily digest;
- link health checker, quality score и inbox triage;
- русские команды для агента;
- Windows-safe path normalization для wiki/memory/link tooling;
- GitHub Actions matrix на Linux и Windows.

## Чем форк отличается от upstream

| Слой | Что добавлено |
|---|---|
| Unified CLI | `dw.py` делегирует в `write`, `graph`, `digest`, `links`, `quality`, `inbox`, `audit` |
| Write safety | `vault_writer.py --dry-run --diff` показывает будущие записи без изменения vault |
| Observability | `vault-changelog.md`, wikilink graph export, daily digest |
| Ops checks | Проверка ссылок, оценка качества заметок, разбор Inbox |
| Russian commands | Готовые формулировки для Codex / Claude Code на русском |
| Windows compatibility | POSIX-style пути для Obsidian-ссылок и тесты на Windows |
| CI | GitHub Actions: Ubuntu + Windows, Python 3.10-3.13 |

## Быстрый старт

```bash
git clone https://github.com/Dimidrol-69/ObsidianDataWeave.git
cd ObsidianDataWeave
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
copy config.example.toml config.toml
python scripts/doctor.py
```

На Linux/macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
cp config.example.toml config.toml
python3 scripts/doctor.py
```

После копирования `config.toml` укажите свой vault:

```toml
[vault]
vault_path = "D:/Obsidian"
```

## Установка через install.sh

Upstream installer сохранен:

```bash
bash install.sh --vault-path "/path/to/your/vault"
```

Режимы:

| Режим | Флаг | Что делает |
|---|---|---|
| Claude | `--mode claude` | Зависимости, config, глобальный skill в `~/.claude/` |
| Codex | `--mode codex` | Зависимости, config, проверка `AGENTS.md` |
| Local | `--mode local` | Только зависимости и config |

Обновление:

```bash
git pull
bash install.sh
python scripts/migrate.py
```

`migrate.py` идемпотентно добавляет недостающие секции `[memory]`, `[observability]`, `[inbox]`, `[quality]` и обновляет FTS5 index, если он включен.

## Два способа запуска

Можно работать через агента или напрямую через CLI.

| Задача | Фраза для агента | CLI |
|---|---|---|
| Проверить окружение | `проверь настройку проекта` | `python scripts/doctor.py` |
| Импортировать `.docx` | `обработай документ "Document.docx"` | `python scripts/process.py "Document.docx"` |
| Импортировать `.docx` без вопросов | `обработай документ "Document.docx" без вопросов` | `python scripts/process.py "Document.docx" --non-interactive --on-conflict skip` |
| Обработать заметку | `обработай заметку "Название"` | `python scripts/process_note.py "Название"` |
| Атомизировать заметку | `атомизируй заметку "Название" без вопросов` | `python scripts/process_note.py "Название" --mode atomize --non-interactive --on-conflict skip` |
| Найти дубли | `покажи кандидатов на дубли` | `python scripts/dedup_vault.py --dry-run --skip-claude` |
| Посмотреть diff перед записью | `покажи diff перед записью из staging "<dir>"` | `python scripts/dw.py write --staging "<dir>" --dry-run --diff --non-interactive` |
| Экспортировать граф | `покажи граф vault` | `python scripts/dw.py graph --format json` |
| Экспортировать GraphML | `экспортируй граф vault в graphml` | `python scripts/dw.py graph --format graphml --output graph.graphml` |
| Daily digest | `создай дайджест vault` | `python scripts/dw.py digest --write` |
| Проверить ссылки | `проверь ссылки в vault` | `python scripts/dw.py links --format markdown` |
| Оценить качество | `оцени качество заметок` | `python scripts/dw.py quality --format markdown --limit 25` |
| Разобрать Inbox | `разбери inbox` | `python scripts/dw.py inbox --format markdown` |
| NotebookLM research | `запусти ресерч в notebook "<id>" по запросу "<query>"` | `python scripts/research_notebook.py run "<notebook_id>" "<query>"` |
| Импорт NotebookLM | `импортируй notebook "<id>" в Obsidian` | `python scripts/process_notebook.py "<notebook_id>"` |
| Создать LLM Wiki | `создай wiki "demo"` | `python scripts/wiki_init.py demo --mode project --title "Demo"` |
| Собрать LLM Wiki | `собери wiki "demo"` | `python scripts/wiki_compile.py demo --since-last-compile` |
| Проверить LLM Wiki | `проверь wiki "demo"` | `python scripts/wiki_lint.py demo --strict` |

Фразы не обязаны совпадать дословно. Agent contract находится в [AGENTS.md](AGENTS.md).

## Unified CLI

`dw.py` - тонкий wrapper над основными операциями:

```bash
python scripts/dw.py write --staging "<dir>" --dry-run --diff
python scripts/dw.py graph --format graphml --output graph.graphml
python scripts/dw.py digest --write
python scripts/dw.py links --format markdown
python scripts/dw.py quality --format markdown --limit 25
python scripts/dw.py inbox --format markdown
python scripts/dw.py audit
```

Маппинг:

| `dw` command | Script |
|---|---|
| `write` | `vault_writer.py` |
| `graph` | `export_graph.py` |
| `digest` | `vault_digest.py` |
| `links` | `link_health.py` |
| `quality` | `quality_score.py` |
| `inbox` | `inbox_triage.py` |
| `audit` | `audit_vault.py` |

## Безопасность записи

Все записи в vault должны проходить через `vault_writer.py`.

Перед любой записью можно посмотреть план:

```bash
python scripts/vault_writer.py --staging "<dir>" --dry-run --diff --non-interactive
```

Dry-run не делает:

- копирование файлов в vault;
- изменение `processed.json`;
- запись в changelog;
- обновление FTS5 index.

## NotebookLM

NotebookLM automation работает через `notebooklm-py` как библиотеку, а не через CLI. Это важно: прямой CLI `notebooklm source add-research --import-all` может дублировать источники при timeout.

Первичная установка:

```bash
python -m venv .venv
.venv/Scripts/python scripts/notebooklm_setup.py --skip-login
```

Логин выполняется отдельно в интерактивном терминале:

```bash
.venv/Scripts/notebooklm login
```

После входа сессия хранится в `~/.notebooklm/storage_state.json`.

Основные команды:

```bash
python scripts/research_notebook.py run "<notebook_id>" "<query>"
python scripts/research_notebook.py dedupe "<notebook_id>" --dry-run
python scripts/process_notebook.py "<notebook_id>"
python scripts/process_notebook.py "<notebook_id>" --include-sources --include-mindmap
python scripts/fetch_notebook.py "<notebook_id>"
```

## LLM Wiki

LLM Wiki - изолированный compiled-knowledge слой внутри vault:

```text
<vault>/<wiki_folder>/<slug>/
```

Режимы:

- `project` - фиксированные core pages: overview, architecture, components, workflows, goals-and-roadmap, glossary, open-questions;
- `corpus` - wiki вокруг entities, concepts, comparisons и queries.

Команды:

```bash
python scripts/wiki_init.py demo --mode project --title "Demo" --lang ru
python scripts/wiki_ingest.py demo path/to/article.md --kind articles
python scripts/wiki_compile.py demo --since-last-compile
python scripts/wiki_lint.py demo --strict
```

Свойства безопасности:

- wiki живет отдельно от atomic notes, MOC и contacts;
- `wiki_folder` защищен от traversal, absolute paths и path separators;
- compile сохраняет существующие `[[wikilinks]]`;
- потеря ссылок приводит к `WIKI_LINKS_LOST`.

## FTS5-память

FTS5 memory - локальный полнотекстовый index всего vault на stdlib SQLite. База хранится вне vault, чтобы синхронизация Obsidian не трогала ее.

```bash
python scripts/memory_index.py status
python scripts/memory_index.py build
python scripts/memory_index.py search "запрос" --json
python scripts/memory_index.py update
```

Если index еще не создан, `vault_writer.py` не создает его автоматически. Первый build явный:

```bash
python scripts/memory_index.py build
```

После этого `[memory].auto_update = true` поддерживает index свежим после записей.

## Observability

Форк добавляет три уровня наблюдаемости:

| Слой | Команда | Назначение |
|---|---|---|
| Changelog | `vault_writer.py` | append-only журнал write-операций |
| Graph export | `python scripts/dw.py graph` | JSON/GraphML wikilink graph, PageRank |
| Digest | `python scripts/dw.py digest --write` | daily summary по changelog, graph и audit |

Примеры:

```bash
python scripts/export_graph.py --format json --output graph.json
python scripts/export_graph.py --format graphml --output graph.graphml
python scripts/export_graph.py --metric pagerank --top 10
python scripts/vault_digest.py --write
```

## Проверки vault

```bash
python scripts/link_health.py --format markdown
python scripts/quality_score.py --format markdown --limit 25
python scripts/inbox_triage.py --format markdown
```

`link_health.py` понимает Obsidian-варианты ссылок:

- `[[Page|Alias]]`
- `[[Page#Heading]]`
- `[[Page#^block-id]]`
- `[[Folder/Page]]`
- `![[Embed.png]]`

## Конфигурация

Ключевые секции `config.toml`:

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

Полный пример: [config.example.toml](config.example.toml).

## Разработка

```bash
python -m pip install -r requirements-dev.txt
pytest -q
python -m py_compile scripts/*.py
```

CI запускает тесты на:

- Ubuntu latest;
- Windows latest;
- Python 3.10, 3.11, 3.12, 3.13.

## Синхронизация с upstream

Upstream: [howdeploy/ObsidianDataWeave](https://github.com/howdeploy/ObsidianDataWeave)  
Fork: [Dimidrol-69/ObsidianDataWeave](https://github.com/Dimidrol-69/ObsidianDataWeave)

Рекомендуемый порядок:

```bash
git fetch origin
git fetch dimidrol
git checkout main
git merge origin/main
pytest -q
```
