# EPIC SPECIFICATIONS v1.0 — BASELINE

**Проект:** Research Prompt Suite  
**Назначение:** рабочие спецификации EPIC-01…EPIC-11 для последующей декомпозиции в TASK.

## 1. Общие правила

Иерархия: ТЗ → State Machine / MCP Contracts → MASTER ROADMAP → EPIC → TASK → CODE/TEST/REVIEW.

При конфликте: **STOP → REPORT → DECISION**.

EPIC не изменяет Core authority, FSM contracts, MCP Tool Contracts, модель данных, security boundary или MVP scope самостоятельно.

EPIC Specification определяет границы, интерфейсы, зависимости и DoD, но не подменяет TASK.

---

## 2. EPIC-01 — FOUNDATION

**Purpose:** воспроизводимая и тестируемая основа приложения.

**Scope:** project structure, package boundaries, configuration, environment abstraction, bootstrap, unified identifiers, time utilities, error model, logging, entrypoint, pytest infrastructure, isolated test environment.

**Constraints:** тесты не зависят от машины разработчика; временные данные изолированы; MCP stdout не загрязняется логами; конфигурация валидируется до запуска зависимых компонентов.

**Gate G-01:** запуск, конфигурация, изоляция тестов, errors, logging, package boundaries и базовые тесты проходят.

---

## 3. EPIC-02 — DATA LAYER

**Purpose:** надёжное SQLite-хранилище и единый DB-write layer.

**Scope:** SQLite, WAL, PRAGMA factory, migrations, transactions, repositories, DB-write layer, Project/Study isolation, global Document registry, FK/indexes/hashes, operation_id/request_id/idempotency, snapshot/backup subsystem, persistence tests.

**Key entities:**

```text
Project
Study
Entity
ResearchIntent
ResearchConfig
ResearchState
ResearchSession
SearchTask
Source
SourceRelation
SearchResult
Document
DocumentChunk
StudyDocumentLink
Evidence
EvidenceContextChunk
Observation
Claim
ClaimEvidence
Contradiction
ResearchGap
SufficiencyEvaluation
WorkingMemory
CacheEntry
LogRecord
Job
```

Нормализованные таблицы (A-03): `EntityAlias`, `IntentEntity`, `IntentInformationNeed`, `IntentConstraint`, `IntentSourcePreference`, `IntentOutputRequirement`, `SourceIdentifier`, `SearchResultIdentifier`, `ChunkNumericSignature`, `DocumentSourceOccurrence`, `SourceQualityAssessment`, `SufficiencyMetric`, `SufficiencyRuleHit`, `BudgetLimit`, `BudgetCounter`, `BudgetReservation`, `BudgetLedger`, `OutboxEvent`.

Стабильные идентификаторы (A-07): `DocumentChunk.chunk_id` детерминирован относительно document identity + версии chunker + позиции; смена версии разбиения (chunk_size/параметры) не ломает существующую доказательную базу — новые версии разбиения создают новые chunk_id без перезаписи существующих.

Синхронизация реестра (Q-01): Project DB — источник истины; registry.db синхронизируется через transactional outbox (событие в той же транзакции + идемпотентный Registry Writer + reconciliation); мультифайловый snapshot не объявляется crash-atomic.

Durability (A-11): `synchronous=FULL` для записи, `foreign_keys=ON` на каждом соединении, backup через SQLite Backup API, мониторинг WAL/свободного места.

Схема должна быть архитектурно готова к FTS5/BM25 для DocumentChunk.

Прямое копирование активной SQLite DB запрещено. Backup/snapshot выполняется штатным backup/checkpoint механизмом.

**Gate G-02:** migrations, CRUD, rollback, FK, isolation, document reuse, idempotency, concurrent read/write, WAL, DB-write layer, deterministic fixtures, FTS5 readiness и WAL-safe snapshot/backup проходят тесты.

---

## 4. EPIC-03 — STATE MACHINES

**Purpose:** формальные автоматы как фундамент Core.

**State machines:** Study, ResearchSession, SearchTask, MCP Operation, LLM Backend, Job runtime lifecycle.

