# EPIC-07 — MCP. TASK BATCH v1.1

Статус: Готов к передаче CODE-агентам.
Зависимости: формально по Dependency Matrix — EPIC-03, EPIC-04, EPIC-05, EPIC-06. Фактически — транзитивно через EPIC-01 и EPIC-02.
Цель EPIC: Реализовать строго ограниченный инструментальный интерфейс (23 инструмента) для взаимодействия с LLM через протокол MCP (stdio JSON-RPC). MCP выступает исключительно как proxy/adapter над Core/Application API.
Gate G-07: 23 tools зарегистрированы; schemas и invalid input корректны; timeout/errors работают; MCP не изменяет FSM напрямую; task_id сохраняется; local-document path защищён; повтор не создаёт duplicate entities; stdout защищён от случайного вывода; статический линтер и runtime-тест подтверждают защиту; MCP работает только через разрешённые Core/Application API.

---

## Общие инварианты и запреты для всех задач EPIC-07

ALLOWED_FILES (глобально для EPIC):

- `src/mcp/` (новая директория для MCP-сервера, транспорта, инструментов)
- `src/mcp/tools/` (реализации 23 инструментов)
- `src/mcp/errors.py`
- `src/mcp/core_adapter.py`
- `src/mcp/operation_fsm.py`
- `src/mcp/tool_registry.py`
- `src/mcp/transport.py`
- `src/mcp/stdout_guard.py`
- `src/mcp/response_limiter.py`
- `src/mcp/schemas/` (JSON schemas для inputs)
- `tests/mcp/` (unit и contract tests)
- `tests/integration/` (integration tests)
- `tests/fixtures/` (mock Core API, fake LLM responses)
- `tools/check_stdout_policy.py` (статический линтер)

FORBIDDEN (глобально для EPIC):

- Прямое изменение `status` у `Study`, `ResearchSession`, `SearchTask` (только через команды/триггеры из EPIC-03).
- Прямая запись в SQLite в обход DB-write layer / Core API.
- Использование `print()`, `sys.stdout.write` или любых логгеров, выводящих в `stdout` (кроме валидного JSON-RPC).
- Приём произвольных filesystem paths от LLM в `add_local_document` (только `file_ref`).
- Автоматическая «тихая» правка финального отчёта в `validate_and_save_report`.
- Создание комплексных инструментов-комбайнов (каждый tool = одна атомарная операция).
- Изменение контрактов FSM (EPIC-03) или Search Core (EPIC-04).

Глобальное правило идентификации операций:

- Каждый вызов инструмента получает уникальный `operation_id` (UUID). Он используется для трассировки, `LogRecord` и связи создаваемых сущностей.
- Повторный вызов с тем же `idempotency_key` не должен создавать дублирующую persistent-сущность.
- `study_id`, `session_id`, `task_id`, `document_id`, `project_id` — UUID.
- MCP layer не вычисляет альтернативные алгоритмы `query_fingerprint`. Fingerprint рассчитывает Search Core (EPIC-04).
- `SOFT_STOP`/`HARD_STOP`/`CANCEL` являются commands, а не состояниями.

Область видимости `MCP Watchdog` (Контур 2 из ТЗ Раздел 5, Секция 17):

Двухконтурная система временной защиты определена в ТЗ Раздел 5, Секция 17:
- Контур 1 (Operation-Level Timeouts) — реализуется в TASK-07-04 и TASK-07-20.
- Контур 2 (MCP Watchdog) — реализуется в EPIC-09 (Integration & Resilience). MCP Watchdog принудительно закрывает зависший процесс, осуществляет чистый перезапуск, извлекает срез из SQLite и активирует `SESSION_RESUMING`. В рамках EPIC-07 Контур 2 не реализуется.

---

## TASK-07-01: MCP Server Bootstrap & JSON-RPC Transport

GOAL: Реализовать базовый stdio-сервер, читающий JSON-RPC 2.0 из `stdin` и отправляющий ответы в `stdout`.

CONTEXT: Транспортный слой MVP. ЛЛМ общается с системой только через этот канал. ТЗ Раздел 5, Секция 3: «В качестве базового транспортного слоя для MVP утверждается механизм stdio».

ALLOWED_FILES: `src/mcp/server.py`, `src/mcp/transport.py`, `tests/mcp/test_transport.py`.

FORBIDDEN: Вывод любых логов в `stdout`. Использование внешних async-фреймворков для stdio (только stdlib `sys.stdin`, `sys.stdout`, `json`).

IMPLEMENTATION DETAILS:

- Создать `MCPTransport`. Метод `run()`: читает строки из `stdin`, парсит JSON.
- Валидация базовой структуры JSON-RPC 2.0: наличие `jsonrpc` (значение `"2.0"`), `method`, `id`. Для notification `id` может быть `null`.
- Формирование ответа (`result` или `error`) и запись в `stdout` с обязательным `\n`.
- Обработка невалидного JSON: отправка JSON-RPC `ParseError` (код -32700).
- Обработка валидного JSON, но невалидного JSON-RPC (отсутствует `method`): отправка `InvalidRequest` (код -32600).
- Инициализация `StdoutGuard` (TASK-07-02) выполняется до создания любых модулей (ранний редирект логгеров).

TESTS:

- Тест чтения валидного JSON-RPC запроса и отправки ответа.
- Тест обработки невалидного JSON (возврат `ParseError` -32700).
- Тест обработки валидного JSON без `method` (возврат `InvalidRequest` -32600).
- Тест: `stdout` содержит только валидный JSON-RPC и символ новой строки.
- Тест: ответ содержит поле `jsonrpc` со значением `"2.0"`.

ACCEPTANCE: Базовый транспорт работает, парсит JSON-RPC 2.0, отвечает в `stdout`.

STOP_CONDITIONS: Если stdio блокируется буферизацией → STOP → REPORT (настроить line-buffering).

---

## TASK-07-02: Stdout Isolation & Logger Redirection

GOAL: Гарантировать, что случайный `print()`, `logging` или traceback не попадут в `stdout` и не сломают JSON-RPC.

CONTEXT: ТЗ Раздел 5, Секция 3.1 определяет четыре меры защиты: ранний редирект логгеров, валидирующая обёртка, статический линтер в CI, обработка исключений. Данная задача реализует пункты 1, 2 и 4. Пункт 3 (статический линтер) реализуется в TASK-07-18.

ALLOWED_FILES: `src/mcp/stdout_guard.py`, `tests/mcp/test_stdout_guard.py`.

FORBIDDEN: Отключение гарда в production коде.

IMPLEMENTATION DETAILS:

- Создать `StdoutGuard`. При старте приложения (до инициализации любых модулей) переназначить `sys.stdout` на кастомный валидирующий wrapper.
- Wrapper проверяет, что записываемая строка является валидным JSON-RPC ответом. Если запись не является JSON-RPC: перенаправить её в `sys.stderr` или лог-файл, заблокировать запись в `stdout`.
- Перехватить `sys.excepthook` для предотвращения вывода трассировки в `stdout`. Все исключения перенаправляются в файл или `stderr`.
- Настроить `logging` так, чтобы все хэндлеры по умолчанию писали в `stderr` или файл. Ни один логгер не выводит в `stdout`.

TESTS:

- Тест: вызов `print("debug")` внутри tool не попадает в `stdout`, уходит в `stderr`.
- Тест: необработанное исключение не ломает транспорт, трассировка уходит в `stderr`.
- Тест: настройка логгера на вывод в основной поток не нарушает работу транспорта.
- Тест: валидный JSON-RPC успешно проходит в `stdout`.
- Тест: попытка записать не-JSON в `stdout` блокируется и логируется.

ACCEPTANCE: `stdout` на 100% чист от не-JSON данных. Все четыре меры защиты ТЗ Раздел 5, Секция 3.1 покрыты (статический линтер — в TASK-07-18).

STOP_CONDITIONS: Если перехват ломает стандартный вывод для GUI (если GUI в том же процессе) → STOP → REPORT (разделить процессы или использовать IPC).

---

## TASK-07-03: Unified Error Mapping & Response Limits

GOAL: Реализовать единый формат ошибок и контроль лимитов ответа.

CONTEXT: ТЗ Раздел 5, Секция 16 определяет 18 базовых кодов ошибок. Все ошибки MCP должны следовать строгому контракту. Ответы не должны превышать лимиты.

ALLOWED_FILES: `src/mcp/errors.py`, `src/mcp/response_limiter.py`, `tests/mcp/test_errors.py`.

FORBIDDEN: Возврат сырых Python-исключений в `error.message`.

IMPLEMENTATION DETAILS:

- Определить класс `MCPError(code: str, message: str, retryable: bool, recommendation: str, operation: str, entity_id: str | None)`.
- Полный справочник кодов ошибок (18 кодов) с указанием `retryable`:

        NETWORK_ERROR (retryable=True)
        TIMEOUT (retryable=True)
        RATE_LIMIT (retryable=False)
        SOURCE_UNAVAILABLE (retryable=False)
        PARSE_ERROR (retryable=False)
        INVALID_INPUT (retryable=False)
        CACHE_ERROR (retryable=False)
        DATABASE_ERROR (retryable=False)
        MCP_ERROR (retryable=False)
        VALIDATION_ERROR (retryable=True, 1 повтор)
        CHUNKING_ERROR (retryable=False)
        RETRIEVAL_PROVIDER_ERROR (retryable=False)
        REPORT_VALIDATION_ERROR (retryable=False)
        LLM_UNREACHABLE (retryable=True)
        LLM_TIMEOUT (retryable=True)
        LLM_DEGRADED (retryable=True)
        CONFIG_CONTEXT_INSUFFICIENT (retryable=False)
        RESPONSE_TOO_LARGE (retryable=False)

- Маппер `ErrorMapper.map(exception, operation) -> MCPError`.
- `ResponseLimiter.check(response_dict, max_bytes, max_items, max_text_length)`. Если превышен лимит → возвращать `RESPONSE_TOO_LARGE`.
- Три лимита: `max_output_bytes` (объём байт), `max_items` (число элементов), `max_text_length` (суммарное число символов текста в ответе).
- Обрезка сниппетов до 200 символов выполняется на уровне `SearchTool` (TASK-07-08), а не на уровне `ResponseLimiter`.

TESTS:

- Тест маппинга `ValueError` в `INVALID_INPUT`.
- Тест маппинга `TimeoutError` в `TIMEOUT` (retryable=True).
- Тест маппинга исключения сети в `NETWORK_ERROR` (retryable=True).
- Тест маппинга исключения парсинга в `PARSE_ERROR` (retryable=False).
- Тест маппинга исключения контекста в `CONFIG_CONTEXT_INSUFFICIENT` (retryable=False).
- Тест: ответ > `max_bytes` → `RESPONSE_TOO_LARGE`.
- Тест: ответ > `max_items` → `RESPONSE_TOO_LARGE`.
- Тест: суммарный текст > `max_text_length` → `RESPONSE_TOO_LARGE`.
- Тест: все 18 кодов присутствуют в справочнике.

ACCEPTANCE: Ошибки унифицированы, все 18 кодов из ТЗ обработаны, три лимита проверяются.

STOP_CONDITIONS: Если формат ошибки противоречит MCP Tool Contracts v1.1 → STOP → REPORT.

---

## TASK-07-04: Core/Application API Adapter & Operation Lifecycle

GOAL: Реализовать мост между MCP tools и Core API. Управлять жизненным циклом `MCP Operation` FSM.

CONTEXT: MCP не принимает бизнес-решений. Он вызывает Core API и отслеживает `operation_id`. `MCP Operation` является runtime-объектом исполнения. Его состояние не сохраняется в БД как доменная сущность и не заменяет состояния `Study`, `ResearchSession` или `SearchTask` (State Machine Spec v1.1, Раздел 4). Контур 1 таймаутов реализуется здесь. Контур 2 (MCP Watchdog) — в EPIC-09.

ALLOWED_FILES: `src/mcp/core_adapter.py`, `src/mcp/operation_fsm.py`, `tests/mcp/test_core_adapter.py`.

FORBIDDEN: Прямой вызов репозиториев БД. Прямое изменение Study/Session/SearchTask FSM.

IMPLEMENTATION DETAILS:

- `CoreAdapter`: проксирует вызовы к `ResearchEngine`, `SearchCore`, `LLMBackend`. Не содержит методов прямого изменения `.status` у доменных моделей.
- `OperationFSM`: состояния `REQUESTED`, `VALIDATING`, `EXECUTING`, `COMPLETED`, `FAILED`, `TIMED_OUT`, `CANCELLED`.
- Полная таблица переходов (9 переходов из State Machine Spec v1.1, Раздел 4):

        REQUESTED → VALIDATING (REQUEST_RECEIVED)
        VALIDATING → EXECUTING (INPUT_VALID)
        VALIDATING → FAILED (INVALID_INPUT)
        EXECUTING → COMPLETED (TOOL_SUCCESS)
        EXECUTING → FAILED (TOOL_ERROR)
        EXECUTING → TIMED_OUT (OPERATION_TIMEOUT)
        EXECUTING → CANCELLED (CANCEL_REQUESTED)
        TIMED_OUT → EXECUTING (RETRY_ALLOWED)
        TIMED_OUT → FAILED (RETRY_EXHAUSTED)

