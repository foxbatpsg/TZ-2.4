# EPIC → TASK DECOMPOSITION v1.0 — BASELINE

**Проект:** Research Prompt Suite  
**Статус:** Draft for TASK generation  
**Основание:** ТЗ v2.4 + УИ v1.0 (A-01…A-21, Q-01…Q-05); State Machine Specification v1.2; BUDGET CONTRACT v1.0; MCP Tool Contracts v1.1 (до выпуска v1.2); MASTER DEVELOPMENT ROADMAP; EPIC SPECIFICATIONS v1.0 — BASELINE; TASK EXECUTION CONTRACT v1.0 — BASELINE.

# 1. Назначение

Документ декомпозирует EPIC-01…EPIC-11 на небольшие, проверяемые TASK.

Это не набор готовых TASK для немедленной передачи CODE Agent. Перед исполнением конкретная TASK должна получить полный Context Header по TASK EXECUTION CONTRACT.

Принцип:

```text
EPIC
 ↓
TASK group
 ↓
atomic TASK
 ↓
CODE / TEST / REVIEW
```

---

# 2. Правила декомпозиции

1. Одна TASK должна иметь один проверяемый результат.
2. TASK должна быть небольшой: предпочтительно XS/S, M только когда разделение создаёт искусственную связанность.
3. TASK не должна одновременно менять несколько архитектурных слоёв без явной необходимости.
4. Каждая TASK имеет `ALLOWED_FILES`.
5. Каждая TASK имеет явные `FORBIDDEN` области.
6. Production implementation и её обязательные unit/component tests могут находиться в одной CODE TASK, если это соответствует контракту.
7. Большие test suites, integration tests и acceptance tests выделяются отдельно.
8. Обнаруженная проблема вне scope: **STOP → REPORT → WAIT**.
9. CODE не создаёт новые TASK.
10. Изменение DB schema, public API, FSM, MCP contract или архитектурной границы без разрешения запрещено.
11. TASK не считается DONE без проверок и Evidence Bundle.

---

# 3. EPIC-01 — FOUNDATION

### Group F1 — Project skeleton

* **E01-T01** — создать базовую структуру пакетов проекта.
* **E01-T02** — определить module/package boundaries.
* **E01-T03** — создать минимальный application entrypoint.
* **E01-T04** — создать базовую конфигурационную модель и загрузчик.

### Group F2 — Common infrastructure

* **E01-T05** — unified identifiers.
* **E01-T06** — time utilities.
* **E01-T07** — unified error model.
* **E01-T08** — logging subsystem.
* **E01-T09** — environment abstraction.

### Group F3 — Testing

* **E01-T10** — pytest configuration.
* **E01-T11** — isolated temporary test environment.
* **E01-T12** — environment independence tests.
* **E01-T13** — stdout/logging isolation fixture для MCP-safe execution.
* **E01-T14** — Foundation integration test.

### Gate

`G-01`

### Main output

Воспроизводимая тестируемая основа, на которой остальные EPIC могут безопасно строиться.

---

# 4. EPIC-02 — DATA LAYER

### Group D1 — Database foundation

* **E02-T01** — SQLite connection factory.
* **E02-T02** — PRAGMA configuration.
* **E02-T03** — WAL configuration and lifecycle.
* **E02-T04** — migration framework.
* **E02-T05** — transaction helpers.

### Group D2 — Core schema

* **E02-T06** — Project/Study schema.
* **E02-T07** — Entity/ResearchIntent/ResearchConfig schema.
* **E02-T08** — ResearchState/ResearchSession schema.
* **E02-T09** — SearchTask/Source/SourceRelation/SearchResult schema.
* **E02-T10** — Document/DocumentChunk/StudyDocumentLink schema.
* **E02-T11** — Evidence/EvidenceContextChunk/Observation schema.
* **E02-T12** — Claim/ClaimEvidence/Contradiction schema.
* **E02-T13** — ResearchGap/SufficiencyEvaluation schema.
* **E02-T14** — WorkingMemory/CacheEntry/LogRecord/Job schema.

### Group D3 — Persistence layer

* **E02-T15** — repository base conventions.
* **E02-T16** — DB-write layer.
* **E02-T17** — foreign keys, indexes and uniqueness constraints.
* **E02-T18** — idempotency / operation_id / request_id persistence.
* **E02-T19** — Project/Study isolation.
* **E02-T20** — global Document reuse.

