---
# MCP TOOL CONTRACTS v1.1

**Статус:** Нормативное приложение к ТЗ v2.5  
**Назначение:** Детальные контракты 23 MCP-инструментов MVP.  
**Приоритет:** Этот документ уточняет и заменяет неоднозначные места версии v1.0.

## 0. Общие правила

1. MCP tool не является владельцем бизнес-состояний. Все изменения `Study`, `ResearchSession`, `SearchTask` и других persistent-сущностей выполняются Core через соответствующий State Machine.
2. Каждый вызов получает уникальный `operation_id`. Он используется для трассировки, `LogRecord` и связи создаваемых сущностей.
3. `study_id`, `session_id`, `task_id`, `document_id`, `project_id` должны быть UUID, если явно не указано иное.
4. MCP layer не вычисляет собственные альтернативные алгоритмы `query_fingerprint`. Fingerprint рассчитывает Search Core.
5. Повторный вызов с тем же `idempotency_key` не должен создавать дублирующую persistent-сущность.
6. Все ответы должны оставаться компактными и укладываться в заданные лимиты.
7. `stdout` MCP stdio-сервера зарезервирован только для JSON-RPC. Логи идут в файл или `stderr`.
8. Все ошибки используют единый формат:

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

9. `SOFT_STOP`/`HARD_STOP`/`CANCEL` являются commands. MCP tool не создаёт одноимённых состояний.
10. Standard MCP tools синхронны. Job-backed операции не должны маскироваться под синхронные tools.
11. `add_local_document` не принимает произвольный filesystem path от LLM. Core должен предварительно зарегистрировать разрешённый пользовательский файл и передавать безопасный `file_ref`.
12. Локальный LLM не является источником фактов; Core валидирует все сохраняемые аналитические объекты.

---

## 1. Planning

### `plan_research`

| Поле | Контракт |
|---|---|
| INPUT | `study_id`, `intent: ResearchIntent` |
| OUTPUT | `plan: List[SearchTaskDraft]`, `operation_id` |
| ERRORS | `INVALID_INPUT`, `VALIDATION_ERROR`, `DATABASE_ERROR` |
| LIMITS | до 20 задач; 16 KiB |
| TIMEOUT | 30 с |
| RETRY | 1 повтор только после `VALIDATION_ERROR` |
| SIDE EFFECTS | Core создаёт валидированные `SearchTask` со статусом `CREATED` |
| IDEMPOTENCY | `SHA256(study_id + canonicalized ResearchIntent)` |
| CANCELLATION | timeout |
| AUTHORITY | LLM предлагает; Core нормализует, валидирует и создаёт задачи |

`canonicalized ResearchIntent` включает все семантически значимые поля: question, goal, entities/target_entities, constraints, time_range, geography, source_preferences, exclusions, expected_output, analysis_strategy.

Tool не переводит Study напрямую. Если требуется `DRAFT → PLANNING → READY`, переходы выполняет Study State Machine.

---

## 2. Retrieval

### Общий контракт `search_*`

| Поле | Контракт |
|---|---|
| INPUT | `study_id`, `task_id`, `query`, `filters`, `limit` |
| OUTPUT | `candidates[]`, `operation_id`, `task_id` |
| ERRORS | `NETWORK_ERROR`, `TIMEOUT`, `RATE_LIMIT`, `SOURCE_UNAVAILABLE`, `INVALID_INPUT`, `RETRIEVAL_PROVIDER_ERROR`, `DATABASE_ERROR` |
| LIMITS | до 10 candidates; 200 символов на snippet; 8 KiB |
| TIMEOUT | 30 с |
| RETRY | 1 повтор для `NETWORK_ERROR`/`TIMEOUT`; без retry для `RATE_LIMIT` |
| SIDE EFFECTS | Core создаёт `SearchResult` и при необходимости `Source`; списывается `network_budget` |
| IDEMPOTENCY | Core использует единый `query_fingerprint`; MCP не вычисляет альтернативный fingerprint |
| CANCELLATION | timeout |
| AUTHORITY | LLM инициирует; Core проверяет SearchTask, fingerprint, budget и выполняет |

`task_id` обязателен. `SearchResult.task_id` должен ссылаться на этот SearchTask.

Допустимый жизненный цикл:

```text
SearchTask:
CREATED → VALIDATING → QUEUED → RUNNING
                                  ↓
                         search_* execution
                                  ↓
                              COMPLETED
```