- `RETRY` не должен бесконечно переводить операцию между `TIMED_OUT` и `EXECUTING`. Максимум 1 повтор.
- При вызове tool: генерировать `operation_id` (UUID), создавать `MCP Operation`, переводить в `REQUESTED` → `VALIDATING`.
- При успехе/ошибке: переводить в `COMPLETED`/`FAILED`, логировать в `LogRecord` с 7 полями (`entity_type`, `entity_id`, `from_state`, `to_state`, `trigger`, `component`, `timestamp`).
- Реализовать таймауты на уровне `OperationFSM` через `threading.Timer`.

TESTS:

- Тест генерации `operation_id` и прохождения через все состояния при успехе.
- Тест перехода в `TIMED_OUT` при превышении таймаута.
- Тест: `CoreAdapter` не имеет методов прямого изменения `.status` у доменных моделей.
- Тест: каждый из 9 переходов работает корректно.
- Тест: недопустимый переход выбрасывает `InvalidStateTransition`.
- Тест: `LogRecord` содержит 7 полей для каждого перехода.
- Тест: `MCP Operation` не сохраняется в БД как доменная сущность.

ACCEPTANCE: Операции трассируются, таймауты работают (Контур 1), все 9 переходов покрыты, `CoreAdapter` не обходит бизнес-сущности.

STOP_CONDITIONS: Если Core API не предоставляет синхронные/асинхронные заглушки для тестов → STOP → REPORT.

---

## TASK-07-05: Tool Registration & Schema Validation

GOAL: Реализовать реестр инструментов и валидацию входных параметров по JSON Schema.

CONTEXT: Каждый из 23 tools имеет строгий контракт по шаблону из ТЗ Раздел 5, Секция 4a: `INPUT`, `OUTPUT`, `ERRORS`, `LIMITS`, `TIMEOUT`, `RETRY POLICY`, `SIDE EFFECTS`, `IDEMPOTENCY`, `CANCELLATION`, `AUTHORITY`.

ALLOWED_FILES: `src/mcp/tool_registry.py`, `src/mcp/schemas/` (JSON schemas для inputs), `tests/mcp/test_registry.py`.

FORBIDDEN: Регистрация tool без полного контракта.

IMPLEMENTATION DETAILS:

- `ToolRegistry.register(name, handler, input_schema, output_schema, timeout, limits, retry_policy, side_effects, idempotency, cancellation, authority)`.
- Сигнатура `register()` включает все 10 параметров контракта инструмента.
- `retry_policy`: dict с полями `allowed_codes` (список кодов ошибок, для которых допустим повтор) и `max_retries`.
- `side_effects`: список создаваемых/изменяемых сущностей.
- `idempotency`: алгоритм вычисления `idempotency_key` (например, `SHA256(study_id + canonicalized ResearchIntent)`).
- `cancellation`: `timeout` для синхронных, `cooperative` для Job-backed.
- `authority`: `Core` или `LLM` (кто принимает решение).
- Перед вызовом `handler`: валидация `params` против `input_schema` (минимальный валидатор из EPIC-06 или stdlib).
- При ошибке валидации: возвращать `INVALID_INPUT` с деталями.
- Делегирование вызова в `handler(params, operation_id, context)`.

TESTS:

- Тест регистрации tool с полным контрактом (10 параметров) и успешного вызова.
- Тест отклонения запроса с отсутствующим обязательным полем (`INVALID_INPUT`).
- Тест отклонения запроса с неверным типом данных.
- Тест: регистрация без `retry_policy` → ошибка.
- Тест: регистрация без `idempotency` для stateful-инструмента → ошибка.

ACCEPTANCE: Реестр хранит полный контракт каждого инструмента, схемы валидируются до исполнения.

STOP_CONDITIONS: Если схемы не покрывают все 23 инструмента → STOP → REPORT.

---

## TASK-07-06: Planning Tool (`plan_research`)

GOAL: Реализовать инструмент `plan_research` с обработкой `RETRY` и `IDEMPOTENCY`.

CONTEXT: ЛЛМ предлагает план, Core нормализует и создаёт `SearchTask`. MCP Tool Contracts v1.1, Раздел 1 определяет: `RETRY: 1 повтор только после VALIDATION_ERROR`, `IDEMPOTENCY: SHA256(study_id + canonicalized ResearchIntent)`.

ALLOWED_FILES: `src/mcp/tools/plan_research.py`, `tests/mcp/tools/test_plan_research.py`.

FORBIDDEN: Прямое создание `SearchTask` в БД. Прямой перевод Study в `PLANNING`.

IMPLEMENTATION DETAILS:

- Принять `study_id`, `intent`.
- Вызвать `CoreAdapter.plan_research(study_id, intent)`.
- Core валидирует intent, нормализует задачи, создаёт `SearchTask` (статус `CREATED`).
- Вернуть список `SearchTaskDraft` и `operation_id`.
- Лимит: до 20 задач, 16 KiB.
- `RETRY`: при получении `VALIDATION_ERROR` разрешается один повтор. При других ошибках повтор запрещён.
- `IDEMPOTENCY`: `idempotency_key` вычисляется как SHA256(study_id + canonicalized ResearchIntent). `canonicalized ResearchIntent` включает все семантически значимые поля: `question`, `goal`, `entities/target_entities`, `constraints`, `time_range`, `geography`, `source_preferences`, `exclusions`, `expected_output`, `analysis_strategy`. Повторный вызов с тем же ключом возвращает существующие задачи.
- `AUTHORITY`: ЛЛМ предлагает; Core нормализует, валидирует и создаёт задачи.
- `SIDE EFFECTS`: Core создаёт валидированные `SearchTask` со статусом `CREATED`.
- Tool не переводит Study напрямую. Если требуется `DRAFT → PLANNING → READY`, переходы выполняет Study State Machine.

TESTS:

- Тест успешного планирования (возвращает задачи).
- Тест: `operation_id` сгенерирован.
- Тест: при невалидном intent возвращается `VALIDATION_ERROR`.
- Тест: при `VALIDATION_ERROR` выполняется один повтор.
- Тест: при `DATABASE_ERROR` повтор не выполняется.
- Тест: повторный вызов с тем же `idempotency_key` возвращает существующие задачи (не создаёт дубли).
- Тест: `canonicalized ResearchIntent` включает все 10 семантических полей.

