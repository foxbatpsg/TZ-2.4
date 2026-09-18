# ARCHITECTURE.md — Research Prompt Suite

**Источник контекста:** ТЗ v2.7 (репозиторий `foxbatpsg/TZ-2.4`, ветка `master`), включая нормативные приложения `STATE MACHINE SPECIFICATION v1.2`, `BUDGET CONTRACT v1.0`, `MCP TOOL CONTRACTS v1.1`, `EPIC SPECIFICATIONS v1.0`, `EPIC → TASK DECOMPOSITION v1.0`, `MASTER DEVELOPMENT ROADMAP v1.2`, `TASK EXECUTION CONTRACT v1.0`.

**Статус документа:** рабочий архитектурный ориентир для декомпозиции задач между ИИ-агентами (Cline / OpenCode). Документ не заменяет ТЗ и нормативные приложения — при конфликте приоритет имеет ТЗ.

**Иерархия приоритета документов:**

```
ТЗ v2.7
  ↓
State Machine Specification v1.2 / MCP Tool Contracts v1.1 / Budget Contract v1.0
  ↓
MASTER DEVELOPMENT ROADMAP v1.2
  ↓
EPIC Specifications v1.0
  ↓
ARCHITECTURE.md (этот документ)
  ↓
TASK (карточка задачи для агента)
```

---

## 1. ТЕХНОЛОГИЧЕСКИЙ СТЕК И ОГРАНИЧЕНИЯ

### 1.1. Класс приложения

Локальное десктопное Windows-приложение (offline-first). Браузер не требуется. Сеть используется только как явно инициированный источник данных (веб-поиск, академические API), а не как транспорт самого приложения.

### 1.2. Основной стек (зафиксирован ТЗ)

| Слой | Технология | Примечание из ТЗ |
|---|---|---|
| Язык ядра и GUI | **Python 3.11+** | Единственный язык реализации Core и GUI |
| GUI-фреймворк | **CustomTkinter** | Раздел 6 ТЗ, Windows-only desktop UI |
| Хранилище | **SQLite (WAL-режим)** | Единый DB-write layer, `PRAGMA synchronous=FULL`, `foreign_keys=ON` на каждом соединении |
| Полнотекстовый локальный поиск | **BM25** (`rank_bm25` или **SQLite FTS5**) | Обязателен CPU-only baseline; MVP gate |
| Морфология RU | **pymorphy3 / pymorphy2** (RussianMorphologyNormalizer) | Обязательна для MVP (A-13), не опциональна |
| Локальный LLM-рантайм | **Ollama**, **LM Studio** (OpenAI-compatible HTTP API), совместимые local HTTP backends | Минимальный класс 12–14B (A-22), верхняя граница не нормирована; GGUF, квантование Q4_K_M/Q5_K_M, движок llama.cpp |
| Протокол вызова инструментов Core | **MCP (Model Context Protocol, Anthropic)** поверх **stdio / JSON-RPC** | MCP — протокол **вызова инструментов**, а не инференса (`02` §3a, ADR-001); `stdout` зарезервирован строго под JSON-RPC |
| Конкурентность | **asyncio** (Worker Thread) + Main Thread (GUI) | Обмен через `asyncio.run_coroutine_threadsafe`, `queue.Queue`, `root.after()` |
| Валидация схем | **pydantic** / JSON Schema | Валидация ResearchIntent, MCP tool input/output, structured LLM output |
| Тестирование | **pytest**, фикстуры, изолированные временные БД | Тесты не зависят от сети и от реальной LLM (кроме явных live-тестов) |
| HTTP-клиент для адаптеров | **httpx / aiohttp** (async) | Rate limiting, timeout, retry/backoff на уровне SourceAdapter |

### 1.3. Расширяемый (Post-MVP) стек

Подключается только через изолированные интерфейсы-провайдеры, не ломая контракт Study API и схему БД:

- Векторный поиск: **ChromaDB / FAISS** через `EmbeddingRetrievalProvider`;
- Гибридный поиск: `HybridRetrievalProvider`;
- Нейросетевой реранкинг: `RerankingProvider`.

### 1.4. Архитектурные ограничения (жёсткие, из ТЗ)