### Group D4 — Snapshot / backup

* **E02-T21** — WAL-safe backup mechanism.
* **E02-T22** — coordinated snapshot subsystem.
* **E02-T23** — restore/checkpoint verification.
* **E02-T24** — snapshot consistency tests.

### Group D5 — Data tests

* **E02-T25** — migration tests.
* **E02-T26** — transaction/rollback tests.
* **E02-T27** — concurrent read/write tests.
* **E02-T28** — deterministic fixtures.
* **E02-T29** — persistence integration tests.

### Gate

`G-02`

---

# 5. EPIC-03 — STATE MACHINES

### Group S1 — FSM framework

* **E03-T01** — generic state/transition representation.
* **E03-T02** — transition guard mechanism.
* **E03-T03** — command model.
* **E03-T04** — invalid transition handling.
* **E03-T05** — atomic state + LogRecord mechanism.

### Group S2 — Study / ResearchSession

* **E03-T06** — Study FSM.
* **E03-T07** — ResearchSession FSM.
* **E03-T08** — session resume/checkpoint semantics.

### Group S3 — SearchTask / Job

* **E03-T09** — SearchTask FSM.
* **E03-T10** — Job lifecycle FSM.
* **E03-T11** — timeout/retry semantics.
* **E03-T12** — task/job cancellation semantics.

### Group S4 — LLM / MCP operation lifecycle

* **E03-T13** — LLM backend lifecycle states.
* **E03-T14** — MCP operation lifecycle states.

### Group S5 — Stop/recovery

* **E03-T15** — Soft Stop.
* **E03-T16** — Hard Stop.
* **E03-T17** — budget exhaustion.
* **E03-T18** — failure/recovery transitions.
* **E03-T19** — resume after interruption.

### Group S6 — Tests

* **E03-T20** — allowed transition tests.
* **E03-T21** — forbidden transition tests.
* **E03-T22** — atomic state/audit tests.
* **E03-T23** — cancellation/timeout/retry tests.
* **E03-T24** — recovery/resume tests.

### Gate

`G-03`

---

# 6. EPIC-04 — SEARCH CORE

### Group R1 — Provider abstraction

* **E04-T01** — SourceAdapter interface.
* **E04-T02** — provider/domain limits.
* **E04-T03** — provider timeout/retry/backoff.
* **E04-T04** — provider result normalization.

### Group R2 — URL and source normalization

* **E04-T05** — URL canonicalization.
* **E04-T06** — source identity normalization.
* **E04-T07** — SourceRelation handling.

### Group R3 — Deduplication

* **E04-T08** — URL/identifier deduplication.
* **E04-T09** — content hash deduplication.
* **E04-T10** — near-duplicate detection.
* **E04-T11** — deduplication tests.

### Group R4 — Query Fingerprint / loop prevention

* **E04-T12** — query normalization.
* **E04-T13** — query_fingerprint generation.
* **E04-T14** — multi-factor duplicate-query protection.
* **E04-T15** — fingerprint integration with budget.
* **E04-T16** — fingerprint integration with ResearchGap.
* **E04-T17** — loop-prevention tests.

### Group R5 — Fetch / parse / chunk

* **E04-T18** — content fetch abstraction.
* **E04-T19** — document parsing.
* **E04-T20** — deterministic chunking.
* **E04-T21** — heading_path.
* **E04-T22** — overlap metadata.
* **E04-T23** — numeric signatures.
* **E04-T24** — chunking tests.

### Group R6 — Normalization / BM25

* **E04-T25** — RetrievalTextNormalizer interface.
* **E04-T26** — BasicNormalizer.
* **E04-T27** — RussianMorphologyNormalizer/plugin boundary.
* **E04-T28** — FTS5 schema/index representation.
* **E04-T29** — BM25 retrieval.
* **E04-T30** — study/document isolation.
* **E04-T31** — normalizer_version metadata.
* **E04-T32** — index_version/language/stopword_version metadata.
* **E04-T33** — index lifecycle: document added.
* **E04-T34** — index lifecycle: normalizer changed → rebuild_all.
* **E04-T35** — index lifecycle: study deleted → cleanup.
* **E04-T36** — FTS5/BM25 consistency tests.