Сам MCP tool не переводит SearchTask напрямую.

### `search_web`

Дополнительные filters: `time_range`, `geography`, `language`.

### `search_academic`

Дополнительные filters: `publication_type`, `min_year`. Candidate может содержать `doi`, `pmid`, `arxiv_id`.

### `search_github`

Дополнительные filters: `language`, `sort_by = STARS|UPDATED|RELEVANCE`.

### `search_stackoverflow`

Дополнительные filters: `tagged`, `min_score`.

### `search_web_community`

Дополнительные filters: `platform = REDDIT|FORUM|BLOG`, `sort_by = RELEVANCE|DATE|RATING`.

---

## 3. Reading

### `read_url_content`

| Поле | Контракт |
|---|---|
| INPUT | `study_id`, `task_id`, `url` ; `refresh` (bool, default `false`, Q-08) |
| OUTPUT | `document_id`, `title`, `content_length`, `chunks_count`, `status`, `operation_id`; `CONTENT_UNCHANGED` при совпадении `content_hash` после `refresh` |
| ERRORS | `NETWORK_ERROR`, `TIMEOUT`, `SOURCE_UNAVAILABLE`, `PARSE_ERROR`, `FULL_TEXT_UNAVAILABLE`, `CONTENT_TOO_LARGE`, `INVALID_INPUT`, `DATABASE_ERROR` |
| LIMITS | max fetch size из `ResearchConfig`; default 5 MiB |
| TIMEOUT | 60 с |
| RETRY | 1 retry для `NETWORK_ERROR`; нет retry для parse/unavailable |
| SIDE EFFECTS | Document/Chunk/Source/StudyDocumentLink/BM25; `fetch_budget` |
| IDEMPOTENCY | `SHA256(canonical_url)` в рамках project; повтор возвращает существующий Document. Флаг `refresh=true` отключает идемпотентное окно и инициирует принудительное обновление (Q-08, ADR-002): при совпадении `content_hash` новая версия Document не создаётся, ответ `CONTENT_UNCHANGED` |
| CANCELLATION | timeout |
| AUTHORITY | LLM выбирает URL; Core проверяет доступность/лимиты и сохраняет |

**Q-08, ADR-002 (2026-09-14):** идемпотентное окно 24 часа; флаг `refresh=true` — явный механизм принудительного обновления (отдельный `refresh`-tool не вводится); Study «замораживает» версию Document, на которую ссылается Evidence (A-21); EXPAND использует последнюю доступную версию; при совпадении `content_hash` новая версия не создаётся.

При недоступном полном тексте возвращается `FULL_TEXT_UNAVAILABLE`. Содержимое запрещено выдумывать.

### `read_youtube_transcript`

| Поле | Контракт |
|---|---|
| INPUT | `study_id`, `task_id`, `video_url` |
| OUTPUT | `document_id`, `title`, `transcript_length`, `chunks_count`, `duration`, `operation_id` |
| ERRORS | `NETWORK_ERROR`, `TIMEOUT`, `SOURCE_UNAVAILABLE`, `PARSE_ERROR`, `INVALID_INPUT`, `DATABASE_ERROR` |
| LIMITS | 100 000 символов |
| TIMEOUT | 60 с |
| RETRY | 1 retry для `NETWORK_ERROR` |
| SIDE EFFECTS | Document/Chunk/Source/StudyDocumentLink/BM25; `fetch_budget` |
| IDEMPOTENCY | `SHA256(canonical_video_url)` |
| CANCELLATION | timeout |
| AUTHORITY | LLM инициирует; Core выполняет |

---

## 4. Documents

### `add_local_document`

| Поле | Контракт |
|---|---|
| INPUT | `study_id`, `file_ref`, `document_type` |
| OUTPUT | `document_id`, `title`, `content_length`, `chunks_count`, `status`, `operation_id` |
| ERRORS | `INVALID_INPUT`, `PARSE_ERROR`, `UNSUPPORTED_FORMAT`, `CONTENT_TOO_LARGE`, `DATABASE_ERROR` |
| LIMITS | default 20 MiB |
| TIMEOUT | 120 с |
| RETRY | нет автоматического retry |
| SIDE EFFECTS | Document/Chunk/Source/StudyDocumentLink/BM25 |
| IDEMPOTENCY | `content_hash`; duplicate возвращает существующий Document |
| CANCELLATION | cooperative cancellation для разрешённых Job-backed imports; синхронный одиночный импорт имеет timeout |
| AUTHORITY | пользователь/GUI выбирает файл; Core разрешает, читает и сохраняет |