1. **Монолит с жёсткими внутренними слоями**, а не микросервисы. Единый процесс приложения, единый DB-write layer, **один процесс ядра на файл Project DB** (второй запуск → `PROJECT_LOCKED`; профили исполнения — `02` §3a).
2. **CPU-Independent (GPU-Independent) baseline** — MVP обязан работать без GPU. GPU/векторные провайдеры — опциональное расширение.
3. **Data isolation per Project** — каждый Project — отдельный файл SQLite; кросс-проектная видимость только через `registry.db` (реестр), без прямого доступа к содержимому чужого проекта.
4. **LLM ≠ источник фактов.** LLM — вычислительный слой интерпретации и синтеза. Любое утверждение без опоры на Evidence Store — галлюцинация, отбрасывается на этапе валидации.
5. **Core обладает исключительным правом на бизнес-переходы состояний** (Study, ResearchSession, SearchTask, MCP Operation, LLM Backend, Job). GUI/LLM/Watchdog/System только инициируют допустимые команды/триггеры. Прямой setter `status` запрещён архитектурно.
6. **Реляционная целостность обязательна.** JSON/сериализованные списки как источник истины для связей (M2M/O2M) запрещены. JSON допустим только в полях `metadata`/`config` (снапшот, не участвует в JOIN/фильтрации).
7. **Идемпотентность обязательна** для всех операций, создающих persistent-сущности (`operation_id`, `request_id`, `idempotency_key`).
8. **Транспорт MCP неприкосновенен.** `stdout` — только JSON-RPC. Все логи, traceback, debug-вывод — в файл/`stderr`. Линтер в CI обязан блокировать сборку при обнаружении `print()`/`sys.stdout.write` вне разрешённых точек.
9. **Многомерный бюджет — единственная граница расходов.** Любая billable-операция обязана пройти `reserve → commit/release`; изменение лимита возможно только через `extend_budget` с явной командой пользователя (никаких silent increase).
10. **Кооперативная, а не принудительная отмена.** Unsafe thread kill запрещён (A-14). Долгие CPU-операции проверяют cancellation token батчами; неотменяемые нативные вызовы — только в дочернем процессе без права записи в SQLite.
11. **Приватность локальных данных.** Абсолютные пути локальных файлов не передаются LLM и не попадают в отчёт — используются обезличенные локальные идентификаторы (A-17).
12. **Безопасность локального FS-доступа.** LLM никогда не передаёт произвольный filesystem path — только заранее зарегистрированный Core `file_ref`.
13. **Security / секреты.** Ключи внешних API (поисковые движки, академические базы) хранятся вне кода и вне репозитория (env/OS credential store), не хардкодятся, не логируются.
14. **Стабильность внешнего контракта важнее внутренней реализации.** Смена ranking/retrieval-провайдера, backend LLM или chunker не должна ломать Study API, схему БД или существующие `chunk_id`/`evidence_hash`.

---

## 2. КАРТА ДИРЕКТОРИЙ (FOLDER STRUCTURE)

Структура построена по границам EPIC (EPIC-01…EPIC-11 из `EPIC SPECIFICATIONS v1.0`) и по принципу «Core как ядро, всё остальное — адаптеры вокруг него» (hexagonal-подобная организация внутри монолита).