**Scope:** states, transitions, triggers, guards, authority, commands, atomic state + LogRecord, invalid transitions, recovery, resume, cancellation, timeout, retry.

**Mandatory:** Soft Stop, Hard Stop, Budget Exhaustion, LLM Failure/Recovery, Session Resume, Task/Job Cancel, Timeout, Retry.

**Invariants:** только Core владеет переходами; command не является state; MCP и GUI не меняют FSM напрямую; transition + audit LogRecord атомарны; public API не допускает произвольного status assignment.

**Gate G-03:** разрешённые/запрещённые переходы и mandatory scenarios покрыты тестами.

---

## 5. EPIC-04 — SEARCH CORE

**Purpose:** детерминированное поисковое и документное ядро без LLM.

**Scope:**
1. SourceAdapter/provider abstraction и domain limits.
2. URL normalization/canonicalization.
3. Search providers, ranking, filtering, concurrency, timeout, retry/backoff.
4. Deduplication: URL, DOI, PMID, arXiv, content hash, near-duplicate, SourceRelation.
5. Query Fingerprint: normalization, `query_fingerprint`, многофакторная защита повторных/семантически одинаковых запросов, интеграция с budget и ResearchGap.
6. Fetch/parse/chunk: heading_path, overlap, overlap_group_id, is_overlap, numeric signatures.
7. SQLite FTS5/BM25, study/document isolation.
8. BM25 index lifecycle: `normalizer_version`, `index_version`, `language`, `stopword_version`; document added → index; normalizer changed → rebuild_all; study deleted → cleanup.
9. Evidence: evidence_hash, target/context distinction, provenance.
10. Cache: key, TTL, hit/miss, cleanup, diagnostics.
11. Budget: time, network, LLM/tool calls, atomic deduction.
12. CoverageCalculator, SufficiencyEvaluator, Information Gain, ResearchGap.

**Normalization:**

```text
RetrievalTextNormalizer
        │
        ├── BasicNormalizer
        └── RussianMorphologyNormalizer
```

Поисковый запрос и индексируемый текст проходят через согласованный normalizer.

**Gate G-04:** retrieval детерминирован; deduplication и query fingerprint работают; FTS5/BM25 согласован с DocumentChunk; lifecycle индекса корректен; evidence provenance, budget, cache и normalizer versioning работают.

Граница ответственности (A-16): EPIC-04 предоставляет чистые типизированные primitives (coverage, sufficiency, budget); второй evaluator в других эпиках не реализуется. G-04 проверяется на fixtures без реальной LLM.

---

## 6. EPIC-05 — RESEARCH ENGINE

**Purpose:** Core-оркестрация исследования.

**Scope:** ResearchIntent validation, ResearchConfig, ResearchState, plan representation, SearchTask orchestration, iteration, CoverageCalculator, SufficiencyEvaluator, ResearchGap lifecycle, primary-source search, contradiction pipeline, aggregation/evidence modes, MATERIALS_ONLY, EXPAND, finalization.

Core владеет task acceptance, duplicate/similar query checks, budget, coverage, sufficiency, execution и completion decision.

Новые SearchTask: `ResearchGap → planning → Core validation → SearchTask`.

**Gate G-05:** mock-LLM E2E проходит `intent → plan → tasks → retrieval → evidence → gap → next task → sufficiency → finalize`.

Примечание (A-16): Research Engine вызывает typed primitives EPIC-04 и не реализует второй SufficiencyEvaluator; G-05 проверяется через FakeLLM. Примечание (A-01): архитектурной зависимости EPIC-06 от EPIC-05 нет; gated-порядок сохраняется. Определение нормы — `MASTER DEVELOPMENT ROADMAP v1.2` §21.1.

---

## 7. EPIC-06 — LLM BACKEND

**Purpose:** единый provider interface для локальных LLM.

**Dependencies:** EPIC-01, EPIC-03. EPIC-05 не является обязательной зависимостью для начала разработки.

