# ObsidianDataWeave Fork Notes

Форк сохраняет базовую идею upstream-проекта: превращать документы, заметки и исследовательские материалы в структурированный Obsidian vault.

Здесь описаны только дополнительные слои форка:

- автоматизация NotebookLM;
- LLM Wiki внутри vault;
- наблюдаемость и проверки качества;
- единый CLI для повседневных операций;
- совместимость LLM Wiki с Windows.

## Два способа запуска

Основные операции можно запускать двумя способами:

1. Через агента: сформулировать задачу для Codex или Claude Code на русском языке.
2. Напрямую: выполнить CLI-команду из корня репозитория.

| Задача | Фраза для агента | CLI |
|---|---|---|
| Проверить окружение | `проверь настройку проекта` | `python scripts/doctor.py` |
| Импортировать `.docx` | `обработай документ "Document.docx"` | `python scripts/process.py "Document.docx"` |
| Импортировать `.docx` без вопросов | `обработай документ "Document.docx" без вопросов` | `python scripts/process.py "Document.docx" --non-interactive --on-conflict skip` |
| Обработать существующую заметку | `обработай заметку "Название заметки"` | `python scripts/process_note.py "Название заметки"` |
| Атомизировать заметку | `атомизируй заметку "Название заметки" без вопросов` | `python scripts/process_note.py "Название заметки" --mode atomize --non-interactive --on-conflict skip` |
| Найти кандидатов на дубли | `покажи кандидатов на дубли` | `python scripts/dedup_vault.py --dry-run --skip-claude` |
| Запустить dedup review | `запусти полный dedup review` | `python scripts/dedup_vault.py` |
| Посмотреть diff перед записью | `покажи diff перед записью из staging "<dir>"` | `python scripts/dw.py write --staging "<dir>" --dry-run --diff --non-interactive` |
| Экспортировать граф в JSON | `покажи граф vault` | `python scripts/dw.py graph --format json` |
| Экспортировать граф в GraphML | `экспортируй граф vault в graphml` | `python scripts/dw.py graph --format graphml --output graph.graphml` |
| Показать связанные заметки | `покажи топ связанных заметок` | `python scripts/dw.py graph --metric pagerank --top 10` |
| Создать daily digest | `создай дайджест vault` | `python scripts/dw.py digest --write` |
| Проверить ссылки | `проверь ссылки в vault` | `python scripts/dw.py links --format markdown` |
| Оценить качество заметок | `оцени качество заметок` | `python scripts/dw.py quality --format markdown --limit 25` |
| Разобрать Inbox | `разбери inbox` | `python scripts/dw.py inbox --format markdown` |
| Запустить NotebookLM research | `запусти ресерч в notebook "<id>" по запросу "<query>"` | `python scripts/research_notebook.py run "<notebook_id>" "<query>"` |
| Почистить источники NotebookLM | `почисти дубли источников в notebook "<id>"` | `python scripts/research_notebook.py dedupe "<notebook_id>" --dry-run` |
| Импортировать NotebookLM notes | `импортируй notebook "<id>" в Obsidian` | `python scripts/process_notebook.py "<notebook_id>"` |
| Импортировать NotebookLM с источниками | `импортируй notebook "<id>" с источниками и mind map` | `python scripts/process_notebook.py "<notebook_id>" --include-sources --include-mindmap` |
| Создать LLM Wiki | `создай wiki "demo"` | `python scripts/wiki_init.py demo --mode project --title "Demo"` |
| Добавить материал в LLM Wiki | `добавь в wiki "demo" файл "path/to/article.md"` | `python scripts/wiki_ingest.py demo path/to/article.md --kind articles` |
| Собрать LLM Wiki | `собери wiki "demo"` | `python scripts/wiki_compile.py demo --since-last-compile` |
| Проверить LLM Wiki | `проверь wiki "demo"` | `python scripts/wiki_lint.py demo --strict` |

Фразы для агента не обязаны совпадать дословно. Они приведены как рекомендуемые формулировки.

## Что добавлено

### NotebookLM automation

Форк добавляет программный слой для работы с NotebookLM через `notebooklm-py`.

Возможности:

- deep/fast research в существующем notebook;
- безопасная дедупликация источников;
- выгрузка заметок, источников и mind map;
- атомизация NotebookLM notes в Obsidian через существующий Zettelkasten pipeline.

Первый интерактивный вход в Google выполняется отдельно:

```bash
.venv/bin/notebooklm login
```

После входа сессия хранится в `~/.notebooklm/storage_state.json`.

### LLM Wiki

LLM Wiki - изолированный wiki-слой внутри vault. Это не RAG и не набор атомарных заметок, а compiled knowledge base, которая обновляется через явный merge.

Wiki-space хранится здесь:

```text
<vault>/<wiki_folder>/<slug>/
```

Поддерживаются два режима:

- `project` - фиксированные core pages: overview, architecture, components, workflows, goals-and-roadmap, glossary, open-questions;
- `corpus` - wiki вокруг entities, concepts, comparisons и queries без обязательного набора core pages.

Защита ссылок: при update существующие `[[wikilinks]]` должны сохраняться. Если LLM теряет старые ссылки, compile завершается ошибкой `WIKI_LINKS_LOST`.

### Observability layer

Слой наблюдаемости показывает состояние vault и историю операций.