```text
research-prompt-suite/
├── app/                              # Точка входа приложения и композиция слоёв (EPIC-01)
│   ├── main.py                       # Единая точка запуска GUI-процесса (Main Thread)
│   ├── bootstrap.py                  # Инициализация конфигурации, логгера, DI-контейнера до старта модулей
│   ├── worker_loop.py                # Постоянный asyncio loop (Worker Thread) и мост GUI↔asyncio
│   └── di_container.py               # Композиция зависимостей (providers, repositories, services)
│
├── core/                             # Search Core — детерминированное ядро, без UI и без "мнения" LLM
│   ├── domain/                       # Чистые доменные модели и правила (EPIC-02/03/04/05, без внешних зависимостей)
│   │   ├── entities/                 # Project, Study, ResearchIntent, SearchTask, Document, Evidence, Claim, ...
│   │   ├── value_objects/            # query_fingerprint, evidence_hash, idempotency_key, интервалы [char_start, char_end)
│   │   └── errors.py                 # Единая доменная модель ошибок (см. раздел 5)
│   ├── state_machines/               # Формальные FSM (EPIC-03) — единственный владелец переходов статусов
│   │   ├── study_fsm.py
│   │   ├── research_session_fsm.py
│   │   ├── search_task_fsm.py
│   │   ├── mcp_operation_fsm.py
│   │   ├── llm_backend_fsm.py
│   │   └── job_fsm.py
│   ├── budget/                       # BUDGET CONTRACT v1.0 (EPIC-04/05)
│   │   ├── budget_ledger.py          # reserve/commit/release/extend_budget, атомарные транзакции
│   │   └── budget_rules.py           # тарификация 7 dimension (step/network/fetch/tool_call/llm_call/llm_token/time)
│   ├── retrieval/                    # Search Core pipeline (EPIC-04)
│   │   ├── source_adapter/           # Абстрактный интерфейс SourceAdapter + провайдеры
│   │   │   ├── base.py               # search(), fetch(), capabilities(), health()
│   │   │   ├── web_search_adapter.py
│   │   │   ├── academic_adapter.py
│   │   │   ├── github_adapter.py
│   │   │   ├── stackoverflow_adapter.py
│   │   │   ├── community_adapter.py  # Reddit/форумы
│   │   │   └── youtube_transcript_adapter.py
│   │   ├── url_normalizer.py         # Каноникализация URL (scheme/host/path/query/tracking-params)
│   │   ├── deduplication/            # 3 уровня: URL / DOI-PMID-arXiv / content-hash (near-duplicate)
│   │   ├── ranking/                  # Раздельное ранжирование relevance vs source quality
│   │   ├── snippetizer.py            # Keyword-Density Snippetizer (детерминированный, лимит 200 симв.)
│   │   ├── chunking/                 # Deterministic chunking: heading_path, overlap_group_id, numeric signatures
│   │   ├── retrieval_provider/       # RetrievalProvider интерфейс + BM25RetrievalProvider (MVP)
│   │   │   ├── base.py
│   │   │   ├── bm25_provider.py
│   │   │   └── normalizer/           # BasicNormalizer, RussianMorphologyNormalizer
│   │   └── cache/                    # CacheEntry: TTL, hit/miss, source-specific TTL
│   ├── evidence/                     # Evidence extraction, provenance, SourceRelation, independence-подсчёт
│   ├── analysis/                     # CoverageCalculator, SufficiencyEvaluator, ResearchGap, Contradiction pipeline
│   ├── research_engine/              # Оркестрация Study (EPIC-05): intent→plan→tasks→iteration→finalize
│   └── config/                       # ResearchConfig (immutable revisions), пороги достаточности, лимиты
│
├── llm/                              # LLM Backend Layer (EPIC-06)
│   ├── provider/                     # LLMProvider интерфейс
│   │   ├── base.py
│   │   ├── ollama_provider.py
│   │   └── lm_studio_provider.py
│   ├── router/                       # LLM Backend Router
│   │   ├── health_monitor.py         # HEALTHY/DEGRADED/UNREACHABLE/RESTARTING (пинги)
│   │   ├── backend_router.py         # Переключение на альтернативный бэкенд
│   │   └── session_resume.py         # Восстановление контекста после сбоя
│   ├── structured_output/            # Constrained decoding → schema validation → semantic validation
│   │   ├── json_schema_validator.py
│   │   ├── semantic_validator.py     # Не оценивает истинность, только структурную корректность
│   │   └── repair_fallback.py        # Контролируемый repair при недоступной grammar
│   ├── token_budget_manager.py       # Интеграция с core/budget (llm_call/llm_token dimensions)
│   └── prompt/                       # Сборка компактного контекста (без сырых HTML/полных страниц)
│
├── mcp_server/                       # MCP-сервер (EPIC-07): транспорт профиля headless --mcp-stdio, контракты 23 инструментов
│   ├── server.py                     # stdio transport, ранний редирект логгеров, guard от левого stdout
│   ├── transport_guard.py            # Валидирующая обёртка: в stdout идёт только корректный JSON-RPC
│   ├── tools/                        # 23 инструмента по группам (MCP TOOL CONTRACTS v1.1)
│   │   ├── planning.py               # plan_research
│   │   ├── retrieval.py              # search_web / search_academic / search_github / search_stackoverflow / search_web_community
│   │   ├── reading.py                # read_url_content / read_youtube_transcript
│   │   ├── documents.py              # add_local_document / search_within_document
│   │   ├── study_management.py       # start_research_session / save_study_material / search_study_materials / get_research_session_statistics / get_study_dashboard
│   │   ├── memory.py                 # update_working_memory / get_working_memory
│   │   ├── cache_diagnostics.py      # get_cache_statistics / get_cache_diagnostics / cleanup_expired_cache
│   │   ├── report.py                 # validate_and_save_report
│   │   └── job_management.py         # get_job_status / cancel_job
│   ├── schemas/                      # JSON Schema input/output для каждого tool
│   └── error_codes.py                # Единый формат ошибок MCP (см. раздел 4.3)
│
├── db/                                # Data Layer (EPIC-02)
│   ├── connection_factory.py          # Единая фабрика соединений: PRAGMA WAL, synchronous=FULL, foreign_keys=ON
│   ├── migrations/                    # Версионированные миграции схемы (по одной директории на Project DB и Registry DB)
│   ├── write_layer/                   # Единый DB-write layer — все INSERT/UPDATE/DELETE только отсюда
│   ├── repositories/                  # Repository-паттерн: по одному репозиторию на агрегат (StudyRepository, EvidenceRepository, ...)
│   ├── registry/                      # registry.db: кросс-проектный реестр, transactional outbox, reconciliation
│   ├── backup/                        # Snapshot/backup через SQLite Backup API (без прямого копирования файла)
│   └── fts/                           # SQLite FTS5 схема и синхронизация индекса с DocumentChunk
│
├── gui/                                # Presentation Layer (CustomTkinter, EPIC-08)
│   ├── main_window.py
│   ├── views/                          # StudyCreation, IntentBlueprintEditor, XRayActivityStream, EvidenceExplorer,
│   │                                    # EvidenceTree, ReportViewer, SystemHealthMonitor, PromptSandbox,
│   │                                    # ResearchSnapshots, ProjectsPanel, ReviewAggregationUI, QueryPreview
│   ├── widgets/                        # Переиспользуемые виджеты
│   ├── viewmodels/                     # Состояние UI, привязка к thread-safe queue из Worker Thread
│   └── bridge/                         # GUI ↔ asyncio мост: run_coroutine_threadsafe, root.after()
│
├── reporting/                          # Синтез и рендер отчётов (Report/PARTIAL_REPORT metadata)
│   ├── report_builder.py
│   ├── templates/
│   └── exporters/                      # Экспорт в Markdown/PDF/DOCX (см. раздел 4.2)
│
├── infra/                              # Инфраструктурные сквозные модули (EPIC-01)
│   ├── logging/                        # Конфигурация логгера: файл/stderr, ротация, structured logging
│   ├── config/                         # Загрузка и валидация конфигурации (env, config-файл) до старта зависимостей
│   ├── identifiers.py                  # UUID-генерация operation_id/request_id/idempotency_key
│   ├── time_utils.py                   # monotonic time для time_budget, единый источник времени
│   └── security/                       # Хранение секретов (credential store), whitelisting file_ref
│
├── packaging/                          # Сборка portable-дистрибутива Windows (PyInstaller)
│
├── docs/                               # Нормативные документы проекта
│   ├── tz/                             # Копия/ссылка на разделы 01–07 ТЗ v2.7
│   ├── contracts/                      # STATE MACHINE SPEC, MCP TOOL CONTRACTS, BUDGET CONTRACT, TASK EXECUTION CONTRACT
│   ├── adr/                            # Architecture Decision Records (см. `INDEX.md` §7, `корзина/REVIEW-REGISTRY.md`)
│   └── ARCHITECTURE.md                 # Этот документ (каноническая копия)
│
├── tests/                              # pytest, изолированные фикстуры (EPIC-01, Gate G-01..G-11)
│   ├── unit/                           # По одному подкаталогу на модуль core/llm/db/mcp_server/gui
│   ├── integration/                    # End-to-end по Gate: db, fsm, search_core, research_engine, llm_backend, mcp
│   ├── fixtures/                       # Детерминированные фикстуры БД, FakeLLM, mock SourceAdapter
│   └── golden/                         # Golden-файлы для chunking/BM25/ranking (воспроизводимость, A-07)
│
├── scripts/                            # Вспомогательные dev-скрипты (миграции, генерация фикстур, lint stdout-guard)
├── pyproject.toml                      # Зависимости, версии, конфигурация pytest/ruff/mypy
└── README.md
```