**Scope:** LLMProvider, LM Studio adapter, Ollama adapter, configuration, health monitor, timeout, degraded/unreachable/restart, backend switching, structured output, JSON Schema validation, constrained decoding/grammar, controlled repair fallback, TokenBudgetManager, context budget, prompt construction.

**Structured output:** constrained decoding → strict schema validation → semantic/contract validation → accepted result. Если grammar недоступна — limited repair + re-validation + retry/failure.

**Semantic validation:** обязательные поля, допустимая пустота, существование reference IDs, числовые пределы, соответствие операции, отсутствие обрыва/зацикливания, минимальные условия схемы. Не оценивает фактическую истину.

Сырые HTML, полные страницы и длинные логи не передаются LLM; Core формирует компактный context.

**Gate G-06:** unreachable, timeout, invalid/truncated JSON, degraded response, restart, backend switch, context budget, schema/semantic validation, constrained decoding, repair fallback и state preservation проходят тесты.

---

## 8. EPIC-07 — MCP

**Purpose:** строго ограниченный инструментальный интерфейс LLM.

**MVP tools:**

`plan_research`, `start_research_session`, `get_research_session_statistics`, `get_study_dashboard`, `search_web`, `search_academic`, `search_github`, `search_stackoverflow`, `search_web_community`, `read_url_content`, `read_youtube_transcript`, `add_local_document`, `search_within_document`, `save_study_material`, `search_study_materials`, `update_working_memory`, `get_working_memory`, `get_cache_statistics`, `get_cache_diagnostics`, `cleanup_expired_cache`, `validate_and_save_report`, `get_job_status`, `cancel_job`.

**Invariant:** MCP — proxy/adapter над Core/Application API. Он не пишет DB напрямую и не меняет FSM напрямую.

```text
LLM → MCP → Command/Application API → Core → FSM/Job → State + DB
```

Обязательны operation_id, idempotency, timeout, unified errors, stdout isolation, schema validation, safe local-document file_ref и compact responses.

**Gate G-07:** все 23 tools зарегистрированы и проходят contract tests.

---

## 9. EPIC-08 — GUI

**Purpose:** Windows GUI как thin client над Core/Application API.

**Stack:** Python + CustomTkinter + SQLite; browser не требуется.

**Scope:** application shell, project/study creation, project switching через registry, Intent Blueprint, X-Ray Activity Stream, Evidence Explorer/Tree, Report Viewer, Dashboard/Health, Snapshot/Offline, Review/Aggregation UI, cooperative cancellation controls.

GUI предоставляет Soft Stop и Hard Stop, но не меняет FSM напрямую.

Main Thread не выполняет retrieval, parsing, indexing, orchestration и длительные DB operations.

Project switching выполняется через project registry; GUI не выбирает DB-файл произвольно.

Snapshot использует EPIC-02; прямое копирование активной DB запрещено.

**Gate G-08:** business rules не находятся в GUI; workers работают; UI responsive; cancellation, project switching, offline и snapshot работают; evidence traceability сохраняется.

---

## 10. EPIC-09 — INTEGRATION & RESILIENCE

**Purpose:** проверить систему как единый отказоустойчивый контур.

```text
GUI → Application/Core → Research Engine → MCP/LLM → Search Core → Data Layer
```

Проверяются LLM failure/recovery/switch, network timeout/rate-limit/unavailable, parse-error, pause/resume, soft/hard stop, budget exhaustion/freeze/extension, partial finalization, DB rollback/restart, interrupted Job, session resume/checkpoint, preservation of Evidence и Claims.

**Gate G-09:** recovery не теряет валидные данные, не создаёт дубликаты, не нарушает FSM, сохраняет audit trail и восстанавливает session/job state.

---

## 11. EPIC-10 — FINAL QA / ACCEPTANCE

**Purpose:** финальная комплексная проверка соответствия ТЗ.

**Levels:** Unit → Component → Integration → FSM → MCP Contract → E2E → Failure Scenarios → Acceptance.