ACCEPTANCE: Tool работает через Core API, не обходит FSM. `RETRY` и `IDEMPOTENCY` корректно обработаны.

STOP_CONDITIONS: Если Core API не возвращает `SearchTaskDraft` → STOP → REPORT.

---

## TASK-07-07: Session Tools (`start_research_session`, `get_research_session_statistics`, `get_study_dashboard`)

GOAL: Реализовать 3 инструмента управления сессией и дашбордом с проверкой идемпотентности и состояния `Study`.

CONTEXT: Запуск сессии триггерит FSM. Статистика и дашборд — read-only. MCP Tool Contracts v1.1, Раздел 5 определяет: `IDEMPOTENCY: активная сессия для того же Study возвращается повторно`, `Precondition: Study.status == READY для перехода READY → RUNNING`.

ALLOWED_FILES: `src/mcp/tools/session_tools.py`, `tests/mcp/tools/test_session_tools.py`.

FORBIDDEN: Прямое присваивание `Study.status = RUNNING`.

IMPLEMENTATION DETAILS:

- `start_research_session`:
    - Проверить, что `Study.status == READY`. Если нет — вернуть `INVALID_STATE`.
    - Проверить идемпотентность: если активная сессия для данного `study_id` уже существует — вернуть её `session_id` со статусом `ALREADY_RUNNING`, не создавая новую.
    - Если сессия не существует: вызвать Core API. Core триггерит `START_RESEARCH` (FSM: `READY → RUNNING`).
    - Возвращает `session_id`, `status` (`STARTED` или `ALREADY_RUNNING`), `operation_id`.
- `get_research_session_statistics`: read-only, возвращает `statistics` с `counts`, `budget_remaining`, `elapsed_time_seconds`.
- `get_study_dashboard`: read-only, возвращает `current_phase`, `study_status`, `session_status`, `budget_remaining`, `evidence_count`, `claims_count`, `open_contradictions`, `open_gaps`, `next_step_recommendation` (детерминированная рекомендация Core, не свободная ЛЛМ-команда).
- Лимит: 2 KiB для статистики, 4 KiB для дашборда.

TESTS:

- Тест запуска сессии из `READY` (проверка перехода через Core).
- Тест: запуск сессии из `RUNNING` возвращает `INVALID_STATE`.
- Тест: повторный запуск сессии для того же Study возвращает `ALREADY_RUNNING`.
- Тест получения статистики и дашборда.
- Тест: дашборд не превышает 4 KiB.
- Тест: `next_step_recommendation` детерминирован (не свободный текст).

ACCEPTANCE: Сессия запускается через FSM с проверкой `READY`, идемпотентность работает, read-only tools не имеют side-effects.

STOP_CONDITIONS: Если `next_step_recommendation` не детерминирован → STOP → REPORT.

---

## TASK-07-08: Search Tools Base & `search_web`

GOAL: Реализовать базовую логику поиска и инструмент `search_web` с дифференцированной обработкой `RETRY`.

CONTEXT: Поиск инициируется ЛЛМ, но выполняется Core с проверкой бюджета и fingerprint. MCP Tool Contracts v1.1, Раздел 2 определяет: `RETRY: 1 повтор для NETWORK_ERROR / TIMEOUT; без retry для RATE_LIMIT`.

ALLOWED_FILES: `src/mcp/tools/search_base.py`, `src/mcp/tools/search_web.py`, `tests/mcp/tools/test_search_web.py`.

FORBIDDEN: Массовый fetch полных текстов. Возврат сырого HTML.

IMPLEMENTATION DETAILS:

- Базовый класс `SearchTool`:
    - Проверка `task_id` (обязателен). `SearchResult.task_id` ссылается на этот SearchTask.
    - Вызов `CoreAdapter.execute_search(...)`.
    - Core проверяет `query_fingerprint`, бюджет, запускает `SourceAdapter`.
    - `RETRY` логика (дифференцированная):
        - При получении `NETWORK_ERROR` или `TIMEOUT` — один повтор.
        - При получении `RATE_LIMIT` — повтор запрещён, вернуть ошибку немедленно.
        - При получении `SOURCE_UNAVAILABLE` — повтор запрещён.
    - Возвращает до 10 кандидатов (`url`, `title`, `snippet` ≤ 200 chars, `score`).
    - Списание `network_budget`.
    - `IDEMPOTENCY`: Core использует единый `query_fingerprint`; MCP не вычисляет альтернативный.
- `search_web`: принимает `time_range`, `geography`, `language`.
- Лимиты: до 10 candidates; 200 символов на snippet; 8 KiB.
- `AUTHORITY`: ЛЛМ инициирует; Core проверяет SearchTask, fingerprint, budget и выполняет.

TESTS:

- Тест успешного поиска (возвращает компактные кандидаты).
- Тест: snippet обрезан до 200 символов.
- Тест: при нулевом бюджете возвращается `BUDGET_REJECT`.
- Тест: при `NETWORK_ERROR` выполняется один повтор.
- Тест: при `TIMEOUT` выполняется один повтор.
- Тест: при `RATE_LIMIT` повтор не выполняется.
- Тест: при `SOURCE_UNAVAILABLE` повтор не выполняется.
- Тест: `task_id` обязателен, при отсутствии — `INVALID_INPUT`.

ACCEPTANCE: Возвращаются только кандидаты, бюджет списан, лимиты соблюдены, `RETRY` дифференцирован.

STOP_CONDITIONS: Если Core не возвращает компактные кандидаты → STOP → REPORT.

---

## TASK-07-09: Specialized Search Tools (`search_academic`, `search_github`, `search_stackoverflow`, `search_web_community`)

GOAL: Реализовать 4 специализированных инструмента поиска.

CONTEXT: Используют ту же базу, что и `search_web`, но с разными фильтрами. Наследуют `RETRY` логику из базового класса `SearchTool`.

ALLOWED_FILES: `src/mcp/tools/search_specialized.py`, `tests/mcp/tools/test_search_specialized.py`.

FORBIDDEN: Дублирование кода базового поиска (использовать наследование/композицию).

IMPLEMENTATION DETAILS:

- `search_academic`: filters `publication_type`, `min_year`. Candidate может содержать `doi`, `pmid`, `arxiv_id`.
- `search_github`: filters `language`, `sort_by = STARS|UPDATED|RELEVANCE`.
- `search_stackoverflow`: filters `tagged`, `min_score`.
- `search_web_community`: filters `platform = REDDIT|FORUM|BLOG`, `sort_by = RELEVANCE|DATE|RATING`.
- Все возвращают компактные кандидаты, лимит 10 items, 8 KiB.
- Все наследуют `RETRY` логику из `SearchTool` (TASK-07-08).