**Комментарии по границам модулей:**

- `core/` не имеет импортов из `gui/`, `llm/`, `mcp_server/` — зависимость направлена внутрь (Core ничего не знает о GUI и о конкретном LLM backend).
- `mcp_server/tools/*` — тонкий адаптер: валидация схемы → вызов `core/research_engine` или `core/retrieval` → сериализация ответа. Бизнес-логика и владение состоянием в `tools/*` запрещены (см. раздел 4.3).
- `db/write_layer/` — единственная точка физической записи в SQLite для всего приложения; `repositories/*` читают напрямую, но пишут только через `write_layer`.
- `gui/` зависит от `app/worker_loop.py` и от `mcp_server`/`core` API, но не содержит бизнес-правил (валидация правил — в `core/domain`).

---

## 3. КЛЮЧЕВЫЕ СУЩНОСТИ И СХЕМА ДАННЫХ (DATA MODEL)

### 3.1. Общие правила хранения

- СУБД: SQLite, режим WAL, отдельный файл БД на каждый `Project`; `registry.db` — глобальный кросс-проектный реестр (источник истины — Project DB, реестр синхронизируется через transactional outbox).
- Любая связь M2M/O2M — отдельная нормализованная таблица с FOREIGN KEY. JSON — только в полях `metadata`/`config`.
- Три класса идентификаторов на каждую операцию: `operation_id` (операция), `request_id` (один fetch = один request_id), `idempotency_key` (детерминированный, SHA256 от семантики операции).

