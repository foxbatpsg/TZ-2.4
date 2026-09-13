# MASTER DEVELOPMENT ROADMAP v1.2

**Проект:** Research Prompt Suite  
**База:** утверждённое ТЗ v2.4  
**Статус:** Development Planning Baseline / Candidate Freeze  
**Версия:** 1.2 (A-01: версия трактуется как 1.2)  
**Назначение:** верхнеуровневая карта разработки. Не заменяет ТЗ, State Machine Specification, MCP Tool Contracts и будущие EPIC/TASK-документы.

---

## 1. Назначение

Roadmap определяет порядок разработки, крупные EPIC, зависимости, контрольные точки и критерии перехода. Подробные инструкции реализации не входят в этот документ.

```text
ТЗ → MASTER ROADMAP → EPIC → TASK → CODE → TEST → ACCEPTANCE GATE → следующий EPIC
```

Roadmap оптимизирован для разработки локальными AI-агентами с ограниченным контекстом.

---

## 2. Базовые правила

### R-01. ТЗ — источник истины

Утверждённое ТЗ v2.4 и нормативные приложения имеют приоритет над Roadmap и TASK.

При противоречии:

**STOP → REPORT → ожидание решения.**

Агент не имеет права самостоятельно выбирать трактовку, меняющую архитектуру или требования.

### R-02. Core — authority

Core единолично владеет:
- бизнес-правилами;
- бюджетами;
- SearchTask execution;
- State Machines;
- достаточностью исследования;
- дедупликацией;
- DB-write policy.

GUI, LLM и MCP не обходят Core.

### R-03. CODE не меняет scope

CODE выполняет только назначенную TASK.

**Обнаружение проблемы ≠ разрешение на её исправление.**

Если обнаружена проблема вне текущей TASK:

**STOP → REPORT → WAIT.**

CODE не создаёт самостоятельно новую задачу, не расширяет scope и не выполняет архитектурное изменение без явного разрешения.

### R-03a. Minimal Change Principle

CODE MUST make the smallest change necessary to satisfy the current TASK. Запрещено без необходимости текущей TASK форматировать, переименовывать, рефакторить или «улучшать» соседний код. Существующий код считается отдельной проблемой только если он препятствует текущей TASK или нарушает её явный acceptance criterion.

### R-09. TASK Context Header

Каждая TASK получает компактный Context Header: применимые инварианты, scope, ограничения, зависимости, acceptance criteria и запреты на изменение соседнего кода. Полный Roadmap не требуется загружать в контекст CODE-агента.

### R-04. Малые задачи

Одна TASK должна давать один проверяемый результат:
- компонент;
- узкую функцию;
- или тесно связанную группу функций.

TASK должна быть выполнима локальным агентом в ограниченном контексте.

### R-05. Tests вместе с implementation

Каждая функциональная TASK содержит соответствующие автоматические тесты.

Тесты являются частью реализации, а не отдельным этапом после завершения разработки.

### R-06. Acceptance Gate

EPIC считается завершённым только после прохождения его Gate.

### R-07. Один EPIC за раз

В работу одновременно передаётся только один EPIC.

Детализация следующего EPIC не выполняется до завершения текущего Gate, если иное явно не разрешено архитектором.

### R-08. Архитектурная инвариантность

Нижестоящие уровни не могут самостоятельно изменять:
- архитектурные границы;
- authority Core;
- контракты FSM;
- MCP Tool Contracts;
- модель данных;
- правила безопасности;
- MVP scope.

Любое необходимое изменение проходит через STOP → REPORT → DECISION.

---

## 3. Архитектурная последовательность

```text
EPIC-01 Foundation
        ↓
EPIC-02 Data Layer
        ↓
EPIC-03 State Machines
        ↓
EPIC-04 Search Core
        ↓
EPIC-05 Research Engine
        ↓
EPIC-06 LLM Backend
        ↓
EPIC-07 MCP
        ↓
EPIC-08 GUI
        ↓
EPIC-09 Integration & Resilience
        ↓
EPIC-10 Final QA / Acceptance
        ↓
EPIC-11 Packaging / Portable
```