TESTS:

- По одному тесту на каждый tool с специфичными фильтрами (4 теста).
- Тест: `search_academic` возвращает `doi` в metadata.
- Тест: `search_github` принимает `sort_by = STARS`.
- Тест: `search_web_community` принимает `platform = REDDIT`.

ACCEPTANCE: Все 4 инструмента работают, фильтры передаются в Core, `RETRY` логика наследована.

STOP_CONDITIONS: Если Core не поддерживает специфичные фильтры → STOP → REPORT.

---

## TASK-07-10: Reading Tools (`read_url_content`, `read_youtube_transcript`)

GOAL: Реализовать инструменты точечного чтения контента с обработкой `CONTENT_TOO_LARGE`.

CONTEXT: ЛЛМ выбирает URL из кандидатов. Core скачивает, парсит, чанкает, индексирует. MCP Tool Contracts v1.1, Раздел 3 определяет код ошибки `CONTENT_TOO_LARGE`.

ALLOWED_FILES: `src/mcp/tools/read_tools.py`, `tests/mcp/tools/test_read_tools.py`.

FORBIDDEN: Возврат полного текста в ответе MCP (только metadata). Выдумывание текста при `FULL_TEXT_UNAVAILABLE`.

IMPLEMENTATION DETAILS:

- `read_url_content`:
    - Принимает `study_id`, `task_id`, `url`.
    - Core проверяет лимиты, скачивает, чанкает.
    - Если размер контента превышает `max fetch size` из `ResearchConfig` (default 5 MiB) — прервать скачивание и вернуть `CONTENT_TOO_LARGE`.
    - Возвращает `document_id`, `title`, `content_length`, `chunks_count`, `status`, `operation_id`.
    - Если сайт заблокирован/paywall: возвращает `FULL_TEXT_UNAVAILABLE`, текст не генерируется.
    - `RETRY`: 1 retry для `NETWORK_ERROR`; нет retry для `PARSE_ERROR` и `FULL_TEXT_UNAVAILABLE`.
    - `IDEMPOTENCY`: SHA256(canonical_url) в рамках project; повтор возвращает существующий Document.
    - `SIDE EFFECTS`: Document/Chunk/Source/StudyDocumentLink/BM25; списывается `fetch_budget`.
    - Лимит: max fetch size из `ResearchConfig`, default 5 MiB.
    - Timeout: 60 с.
- `read_youtube_transcript`: аналогично, но для видео. Лимит: 100 000 символов. `IDEMPOTENCY`: SHA256(canonical_video_url).

TESTS:

- Тест успешного чтения (возвращает metadata, не текст).
- Тест: при блокировке возвращается `FULL_TEXT_UNAVAILABLE`.
- Тест: при превышении `max fetch size` возвращается `CONTENT_TOO_LARGE`.
- Тест: при `NETWORK_ERROR` выполняется один повтор.
- Тест: при `PARSE_ERROR` повтор не выполняется.
- Тест: повторный вызов того же URL возвращает существующий `document_id` (идемпотентность).

ACCEPTANCE: Тексты не передаются в MCP ответе, идемпотентность работает, бюджет списан, `CONTENT_TOO_LARGE` обработан.

STOP_CONDITIONS: Если Core возвращает полный текст в MCP → STOP → REPORT.

---

## TASK-07-11: Document Tools (`add_local_document`, `search_within_document`)

GOAL: Реализовать работу с локальными документами с обработкой `UNSUPPORTED_FORMAT`.

CONTEXT: `add_local_document` принимает только `file_ref`. `search_within_document` изолирован по Study. MCP Tool Contracts v1.1, Раздел 4 определяет код ошибки `UNSUPPORTED_FORMAT`.

ALLOWED_FILES: `src/mcp/tools/document_tools.py`, `tests/mcp/tools/test_document_tools.py`.

FORBIDDEN: Приём произвольных путей (`C:\...`). Поиск по документам из других Studies.

IMPLEMENTATION DETAILS:

- `add_local_document`:
    - Принимает `study_id`, `file_ref` (UUID, зарегистрированный в Core/GUI), `document_type`.
    - Core читает, парсит, чанкает.
    - Если формат файла не поддерживается парсером (например, бинарный файл без текстового содержимого) — вернуть `UNSUPPORTED_FORMAT`.
    - `IDEMPOTENCY`: `content_hash`; duplicate возвращает существующий Document.
    - Лимит: default 20 MiB.
    - Timeout: 120 с.
    - `RETRY`: нет автоматического retry.
    - `SIDE EFFECTS`: Document/Chunk/Source/StudyDocumentLink/BM25.
    - `CANCELLATION`: cooperative cancellation для разрешённых Job-backed imports; синхронный одиночный импорт имеет timeout.
    - `AUTHORITY`: пользователь/GUI выбирает файл; Core разрешает, читает и сохраняет.
    - `file_ref` должен указывать на заранее зарегистрированный Core-approved файл. Передача ЛЛМ произвольного `C:\...` пути запрещена.
- `search_within_document`:
    - Принимает `study_id`, `document_id`, `query`, `limit`.
    - Core проверяет `StudyDocumentLink` (изоляция Study). Возвращает чанки.
    - Лимит: 20 items, 8 KiB.
    - `RETRY`: нет.
    - `SIDE EFFECTS`: нет.
    - `IDEMPOTENCY`: read-only.

TESTS:

- Тест: передача сырого пути в `add_local_document` отклоняется (`INVALID_INPUT`).
- Тест: успешное добавление по `file_ref`.
- Тест: неподдерживаемый формат файла → `UNSUPPORTED_FORMAT`.
- Тест: повторное добавление того же файла → возвращает существующий `document_id` (идемпотентность по `content_hash`).
- Тест: `search_within_document` не находит чанки, если документ не привязан к Study.

ACCEPTANCE: Пути защищены, изоляция Study соблюдается, `UNSUPPORTED_FORMAT` обработан, идемпотентность работает.

STOP_CONDITIONS: Если GUI не предоставляет механизм регистрации `file_ref` → STOP → REPORT (использовать mock для тестов).

---

## TASK-07-12: Material Tools (`save_study_material`, `search_study_materials`)

GOAL: Реализовать сохранение и поиск аналитических материалов с проверкой обязательности `task_id` для Evidence.

CONTEXT: ЛЛМ формирует объект, Core валидирует и сохраняет. MCP Tool Contracts v1.1, Раздел 5 определяет: `task_id (обязателен для Evidence)`.