### 3.2. Основные сущности и связи (ER, укрупнённо)

```
Project 1──* Study
Study 1──1 ResearchIntent
Study 1──* SearchTask
Study 1──* ResearchSession
Study 1──* Evidence / Observation / Claim / Contradiction / ResearchGap
Study 1──1 SufficiencyEvaluation (текущая) / *──история

SearchTask 1──* SearchResult
SearchResult *──1 Source
Source 1──* SourceIdentifier (DOI/PMID/arXiv)
Source *──* Source  (через SourceRelation: COPY | REWRITE | CITATION | SAME_PRIMARY | UNKNOWN)

Document (глобальный, в рамках Project) *──* Study   (через StudyDocumentLink)
Document 1──* DocumentChunk
Document *──* Source  (через DocumentSourceOccurrence — одно "тело" документа, много происхождений)
DocumentChunk 1──* Evidence (is_target=TRUE) 
Evidence *──* DocumentChunk (is_target=FALSE, контекстные чанки через EvidenceContextChunk)

Claim *──* Evidence   (через ClaimEvidence)
Claim 1──* Contradiction (опционально, пара Claim↔Claim)
ResearchGap *──1 SearchTask (gap_id → породившая gap задача-источник новых SearchTask)

ResearchIntent 1──* IntentEntity / IntentInformationNeed / IntentConstraint /
                    IntentSourcePreference / IntentOutputRequirement

ResearchConfig (immutable revision) 1──* Study/ResearchSession (текущая активная ревизия)
BudgetLimit 1──* BudgetCounter / BudgetReservation / BudgetLedger
LogRecord *──1 (entity_type, entity_id) — audit-лог всех переходов состояний
OutboxEvent — очередь синхронизации Project DB → registry.db
```

### 3.3. Полный реестр сущностей (по ТЗ, раздел 3 «Модель данных и хранение»)

**Базовые сущности:** `Project`, `Study`, `ResearchIntent`, `SearchTask`, `SearchResult`, `Source`, `SourceRelation`, `Entity`, `Document`, `StudyDocumentLink`, `DocumentChunk`, `Evidence`, `EvidenceContextChunk`, `Observation`, `Claim`, `ClaimEvidence`, `Contradiction`, `ResearchGap`, `SufficiencyEvaluation`, `ResearchConfig`, `ResearchSession`, `ResearchState`, `WorkingMemory`, `CacheEntry`, `LogRecord`, `Job`.

**Нормализующие/связующие таблицы:** `EntityAlias`, `IntentEntity`, `IntentInformationNeed`, `IntentConstraint`, `IntentSourcePreference`, `IntentOutputRequirement`, `SourceIdentifier`, `SearchResultIdentifier`, `ChunkNumericSignature`, `DocumentSourceOccurrence`, `SourceQualityAssessment`, `SufficiencyMetric`, `SufficiencyRuleHit`, `BudgetLimit`, `BudgetCounter`, `BudgetReservation`, `BudgetLedger`, `OutboxEvent`.

### 3.4. Ключевые таблицы (концептуальная схема полей)