`file_ref` должен указывать на заранее зарегистрированный Core-approved файл. Передача LLM произвольного `C:\...` пути запрещена.

### `search_within_document`

| Поле | Контракт |
|---|---|
| INPUT | `study_id`, `document_id`, `query`, `limit` |
| OUTPUT | `chunks[]: chunk_id, text_snippet, relevance_score, position_index` |
| ERRORS | `INVALID_INPUT`, `RETRIEVAL_PROVIDER_ERROR`, `DATABASE_ERROR` |
| LIMITS | 20 items; 8 KiB |
| TIMEOUT | 30 с |
| RETRY | нет |
| SIDE EFFECTS | нет |
| IDEMPOTENCY | read-only |
| CANCELLATION | timeout |
| AUTHORITY | LLM инициирует; Core проверяет принадлежность Document Study и выполняет |

Изоляция Study обязательна через `StudyDocumentLink`.

---

## 5. Study Management

### `start_research_session`

| Поле | Контракт |
|---|---|
| INPUT | `study_id` |
| OUTPUT | `session_id`, `status = STARTED|ALREADY_RUNNING`, `operation_id` |
| ERRORS | `INVALID_INPUT`, `INVALID_STATE`, `DATABASE_ERROR`, `LLM_UNREACHABLE` |
| LIMITS | 2 KiB |
| TIMEOUT | 10 с |
| RETRY | нет автоматического retry |
| SIDE EFFECTS | создаётся/возобновляется ResearchSession; Study переход выполняется только FSM; списывается `step_budget` только за реально созданный шаг |
| IDEMPOTENCY | активная сессия для того же Study возвращается повторно |
| CANCELLATION | timeout |
| AUTHORITY | LLM/GUI инициирует; Core проверяет Study и запускает FSM |

Нельзя напрямую присваивать `Study.status = RUNNING`. Сначала требуется допустимый переход `READY → RUNNING`.

### `save_study_material`

| Поле | Контракт |
|---|---|
| INPUT | `study_id`, `task_id` (обязателен для Evidence), `material_type`, `payload`, `idempotency_key` |
| OUTPUT | `entity_id`, `status = SAVED|DUPLICATE|VALIDATION_FAILED`, `operation_id` |
| ERRORS | `INVALID_INPUT`, `VALIDATION_ERROR`, `DATABASE_ERROR` |
| LIMITS | 4 KiB payload |
| TIMEOUT | 10 с |
| RETRY | нет автоматического retry |
| SIDE EFFECTS | создание Evidence/Observation/Claim/Contradiction/ResearchGap; `tool_call_budget` |
| IDEMPOTENCY | Evidence → `evidence_hash`; остальные → канонизированный payload |
| CANCELLATION | timeout |
| AUTHORITY | LLM формирует объект; Core валидирует и сохраняет |

Допустимые `material_type`:

`EVIDENCE`, `OBSERVATION`, `CLAIM`, `CONTRADICTION`, `GAP`.

### `search_study_materials`

| Поле | Контракт |
|---|---|
| INPUT | `study_id`, `query`, `material_type`, `limit` |
| OUTPUT | `results[]` |
| ERRORS | `INVALID_INPUT`, `RETRIEVAL_PROVIDER_ERROR`, `DATABASE_ERROR` |
| LIMITS | 20 items; 8 KiB |
| TIMEOUT | 30 с |
| RETRY | нет |
| SIDE EFFECTS | нет |
| IDEMPOTENCY | read-only |
| CANCELLATION | timeout |
| AUTHORITY | LLM инициирует; Core выполняет с изоляцией Study |

`material_type = ALL|EVIDENCE|OBSERVATION|CLAIM|CONTRADICTION|GAP`.

### `get_research_session_statistics`

| Поле | Контракт |
|---|---|
| INPUT | `study_id` |
| OUTPUT | `statistics` с counts, budget_remaining, elapsed_time_seconds |
| ERRORS | `INVALID_INPUT`, `DATABASE_ERROR` |
| LIMITS | 2 KiB |
| TIMEOUT | 5 с |
| RETRY | нет |
| SIDE EFFECTS | нет |
| IDEMPOTENCY | read-only |
| CANCELLATION | timeout |
| AUTHORITY | Core |