**Coverage:** data isolation, BM25, RetrievalTextNormalizer, Russian morphology (обязательна для MVP, A-13; Acceptance морфологии — обязательный критерий G-10), deterministic chunking, overlap protection, FTS5/index consistency, normalizer/index versioning, query fingerprint, evidence_hash, aggregation, claims, contradictions, primary source, context protection, LLM resilience, two-level structured output validation, GUI responsiveness, cooperative cancellation, project switching, network resilience, security, MATERIALS_ONLY, offline, CPU-only MVP.

**Gate G-10:** все обязательные критерии ТЗ выполнены; критических известных дефектов нет.

---

## 12. EPIC-11 — PACKAGING / PORTABLE

**Purpose:** эксплуатационный portable MVP.

**Scope:** portable folder, configuration, local DB handling, environment checker, dependency diagnostics, startup checks, logging, backup/recovery instructions.

Environment checker проверяет runtime, компоненты, права, filesystem requirements и состояние локальной БД. При проблеме выдаёт понятную диагностику и информацию для администратора.

**Административный диагностический доступ (Q-13):** привилегированный administrator diagnostic token **исключён из MVP** — не вводится. Локальная диагностика работает без специального скрытого доступа. Любой будущий привилегированный/удалённый механизм диагностики вводится отдельным архитектурным решением с полным контрактом (кто выдаёт, кто использует, срок действия, область полномочий, хранение, отзыв, аудит). Решение закрыто 2026-09-13.

**MVP non-goals:** полноценный Android runtime, отдельный Linux UX, embeddings, vector DB, reranker. Нет скрытых обязательных GPU/vector dependencies.

**Gate G-11:** приложение запускается на целевой Windows-среде без IDE и выдаёт понятную диагностику отсутствующих компонентов.

---

# 13. DEPENDENCY MATRIX

| EPIC | Depends on | Parallel | Blocks |
|---|---|---|---|
| 01 Foundation | — | — | 02 |
| 02 Data Layer | 01 | — | 03, 04 |
| 03 State Machines | 02 | — | 04, 05, 06, 07 |
| 04 Search Core | 02, 03 | 06 | 05, 07, 08 |
| 05 Research Engine | 03, 04 | 06 | 07, 08 |
| 06 LLM Backend | 01, 03 | 04, 05 | 07, 09 |
| 07 MCP | 03, 04, 05, 06 | limited QA | 08, 09 |
| 08 GUI | 02, 03, 04, 05, 07 | QA | 09 |
| 09 Integration | 01–08 | — | 10 |
| 10 Final QA | 01–09 | — | 11 |
| 11 Packaging | 10 | — | Release |

---

# 14. PARALLELIZATION RULES

**P-01.** Параллельная разработка допускается только при стабильных контрактах между EPIC.

**P-02.** Параллельные ветки не меняют общий контракт самостоятельно. Изменение: **STOP → REPORT → ARCHITECTURAL DECISION**.

**P-03.** Каждая ветка работает в собственном TASK scope.

**P-04.** Интеграция только через определённые interfaces/contracts. Временные обходы, меняющие архитектуру, запрещены.

**P-05.** Необходимость изменения другого EPIC: **STOP → REPORT → WAIT**.

**P-06.** Наличие заранее написанного, но неиспользуемого кода не является основанием менять соседний EPIC.

---

# 15. EPIC DEFINITION OF DONE

```text
Implementation
 ↓
Unit/Component Tests
 ↓
Contract Tests
 ↓
Scope Check
 ↓
Architecture Check
 ↓
Gate
 ↓
Baseline
```

EPIC не считается завершённым только по факту написания кода.

---

# 16. NEXT STEP

```text
EPIC SPECIFICATIONS v1.0 — BASELINE
                ↓
EPIC INTERDEPENDENCY / PARALLELIZATION
                ↓
TASK decomposition
                ↓
TASK EXECUTION CONTRACT
                ↓
CODE / TEST / REVIEW
```

Первой рабочей веткой является **EPIC-01 — FOUNDATION**. EPIC-02…EPIC-11 уже задают архитектурный каркас и могут получать независимые TASK при наличии разрешения архитектора.

**Конец EPIC SPECIFICATIONS v1.0 — BASELINE**