```
Project
├── project_id (TEXT PK, UUID)
├── name (TEXT NOT NULL)
├── description (TEXT)
├── created_at / updated_at (TIMESTAMP)
└── archived (BOOLEAN)

Study
├── study_id (TEXT PK, UUID)
├── project_id (FK → Project)
├── title, goal, domain, research_mode (TEXT NOT NULL)
├── status (TEXT)  -- изменяется ТОЛЬКО через Study FSM
├── budget (TEXT)  -- ссылка на активную ConfigRevision/BudgetLimit
└── metadata (TEXT, JSON — снапшот, не источник истины)

ResearchIntent
├── intent_id (TEXT PK, UUID)
├── study_id (FK → Study, UNIQUE)
├── question, goal (TEXT/ENUM)
├── target_entities / constraints / source_preferences / expected_output (TEXT — API-снапшот)
└── version (INTEGER)
-- источник истины для перечислимых полей: IntentEntity, IntentInformationNeed,
-- IntentConstraint, IntentSourcePreference, IntentOutputRequirement (по intent_id)

SearchTask
├── task_id (TEXT PK, UUID)
├── study_id (FK → Study)
├── query, purpose, source_scope (TEXT NOT NULL)
├── query_fingerprint (TEXT NOT NULL) -- UNIQUE (study_id, query_fingerprint)
├── gap_id (FK → ResearchGap, NULL допустим)
├── status (TEXT) -- изменяется ТОЛЬКО через SearchTask FSM
├── operation_id, idempotency_key (TEXT)
└── priority (INTEGER)

Document
├── document_id (TEXT PK, UUID)
├── project_id (FK → Project)  -- глобален в рамках проекта
├── content_hash (TEXT, UNIQUE в рамках project)
├── version (INTEGER)  -- обновление URL создаёт новую версию, не перезаписывает
└── ... (title, fetched_at, content_ref)

DocumentChunk
├── chunk_id (TEXT PK)  -- детерминирован: document identity + версия chunker + позиция
├── document_id (FK → Document)
├── char_start, char_end (INTEGER) -- полуоткрытый интервал [char_start, char_end)
├── heading_path, overlap_group_id, is_overlap (TEXT/BOOLEAN)
└── numeric_signatures (через ChunkNumericSignature, 1──*)

Evidence
├── evidence_id (TEXT PK)
├── evidence_hash (TEXT, UNIQUE) -- study + document version + [char_start,char_end) + точный текст
├── target_chunk_id (FK → DocumentChunk, is_target=TRUE)
├── context_chunks (через EvidenceContextChunk, ±1 чанк)
└── source_id (FK → Source)

Claim
├── claim_id (TEXT PK)
├── study_id (FK → Study)
├── status (FACT | OPINION | INFERENCE | HYPOTHESIS | INSUFFICIENT_EVIDENCE)
├── confidence (REAL)
└── evidence (через ClaimEvidence, M2M)

BudgetLimit / BudgetCounter / BudgetReservation / BudgetLedger
├── dimension (step | network | fetch | tool_call | llm_call | llm_token | time)
├── limit, consumed, reserved, available = limit - consumed - reserved
├── config_revision (FK → ResearchConfig)
└── reservation_id, operation_id, status, created_at, committed_at
```

**Критическое правило (неизменяемое):** ни одна из перечисленных связей не хранится как JSON-массив или строка с разделителями — только явные FK-таблицы, проверяемые тестами на «5 копий документа → 1 тело + 5 DocumentSourceOccurrence» (A-08) и аналогичными.

---

## 4. ТОЧКИ ИНТЕГРАЦИИ И API

### 4.1. Внутренний транспорт: MCP поверх stdio

**MCP — протокол вызова инструментов, а не протокол инференса** (`02` §3a, ADR-001). Любой вызов инструмента Core проходит через MCP-контракт инструмента; обращение к LLM идёт отдельным каналом — OpenAI-compatible HTTP API (`05` §1–2). Прямых импортов Core внутри промптов/кода LLM не существует.

Профили исполнения (`02` §3a): **desktop orchestration** (по умолчанию) — агентный цикл ведёт Orchestrator в процессе приложения, вызовы инструментов идут в единый ToolDispatcher; **headless `--mcp-stdio`** — агентный цикл ведёт внешний MCP-клиент, stdio-адаптер транслирует вызовы в тот же ToolDispatcher. Состав инструментов в обоих профилях одинаков.

Полный реестр — 23 инструмента (`MCP TOOL CONTRACTS v1.1`):

| Группа | Инструменты |
|---|---|
| Planning | `plan_research` |
| Retrieval | `search_web`, `search_academic`, `search_github`, `search_stackoverflow`, `search_web_community` |
| Reading | `read_url_content`, `read_youtube_transcript` |
| Documents | `add_local_document`, `search_within_document` |
| Study Management | `start_research_session`, `save_study_material`, `search_study_materials`, `get_research_session_statistics`, `get_study_dashboard` |
| Memory | `update_working_memory`, `get_working_memory` |
| Cache / Diagnostics | `get_cache_statistics`, `get_cache_diagnostics`, `cleanup_expired_cache` |
| Report | `validate_and_save_report` |
| Job Management | `get_job_status`, `cancel_job` |

**Общий контракт каждого tool обязателен и включает:** `INPUT`/`OUTPUT` схему, список `ERRORS`, `LIMITS` (размер ответа/кол-во элементов), `TIMEOUT`, `RETRY`-политику, `SIDE EFFECTS` (какие сущности создаются и какой budget списывается), `IDEMPOTENCY` (формула ключа), `CANCELLATION`, `AUTHORITY` (кто инициирует, кто исполняет).

Пример нормативного формата ошибки (обязателен для всех tools):

```json
{
  "code": "ERROR_CODE",
  "message": "краткое описание",
  "retryable": false,
  "recommendation": "детерминированная рекомендация Core",
  "operation": "tool_name",
  "entity_id": "uuid-or-null"
}
```

### 4.2. Внешние интеграции (через SourceAdapter)