QA выполняется параллельно каждому EPIC.

---

# 4. EPIC-01 — Foundation

**Цель:** минимальное запускаемое приложение.

**Включает:** project structure, package boundaries, configuration, environment, bootstrap, logging, unified errors, identifiers, time utilities, pytest/test infrastructure, development entrypoint.

**Не включает:** SQLite domain schema, Search, MCP, GUI, LLM, исследовательскую бизнес-логику.

**Требование изоляции:** тесты не зависят от пользовательских переменных среды, рабочей директории, пользовательских данных или production DB; используют собственные временные каталоги и тестовую БД с очисткой.

**Gate G-01:** приложение запускается; конфигурация валидируется; тесты выполняются в изолированной среде; временные данные очищаются; ошибки унифицированы; stdout policy проверяется автоматически; границы пакетов определены.

---

# 5. EPIC-02 — Data Layer

**Цель:** надёжное SQLite-хранилище и DB-write layer.

**Включает:** SQLite/WAL/PRAGMA factory, migrations, transactions, repositories, DB-write layer, Project/Study isolation, global document registry, все сущности ТЗ, FK/indexes/hashes, operation_id/request_id/idempotency, persistence tests.

**Ключевые сущности:** Project, Study, ResearchIntent, ResearchSession, SearchTask, SearchResult, Source, SourceRelation, Entity, Document, DocumentChunk, StudyDocumentLink, Evidence, EvidenceContextChunk, Observation, Claim, ClaimEvidence, Contradiction, ResearchGap, SufficiencyEvaluation, ResearchConfig, ResearchState, WorkingMemory, CacheEntry, LogRecord, Job.

**Нормализованные таблицы (A-03):** EntityAlias, IntentEntity, IntentInformationNeed, IntentConstraint, IntentSourcePreference, IntentOutputRequirement, SourceIdentifier, SearchResultIdentifier, ChunkNumericSignature, DocumentSourceOccurrence, SourceQualityAssessment, SufficiencyMetric, SufficiencyRuleHit, BudgetLimit, BudgetCounter, BudgetReservation, BudgetLedger, OutboxEvent — реализуются в EPIC-02.

**Синхронизация с реестром (Q-01):** Project DB — источник истины; синхронизация registry.db выполняется через transactional outbox (OutboxEvent в той же транзакции + идемпотентный Registry Writer + reconciliation). Snapshot manifest не является crash-atomic; восстановление проверяет manifest и выполняет outbox reconciliation.

**Durability (A-11):** synchronous=FULL для записи, foreign_keys=ON на каждом соединении, backup через SQLite Backup API, мониторинг WAL/свободного места.

### Требование FTS5/BM25 readiness

Схема и persistence layer должны быть архитектурно совместимы с последующей FTS5/BM25-индексацией `DocumentChunk`.

Обязательна детерминированная связь:

```text
DocumentChunk.content
        ↓
FTS5/BM25 index representation
        ↓
retrieval result
        ↓
DocumentChunk / Document / Study
```

Изменение индексируемого текста не должно приводить к рассинхронизации retrieval-индекса и `DocumentChunk`.

**Важно:** реализация FTS5/BM25 относится к EPIC-04. EPIC-02 не обязан реализовывать полноценный retrieval engine.

**Правило:** Data Layer не содержит Search/LLM/GUI orchestration.

**WAL-safe snapshot:** DB-write layer/snapshot subsystem обеспечивает согласованный backup SQLite в WAL. Прямое копирование `.db` во время активной WAL-операции запрещено. Конкретный механизм определяется при реализации.

**Gate G-02:** migrations, CRUD, rollback, FK, project/study isolation, document reuse, idempotency, concurrent read/write, WAL, DB-write layer, deterministic fixtures, архитектурная готовность схемы к FTS5/BM25 и тесты проходят.