### Group R7 — Evidence

* **E04-T37** — Evidence creation.
* **E04-T38** — evidence_hash.
* **E04-T39** — target/context distinction.
* **E04-T40** — provenance.
* **E04-T41** — Evidence tests.

### Group R8 — Cache / budget

* **E04-T42** — cache key/TTL.
* **E04-T43** — cache hit/miss diagnostics.
* **E04-T44** — expired cache cleanup.
* **E04-T45** — budget model.
* **E04-T46** — atomic budget deduction.
* **E04-T47** — cache/budget tests.

### Group R9 — Coverage / gaps

* **E04-T48** — CoverageCalculator.
* **E04-T49** — SufficiencyEvaluator interface.
* **E04-T50** — information gain.
* **E04-T51** — ResearchGap model/operations.
* **E04-T52** — coverage/sufficiency tests.

### Gate

`G-04`

---

# 7. EPIC-05 — RESEARCH ENGINE

Примечание (A-01): архитектурной зависимости EPIC-06 от EPIC-05 нет; фактический gated-порядок сохраняется. Определение нормы — `MASTER DEVELOPMENT ROADMAP v1.2` §21.1. Примечание (A-16): EPIC-05 вызывает typed primitives EPIC-04 (coverage/sufficiency/budget, группы R8–R9) и не реализует второй SufficiencyEvaluator; G-05 проверяется через FakeLLM.

### Group RE1 — Research configuration

* **E05-T01** — ResearchIntent validation.
* **E05-T02** — ResearchConfig handling.
* **E05-T03** — ResearchState integration.
* **E05-T04** — plan representation.

### Group RE2 — Task orchestration

* **E05-T05** — SearchTask creation request.
* **E05-T06** — Core task acceptance.
* **E05-T07** — duplicate/similar query check.
* **E05-T08** — task execution loop.
* **E05-T09** — iteration state handling.

### Group RE3 — Research control

* **E05-T10** — coverage calculation integration.
* **E05-T11** — sufficiency evaluation integration.
* **E05-T12** — ResearchGap lifecycle.
* **E05-T13** — budget control.
* **E05-T14** — completion decision.

### Group RE4 — Research modes

* **E05-T15** — MATERIALS_ONLY.
* **E05-T16** — EXPAND.
* **E05-T17** — primary-source search.
* **E05-T18** — contradiction pipeline.
* **E05-T19** — aggregation/evidence modes.

### Group RE5 — Finalization

* **E05-T20** — partial finalization.
* **E05-T21** — finalization state.
* **E05-T22** — report handoff.

### Group RE6 — Tests

* **E05-T23** — mock-LLM research loop.
* **E05-T24** — duplicate-query/loop tests.
* **E05-T25** — budget tests.
* **E05-T26** — sufficiency/completion tests.
* **E05-T27** — MATERIALS_ONLY tests.
* **E05-T28** — recovery/finalization tests.

### Gate

`G-05`

---

# 8. EPIC-06 — LLM BACKEND

### Group L1 — Provider abstraction

* **E06-T01** — LLMProvider interface.
* **E06-T02** — backend configuration.
* **E06-T03** — request/response normalization.

### Group L2 — Adapters

* **E06-T04** — LM Studio adapter.
* **E06-T05** — Ollama adapter.
* **E06-T06** — adapter contract tests.

### Group L3 — Health / resilience

* **E06-T07** — health monitor.
* **E06-T08** — timeout handling.
* **E06-T09** — unreachable/degraded states.
* **E06-T10** — restart/recovery.
* **E06-T11** — backend switching.
* **E06-T12** — resilience tests.

### Group L4 — Structured output

* **E06-T13** — JSON Schema contract layer.
* **E06-T14** — constrained decoding/grammar interface.
* **E06-T15** — engine-specific grammar configuration.
* **E06-T16** — strict schema validation.
* **E06-T17** — semantic validation.
* **E06-T18** — controlled repair fallback.
* **E06-T19** — retry/failure policy.
* **E06-T20** — structured-output tests.

### Group L5 — Context / budget

* **E06-T21** — TokenBudgetManager.
* **E06-T22** — context budget.
* **E06-T23** — prompt construction.
* **E06-T24** — compact context enforcement.
* **E06-T25** — context overflow tests.