ALLOWED_FILES: `src/mcp/tools/material_tools.py`, `tests/mcp/tools/test_material_tools.py`.

FORBIDDEN: Сохранение невалидных объектов. Обход `evidence_hash`.

IMPLEMENTATION DETAILS:

- `save_study_material`:
    - Принимает `study_id`, `task_id`, `material_type`, `payload`, `idempotency_key`.
    - Если `material_type = EVIDENCE` и `task_id` отсутствует или пустой — вернуть `INVALID_INPUT`. Для остальных типов `task_id` опционален.
    - Допустимые `material_type`: `EVIDENCE`, `OBSERVATION`, `CLAIM`, `CONTRADICTION`, `GAP`.
    - Core валидирует payload по типу. Для Evidence вычисляет `evidence_hash`.
    - Если дубликат → возвращает `DUPLICATE` и существующий `entity_id`.
    - `IDEMPOTENCY`: Evidence → `evidence_hash`; остальные → канонизированный payload.
    - `SIDE EFFECTS`: создание Evidence/Observation/Claim/Contradiction/ResearchGap; списывается `tool_call_budget`.
    - Лимит: 4 KiB payload.
    - Timeout: 10 с.
    - `RETRY`: нет автоматического retry.
- `search_study_materials`:
    - Read-only, поиск по материалам Study.
    - `material_type = ALL|EVIDENCE|OBSERVATION|CLAIM|CONTRADICTION|GAP`.
    - Лимит: 20 items, 8 KiB.
    - `SIDE EFFECTS`: нет.
    - `IDEMPOTENCY`: read-only.

TESTS:

- Тест сохранения Evidence (проверка `evidence_hash`).
- Тест: сохранение Evidence без `task_id` → `INVALID_INPUT`.
- Тест: сохранение Observation без `task_id` → допускается.
- Тест: повторный вызов с тем же `idempotency_key` возвращает `DUPLICATE`.
- Тест: поиск материалов возвращает только данные текущего Study.
- Тест: все 5 типов `material_type` обрабатываются.

ACCEPTANCE: Материалы сохраняются через Core, дубли блокируются, `task_id` обязателен для Evidence.

STOP_CONDITIONS: Если Core не вычисляет `evidence_hash` → STOP → REPORT.

---

## TASK-07-13: Memory Tools (`update_working_memory`, `get_working_memory`)

GOAL: Реализовать управление рабочей памятью.

CONTEXT: WorkingMemory — краткая шпаргалка для ЛЛМ, не замена БД. MCP Tool Contracts v1.1, Раздел 6 определяет лимит 200 токенов.

ALLOWED_FILES: `src/mcp/tools/memory_tools.py`, `tests/mcp/tools/test_memory_tools.py`.

FORBIDDEN: Сохранение текста > 200 токенов.

IMPLEMENTATION DETAILS:

- `update_working_memory`:
    - Принимает `study_id`, `summary`.
    - Core проверяет длину (≤ 200 токенов). Оценка токенов: `len(summary) // 3` (консервативная оценка для русского).
    - Сохраняет. Возвращает `status = SAVED|TOO_LONG`, `tokens_used`, `version`, `operation_id`.
    - `IDEMPOTENCY`: повтор того же текста не создаёт новую сущность.
    - Лимит: максимум 200 токенов.
    - Timeout: 5 с.
- `get_working_memory`:
    - Read-only, возвращает `summary`, `version`, `updated_at`.
    - Лимит: 1 KiB.
    - Timeout: 5 с.

TESTS:

- Тест успешного обновления.
- Тест: текст > 200 токенов отклоняется (`TOO_LONG`).
- Тест: повтор того же текста → идемпотентность (не создаёт новую версию).
- Тест: `get_working_memory` возвращает актуальные данные.

ACCEPTANCE: Лимит токенов соблюдается, идемпотентность работает.

STOP_CONDITIONS: Если Core не считает токены → STOP → REPORT (использовать приблизительную оценку `len(text) // 3`).

---

## TASK-07-14: Cache & Diagnostics Tools (`get_cache_statistics`, `get_cache_diagnostics`, `cleanup_expired_cache`)

GOAL: Реализовать инструменты управления кэшем.

CONTEXT: Кэш изолирован по Project. MCP Tool Contracts v1.1, Раздел 7 определяет контракты.

ALLOWED_FILES: `src/mcp/tools/cache_tools.py`, `tests/mcp/tools/test_cache_tools.py`.

FORBIDDEN: Удаление активных записей без `force=true` (и даже с ним — только разрешённых Core).

IMPLEMENTATION DETAILS:

- `get_cache_statistics`: read-only, возвращает `total_entries`, `hit_count`, `miss_count`, `expired_count`, `total_size_bytes`, `oldest_entry`, `newest_entry`. Scope: Project.
- `get_cache_diagnostics`: read-only, возвращает `expired_entries_count`, `blocked_domains[]`, `stale_entries_count`, `recommendations`.
- `cleanup_expired_cache`: удаляет истёкшие записи. Возвращает `status = COMPLETED|PARTIAL`, `removed_count`, `freed_bytes`.
    - `force=true` может удалять только записи, которые явно определены Core как допустимые для принудительной очистки.
    - `IDEMPOTENCY`: повтор без изменений → `removed_count = 0`.
    - `CANCELLATION`: cooperative cancellation.
    - Timeout: 60 с.

TESTS:

- Тест получения статистики.
- Тест получения диагностики.
- Тест очистки: удаляются только expired записи.
- Тест: повторная очистка без изменений → `removed_count = 0`.
- Тест: `force=true` не удаляет активные записи.

ACCEPTANCE: Кэш управляется безопасно, статистика компактна, идемпотентность работает.

STOP_CONDITIONS: Если Core не поддерживает очистку кэша → STOP → REPORT.

---

## TASK-07-15: Report Tool (`validate_and_save_report`)

GOAL: Реализовать финальный инструмент сохранения отчёта с `idempotency_key`.

CONTEXT: Строгая валидация, никаких тихих правок. Переход Study в `COMPLETED`. MCP Tool Contracts v1.1, Раздел 8 определяет: `IDEMPOTENCY: SHA256(study_id + session_id + report_content)`, `Precondition: Study.status == FINALIZING`.

ALLOWED_FILES: `src/mcp/tools/report_tool.py`, `tests/mcp/tools/test_report_tool.py`.

FORBIDDEN: Тихая правка JSON. Прямой перевод `RUNNING → FINALIZING`.

IMPLEMENTATION DETAILS:

- Precondition: `Study.status == FINALIZING`. Если нет → `INVALID_STATE`.
- Принять `study_id`, `session_id`, `report_format`, `report_content`, `idempotency_key`.
- `idempotency_key` вычисляется как SHA256(study_id + session_id + report_content). Повторный вызов с тем же ключом возвращает существующий `report_id` со статусом `SAVED`, не создавая дубликат.
- Core валидирует синтаксис, наличие ссылок на Evidence/Source (JOIN).
- Если валидно: сохраняет отчёт, триггерит `REPORT_VALID` (FSM: `FINALIZING → COMPLETED`).
- Если невалидно: возвращает `REPORT_VALIDATION_ERROR` со списком `validation_errors[]`. Тихая правка запрещена.
- Возвращает `status = SAVED|VALIDATION_FAILED`, `validation_errors[]`, `report_id`, `operation_id`.
- `SIDE EFFECTS`: создание/обновление Claim/ClaimEvidence и сохранение отчёта.
- `CANCELLATION`: timeout/cancel; частичные валидные данные обрабатываются процедурой Partial Report.
- `REPORT_TRUNCATED_PARTIAL` является result/metadata и не является Study state.
- `LLM_TIMEOUT` не является ошибкой самого `validate_and_save_report`: timeout генерации ЛЛМ относится к ЛЛМ operation/backend layer.
- Tool не переводит `RUNNING → FINALIZING`.
- Лимит: default 100 000 символов.
- Timeout: 60 с.

TESTS:

- Тест успешного сохранения (Study переходит в `COMPLETED`).
- Тест: при отсутствии Evidence в БД возвращается `REPORT_VALIDATION_ERROR`.
- Тест: вызов при `Study.status != FINALIZING` возвращает `INVALID_STATE`.
- Тест: повторный вызов с тем же контентом возвращает существующий `report_id` (идемпотентность).
- Тест: тихая правка не выполняется (невалидный JSON возвращает ошибку, не исправляет).

ACCEPTANCE: Отчёт валидируется жестко, идемпотентность работает, FSM переводится корректно.

STOP_CONDITIONS: Если Core не проверяет ссылки на Evidence → STOP → REPORT.

---

## TASK-07-16: Job Management Tools (`get_job_status`, `cancel_job`)

GOAL: Реализовать управление фоновыми задачами.

CONTEXT: Job используются для долгих операций (индексация, импорт). Кооперативная отмена.

ALLOWED_FILES: `src/mcp/tools/job_tools.py`, `tests/mcp/tools/test_job_tools.py`.

FORBIDDEN: Прямое присваивание `Job.status = CANCELLED`.

IMPLEMENTATION DETAILS:

- `get_job_status`:
    - Read-only, возвращает `job_id`, `job_type`, `status`, `progress`, `error?`, `created_at`, `started_at`, `completed_at`.
    - Допустимые Job states: `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`.
    - Timeout: 5 с.
- `cancel_job`:
    - Устанавливает cooperative cancellation flag. Возвращает `CANCEL_REQUESTED`.
    - Фактический переход в `CANCELLED` делает Job runner/Core.
    - `cancel_job` не имеет права напрямую присваивать `Job.status = CANCELLED`, если Job runner ещё не подтвердил безопасную отмену.
    - `IDEMPOTENCY`: повтор после отмены → `ALREADY_CANCELLED`.
    - Timeout: 5 с.
    - `RETRY`: повтор допустим и должен быть идемпотентным.

TESTS:

- Тест получения статуса.
- Тест: `cancel_job` возвращает `CANCEL_REQUESTED`, статус Job не меняется мгновенно.
- Тест: повторный `cancel_job` возвращает `ALREADY_CANCELLED`.
- Тест: `cancel_job` не присваивает `Job.status = CANCELLED` напрямую.

ACCEPTANCE: Отмена кооперативная, статусы читаются корректно, идемпотентность работает.

STOP_CONDITIONS: Если Job runner не поддерживает cooperative cancellation → STOP → REPORT.

---

## TASK-07-17: Idempotency & Duplicate Prevention Integration

GOAL: Комплексно проверить идемпотентность всех stateful tools.

CONTEXT: Повторный вызов с тем же `idempotency_key` не должен создавать дубли.

ALLOWED_FILES: `tests/integration/test_mcp_idempotency.py`.

FORBIDDEN: Изменение production кода.

IMPLEMENTATION DETAILS:

- Тест `plan_research`: повторный вызов с тем же intent возвращает те же task_ids.
- Тест `read_url_content`: повторный вызов возвращает тот же `document_id`.
- Тест `save_study_material`: повторный вызов возвращает `DUPLICATE`.
- Тест `validate_and_save_report`: повторный вызов с тем же контентом возвращает существующий `report_id`.
- Тест `update_working_memory`: повтор того же текста не создаёт новую версию.

TESTS:

- Указанные 5 сценариев. Проверка, что в БД не создано дублей.
- Проверка `LogRecord` для каждого вызова.

ACCEPTANCE: Идемпотентность работает на уровне всей системы для всех 5 типов операций.

STOP_CONDITIONS: Если идемпотентность нарушается на уровне Core → STOP → REPORT.

---

## TASK-07-18: Stdout Transport Contract Test & Static Linter

GOAL: Реализовать два механизма защиты `stdout`: статический линтер исходного кода (проверка в CI) и runtime-тест.

CONTEXT: ТЗ Раздел 5, Секция 3.1, пункт 3: «Линтер в CI: Автоматическая проверка исходного кода на наличие вызовов `print()` и `sys.stdout.write` вне разрешённых мест. Обнаружение таких вызовов блокирует сборку». Данная задача реализует оба механизма.

ALLOWED_FILES: `tools/check_stdout_policy.py`, `tests/integration/test_stdout_protection.py`, `tests/integration/test_stdout_linter.py`.

FORBIDDEN: Изменение production кода. Отключение линтера.

IMPLEMENTATION DETAILS:

- **Статический линтер** (проверка исходного кода):
    - Скрипт `tools/check_stdout_policy.py` сканирует `src/mcp/` на наличие вызовов `print(` и `sys.stdout.write(` вне разрешённых файлов (`transport.py`, `stdout_guard.py`).
    - При обнаружении нарушений: вывести список файлов и строк, завершиться с кодом 1 (блокировка сборки).
    - Тест `test_no_print_in_mcp_source` запускает этот скрипт и падает при обнаружении нарушений.
    - Данный тест должен быть интегрирован в CI pipeline как блокирующий.
- **Runtime-тест** (внедрение в подпроцессе):
    - Запустить MCP-сервер в подпроцессе.
    - Внедрить `print("debug")` и `logging.error("test")` в произвольный tool.
    - Вызвать tool через `stdin`.
    - Перехватить `stdout`. Проверить, что там только валидный JSON-RPC ответ.
    - Перехватить `stderr`. Проверить, что debug/log ушли туда.