---

# 6. EPIC-03 — State Machines

**Цель:** реализовать формальные автоматы как самостоятельный фундамент.

**Автоматы:** Study, ResearchSession, SearchTask, MCP Operation, LLM Backend, Job runtime lifecycle.

**Включает:** states, transitions, triggers, guards, authority, atomic state + LogRecord, invalid transitions, command handling, recovery scenarios.

**Обязательные сценарии:** Soft Stop, Hard Stop, Budget Exhaustion, LLM Failure/Recovery, Session Resume, Task Cancel, Job Cancel, Timeout, Retry.

**Gate G-03:** каждый допустимый и запрещённый переход тестируется; прямое изменение status через публичный domain API невозможно; переход + audit LogRecord атомарны; commands не превращены в states.

---

# 7. EPIC-04 — Search Core

**Цель:** детерминированное поисковое и документное ядро, работающее без LLM.

**Подэтапы:**
1. SourceAdapter/provider abstraction и domain limits.
2. URL normalization/canonicalization.
3. Search providers, ranking, filtering, concurrency, timeout, retry/backoff.
4. Deduplication: URL, DOI, PMID, arXiv, content hash, near-duplicate, SourceRelation.
5. Query Fingerprint & Loop Prevention: query normalization, `query_fingerprint`, многофакторная защита от повторных/семантически одинаковых запросов и интеграция с budget/ResearchGap.
6. Fetch/parse/chunk: heading_path, overlap, overlap_group_id, is_overlap, numeric signatures.
7. Local retrieval: SQLite FTS5/BM25, study/document isolation.
9. Evidence: evidence_hash, target/context distinction, provenance.
11. Cache: key, TTL, hit/miss, cleanup, diagnostics.
12. Budget: time, network, LLM/tool calls, atomic deduction.
13. CoverageCalculator, SufficiencyEvaluator, information gain, ResearchGap.

### Retrieval text normalization

Retrieval должен использовать абстракцию tokenizer:

```text
RetrievalTextNormalizer
       │
       ├── BasicNormalizer
       │
       └── RussianMorphologyNormalizer
```

Требования:
- normalizer не должен быть жёстко связан с конкретной библиотекой;
- конкретная реализация RussianMorphologyNormalizer выбирается и проверяется в EPIC-04;
- полноценная русская морфологическая нормализация не считается автоматически выполненной только из-за наличия FTS5;
- выбор tokenizer должен подтверждаться тестами/benchmark на целевом корпусе;
- fallback на BasicTokenizer должен быть допустимым и явно диагностируемым.

Примечание (A-01): пропуски номеров подэтапов (8, 10) в списке EPIC-04 — техническое следствие нумерации, а **не отсутствующие требования**. Обоснование и критерий приёмки нормы — §21.1 настоящего документа.

Границы ответственности (A-16): EPIC-04 предоставляет чистые типизированные primitives (coverage, sufficiency, budget); EPIC-05 вызывает их и не реализует второй evaluator.

Не следует фиксировать в Roadmap конкретный Python API или конкретный morphology engine до проверки совместимости с целевой SQLite/FTS5 реализацией.

**Gate G-04:** проходит полный CPU-only pipeline

```text
query → candidates → normalization → deduplication → fetch
→ parse → chunk → store → FTS5/BM25 → Evidence
```

без LLM и GUI.

Дополнительно Gate должен подтверждать:
- консистентность `DocumentChunk` ↔ retrieval index;
- deterministic retrieval;
- isolation по Study/Document;
- корректную работу выбранного tokenizer;
- отсутствие обязательной зависимости от GPU/embeddings/vector DB.

---

# 8. EPIC-05 — Research Engine

**Цель:** управляемый исследовательский цикл.

```text
Question → ResearchIntent → Analysis Strategy → Research Plan
→ Search Tasks → Retrieval → Evidence → Observation/Claim
→ Analysis → Research Gaps → SufficiencyEvaluator
→ continue/stop → Report
```