### `get_study_dashboard`

| Поле | Контракт |
|---|---|
| INPUT | `study_id` |
| OUTPUT | `current_phase`, `study_status`, `session_status`, `budget_remaining`, `evidence_count`, `claims_count`, `open_contradictions`, `open_gaps`, `next_step_recommendation` |
| ERRORS | `INVALID_INPUT`, `DATABASE_ERROR` |
| LIMITS | 4 KiB |
| TIMEOUT | 5 с |
| RETRY | нет |
| SIDE EFFECTS | нет |
| IDEMPOTENCY | read-only |
| CANCELLATION | timeout |
| AUTHORITY | Core |

`next_step_recommendation` — только детерминированная рекомендация Core, не свободная LLM-команда.

---

## 6. Working Memory

### `update_working_memory`

| Поле | Контракт |
|---|---|
| INPUT | `study_id`, `summary` |
| OUTPUT | `status = SAVED|TOO_LONG`, `tokens_used`, `version`, `operation_id` |
| ERRORS | `INVALID_INPUT`, `VALIDATION_ERROR`, `DATABASE_ERROR` |
| LIMITS | максимум 200 токенов |
| TIMEOUT | 5 с |
| RETRY | нет |
| SIDE EFFECTS | обновление WorkingMemory |
| IDEMPOTENCY | повтор того же текста не создаёт новую сущность |
| CANCELLATION | timeout |
| AUTHORITY | LLM формирует; Core валидирует и сохраняет |

### `get_working_memory`

| Поле | Контракт |
|---|---|
| INPUT | `study_id` |
| OUTPUT | `summary`, `version`, `updated_at` |
| ERRORS | `INVALID_INPUT`, `DATABASE_ERROR` |
| LIMITS | 1 KiB |
| TIMEOUT | 5 с |
| RETRY | нет |
| SIDE EFFECTS | нет |
| IDEMPOTENCY | read-only |
| CANCELLATION | timeout |
| AUTHORITY | Core |

---

## 7. Cache / Diagnostics

### `get_cache_statistics`

`INPUT: project_id?`  
`OUTPUT: total_entries, hit_count, miss_count, expired_count, total_size_bytes, oldest_entry, newest_entry`  
`ERRORS: INVALID_INPUT, DATABASE_ERROR, CACHE_ERROR`  
`LIMITS: 2 KiB`  
`TIMEOUT: 5 с`  
`RETRY: нет`  
`SIDE EFFECTS: нет`  
`IDEMPOTENCY: read-only`  
`CANCELLATION: timeout`  
`AUTHORITY: Core`

Scope cache: Project.

### `get_cache_diagnostics`

`INPUT: project_id?, include_blocked_domains=true`  
`OUTPUT: expired_entries_count, blocked_domains[], stale_entries_count, recommendations`  
`ERRORS: INVALID_INPUT, DATABASE_ERROR, CACHE_ERROR`  
`LIMITS: 4 KiB`  
`TIMEOUT: 10 с`  
`RETRY: нет`  
`SIDE EFFECTS: нет`  
`IDEMPOTENCY: read-only`  
`CANCELLATION: timeout`  
`AUTHORITY: Core`

### `cleanup_expired_cache`

`INPUT: project_id?, force=false`  
`OUTPUT: status=COMPLETED|PARTIAL, removed_count, freed_bytes`  
`ERRORS: INVALID_INPUT, DATABASE_ERROR, CACHE_ERROR`  
`LIMITS: implementation-defined batch limit`  
`TIMEOUT: 60 с`  
`RETRY: нет автоматического retry`  
`SIDE EFFECTS: удаление истёкших CacheEntry`  
`IDEMPOTENCY: повтор без изменений → removed_count=0`  
`CANCELLATION: cooperative cancellation`  
`AUTHORITY: Core; запуск возможен из GUI`

`force=true` может удалять только записи, которые явно определены Core как допустимые для принудительной очистки; произвольное удаление активных записей запрещено.

---

## 8. Report

### `validate_and_save_report`