TESTS:

- `test_no_print_in_mcp_source`: статический линтер не находит нарушений.
- `test_print_does_not_break_transport`: runtime-тест с внедрённым `print`.
- `test_exception_traceback_does_not_break_transport`: runtime-тест с исключением.
- `test_logger_does_not_break_transport`: runtime-тест с логгером в `stdout`.

ACCEPTANCE: Статический линтер блокирует сборку при нарушениях. Runtime-тест подтверждает, что `stdout` остаётся чистым при любых сбоях и логах.

STOP_CONDITIONS: Если тест нестабилен из-за буферизации → STOP → REPORT.

---

## TASK-07-19: No-Direct-FSM & No-Direct-DB Contract Tests

GOAL: Доказать, что MCP tools не обходят Core и не меняют FSM напрямую.

CONTEXT: Архитектурный инвариант: «ЛЛМ → MCP → Command / Application API → Core → FSM / Job → State + DB». MCP не имеет права самостоятельно менять FSM, обходить Core или выполнять DB-write.

ALLOWED_FILES: `tests/integration/test_mcp_authority.py`.

FORBIDDEN: Изменение production кода.

IMPLEMENTATION DETAILS:

- Анализ кода: проверить, что `src/mcp/tools/` не содержит импортов `src/db/repositories/` напрямую.
- Анализ кода: проверить, что `src/mcp/tools/` не содержит прямых вызовов `transition()` на доменных моделях.
- Убедиться, что все вызовы идут через `CoreAdapter`.
- Попытаться вызвать tool, который должен изменить FSM (например, `start_research_session`), но с невалидным состоянием Study. Проверить, что MCP вернул `INVALID_STATE`, а не упал с исключением БД.

TESTS:

- Тест: `src/mcp/tools/` не содержит импортов `src/db/repositories/` напрямую.
- Тест: `src/mcp/tools/` не содержит прямых вызовов `transition()`.
- Тест: все переходы FSM инициируются через Core API команды.
- Тест: невалидное состояние → `INVALID_STATE`, не исключение БД.

ACCEPTANCE: MCP строго следует паттерну Proxy. Все вызовы идут через `CoreAdapter`.

STOP_CONDITIONS: Если обнаружен прямой вызов БД в tools → STOP → REPORT (переписать через `CoreAdapter`).

---

## TASK-07-20: Timeout & Cancellation Contract Tests

GOAL: Проверить обработку таймаутов, отмен и `RETRY` логики на уровне MCP.

CONTEXT: MCP tools не должны блокировать транспорт. `RETRY` не должен бесконечно переводить операцию между `TIMED_OUT` и `EXECUTING`.

ALLOWED_FILES: `tests/integration/test_mcp_timeouts.py`.

FORBIDDEN: Изменение production кода.

IMPLEMENTATION DETAILS:

- Настроить `CoreAdapter` с задержкой (mock).
- Вызвать `search_web` с таймаутом 1 сек, при задержке Core 5 сек.
- Проверить, что MCP вернул `TIMEOUT` (retryable=True), а транспорт не завис.
- Вызвать `cancel_job` для активной задачи. Проверить `CANCEL_REQUESTED`.
- **Тест `RETRY` логики**:
    - Настроить `CoreAdapter` так, чтобы первый вызов вернул `NETWORK_ERROR`, а второй — успех.
    - Вызвать `search_web`.
    - Проверить, что первая попытка вернула `TIMED_OUT`/`NETWORK_ERROR`, затем `RETRY_ALLOWED` перевёл операцию в `EXECUTING`, и вторая попытка вернула `COMPLETED`.
    - Проверить, что `RETRY` не бесконечный (максимум 1 повтор).
    - Проверить переход `TIMED_OUT → EXECUTING` при `RETRY_ALLOWED`.
    - Проверить переход `TIMED_OUT → FAILED` при `RETRY_EXHAUSTED`.

TESTS:

- Тест таймаута операции (возврат `TIMEOUT`, транспорт жив).
- Тест кооперативной отмены (`cancel_job`).
- Тест `RETRY`: `TIMED_OUT → EXECUTING` при `RETRY_ALLOWED`.
- Тест `RETRY`: `TIMED_OUT → FAILED` при `RETRY_EXHAUSTED`.
- Тест: `RETRY` не превышает 1 повтор.

ACCEPTANCE: Таймауты работают, транспорт жив, `RETRY` логика корректна и ограничена.

STOP_CONDITIONS: Если таймауты не прерывают выполнение → STOP → REPORT.

---

## Gate G-07 Acceptance Criteria

- 23 Tools Registered: Все инструменты из MCP Tool Contracts v1.1 реализованы и зарегистрированы. Реестр хранит полный контракт (10 параметров).
- Core Authority: MCP не содержит бизнес-логики, не пишет в БД напрямую, не меняет FSM напрямую. Все через `CoreAdapter`.
- Stdout Protection: Статический линтер блокирует сборку при нарушениях. Runtime-тесты подтверждают, что `stdout` содержит только JSON-RPC.
- Idempotency: Повторные вызовы с теми же ключами не создают дубли в БД. Покрыты 5 типов операций.
- Security: `add_local_document` принимает только `file_ref`. Произвольные пути отклоняются.
- Limits & Timeouts: Ответы не превышают три лимита (`max_output_bytes`, `max_items`, `max_text_length`). Таймауты возвращают структурированные ошибки.
- RETRY: Дифференцированная обработка `RETRY` для разных ошибок. `plan_research`: 1 повтор после `VALIDATION_ERROR`. `search_*`: 1 повтор для `NETWORK_ERROR`/`TIMEOUT`, без retry для `RATE_LIMIT`.
- Report Validation: `validate_and_save_report` не производит тихой правки, жестко валидирует ссылки, переводит FSM. `idempotency_key` обработан.
- FSM Invariants: Ни один тест не использует прямое присваивание `.status`. `MCP Operation` — runtime-объект, не заменяет бизнес-состояния.
- Error Contract: Все 18 кодов ошибок из ТЗ Раздел 5, Секция 16 обработаны.
- Isolation: Тесты используют `tmp_path`, mock Core API, не требуют реальной сети или ЛЛМ.
- Scope: Не добавлено новых сущностей в БД, не изменены контракты FSM или Search Core.
- Watchdog: Контур 2 (MCP Watchdog) реализуется в EPIC-09. В EPIC-07 реализован только Контур 1.

Статус EPIC-07: Готов к передаче в разработку.