**Включает:** ResearchIntent validation, plan representation, SearchTask orchestration, iteration, CoverageCalculator, SufficiencyEvaluator, ResearchGap lifecycle, primary-source search, contradiction pipeline, aggregation/evidence modes, MATERIALS_ONLY, EXPAND.

Новые SearchTask создаются только через предусмотренный механизм ResearchGap → planning → Core validation.

Core остаётся владельцем task acceptance, duplicate/similar query checks, budget, coverage, sufficiency и execution.

A-16: Research Engine вызывает typed primitives EPIC-04 (coverage/sufficiency/budget) и не реализует второй SufficiencyEvaluator. G-04 проверяется на fixtures без реальной LLM, G-05 — через FakeLLM.

**Gate G-05:** mock-LLM end-to-end цикл `intent → plan → tasks → retrieval → evidence → gap → next task → sufficiency → finalize` проходит. Решение о завершении принимает Core.

---

# 9. EPIC-06 — LLM Backend

**Цель:** изолировать локальные LLM единым provider interface.

**Включает:** LLMProvider, LM Studio/Ollama adapters, backend configuration, health monitor, timeout, degraded/unreachable/restart, switching, structured output, JSON Schema validation, constrained decoding / grammar-based structured generation, если поддерживается backend, controlled repair как fallback, TokenBudgetManager, context budget, prompt construction.

### Structured output policy

Приоритет:

```text
LLM
 ↓
JSON Schema / grammar constrained decoding
 ↓
strict schema validation
 ↓
semantic/content validation
 ↓
accepted result
```

Если backend не поддерживает constrained decoding:

```text
normal generation
 ↓
strict JSON Schema validation
 ↓
limited controlled repair
 ↓
re-validation
 ↓
retry / failure
```

Post-hoc repair не является основным механизмом получения структурированного результата.

Результат считается действительным только после успешной валидации схемы и минимальной содержательной проверки.

**Контекстная граница:** сырые HTML, полные страницы и длинные логи не передаются LLM. Core формирует компактный контекст из Evidence, состояния и ResearchGap.

### Content validation

Помимо schema validation проверяются обязательные ключевые данные, существование ссылок на Evidence/объекты, допустимые диапазоны, соответствие текущей операции и отсутствие очевидного обрыва/зацикливания. Формально валидный, но недопустимо пустой результат отклоняется. Проверка не определяет истинность утверждений.

**Gate G-06:** unreachable, timeout, invalid/truncated JSON, degraded response, restart, backend switch, context budget, structured output validation, constrained decoding при наличии поддержки, controlled repair fallback и сохранение state проходят тесты.

---

# 10. EPIC-07 — MCP

**Цель:** строго ограниченный инструментальный интерфейс LLM.

### MCP-1 Planning / Session
`plan_research`, `start_research_session`, `get_research_session_statistics`, `get_study_dashboard`

### MCP-2 Retrieval
`search_web`, `search_academic`, `search_github`, `search_stackoverflow`, `search_web_community`

### MCP-3 Reading / Documents
`read_url_content`, `read_youtube_transcript`, `add_local_document`, `search_within_document`

### MCP-4 Materials / Memory
`save_study_material`, `search_study_materials`, `update_working_memory`, `get_working_memory`

### MCP-5 Operational / Report
`get_cache_statistics`, `get_cache_diagnostics`, `cleanup_expired_cache`, `validate_and_save_report`, `get_job_status`, `cancel_job`

**Включает:** JSON-RPC transport, schemas, validation, MCP Operation lifecycle, operation_id, idempotency, timeout, error mapping, stdout isolation, contract tests.

На уровне MCP integration tests stdout/stderr перехватывается; произвольный debug output в transport channel должен приводить к падению теста.

### MCP architectural invariant

MCP является **proxy/adapter над Core/Application API**.

Запрещён маршрут:

```text
LLM → MCP → прямое изменение FSM
```