### Gate

`G-06`

---

# 9. EPIC-07 — MCP

### Group M1 — Transport/core boundary

* **E07-T01** — MCP server bootstrap.
* **E07-T02** — Core/Application API adapter.
* **E07-T03** — tool registration mechanism.
* **E07-T04** — MCP error mapping.
* **E07-T05** — stdout isolation.

### Group M2 — Planning/session tools

* **E07-T06** — `plan_research`.
* **E07-T07** — `start_research_session`.
* **E07-T08** — `get_research_session_statistics`.
* **E07-T09** — `get_study_dashboard`.

### Group M3 — Search tools

* **E07-T10** — `search_web`.
* **E07-T11** — `search_academic`.
* **E07-T12** — `search_github`.
* **E07-T13** — `search_stackoverflow`.
* **E07-T14** — `search_web_community`.

### Group M4 — Reading/document tools

* **E07-T15** — `read_url_content`.
* **E07-T16** — `read_youtube_transcript`.
* **E07-T17** — `add_local_document`.
* **E07-T18** — `search_within_document`.

### Group M5 — Materials/memory tools

* **E07-T19** — `save_study_material`.
* **E07-T20** — `search_study_materials`.
* **E07-T21** — `update_working_memory`.
* **E07-T22** — `get_working_memory`.

### Group M6 — Operational/report tools

* **E07-T23** — `get_cache_statistics`.
* **E07-T24** — `get_cache_diagnostics`.
* **E07-T25** — `cleanup_expired_cache`.
* **E07-T26** — `validate_and_save_report`.
* **E07-T27** — `get_job_status`.
* **E07-T28** — `cancel_job`.

### Group M7 — Contract tests

* **E07-T29** — operation_id/idempotency tests.
* **E07-T30** — timeout/error contract tests.
* **E07-T31** — schema validation tests.
* **E07-T32** — no-direct-FSM/no-direct-DB tests.
* **E07-T33** — compact-response tests.
* **E07-T34** — all-tools registration/contract suite.

### Gate

`G-07`

---

# 10. EPIC-08 — GUI

### Group G1 — Shell

* **E08-T01** — application shell.
* **E08-T02** — navigation/layout.
* **E08-T03** — project registry integration.
* **E08-T04** — project switching.

### Group G2 — Study / research UI

* **E08-T05** — project/study creation.
* **E08-T06** — Intent Blueprint.
* **E08-T07** — research status/control view.
* **E08-T08** — Dashboard/Health.

### Group G3 — Activity / evidence

* **E08-T09** — X-Ray Activity Stream.
* **E08-T10** — Evidence Explorer/Tree.
* **E08-T11** — traceability view.

### Group G4 — Report / review

* **E08-T12** — Report Viewer.
* **E08-T13** — Review/Aggregation UI.
* **E08-T14** — report validation/save integration.

### Group G5 — Operations

* **E08-T15** — cooperative cancellation command layer.
* **E08-T16** — Soft Stop UI.
* **E08-T17** — Hard Stop UI.
* **E08-T18** — worker/background execution.
* **E08-T19** — responsiveness tests.

### Group G6 — Offline/snapshot

* **E08-T20** — Snapshot UI.
* **E08-T21** — Offline/MATERIALS_ONLY UI.
* **E08-T22** — snapshot consistency integration test.

### Gate

`G-08`

---

# 11. EPIC-09 — INTEGRATION & RESILIENCE

### Group I1 — Full-path integration

* **E09-T01** — GUI → Core integration.
* **E09-T02** — Core → Search integration.
* **E09-T03** — Core → LLM integration.
* **E09-T04** — Core → MCP integration.
* **E09-T05** — persistence integration.

### Group I2 — Failure scenarios

* **E09-T06** — LLM failure/recovery/switch.
* **E09-T07** — network timeout/rate-limit/unavailable.
* **E09-T08** — parse-error recovery.
* **E09-T09** — pause/resume.
* **E09-T10** — Soft Stop/Hard Stop.
* **E09-T11** — budget exhaustion/freeze/extension.
* **E09-T12** — partial finalization.

### Group I3 — Persistence/recovery