| Интеграция | Назначение | Класс адаптера |
|---|---|---|
| Веб-поиск (поисковые движки/API) | `search_web` | `WebSearchAdapter` |
| Академические базы (напр. Crossref/PubMed/arXiv-совместимые API) | `search_academic`, выдаёт DOI/PMID/arXiv | `AcademicAdapter` |
| GitHub API | `search_github` (фильтры `language`, `sort_by`) | `GithubAdapter` |
| StackOverflow API | `search_stackoverflow` (`tagged`, `min_score`) | `StackOverflowAdapter` |
| Reddit/форумы/блоги | `search_web_community` (`platform`, `sort_by`) | `CommunityAdapter` |
| YouTube (транскрипты) | `read_youtube_transcript` | `YoutubeTranscriptAdapter` |
| Локальная файловая система | `add_local_document`, `search_within_document` | `LocalDocumentAdapter` (только через Core-approved `file_ref`) |
| Локальный LLM backend | Ollama REST API / LM Studio (OpenAI-совместимый HTTP) | `OllamaProvider`, `LMStudioProvider` |

Все внешние сетевые интеграции обязаны: проходить через `URL Normalization` → `Deduplication` → `budget.reserve()`; иметь per-domain rate limiting; не отдавать LLM сырой HTML — только очищенный текст, нарезанный на чанки.

### 4.3. Границы MCP tool (нормативно, не подлежит нарушению)

1. MCP tool **не владеет бизнес-состоянием** — любое изменение `Study`/`ResearchSession`/`SearchTask` только через соответствующий FSM.
2. Tool **не вычисляет собственный `query_fingerprint`** — только Core.
3. `add_local_document` не принимает произвольный путь от LLM, только зарегистрированный `file_ref`.
4. `SOFT_STOP`/`HARD_STOP`/`CANCEL` — команды, а не результат вызова tool, создающий одноимённый статус.
5. Синхронные tools остаются синхронными; job-backed (длительные) операции не маскируются под них.

### 4.4. Внешний GUI ↔ Core API (внутренний, не сетевой)

GUI обращается к Core через тот же MCP-слой либо через прямой internal service-facade (`core/research_engine`) — **без обхода FSM**. Ключевые команды: `create_project`, `create_study`, `edit_intent`, `approve_plan`, `start_research`, `pause`, `resume`, `soft_stop`, `hard_stop`, `extend_budget`, `export_report`, `create_snapshot`, `restore_snapshot`.

---

## 5. ПРАВИЛА И СТАНДАРТЫ ДЛЯ ИИ-АГЕНТОВ (AGENTS GUIDELINES)

> Источник: `TASK EXECUTION CONTRACT v1.0`, `STATE MACHINE SPECIFICATION v1.2 §0`, ТЗ разделы 5 и 7. Эти правила являются частью системного промпта для Cline/OpenCode и не могут быть смягчены агентом самостоятельно.

### 5.1. Главный принцип работы агента

```
TASK → READ → UNDERSTAND → PLAN → IMPLEMENT → TEST → VERIFY → REPORT
```

Агент выполняет **назначенную TASK**, а не «улучшает проект». Найденная вне scope проблема не становится автоматически новой задачей — она фиксируется в отчёте (`STOP → REPORT → WAIT`, если проблема мешает выполнить текущую TASK; иначе просто фиксируется).

### 5.2. Обработка ошибок (Error Handling)

1. Единая модель ошибок для всего проекта — `core/domain/errors.py`; MCP-инструменты используют единый JSON-формат ошибки (см. §4.1): `code`, `message`, `retryable`, `recommendation`, `operation`, `entity_id`.
2. Ошибки классифицируются по типу: `INVALID_INPUT`, `VALIDATION_ERROR`, `NETWORK_ERROR`, `TIMEOUT`, `RATE_LIMIT`, `SOURCE_UNAVAILABLE`, `PARSE_ERROR`, `DATABASE_ERROR`, `RETRIEVAL_PROVIDER_ERROR`, `INVALID_STATE`, `LLM_UNREACHABLE` и т.д. Запрещено вводить новый код ошибки без явного разрешения TASK/EPIC.
3. Недопустимый переход состояния **не изменяет** состояние — Core обязан вернуть детерминированную ошибку, а не «подогнать» переход.
4. Необработанные исключения никогда не попадают в `stdout` MCP-сервера — только в файл/`stderr`.
5. Ретраи — только там, где явно разрешено контрактом tool (`RETRY` policy); запрещены неограниченные/тихие ретраи.
6. LLM-контент, не прошедший semantic/schema-валидацию, не сохраняется как факт — деградирует до `repair fallback` или ошибки, но не «додумывается» кодом агента.

### 5.3. Логирование