Обязательный принцип:

```text
LLM
 ↓
MCP
 ↓
Command / Application API
 ↓
Core
 ↓
FSM / Job
 ↓
State + DB
```

MCP не имеет права самостоятельно:
- менять FSM state;
- обходить Core;
- выполнять DB-write в обход DB-write policy;
- самостоятельно принимать бизнес-решения.

Только Core/Application layer инициирует предусмотренные переходы и операции.

**Gate G-07:** 23 tools зарегистрированы; schemas и invalid input корректны; timeout/errors работают; MCP не изменяет FSM напрямую; task_id сохраняется; local-document path защищён; повтор не создаёт duplicate entities; MCP работает только через разрешённые Core/Application API.

---

# 11. EPIC-08 — GUI

**Цель:** Windows GUI как тонкий клиент над Core/Application API.

**Стек:** Python + CustomTkinter + SQLite. Browser не требуется.

**Подэтапы:** application shell; project/study creation; project switching через Project Registry; Intent Blueprint; X-Ray Activity Stream; Evidence Explorer/Tree; Report Viewer; Dashboard/Health; Snapshot/Offline; Review/Aggregation UI; cooperative cancellation.

**Кооперативная отмена (A-14):** применяется в GUI-слое — cancellation token + ограниченные батчи; unsafe thread kill запрещён; неотменяемые CPU-библиотеки выносятся в дочерний процесс без DB-write (см. раздел 6 ТЗ, §9 и раздел 4 ТЗ, §28).

**Правило:** Main Thread не выполняет тяжёлый retrieval, parsing, indexing или orchestration.

**Gate G-08:** GUI не содержит бизнес-правил; worker независим; UI остаётся отзывчивым; soft/hard stop, offline, snapshot и Evidence traceability работают.

---

# 12. EPIC-09 — Integration & Resilience

**Полный маршрут:**

```text
GUI → Application/Core → Research Engine → MCP/LLM → Search Core → Data Layer
```

**Проверить:** LLM failure/recovery/switch; network timeout/rate-limit/unavailable/parse-error; pause/resume/soft-stop/hard-stop; budget exhaustion/freeze/extension/partial finalization; DB rollback/restart; interrupted Job; session resume/checkpoint; preservation of Evidence/Claims.

**Gate G-09:** восстановление не теряет валидные сохранённые данные и не нарушает FSM.

---

# 13. EPIC-10 — Final QA / Acceptance

**Уровни:** Unit → Component → Integration → FSM → MCP Contract → E2E → Failure Scenarios → Acceptance.

**Обязательные области:** data isolation, BM25, tokenizer, Russian morphology (обязательна для MVP — A-13; Acceptance морфологии — обязательный критерий G-10), deterministic chunking, overlap protection, FTS5/index consistency, evidence_hash, aggregation, claims, contradictions, primary source, context protection, LLM resilience, structured JSON validation, GUI responsiveness, cooperative cancellation, network resilience, security, MATERIALS_ONLY, offline, CPU-only.

**Gate G-10:** все обязательные критерии Раздела 07 ТЗ выполнены; критических известных дефектов нет.

---

# 14. EPIC-11 — Packaging / Portable

**Цель:** эксплуатационный MVP.

**Включает:** portable folder, configuration, local DB handling, environment checker, dependency diagnostics, administrator diagnostic token, startup checks, logging, backup/recovery instructions.

**Не входит в MVP:** полноценный Android runtime, отдельный Linux UX, embeddings, vector DB, reranker.

Архитектурная совместимость сохраняется.

В MVP не допускаются скрытые обязательные зависимости от embeddings, vector search, vector DB или GPU.

**Gate G-11:** приложение запускается на целевой Windows-среде без IDE и выдаёт понятную диагностику отсутствующих компонентов.

---

# 15. Dependency Matrix