Компоненты:

- `vault-changelog.md` - append-only журнал операций записи;
- `export_graph.py` - экспорт wikilink-графа;
- `vault_digest.py` - ежедневный digest по changelog, graph и audit.

`vault_digest.py --write` пишет digest обратно в vault через `vault_writer.py` и не обходит общий write boundary.

### Unified Ops Layer

Операционный слой собирает ежедневное обслуживание vault в отдельные проверки.

#### Dry-run diff

`vault_writer.py` показывает будущие write-операции без изменения vault:

```bash
python scripts/vault_writer.py --staging "<dir>" --dry-run --diff --non-interactive
```

В dry-run режиме не выполняются:

- копирование файлов в vault;
- обновление `processed.json`;
- запись в changelog.

#### Link health checker

Проверяет broken links, self-links и duplicate titles:

```bash
python scripts/link_health.py --format markdown
python scripts/link_health.py --format json --output link-health.json
```

#### Quality score

Считает score 0-100 для заметок и показывает слабые места:

```bash
python scripts/quality_score.py --format markdown
python scripts/quality_score.py --format json --limit 50
```

Сейчас учитываются:

- наличие frontmatter;
- теги;
- длина atomic note;
- outlinks;
- backlinks и orphan status;
- `source_doc`.

#### Inbox triage

Классифицирует заметки из `Inbox/` и предлагает следующее действие:

```bash
python scripts/inbox_triage.py --format markdown
python scripts/inbox_triage.py --folder "Inbox" --format json
```

Категории:

- `contact`;
- `source`;
- `atomize`;
- `enrich`;
- `archive`;
- `manual`.

MVP работает в read-only режиме: предлагает next action, но не перемещает и не переписывает заметки.

### Единый CLI

`dw.py` - thin wrapper для основных операционных команд:

```bash
python scripts/dw.py write --staging "<dir>" --dry-run --diff
python scripts/dw.py graph --format graphml --output graph.graphml
python scripts/dw.py digest --write
python scripts/dw.py links --format markdown
python scripts/dw.py quality --format markdown
python scripts/dw.py inbox --format markdown
python scripts/dw.py audit
```

`dw.py` не дублирует бизнес-логику. Он делегирует в существующие скрипты:

| `dw` command | Script |
|---|---|
| `write` | `vault_writer.py` |
| `graph` | `export_graph.py` |
| `digest` | `vault_digest.py` |
| `links` | `link_health.py` |
| `quality` | `quality_score.py` |
| `inbox` | `inbox_triage.py` |
| `audit` | `audit_vault.py` |

### Windows compatibility для LLM Wiki

Исправлена обработка путей в wiki compile/lint на Windows.

Внутренние wiki paths нормализуются как POSIX-style строки:

```text
pages/architecture.md
raw/docs/article.md
entities/postgres.md
```

Это нужно для wiki-контракта, glob matching и тестов: они ожидают `/`, а Windows по умолчанию использует `\`.

## Конфигурация

Пример дополнительных секций `config.toml`:

```toml
[observability]
enabled = true
changelog_file = "vault-changelog.md"
digest_folder = "Daily Digest"

[inbox]
folder = "Inbox"

[quality]
min_atomic_words = 80

[notebooklm]
profile = ""
include_sources = false
include_mindmap = false

[wiki]
wiki_folder = "LLM Wiki"
default_mode = "project"
default_lang = "en"
max_raw_per_compile = 30
```

Существующий `config.toml` не перезаписывается автоматически. Для новых опций используйте `config.example.toml`.

## Ежедневный workflow

Проверить входящие заметки:

```bash
python scripts/dw.py inbox --format markdown
```

Проверить ссылки:

```bash
python scripts/dw.py links --format markdown
```

Найти слабые заметки:

```bash
python scripts/dw.py quality --format markdown --limit 25
```

Собрать digest:

```bash
python scripts/dw.py digest --write
```

Перед batch-записью посмотреть diff:

```bash
python scripts/dw.py write --staging "<dir>" --dry-run --diff --non-interactive
```

## Проверка

На Windows после исправления wiki path handling полный набор тестов проходит:

```bash
uv run --with pytest --with PyYAML --with python-docx python -m pytest -q
```

Ожидаемый результат на момент подготовки README:

```text
180 passed
```

## Основные новые файлы

```text
scripts/
  dw.py
  write_preview.py
  link_health.py
  quality_score.py
  inbox_triage.py
  export_graph.py
  vault_digest.py
  wiki_init.py
  wiki_ingest.py
  wiki_compile.py
  wiki_lint.py
  wiki_models.py
  fetch_notebook.py
  process_notebook.py
  research_notebook.py
  notebooklm_setup.py

tests/
  test_ops_layer.py
  test_observability.py
  test_wiki_compile.py
  test_wiki_lint.py
  test_wiki_models.py
  test_wiki_routing.py
```

## Идеи для следующих улучшений

- Добавить в `inbox_triage.py` безопасный `--apply`, который вызывает существующие process scripts.
- Расширить `quality_score.py`: учитывать review status, changelog history и semantic similarity.
- Добавить в `link_health.py` auto-fix режим для очевидных rename/alias случаев.
- Сделать `load_registry()` tolerant к `utf-8-sig`, если на отдельных машинах появится warning из-за UTF-8 BOM в `processed.json`.