1. Ранний редирект логов до инициализации любых модулей: ни один логгер не пишет в `stdout` MCP-процесса.
2. Каждый выполненный переход FSM обязан порождать атомарную запись `LogRecord`: `entity_type`, `entity_id`, `from_state`, `to_state`, `trigger`, `component`, `timestamp`. Переход и `LogRecord` — одна атомарная операция.
3. Логи не содержат: сырых абсолютных путей локальных файлов пользователя (A-17), секретов/токенов, полного содержимого страниц.
4. Уровни логирования различают операционные события (X-Ray Activity Stream в GUI) и диагностические/отладочные записи (файл).
5. Деградация до `BasicNormalizer` вместо `RussianMorphologyNormalizer` обязана явно логироваться как fallback (A-13) — не маскируется.

### 5.4. Обязательные требования к автотестам

1. Каждая функциональная TASK обязана включать проверяемые acceptance-тесты минимум по схеме: valid input, empty input, invalid input, duplicate input (идемпотентность), boundary condition.
2. Каждый новый MCP-инструмент/эндпоинт покрывается интеграционным тестом в `tests/integration/mcp/`, включающим позитивный сценарий, ошибочный ввод и проверку идемпотентности повторного вызова.
3. Каждое изменение FSM покрывается тестами разрешённых и запрещённых переходов в `tests/integration/state_machines/` (Gate G-03).
4. Тесты Core/DB/MCP не зависят от реальной сети и реальной LLM — используются `FakeLLM` и mock `SourceAdapter`, кроме явно помеченных `live`-тестов.
5. Изменение схемы БД обязано сопровождаться миграцией в `db/migrations/` и тестом на обратную совместимость существующих `chunk_id`/`evidence_hash` (A-07).
6. Агент не имеет права ослаблять, отключать или удалять существующий тест ради получения PASS — только через отдельную явно разрешённую TASK.
7. Repair-цикл «код → тест → fail → debug» ограничен **3 итерациями**; после лимита — статус `NEEDS_HUMAN`, а не подгонка теста под код.

### 5.5. Категорические запреты

1. **Запрещено** изменять `status` persistent-сущности напрямую, в обход FSM (публичного setter не существует).
2. **Запрещено** хранить связи сущностей в JSON/CSV-строках как источник истины; только нормализованные FK-таблицы.
3. **Запрещено** писать в `stdout` MCP-процесса что-либо, кроме JSON-RPC (никаких `print()`/debug-вывода).
4. **Запрещено** хардкодить секреты, API-ключи, пути к моделям — только конфигурация/переменные окружения/credential store.
5. **Запрещено** передавать в LLM сырой HTML, абсолютные локальные пути пользователя или неограниченные по объёму материалы — только очищенный, лимитированный, обезличенный контекст.
6. **Запрещено** объявлять LLM-утверждение фактом без привязки к Evidence через `ClaimEvidence`.
7. **Запрещено** принудительно убивать (`thread kill`) активные CPU-потоки — только кооперативная отмена через cancellation token.
8. **Запрещено** самостоятельно добавлять новые зависимости, менять схему БД, публичный API/MCP-контракт или архитектурные границы модулей без явного разрешения конкретной TASK/EPIC (в противном случае — `STOP → REPORT → WAIT`).
9. **Запрещено** реализовывать «второй» `SufficiencyEvaluator`/`CoverageCalculator` вне `core/analysis` — переиспользуются типизированные примитивы EPIC-04 (A-16).
10. **Запрещено** агенту выходить за пределы `ALLOWED_FILES`/`SCOPE`, указанных в Context Header задачи; незапрошенный рефакторинг соседнего кода, переименования и «попутные» исправления запрещены (Minimal Change Principle).
11. **Запрещено** GUI-слою напрямую обращаться к `db/write_layer` в обход Core/MCP — вся запись идёт по установленному пути.
12. **Запрещено** выдавать «должно работать» как доказательство выполнения — обязательна цепочка `Implementation → Tests → Diff inspection → Acceptance verification → Report`.

### 5.6. Формат сдачи задачи (Evidence Bundle)

Каждая завершённая TASK возвращается в формате: `TASK-ID`, `status`, изменённые файлы, краткое описание, выполненные тесты и их результат, `acceptance result`, известные ограничения, найденные вне-scope проблемы, блокирующие вопросы. При конфликте с вышестоящим документом — статус `BLOCKED`, а не самостоятельное решение.

---

## 6. Definition of Done (сквозной, по Gate из EPIC Specifications)

Компонент считается готовым, если: цель EPIC/TASK реализована; проверки соответствующего Gate (G-01…G-11) проходят; тесты детерминированы и не зависят от внешней сети/живой LLM; FSM-инварианты не нарушены; бюджетная модель не обойдена; MCP-транспорт не загрязнён; изменения ограничены заявленным scope.