| EPIC | Зависит от | Блокирует |
|---|---|---|
| 01 Foundation | — | 02 |
| 02 Data Layer | 01 | 03, 04, 05 |
| 03 State Machines | 02 | 04, 05, 06, 07 |
| 04 Search Core | 02, 03 | 05, 07, 08 |
| 05 Research Engine | 03, 04 | 07, 08 |
| 06 LLM Backend | 01, 03 | 07, 09 |
| 07 MCP | 03, 04, 05, 06 | 08, 09 |
| 08 GUI | 02, 03, 04, 05, 07 | 09 |
| 09 Integration | 01–08 | 10 |
| 10 Final QA | 01–09 | 11 |
| 11 Packaging | 10 | Release |

---

# 16. Milestones

- **M0 Skeleton:** после G-01 — приложение запускается, тесты работают.
- **M1 Persistent Core:** после G-02 — database + repositories + isolation + FTS5 readiness.
- **M2 Formal Core:** после G-03 — FSM + audit + commands.
- **M3 Search Core:** после G-04 — deterministic search/retrieval/document pipeline.
- **M4 Research Core:** после G-05 — research cycle без реального LLM.
- **M5 LLM Integration:** после G-06 — локальная LLM безопасно подключена.
- **M6 MCP Complete:** после G-07 — 23 tools под контрактом.
- **M7 Usable GUI:** после G-08 — человек может работать с системой.
- **M8 Resilient System:** после G-09 — recovery/stop/budget/error scenarios.
- **M9 Accepted MVP:** после G-10 — acceptance pass.
- **M10 Portable Release:** после G-11 — deployable MVP.

---

# 17. Definition of Done для EPIC

EPIC считается DONE только если:

1. код реализован;
2. соответствующие тесты реализованы;
3. тесты проходят;
4. acceptance criteria выполнены;
5. нет известных нарушений утверждённой архитектуры;
6. документация EPIC обновлена;
7. scope не расширен;
8. Gate пройден;
9. результат зафиксирован Orchestrator;
10. обнаруженные, но не входящие в scope проблемы зарегистрированы отдельно и не были самовольно исправлены.

---

# 18. Следующий уровень детализации

После утверждения Roadmap создаётся **только один EPIC-документ за раз**. Затем он декомпозируется в TASK.

```text
Roadmap
  ↓
один EPIC
  ↓
детализация EPIC
  ↓
TASK batch
  ↓
implementation
  ↓
TEST
  ↓
Gate
  ↓
следующий EPIC
```

Все TASK заранее не создаются.

Это:
- ограничивает контекст локального агента;
- уменьшает риск накопления ошибочных предположений;
- позволяет корректировать план без переписывания всего проекта;
- сохраняет контроль архитектора над scope.

---

# 19. Нормативные источники

При разработке приоритет следующий:

1. утверждённое ТЗ v2.4 + утверждённые изменения (УИ v1.0: A-01…A-21, Q-01…Q-05);
2. `STATE MACHINE SPECIFICATION v1.2`;
3. `BUDGET CONTRACT v1.0`;
4. `MCP TOOL CONTRACTS v1.1` (до выпуска v1.2);
5. EPIC-документ текущего этапа;
6. TASK текущего этапа;
7. код и существующие тесты.

Нижестоящий документ не имеет права самостоятельно переопределять вышестоящий.

---

# 20. Change Log v1.2

По сравнению с v1.1:

1. Добавлены изоляция тестовой среды и автоматическая проверка stdout policy.
2. Введены R-03a Minimal Change Principle и R-09 TASK Context Header.
3. EPIC-02 дополнен шестью обязательными сущностями: `Entity`, `SearchResult`, `EvidenceContextChunk`, `SufficiencyEvaluation`, `ResearchConfig`, `ResearchState`.
4. EPIC-02 дополнен WAL-safe snapshot/backup policy.
5. EPIC-04 дополнен Query Fingerprint и многофакторной защитой от дублирующих/циклических запросов.
6. EPIC-04 дополнен lifecycle BM25 index и version metadata.
7. EPIC-04 уточнён как Python-side retrieval text normalization с одинаковой логикой для Query и Document.
8. EPIC-06 освобождён от зависимости от EPIC-05; добавлена semantic/content validation.
9. EPIC-07 дополнен автоматическим stdout transport contract test.
10. EPIC-08 дополнен cooperative cancellation и project switching через Project Registry.
11. Dependency Matrix исправлена.