* **E09-T13** — DB rollback/restart.
* **E09-T14** — interrupted Job recovery.
* **E09-T15** — session resume/checkpoint.
* **E09-T16** — Evidence preservation.
* **E09-T17** — Claim preservation.
* **E09-T18** — duplicate-prevention after recovery.

### Gate

`G-09`

---

# 12. EPIC-10 — FINAL QA / ACCEPTANCE

### Group Q1 — Test coverage audit

* **E10-T01** — unit/component coverage audit.
* **E10-T02** — DB/data isolation audit.
* **E10-T03** — Search/BM25 audit.
* **E10-T04** — FSM audit.
* **E10-T05** — MCP contract audit.
* **E10-T06** — LLM resilience/validation audit.
* **E10-T07** — GUI audit.
* **E10-T08** — security audit.

### Group Q2 — E2E / acceptance

* **E10-T09** — full E2E research scenario.
* **E10-T10** — MATERIALS_ONLY scenario.
* **E10-T11** — offline scenario.
* **E10-T12** — failure/recovery scenario.
* **E10-T13** — cancellation scenario.
* **E10-T14** — context protection scenario.
* **E10-T15** — CPU-only MVP scenario.

### Group Q3 — Release readiness

* **E10-T16** — critical defect audit.
* **E10-T17** — acceptance evidence bundle.
* **E10-T18** — final requirements traceability.
* **E10-T19** — Gate G-10 decision package.

### Gate

`G-10`

---

# 13. EPIC-11 — PACKAGING / PORTABLE

### Group P1 — Portable structure

* **E11-T01** — portable folder layout.
* **E11-T02** — runtime/config packaging.
* **E11-T03** — local data/DB packaging rules.
* **E11-T04** — startup/bootstrap packaging.

### Group P2 — Environment checker

* **E11-T05** — runtime check.
* **E11-T06** — dependency/component check.
* **E11-T07** — permissions/filesystem check.
* **E11-T08** — SQLite health check.
* **E11-T09** — administrator diagnostic token.
* **E11-T10** — user-facing diagnostics.

### Group P3 — Backup/recovery

* **E11-T11** — packaged backup flow.
* **E11-T12** — restore verification.
* **E11-T13** — recovery documentation.

### Group P4 — Release tests

* **E11-T14** — clean Windows environment test.
* **E11-T15** — no-IDE launch test.
* **E11-T16** — missing-dependency diagnostics test.
* **E11-T17** — portable data persistence test.
* **E11-T18** — final packaging acceptance.

### Gate

`G-11`

---

# 14. TASK GENERATION RULE

Эта декомпозиция является картой работ.

Конкретная TASK создаётся только после определения:

```text
TASK-ID
TYPE
ROLE
EPIC
GOAL
SCOPE
ALLOWED_FILES
FORBIDDEN
INPUTS
OUTPUTS
CONTRACT
DEPENDENCIES
TESTS
ACCEPTANCE
STOP_CONDITIONS
DONE
ESCALATION
```

в соответствии с **TASK EXECUTION CONTRACT v1.0 — BASELINE**.

---

# 15. РЕКОМЕНДУЕМЫЙ ПОРЯДОК ПОДГОТОВКИ TASK

Не генерировать сразу все детальные TASK для всех EPIC.

Первый пакет:

```text
EPIC-01
 ↓
E01-T01 ... E01-T14
```

После стабилизации Foundation подготовить:

```text
EPIC-02
EPIC-03
```

После стабилизации их контрактов:

```text
EPIC-04
EPIC-06
```

Затем:

```text
EPIC-05
EPIC-07
EPIC-08
```

И в конце:

```text
EPIC-09
EPIC-10
EPIC-11
```

Это сохраняет возможность параллельной работы, но не создаёт преждевременную детализацию implementation details.

---

# 16. IMPORTANT

Количество TASK в этой карте **не является окончательным числом TASK проекта**.

При генерации конкретной TASK допускается:

* объединить две слишком маленькие TASK;
* разделить слишком большую TASK;
* добавить TEST/REVIEW TASK;
* изменить внутреннюю декомпозицию.

Но нельзя менять EPIC scope, архитектурные контракты или зависимости без соответствующего решения.

**Конец EPIC → TASK DECOMPOSITION v1.0 — BASELINE**