| Поле | Контракт |
|---|---|
| INPUT | `study_id`, `session_id`, `report_format`, `report_content`, `idempotency_key` |
| OUTPUT | `status = SAVED|VALIDATION_FAILED`, `validation_errors[]`, `report_id`, `operation_id` |
| ERRORS | `INVALID_INPUT`, `REPORT_VALIDATION_ERROR`, `DATABASE_ERROR`, `INVALID_STATE` |
| LIMITS | default 100 000 символов |
| TIMEOUT | 60 с |
| RETRY | нет автоматического retry |
| SIDE EFFECTS | создание/обновление Claim/ClaimEvidence и сохранение отчёта; списание `llm_call_budget` только при успешной операции согласно Core policy |
| IDEMPOTENCY | `SHA256(study_id + session_id + report_content)` |
| CANCELLATION | timeout/cancel; частичные валидные данные обрабатываются процедурой Partial Report |
| AUTHORITY | LLM формирует; Core единолично валидирует и сохраняет |

Precondition:

```text
Study.status == FINALIZING
```

Успех вызывает только допустимый переход:

```text
FINALIZING → COMPLETED
```

Tool не переводит `RUNNING → FINALIZING`.

Автоматическая тихая правка финального отчёта запрещена.

`REPORT_TRUNCATED_PARTIAL` является result/metadata и **не является Study state**.

`LLM_TIMEOUT` не является ошибкой самого `validate_and_save_report`: timeout генерации LLM относится к LLM operation/backend layer.

---

## 9. Job Management

Job-механизм определён Search Core и применяется только к долгим операциям. Текущий MVP использует Job для массовой индексации, перестроения BM25, крупного импорта и длительной пакетной обработки.

### `get_job_status`

`INPUT: job_id`  
`OUTPUT: job_id, job_type, status, progress, error?, created_at, started_at, completed_at`  
`ERRORS: INVALID_INPUT, DATABASE_ERROR`  
`LIMITS: 1 KiB`  
`TIMEOUT: 5 с`  
`RETRY: нет`  
`SIDE EFFECTS: нет`  
`IDEMPOTENCY: read-only`  
`CANCELLATION: timeout`  
`AUTHORITY: Core`

Допустимые Job states:

`QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`.

### `cancel_job`

`INPUT: job_id`  
`OUTPUT: CANCEL_REQUESTED|ALREADY_COMPLETED|ALREADY_CANCELLED|NOT_FOUND`  
`ERRORS: INVALID_INPUT, DATABASE_ERROR`  
`LIMITS: 1 KiB`  
`TIMEOUT: 5 с`  
`RETRY: повтор допустим и должен быть идемпотентным`  
`SIDE EFFECTS: установка cooperative cancellation flag; фактический переход Job → CANCELLED выполняет Job runner/Core`  
`IDEMPOTENCY: повтор после отмены → ALREADY_CANCELLED`  
`CANCELLATION: сам является cancellation command`  
`AUTHORITY: пользователь/LLM инициирует; Core выполняет`

`cancel_job` не имеет права напрямую присваивать `Job.status = CANCELLED`, если Job runner ещё не подтвердил безопасную отмену.

---

## 10. Сводная таблица

| # | Tool | Timeout | Side effects |
|---|---|---:|---|
| 1 | `plan_research` | 30с | SearchTask |
| 2 | `search_web` | 30с | SearchResult/Source |
| 3 | `search_academic` | 30с | SearchResult/Source |
| 4 | `search_github` | 30с | SearchResult/Source |
| 5 | `search_stackoverflow` | 30с | SearchResult/Source |
| 6 | `search_web_community` | 30с | SearchResult/Source |
| 7 | `read_url_content` | 60с | Document/Chunk/Link |
| 8 | `read_youtube_transcript` | 60с | Document/Chunk/Link |
| 9 | `add_local_document` | 120с | Document/Chunk/Link |
| 10 | `search_within_document` | 30с | — |
| 11 | `start_research_session` | 10с | ResearchSession |
| 12 | `save_study_material` | 10с | аналитическая сущность |
| 13 | `search_study_materials` | 30с | — |
| 14 | `get_research_session_statistics` | 5с | — |
| 15 | `get_study_dashboard` | 5с | — |
| 16 | `update_working_memory` | 5с | WorkingMemory |
| 17 | `get_working_memory` | 5с | — |
| 18 | `get_cache_statistics` | 5с | — |
| 19 | `get_cache_diagnostics` | 10с | — |
| 20 | `cleanup_expired_cache` | 60с | CacheEntry |
| 21 | `validate_and_save_report` | 60с | Report/Claim/ClaimEvidence |
| 22 | `get_job_status` | 5с | — |
| 23 | `cancel_job` | 5с | Job cancellation request |

**Конец MCP Tool Contracts v1.1**