По применению УИ v1.0 (A-01…A-21, Q-01…Q-05):

12. Версия документа трактуется как 1.2 (A-01); пропуски пунктов 8/10 в EPIC-04 — не отсутствующие требования; ребро EPIC-05 → EPIC-06 в Dependency Matrix удалено (A-01). **Обоснование:** Change Log п.8 и строка зависимостей EPIC-06 разрешают независимый backend; пропуски 8/10 — техническое следствие ревизии нумерации подэтапов. **Критерий приёмки:** граф ацикличен; заявленные зависимости и обратные связи согласованы. Полное определение нормы — §21.1.
13. EPIC-02 дополнен нормализованными таблицами (A-03), outbox-синхронизацией реестра (Q-01) и durability-гарантиями (A-11).
14. EPIC-04/EPIC-05 разведены по typed primitives (A-16); G-04 — fixtures без LLM, G-05 — FakeLLM.
15. Acceptance морфологии — обязательный критерий G-10 (A-13).
16. Нормативные источники переведены на FSM v1.2 и BUDGET CONTRACT v1.0.

---

## 21. Реестр утверждённых изменений (УИ v1.0)

> Состав: `A-01…A-21`, `Q-01…Q-05`. Этот реестр — нормативное определение утверждённых изменений, на которые ссылаются шапки приложений и §19 «Нормативные источники». Формулировки норм `A-02…A-21` и `Q-01…Q-05` определены в разделах ТЗ `01`–`07` и приведены здесь адресно; определения не дублируются, первичный источник указан в поле «Где определено».

### 21.1. Редакционные ошибки Roadmap и граф зависимостей

**Редакционные ошибки Roadmap и граф зависимостей (A-01):** версия Roadmap в шапке — 1.2, а не 1.1; пропуски пунктов 8 и 10 в списке подэтапов EPIC-04 не означают отсутствующие требования, так как карточки привязаны к названиям подэтапов, а не к ошибочной нумерации; техническое ребро EPIC-05 → EPIC-06 в Dependency Matrix удалено, поскольку Change Log и строка зависимостей EPIC-06 явно разрешают независимый backend; последовательность выдачи эпиков при этом остаётся gated.

**Источник правила:** Roadmap, заголовок, §7, §15, Change Log.

**Обоснование:** Change Log (пункт 8) и строка зависимостей EPIC-06 явно разрешают независимый backend — ребро EPIC-05 → EPIC-06 устанавливало архитектурную зависимость при отсутствии фактической; пропуски нумерации 8/10 в EPIC-04 — техническое следствие переработки списка подэтапов при ревизии, при котором карточки остались привязаны к названиям подэтапов.

**Применения:** `EPIC SPECIFICATIONS v1.0` стр. 146; заголовок настоящего документа, стр. 6; §7 стр. 244; Change Log п. 12 стр. 575; `EPIC → TASK DECOMPOSITION v1.0` стр. 269; `TASK EXECUTION CONTRACT v1.0` стр. 14.

**Критерий приёмки:** граф ацикличен; заявленные зависимости и обратные связи согласованы.

Дополнительно нормы закрепляют следующее:

- **Версия Roadmap (A-01):** версия документа трактуется как 1.2.
- **Пропуски нумерации подэтапов (A-01):** пропуски номеров подэтапов (8, 10) в списке EPIC-04 — техническое следствие нумерации, а **не отсутствующие требования**.
- **Граф зависимостей EPIC (A-01):** архитектурной зависимости EPIC-06 от EPIC-05 нет; gated-порядок сохраняется.

### 21.2. Прочие нормы состава УИ v1.0

| Норма | Где определено | Краткое содержание |
|---|---|---|
| `A-02` | ТЗ `01` §2.3, стр. 84 | Разграничение ролей при переходах: LLM предлагает, Watchdog сигнализирует, Core выполняет |
| `A-03` | ТЗ `03` §2, стр. 91 | JSON/сериализация — не источник истины; связи только через нормализованные таблицы |
| `A-04` | ТЗ `03` §6, стр. 178 | Область уникальности и идемпотентности — в пределах Study/Project |
| `A-05` | ТЗ `03` §13, стр. 425 | Уникальность Evidence: проверка по позиции до `evidence_hash` |
| `A-06` | ТЗ `03` §11, стр. 387 | Полуоткрытые интервалы `[char_start, char_end)`; алгоритм склейки overlap |
| `A-07` | ТЗ `03` §11, стр. 350 | Стабильные идентификаторы `chunk_id`; `DocumentChunk.text` (не `content`) |
| `A-08` | ТЗ `03` §9a, стр. 293 | Одно очищенное тело документа + множество `DocumentSourceOccurrence` |
| `A-09` | ТЗ `03` §25.2, стр. 814 | Границы реестра: только идентичность и расположение, без доступа к содержимому |
| `A-10` | ТЗ `03` §15, стр. 500 | Разделение класса доказательности и оценки качества источника |
| `A-11` | ТЗ `03` §24, стр. 770 | Durability: `synchronous=FULL`, `foreign_keys=ON`, backup через SQLite Backup API |
| `A-12` | ТЗ `02` §6a, стр. 141 | Расчёт контекста по режимам `fixed`/`auto`/`auto_with_config_cap` |
| `A-13` | ТЗ `04` §14.1, стр. 284 | RU-морфология обязательна для MVP; BasicNormalizer — только degraded fallback |
| `A-14` | ТЗ `04` §28, стр. 695 | Кооперативная отмена; unsafe thread kill запрещён |
| `A-15` | ТЗ `01` §7, стр. 211 | Стартовый план создаёт ResearchGap; запуск поиска через сохранённый gap |
| `A-16` | ТЗ `04` §26, стр. 580 | Границы ответственности: Core даёт typed primitives, Engine не дублирует evaluator |
| `A-17` | ТЗ `02` стр. 100 | Приватность локальных источников: пути не передаются LLM и в отчёт |
| `A-18` | ТЗ `03` §17b, стр. 583 | Неизменяемые ревизии `ResearchConfig`; backend версионируется отдельно от порогов |
| `A-19` | ТЗ `05` §16, стр. 329 | Protocol error ≠ domain error (JSON-RPC коды vs доменный `code`) |
| `A-20` | ТЗ `05` §3.1, стр. 54 | Runtime stdout protection: перехват постороннего вывода без разрушения транспорта |
| `A-21` | ТЗ `03` §9, стр. 291 | Неизменяемость Document; обновление URL/контента создаёт новую версию |
| `Q-01` | ТЗ `03` §25.3, стр. 816 | Синхронизация Project DB → `registry.db` через transactional outbox |
| `Q-02` | ТЗ `01` §7, стр. 341 | Независимость источников на уровне Claim (claim-scoped) |
| `Q-03` | ТЗ `04` §22, стр. 578 | Strategy profiles и пороги остановки (EVIDENCE / AGGREGATION) |
| `Q-04` | ТЗ `03` §17c, стр. 644 | Бюджет: `reserve`/`commit`/`release` в одной транзакции |
| `Q-05` | ТЗ `01` §2.3, стр. 115 | Межавтоматная policy при восстановлении после recovery |

**Приоритет при конфликте.** A-01 входит в пункт 1 §19 «Нормативные источники» (утверждённые изменения) и имеет приоритет выше EPIC-документа.

---

**Конец MASTER DEVELOPMENT ROADMAP v1.2**
