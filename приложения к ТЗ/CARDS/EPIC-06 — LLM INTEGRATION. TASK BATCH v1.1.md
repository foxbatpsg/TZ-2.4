# EPIC-06 — LLM INTEGRATION. TASK BATCH v1.1

Статус: Готов к передаче CODE-агентам.
Зависимости: EPIC-01 (Foundation), EPIC-02 (Data Layer), EPIC-03 (State Machines). Фактическая зависимость от доменных моделей EPIC-05 для мапперов (`SearchTaskDraft`, `ResearchPlan`).
Цель EPIC: Безопасно подключить локальную LLM (CPU-only). Обеспечить health-мониторинг бэкенда, парсинг/валидацию/repair JSON-ответов, маппинг выводов LLM в доменные модели, управление контекстным бюджетом через `TokenBudgetManager`, семантическую валидацию и защиту от prompt-injection. LLM только предлагает — Core валидирует и принимает решения.
Gate G-06: Локальная LLM безопасно подключена. Fake-backend end-to-end: LLM-ответ → JSON repair → schema validation → semantic validation → domain mapping → Core acceptance. Health FSM корректно обрабатывает сценарии DEGRADED/UNREACHABLE/RESTARTING. Контекстный бюджет рассчитывается через `TokenBudgetManager`. Сквозной сценарий `LLM Failure / Recovery` с участием `ResearchSession` проходит.

---

## Общие инварианты и запреты для всех задач EPIC-06

ALLOWED_FILES (глобально для EPIC):

- `src/core/llm/` (новая директория для LLM-интеграции)
- `src/core/models/` (только чтение доменных моделей; добавление Pydantic/dataclass схем для LLM-ответов)
- `tests/core/llm/`
- `tests/fixtures/` (добавление FakeLLMBackend, sample prompts/responses)

FORBIDDEN (глобально для EPIC):

- Прямое изменение статуса `Study`, `ResearchSession`, `SearchTask` в обход FSM.
- Изменение схемы SQLite или миграций (EPIC-02).
- Изменение контрактов MCP (EPIC-07).
- Изменение GUI (EPIC-08).
- Использование реальной сети в тестах.
- Использование реальной LLM в тестах (только FakeLLMBackend).
- Установка зависимости от GPU-библиотек (torch с CUDA, ctransformers с GPU и т.п.).
- Сохранение сырых LLM-ответов в БД без прохождения Core-валидации.
- LLM принимает решения о stop/continue/budget (решения только за Core).

Область видимости `LLM Backend Router` (ТЗ Раздел 5, Секция 2):

Из четырёх обязательных модулей `LLM Backend Router` в MVP реализуется только `Health Monitor` (TASK-06-03).

- `Health Monitor` — MVP, TASK-06-03.
- `LLM Controller` (инициализация, остановка, конфигурация инференса) — Post-MVP. В MVP управление процессом бэкенда выполняется внешним оператором.
- `Backend Router` (переключение на альтернативный порт) — Post-MVP. В MVP поддерживается один активный бэкенд.
- `Session Resume` (диспетчер восстановления контекста) — реализуется в EPIC-09 (Integration & Resilience) как часть сквозного сценария восстановления.

Структурированный вывод (ТЗ Раздел 5, Секция 10, Roadmap Раздел 9):

Приоритетный путь: `LLM → constrained decoding / grammar → strict schema validation → semantic validation → accepted result`.

Для MVP поддерживается только путь fallback:

    normal generation
    → strict JSON Schema validation
    → limited controlled repair (только для промежуточных объектов)
    → re-validation
    → semantic/content validation
    → retry / failure

`Constrained decoding / grammar-based structured generation` — Post-MVP, зависит от поддержки конкретным бэкендом. Архитектурно интерфейс `LLMBackend.generate()` должен допускать передачу параметра `response_format` для будущего расширения.

---

## TASK-06-01: LLM Backend Abstract Interface & Configuration

GOAL: Определить абстрактный интерфейс `LLMBackend`, конфигурацию подключения и параметры контекстного бюджета для `TokenBudgetManager`.

CONTEXT: Система должна поддерживать смену LLM-провайдера без изменения Core. Интерфейс определяет контракт: отправить промпт → получить текстовый ответ. Конфигурация включает параметры контекстного бюджета согласно ТЗ Раздел 2, Секция 6a.

ALLOWED_FILES: `src/core/llm/interface.py`, `src/core/llm/config.py`, `tests/core/llm/test_interface.py`.

FORBIDDEN: Реализация конкретного адаптера. Сетевые вызовы.

IMPLEMENTATION DETAILS:

- Определить `Protocol` (или ABC) `LLMBackend` с методами:
    - `generate(prompt: str, max_tokens: int, temperature: float, response_format: str | None = None) -> LLMResponse`
    - `health_check() -> HealthStatus`
    - `get_context_info() -> ContextInfo | None`
- Параметр `response_format` зарезервирован для будущего `constrained decoding`. В MVP передаётся `None`.
- Определить dataclass `LLMResponse(text: str, model: str, tokens_used: int, latency_ms: float)`.
- Определить dataclass `ContextInfo(backend_reported_context: int | None)` — информация о контексте от бэкенда (best effort, может быть `None`).
- Определить dataclass `LLMConfig` со следующими полями:
    - `backend_type: str` — тип бэкенда (`LM_STUDIO`, `OLLAMA`, `CUSTOM`)
    - `endpoint: str` — URL локального сервера
    - `model_name: str`
    - `max_context_tokens: int` — максимальный контекст (используется как `config_server`)
    - `timeout_s: float`
    - `temperature: float`
    - `fallback_context_tokens: int` — обязательный fallback при недоступности автоопределения (default 4096)
    - `max_allowed_context_tokens: int` — операторский лимит для режима `auto_with_config_cap` (default 8192)
    - `output_reserve_tokens: int` — резерв на генерацию ответа (default 1024)
    - `safety_margin_tokens: int` — запас безопасности (default 128)
    - `context_mode: ContextBudgetMode` — режим работы контекстного бюджета
- Определить Enum `ContextBudgetMode` со значениями: `AUTO`, `FIXED`, `AUTO_WITH_CONFIG_CAP`.
- `HealthStatus` — Enum: `HEALTHY`, `DEGRADED`, `UNREACHABLE`, `RESTARTING`. Примечание: `health_check()` не возвращает `RESTARTING`; этот статус устанавливается `LLM Controller` (Post-MVP) при инициировании перезагрузки.
- Валидация `LLMConfig`:
    - `max_context_tokens > 0`
    - `timeout_s > 0`
    - `endpoint` не пустой
    - `fallback_context_tokens > 0`
    - `output_reserve_tokens >= 0`
    - `safety_margin_tokens >= 0`
    - `max_allowed_context_tokens >= fallback_context_tokens`
    - `context_mode` является валидным значением `ContextBudgetMode`

TESTS:

- Тест создания валидной `LLMConfig` со всеми полями контекстного бюджета.
- Тест отклонения `LLMConfig` с `max_context_tokens = 0`.
- Тест отклонения `LLMConfig` с `fallback_context_tokens = 0`.
- Тест отклонения `LLMConfig` с `max_allowed_context_tokens < fallback_context_tokens`.
- Тест: `LLMBackend` Protocol имеет ожидаемые методы.
- Тест: `HealthStatus` содержит четыре значения.
- Тест: `ContextBudgetMode` содержит три значения.
- Тест: `get_context_info()` возвращает `None` при недоступности данных.

ACCEPTANCE: Интерфейс определён, конфигурация валидируется, все параметры контекстного бюджета присутствуют, нет зависимостей от конкретных бэкендов.

STOP_CONDITIONS: Если Protocol не совместим с Python 3.11 typing → STOP → REPORT.

---

## TASK-06-02: LLM Backend Health State Machine

GOAL: Реализовать FSM для отслеживания состояния LLM-бэкенда в соответствии с STATE MACHINE SPECIFICATION v1.1.

CONTEXT: Health FSM — runtime/operational state. Не хранится в `ResearchSession.budget_state`. Переходы фиксируются в `LogRecord`.

ALLOWED_FILES: `src/core/llm/health_fsm.py`, `tests/core/llm/test_health_fsm.py`.

FORBIDDEN: Запись health-статуса в `ResearchSession.budget_state`. Прямое присваивание `.status` в обход `transition()`.

IMPLEMENTATION DETAILS:

- Состояния: `HEALTHY`, `DEGRADED`, `UNREACHABLE`, `RESTARTING`.
- Переходы (строго по таблице из STATE MACHINE SPECIFICATION v1.1, Раздел 5):
    - `HEALTHY → DEGRADED` (trigger: `HEALTH_DEGRADED`)
    - `HEALTHY → UNREACHABLE` (trigger: `HEALTH_FAILED`)
    - `DEGRADED → HEALTHY` (trigger: `HEALTH_RECOVERED`)
    - `DEGRADED → UNREACHABLE` (trigger: `HEALTH_FAILED`)
    - `UNREACHABLE → RESTARTING` (trigger: `RESTART_REQUESTED`)
    - `UNREACHABLE → HEALTHY` (trigger: `BACKEND_RECOVERED`)
    - `RESTARTING → HEALTHY` (trigger: `RESTART_SUCCESS`)
    - `RESTARTING → UNREACHABLE` (trigger: `RESTART_FAILED`)
- Метод `transition(trigger: str) -> bool`. Возвращает `False` и выбрасывает `InvalidStateTransition` при недопустимом переходе.
- Метод `log_transition(log_record_writer)` — запись в `LogRecord` с полями: `entity_type`, `entity_id`, `from_state`, `to_state`, `trigger`, `component`, `timestamp`.
- Метод `current_state() -> str`.

TESTS:

- Тест каждого допустимого перехода (8 переходов).
- Тест каждого недопустимого перехода (ожидается `InvalidStateTransition`).
- Тест: после `transition()` вызывается `log_record_writer` с 7 полями.
- Тест: `RESTARTING` не является результатом `health_check()`.

ACCEPTANCE: FSM строго соответствует таблице переходов. Нарушения невозможны.

STOP_CONDITIONS: Если `LogRecord` writer из EPIC-03 не предоставляет требуемый интерфейс → STOP → REPORT.

---

## TASK-06-03: LLM Health Monitor (Watchdog)

GOAL: Реализовать Watchdog, который периодически проверяет `LLMBackend.health_check()` и управляет Health FSM.

CONTEXT: Watchdog вызывает `health_check()`, интерпретирует результат и отправляет триггеры в Health FSM. Является модулем `Health Monitor` из `LLM Backend Router`.

ALLOWED_FILES: `src/core/llm/health_monitor.py`, `tests/core/llm/test_health_monitor.py`.

FORBIDDEN: Блокировка основного потока. Прямое изменение `ResearchSession` состояний.

IMPLEMENTATION DETAILS:

- Создать `LLMHealthMonitor(backend: LLMBackend, health_fsm: LLMHealthFSM, log_writer)`.
- Метод `check_once()`: вызывает `backend.health_check()`, маппит `HealthStatus` в триггер FSM.
- Логика маппинга (явная таблица для слабых агентов):

        Текущее FSM → Результат health_check → Триггер:
        DEGRADED → HEALTHY → HEALTH_RECOVERED
        UNREACHABLE → HEALTHY → BACKEND_RECOVERED
        RESTARTING → HEALTHY → RESTART_SUCCESS
        HEALTHY → DEGRADED → HEALTH_DEGRADED
        DEGRADED → DEGRADED → (нет перехода, логировать аномалию)
        HEALTHY → UNREACHABLE → HEALTH_FAILED
        DEGRADED → UNREACHABLE → HEALTH_FAILED
        RESTARTING → DEGRADED → (нет перехода в таблице, логировать аномалию, не менять состояние)
        Любое → исключение → интерпретировать как UNREACHABLE → HEALTH_FAILED

- Метод `request_restart()`: отправляет `RESTART_REQUESTED` в FSM.
- Не запускать фоновый поток в этой задаче (только синхронный `check_once`). Периодика — в EPIC-09.

TESTS:

- Тест: backend возвращает `HEALTHY`, FSM в `DEGRADED` → переход в `HEALTHY` через `HEALTH_RECOVERED`.
- Тест: backend возвращает `HEALTHY`, FSM в `UNREACHABLE` → переход в `HEALTHY` через `BACKEND_RECOVERED`.
- Тест: backend возвращает `HEALTHY`, FSM в `RESTARTING` → переход в `HEALTHY` через `RESTART_SUCCESS`.
- Тест: backend возвращает `UNREACHABLE`, FSM в `HEALTHY` → переход в `UNREACHABLE`.
- Тест: backend возвращает `DEGRADED`, FSM в `RESTARTING` → перехода нет, аномалия залогирована.
- Тест: backend выбрасывает исключение → интерпретируется как `UNREACHABLE`.

ACCEPTANCE: Watchdog корректно маппит health_check-результаты в FSM-триггеры. Все переходы из таблицы покрыты.

STOP_CONDITIONS: Если `LLMBackend.health_check()` не возвращает `HealthStatus` → STOP → REPORT.

---

## TASK-06-04: Local LLM Client Adapter (CPU-only)

GOAL: Реализовать адаптеры для двух поддерживаемых бэкендов: `LMStudioAdapter` и `OllamaAdapter`, оба реализующие `LLMBackend`.

CONTEXT: ТЗ Раздел 5, Секция 1 фиксирует два бэкенда: LM Studio (OpenAI-compatible, `/v1/completions`) и Ollama (REST API, `/api/generate`). Адаптер общается с локальным LLM-сервером через HTTP (localhost). В тестах используется FakeLLMBackend.

ALLOWED_FILES: `src/core/llm/local_adapter.py`, `src/core/llm/ollama_adapter.py`, `tests/core/llm/test_local_adapter.py`, `tests/core/llm/test_ollama_adapter.py`, `tests/fixtures/fake_llm_backend.py`.

FORBIDDEN: Зависимость от GPU-библиотек. Реальные сетевые вызовы в тестах (использовать `unittest.mock.patch` для `urllib.request`).

IMPLEMENTATION DETAILS:

- Создать базовый класс `BaseHTTPAdapter(config: LLMConfig)`, реализующий `LLMBackend`, с общей логикой HTTP-вызовов через `urllib.request` из stdlib.
- `LMStudioAdapter(BaseHTTPAdapter)`:
    - `generate()`: формирует JSON-запрос к `{config.endpoint}/v1/completions` (OpenAI-compatible формат).
    - `health_check()`: GET `{config.endpoint}/health`.
    - `get_context_info()`: попытка извлечь `max_context_length` из ответа `/v1/models` (best effort, может вернуть `None`).
- `OllamaAdapter(BaseHTTPAdapter)`:
    - `generate()`: формирует JSON-запрос к `{config.endpoint}/api/generate` (Ollama-native формат: `{"model": ..., "prompt": ..., "stream": false}`).
    - `health_check()`: GET `{config.endpoint}/api/tags`.
    - `get_context_info()`: попытка извлечь `num_ctx` из конфигурации модели (best effort, может вернуть `None`).
- Оба адаптера используют только `urllib.request` из stdlib (без `requests`, без `httpx`).
- Таймаут из `config.timeout_s`.
- Обработка ошибок сети → `LLMConnectionError` (custom exception).
- Обработка таймаута → `LLMTimeoutError` (custom exception).
- Создать `FakeLLMBackend` в `tests/fixtures/`: предзаданные ответы по ключевым словам в промпте. `get_context_info()` возвращает `ContextInfo(backend_reported_context=4096)`.

TESTS:

- Тест `LMStudioAdapter.generate()` с мокнутым `urllib.request` (возвращает валидный OpenAI JSON).
- Тест `OllamaAdapter.generate()` с мокнутым `urllib.request` (возвращает валидный Ollama JSON).
- Тест `generate()` при таймауте → `LLMTimeoutError`.
- Тест `health_check()` при 200 OK → `HEALTHY`.
- Тест `health_check()` при connection refused → `UNREACHABLE`.
- Тест `get_context_info()` возвращает `ContextInfo` или `None`.
- Тест `FakeLLMBackend` возвращает предзаданный ответ.

ACCEPTANCE: Оба адаптера работают через stdlib, не зависят от GPU, обрабатывают ошибки. Поддержка двух бэкендов обеспечена.

STOP_CONDITIONS: Если локальный LLM-сервер использует не-совместимый API → STOP → REPORT (потребуется другой адаптер).

---

## TASK-06-05: Prompt Template Engine

GOAL: Реализовать простой шаблонизатор промптов с подстановкой переменных и системных инструкций.

CONTEXT: Промпты для LLM формируются из шаблонов. Нужна безопасная подстановка (без eval, без произвольного кода). Финальная длина промпта контролируется `TokenBudgetManager` (TASK-06-12).

ALLOWED_FILES: `src/core/llm/prompt_engine.py`, `src/core/llm/templates/` (директория с .txt шаблонами), `tests/core/llm/test_prompt_engine.py`.

FORBIDDEN: Использование Jinja2 или любых внешних шаблонизаторов. `eval()`, `exec()`.

IMPLEMENTATION DETAILS:

- Использовать `string.Template` из stdlib (`$variable` синтаксис).
- Метод `render(template_name: str, **kwargs) -> str`.
- Загрузка шаблонов из `src/core/llm/templates/`.
- Метод `build_prompt(system_instruction: str, user_content: str, context: str) -> str` — собирает финальный промпт.
- Проверка: все `$variable` в шаблоне должны быть подставлены. Если нет → `PromptRenderError`.
- Ограничение длины финального промпта: если > `max_context_tokens * 3` (приблизительная оценка символов) → делегировать усечение `TokenBudgetManager` (TASK-06-12), а не обрезать самостоятельно.

TESTS:

- Тест успешного рендеринга шаблона с подстановкой.
- Тест `PromptRenderError` при пропущенной переменной.
- Тест сборки промпта с system/user/context.

ACCEPTANCE: Шаблоны рендерятся безопасно, без внешних зависимостей.

STOP_CONDITIONS: Если `string.Template` не поддерживает требуемый синтаксис → STOP → REPORT.

---

## TASK-06-06: JSON Output Schema Definitions

GOAL: Определить JSON-схемы для всех типов ответов LLM, которые система ожидает.

CONTEXT: LLM возвращает JSON. Каждая точка интеграции (plan, evidence, observation, gap, contradiction, report, working memory) имеет свою схему.

ALLOWED_FILES: `src/core/llm/schemas/` (директория с .json файлами схем), `src/core/llm/schema_registry.py`, `tests/core/llm/test_schemas.py`.

FORBIDDEN: Изменение доменных моделей в `src/core/models/`.

IMPLEMENTATION DETAILS:

- Создать JSON Schema (Draft 2020-12 или совместимый) для каждого типа:
    - `research_plan_response` (список задач с полями: `query`, `purpose`, `source_scope`, `filters`, `exclusions`, `expected_material_type`, `priority`)
    - `observation_response` (наблюдения)
    - `evidence_response` (доказательства)
    - `research_gap_response` (пробелы с полями: `question`, `reason`, `missing_evidence`, `recommended_query`, `priority`)
    - `contradiction_candidate_response` (кандидаты в противоречия)
    - `report_section_response` (секции отчёта)
    - `working_memory_response` (рабочая память: `summary` string max 200 токенов, `status` Enum `SAVED|TOO_LONG`, `tokens_used` integer, `version` integer)
- `SchemaRegistry.get(schema_name: str) -> dict` — загрузка схемы по имени.
- Каждая схема: `type`, `required`, `properties`, `additionalProperties: false`.
- Схемы хранятся как `.json` файлы в `src/core/llm/schemas/`.
- Схема `research_plan_response` обязана включать `exclusions` и `expected_material_type` как обязательные поля (совместимость с исправленным EPIC-05 v1.1).

TESTS:

- Тест загрузки каждой схемы через `SchemaRegistry` (7 схем).
- Тест: каждая схема является валидным JSON Schema (проверка наличия `type` и `properties`).
- Тест: схема `research_plan_response` содержит `exclusions` и `expected_material_type`.
- Тест: схема `working_memory_response` содержит `summary`, `status`, `tokens_used`, `version`.

ACCEPTANCE: Все схемы загружаются, имеют корректную структуру. Совместимость с исправленным EPIC-05 v1.1 обеспечена.

STOP_CONDITIONS: Если требуется поддержка `oneOf`/`anyOf` с сложной логикой, не реализуемой stdlib → STOP → REPORT.

---

## TASK-06-07: JSON Parser & Repair

GOAL: Реализовать парсер JSON с механизмом repair для обработки некорректных LLM-ответов, с разграничением между промежуточными объектами и финальным отчётом.

CONTEXT: LLM может вернуть JSON с лишними запятыми, без кавычек у ключей, с комментариями, с обёрткой в markdown-блоки. Нужен repair. ТЗ Раздел 5, Секция 10.1 определяет критическое разграничение: ремонт промежуточных объектов разрешён, ремонт финального отчёта запрещён.

ALLOWED_FILES: `src/core/llm/json_parser.py`, `tests/core/llm/test_json_parser.py`.

FORBIDDEN: Использование внешних библиотек (`json5`, `dirtyjson`, `demjson`). `eval()`. Автоматическая правка финального отчёта.

IMPLEMENTATION DETAILS:

- Метод `parse_and_repair(raw_text: str, allow_repair: bool = True) -> dict | list`.
- Параметр `allow_repair`:
    - `True` (по умолчанию) — для промежуточных объектов (наблюдения, пробелы, противоречия). Ремонт разрешён.
    - `False` — для финального отчёта (`validate_and_save_report`). Ремонт запрещён. Только строгий `json.loads`. При несовпадении → `JSONParseError`.
- Метод `parse_strict(raw_text: str) -> dict | list` — эквивалент `parse_and_repair(raw_text, allow_repair=False)`.
- Пайплайн repair (последовательно, до первого успешного `json.loads`, только при `allow_repair=True`):
    - a. Удаление markdown-обёрток.
    - b. Удаление однострочных комментариев.
    - c. Удаление завершающих запятых перед `}` или `]`.
    - d. Обёртка не-JSON текста в `{"raw": "..."}` (fallback).
- Каждый шаг repair — отдельная приватная функция.
- Если после всех шагов `json.loads` не succeeds → выбросить `JSONParseError` с оригинальным текстом.
- Логировать, какой шаг repair сработал (через `logging`).
- Возвращать метадату `was_repaired: bool` вместе с результатом (через dataclass `ParseResult(data, was_repaired: bool, repair_step: str | None)`).

TESTS:

- Тест: валидный JSON проходит без изменений, `was_repaired=False`.
- Тест: JSON в markdown-блоке → извлечён, `was_repaired=True`.
- Тест: JSON с завершающей запятой → исправлен, `was_repaired=True`.
- Тест: JSON с однострочными комментариями → исправлен, `was_repaired=True`.
- Тест: полностью не-JSON текст → fallback, `was_repaired=True`.
- Тест: `JSONParseError` при непарсируемом содержимом после всех шагов (если fallback отключён).
- Тест: `parse_strict` с невалидным JSON → `JSONParseError` (ремонт не применяется).
- Тест: `parse_and_repair(raw, allow_repair=False)` с невалидным JSON → `JSONParseError`.

ACCEPTANCE: Парсер обрабатывает типичные LLM-артефакты. Разграничение между промежуточными объектами и финальным отчётом соблюдено. Не использует внешние библиотеки.

STOP_CONDITIONS: Если repair-пайплайн не покрывает >80% типичных LLM-артефактов → STOP → REPORT (добавить шаги).

---

## TASK-06-08: JSON Schema Validation

GOAL: Реализовать валидацию распарсенных JSON-объектов против схем из TASK-06-06 с логированием факта восстановления.

CONTEXT: После repair JSON должен соответствовать ожидаемой схеме. Невалидные объекты отбрасываются с диагностикой. Факт восстановления фиксируется.

ALLOWED_FILES: `src/core/llm/schema_validator.py`, `tests/core/llm/test_schema_validator.py`.

FORBIDDEN: Использование `jsonschema` или других внешних библиотек для валидации.

IMPLEMENTATION DETAILS:

- Реализовать минимальный валидатор, поддерживающий: `type`, `required`, `properties`, `items`, `enum`, `additionalProperties`.
- Метод `validate(data: dict | list, schema: dict, was_repaired: bool = False) -> ValidationResult`.
- `ValidationResult(valid: bool, errors: list[str], was_repaired: bool)`.
- Поле `was_repaired` заполняется на основе информации из `ParseResult` (TASK-06-07).
- Проверка типов: `string`, `integer`, `number`, `boolean`, `array`, `object`, `null`.
- Проверка `required`: все обязательные поля присутствуют.
- Проверка `additionalProperties: false`: нет лишних полей.
- Проверка `enum`: значение входит в список.
- Рекурсивная валидация вложенных объектов и массивов.
- Если объект был восстановлен (`was_repaired=True`) и прошёл валидацию — зафиксировать факт восстановления в `LogRecord` или диагностическом логе.

TESTS:

- Тест: валидный объект проходит, `was_repaired=False`.
- Тест: отсутствует required-поле → ошибка.
- Тест: лишнее поле при `additionalProperties: false` → ошибка.
- Тест: неверный тип поля → ошибка.
- Тест: значение не в enum → ошибка.
- Тест: валидация вложенного массива объектов.
- Тест: восстановленный объект (`was_repaired=True`) проходит валидацию → факт зафиксирован.
- Тест: восстановленный объект не проходит валидацию → ошибка содержит `was_repaired=True`.

ACCEPTANCE: Валидатор покрывает необходимое подмножество JSON Schema. Факт восстановления логируется. Без внешних зависимостей.

STOP_CONDITIONS: Если схемы из TASK-06-06 используют неподдерживаемые ключевые слова (например `$ref`, `patternProperties`) → STOP → REPORT.

---

## TASK-06-09: LLM Response → Domain Model Mapper (Plan)

GOAL: Реализовать маппер, преобразующий валидированный JSON LLM-ответа в `ResearchPlan` (доменную модель из EPIC-05), включая поля `exclusions` и `expected_material_type`.

CONTEXT: LLM предлагает план. Core принимает его через `PlanNormalizer`. Маппер — мост между JSON и доменом. Совместимость с исправленным EPIC-05 v1.1 обязательна.

ALLOWED_FILES: `src/core/llm/mappers/plan_mapper.py`, `tests/core/llm/test_plan_mapper.py`.

FORBIDDEN: Изменение `ResearchPlan` или `SearchTaskDraft` структур. Создание записей в БД.

IMPLEMENTATION DETAILS:

- Метод `map_plan_response(json_data: dict) -> list[SearchTaskDraft]`.
- Извлечение полей из JSON по ключам, определённым в схеме `research_plan_response`:
    - `query: str`
    - `purpose: str`
    - `source_scope: str`
    - `filters: str`
    - `exclusions: str` — обязательное поле для расчёта `query_fingerprint`
    - `expected_material_type: str` — обязательное поле для расчёта `query_fingerprint`
    - `priority: int`
- Маппинг `source_scope` string → соответствующий Enum.
- Если поле отсутствует или невалидно — пропустить задачу, залогировать warning.
- Если `exclusions` или `expected_material_type` отсутствуют — пропустить задачу с явным указанием причины (эти поля обязательны для `query_fingerprint`).
- Возвращает список `SearchTaskDraft` (не сохраняет).

TESTS:

- Тест: валидный JSON со всеми семью полями → корректный список `SearchTaskDraft`.
- Тест: задача с невалидным `source_scope` → пропущена, остальные маппятся.
- Тест: задача без `exclusions` → пропущена, причина залогирована.
- Тест: задача без `expected_material_type` → пропущена, причина залогирована.
- Тест: пустой список задач → пустой список.

ACCEPTANCE: Маппер работает детерминированно, не создаёт side-effects. Поля `exclusions` и `expected_material_type` извлекаются.

STOP_CONDITIONS: Если `SearchTaskDraft` из EPIC-05 изменил поля → STOP → REPORT.

---

## TASK-06-10: LLM Response → Domain Model Mapper (Evidence, Observation, Gap, Contradiction)

GOAL: Реализовать мапперы для остальных типов LLM-ответов: Evidence, Observation, ResearchGap, ContradictionCandidate.

CONTEXT: LLM предлагает материалы. Core валидирует и сохраняет через `save_study_material`.

ALLOWED_FILES: `src/core/llm/mappers/material_mappers.py`, `tests/core/llm/test_material_mappers.py`.

FORBIDDEN: Прямая запись в БД. Изменение доменных моделей.

IMPLEMENTATION DETAILS:

- `map_observation_response(json_data) -> list[ObservationDraft]`.
- `map_evidence_response(json_data) -> list[EvidenceDraft]`.
- `map_gap_response(json_data) -> list[ResearchGapDraft]`.
- `map_contradiction_response(json_data) -> list[ContradictionCandidateDraft]`.
- Каждый маппер: извлечение полей, приведение типов, пропуск невалидных элементов с логированием.
- Для `ResearchGapDraft`: извлекать поля `question`, `reason`, `missing_evidence`, `recommended_query`, `priority`. Если `priority` отсутствует — использовать дефолт `0`.
- Для `ContradictionCandidateDraft`: извлекать поля `chunk_a_id`, `chunk_b_id`, `value_a`, `value_b`, `unit`, `type`, `evidence_a_id`, `evidence_b_id`, `contradiction_type`.
- Draft-объекты — простые dataclass, не привязанные к БД.
- Для Contradiction: маппер только формирует кандидаты. Детерминистическая проверка — в EPIC-05 `ContradictionDetector`.

TESTS:

- По одному тесту успешного маппинга на каждый тип (4 теста).
- По одному тесту пропуска невалидного элемента на каждый тип (4 теста).
- Тест: `ResearchGapDraft` без `priority` → дефолт `0`.
- Тест: `ResearchGapDraft` со всеми полями → корректный объект.
- Тест: все мапперы возвращают Draft-объекты, а не ORM/DB-модели.

ACCEPTANCE: Все мапперы работают, Draft-объекты корректны. `priority` для `ResearchGap` обрабатывается.

STOP_CONDITIONS: Если доменные модели из EPIC-02 не имеют соответствующих Draft-аналогов → STOP → REPORT.

---

## TASK-06-11: LLM Response → Report Section Mapper

GOAL: Реализовать маппер для секций финального отчёта.

CONTEXT: LLM формирует текстовые секции отчёта. Core проверяет, что каждая секция ссылается на валидные Claim/Evidence. Маппер совместим с процедурой частичных отчётов (ТЗ Раздел 5, Секция 15).

ALLOWED_FILES: `src/core/llm/mappers/report_mapper.py`, `tests/core/llm/test_report_mapper.py`.

FORBIDDEN: Тихая правка отчёта. Запись в БД. Автоматическая правка финального отчёта.

IMPLEMENTATION DETAILS:

- Метод `map_report_response(json_data) -> list[ReportSection]`.
- `ReportSection`: dataclass с полями `title`, `content`, `referenced_claim_ids`, `referenced_evidence_ids`, `is_partial: bool`.
- Проверка: каждый `referenced_claim_id` и `referenced_evidence_ids` — непустой string.
- Если секция ссылается на несуществующий ID — не отбрасывать (проверка на существование — задача Core при финализации, EPIC-05), но пометить `has_unresolved_refs = True`.
- Поле `is_partial` используется для поддержки `REPORT_TRUNCATED_PARTIAL` (метаданные, не состояние).
- Маппер не выполняет валидацию отчёта — только формирует структуру. Валидация — задача `validate_and_save_report` (EPIC-07).

TESTS:

- Тест: валидный JSON → список `ReportSection`.
- Тест: секция с пустым `referenced_claim_ids` → `has_unresolved_refs = True`.
- Тест: секция с `is_partial = True` → корректно передаётся.

ACCEPTANCE: Маппер формирует секции, не проверяет существование ID (это задача Core). Поддержка частичных отчётов обеспечена.

STOP_CONDITIONS: Если структура отчёта из ТЗ изменилась → STOP → REPORT.

---

## TASK-06-12: TokenBudgetManager (Context Budget)

GOAL: Реализовать полноценный `TokenBudgetManager` для динамического расчёта контекстного бюджета согласно ТЗ Раздел 2, Секция 6a.

CONTEXT: Локальные CPU-only модели имеют ограниченное контекстное окно. Бюджет рассчитывается динамически с учётом бэкенда, конфигурации и режима работы. Жёстко фиксировать бюджет в коде запрещено.

ALLOWED_FILES: `src/core/llm/token_budget_manager.py`, `tests/core/llm/test_token_budget_manager.py`.

FORBIDDEN: Изменение доменных моделей. Сетевые вызовы. Жёсткая фиксация контекстного бюджета в коде.

IMPLEMENTATION DETAILS:

- Создать `TokenBudgetManager(config: LLMConfig)`.
- Метод `calculate_effective_context(backend_context_info: ContextInfo | None) -> int`:
    - Режим `AUTO`: `effective_context = min(backend_reported or fallback, fallback_context_tokens)`. Если `backend_reported` доступен — использовать его, иначе `fallback_context_tokens`.
    - Режим `FIXED`: `effective_context = config.max_context_tokens` (всегда из конфигурации).
    - Режим `AUTO_WITH_CONFIG_CAP`: `effective_context = min(backend_reported or fallback, config.max_allowed_context_tokens)`. Автоопределение, но не выше операторского лимита.
- Метод `calculate_usable_prompt(effective_context: int) -> int`:

        usable_prompt = effective_context - output_reserve_tokens - safety_margin_tokens

- Метод `allocate_quota(usable_prompt: int) -> ContextAllocation`:
    - `ContextAllocation(fixed_sections: int, evidence_budget: int)`
    - `fixed_sections` = оценка токенов для: `system_prompt + dashboard + working_memory + research_gaps + tool_instructions`.
    - `evidence_budget = usable_prompt - fixed_sections`.
    - Если `evidence_budget <= 0` → выбросить `ConfigContextInsufficientError`.
- Метод `fit_context(context_items: list[str], evidence_budget: int) -> list[str]`:
    - Приоритетное усечение эластичных частей:
        1. Уменьшить число Evidence в одном вызове.
        2. Уменьшить число чанков в контекстном коридоре (но не ниже ±1 для target).
        3. Уменьшить список второстепенных gaps.
        4. Уменьшить объём dashboard.
    - Если после всех усечений минимальный контекст не собирается → выбросить `ConfigContextInsufficientError`.
    - Запрещено молча обрезать контекст без логирования.
- Метод `estimate_tokens(text: str) -> int` — возвращает `len(text) // 3` (консервативная оценка для русского).
- Триггеры пересчёта (вызываются извне, но метод `recalculate()` должен быть доступен):
    - Старт приложения / старт Study.
    - Смена бэкенда / модели / конфигурации.
    - Переход `HEALTHY → DEGRADED → UNREACHABLE → RESTARTING`.
    - Восстановление сессии через `SESSION_RESUMING`.

TESTS:

- Тест: режим `AUTO` с `backend_reported=8192`, `fallback=4096` → `effective_context=4096`.
- Тест: режим `AUTO` с `backend_reported=None`, `fallback=4096` → `effective_context=4096`.
- Тест: режим `FIXED` с `max_context_tokens=4096` → `effective_context=4096`.
- Тест: режим `AUTO_WITH_CONFIG_CAP` с `backend_reported=16384`, `max_allowed=8192` → `effective_context=8192`.
- Тест: расчёт `usable_prompt` с вычетом `output_reserve` и `safety_margin`.
- Тест: расчёт `evidence_budget` как `usable_prompt - fixed_sections`.
- Тест: `evidence_budget <= 0` → `ConfigContextInsufficientError`.
- Тест: `fit_context` усечение эластичных частей при нехватке бюджета.
- Тест: `fit_context` не усечение ниже минимального контекста (±1 чанк).
- Тест: `estimate_tokens` возвращает ожидаемое значение.

ACCEPTANCE: `TokenBudgetManager` реализует формулу расчёта, три режима, распределение квот и приоритетное усечение. `ConfigContextInsufficientError` выбрасывается при невозможности собрать минимальный контекст.

STOP_CONDITIONS: Если `LLMConfig` не содержит полей контекстного бюджета → STOP → REPORT.

---

## TASK-06-13: Input Sanitization & Prompt Injection Guard

GOAL: Реализовать базовую защиту от prompt-injection в пользовательском вводе, передаваемом в LLM.

CONTEXT: Пользовательские данные (вопросы, цитаты, тексты документов) попадают в промпт. Необходимо снизить риск инъекции. Санитайзер работает в связке с `TokenBudgetManager` (TASK-06-12) для обеспечения полной защиты контекста.

ALLOWED_FILES: `src/core/llm/sanitizer.py`, `tests/core/llm/test_sanitizer.py`.

FORBIDDEN: Использование внешних библиотек для sanitization. Блокировка легитимного ввода.

IMPLEMENTATION DETAILS:

- Метод `sanitize_user_input(text: str) -> str`.
- Правила:
    - a. Удаление управляющих символов (ASCII < 32, кроме `\n`, `\t`).
    - b. Экранирование маркеров markdown-блоков.
    - c. Обёртка пользовательского контента в явные разделители: `=== USER CONTENT START ===` / `=== USER CONTENT END ===`.
    - d. Ограничение длины: если > `max_input_chars` (по умолчанию 50000) → обрезать.
- Метод `wrap_for_prompt(system_instruction: str, user_content: str) -> str` — собирает безопасный промпт.
- Не блокировать текст, а трансформировать.
- Перекрёстная ссылка: санитайзер не заменяет `TokenBudgetManager`. Запрет на передачу сырых HTML, объёмных кусков, длинных логов реализуется через `TokenBudgetManager` и контекстный менеджер.

TESTS:

- Тест: управляющие символы удалены.
- Тест: markdown-блоки экранированы.
- Тест: пользовательский контент обёрнут в разделители.
- Тест: длинный текст обрезан.
- Тест: нормальный русский текст не изменён (кроме обёртки).

ACCEPTANCE: Sanitizer снижает риск инъекции без потери легитимных данных.

STOP_CONDITIONS: Если правила sanitization конфликтуют с Prompt Template Engine (TASK-06-05) → STOP → REPORT.

---

## TASK-06-14: LLM Error Handling & Retry

GOAL: Реализовать обработку ошибок LLM-вызовов и ограниченную политику retry в соответствии с ТЗ Раздел 5, Секция 16 (Единый контракт системных ошибок).

CONTEXT: LLM может не ответить, вернуть ошибку, таймаутить. Нужна предсказуемая обработка. Коды ошибок из ТЗ: `LLM_UNREACHABLE`, `LLM_TIMEOUT`, `LLM_DEGRADED`, `CONFIG_CONTEXT_INSUFFICIENT`.

ALLOWED_FILES: `src/core/llm/error_handler.py`, `tests/core/llm/test_error_handler.py`.

FORBIDDEN: Бесконечный retry. Автоматический retry для `INVALID_INPUT`.

IMPLEMENTATION DETAILS:

- Определить исключения:
    - `LLMConnectionError` — соответствует коду `LLM_UNREACHABLE`
    - `LLMTimeoutError` — соответствует коду `LLM_TIMEOUT`
    - `LLMDegradedError` — соответствует коду `LLM_DEGRADED`
    - `ConfigContextInsufficientError` — соответствует коду `CONFIG_CONTEXT_INSUFFICIENT`
    - `LLMResponseError` — общая ошибка ответа
    - `JSONParseError` — ошибка парсинга
    - `SchemaValidationError` — ошибка валидации схемы
    - `SemanticValidationError` — ошибка семантической валидации (для TASK-06-18)
- Создать `LLMErrorClassifier`. Метод `classify(exception: Exception) -> ErrorCategory` (`RETRYABLE`, `NON_RETRYABLE`, `FATAL`).
- Правила:
    - `LLMConnectionError`, `LLMTimeoutError` → `RETRYABLE` (max 1 retry).
    - `LLMDegradedError` → `RETRYABLE` (max 1 retry, с увеличенным таймаутом).
    - `JSONParseError`, `SchemaValidationError`, `SemanticValidationError` → `NON_RETRYABLE` (вернуть ошибку Core).
    - `ConfigContextInsufficientError` → `NON_RETRYABLE` (вернуть рекомендации: уменьшить `chunk_size`, увеличить контекст в сервере, выбрать другую модель).
    - Непредвиденные исключения → `FATAL`.
- Создать `RetryPolicy`. Метод `execute_with_retry(callable, max_retries=1)`.
- При исчерпании retry → обновить Health FSM через `LLMHealthMonitor` (TASK-06-03).

TESTS:

- Тест: `LLMTimeoutError` → RETRYABLE.
- Тест: `LLMDegradedError` → RETRYABLE.
- Тест: `JSONParseError` → NON_RETRYABLE.
- Тест: `ConfigContextInsufficientError` → NON_RETRYABLE с рекомендациями.
- Тест: `SemanticValidationError` → NON_RETRYABLE.
- Тест: retry succeeds на 2-й попытке → результат возвращён.
- Тест: retry exhausted → исключение проброшено, health monitor уведомлён.

ACCEPTANCE: Ошибки классифицируются, все четыре кода из ТЗ обработаны, retry ограничен, FSM обновляется при сбоях.

STOP_CONDITIONS: Если retry логика конфликтует с Operation FSM (EPIC-03) → STOP → REPORT.

---

## TASK-06-15: Full LLM Pipeline Integration (Fake Backend)

GOAL: Реализовать сквозной пайплайн: Prompt → TokenBudgetManager → LLM (Fake) → JSON Parse → Repair → Validate → Semantic Validate → Map → Domain Objects.

CONTEXT: Интеграция всех компонентов EPIC-06 в единый вызов. Пайплайн использует `TokenBudgetManager` для расчёта контекстного бюджета перед каждым вызовом.

ALLOWED_FILES: `src/core/llm/pipeline.py`, `tests/core/llm/test_pipeline.py`.

FORBIDDEN: Реальная LLM. Реальная сеть. Запись в БД.

IMPLEMENTATION DETAILS:

- Создать `LLMPipeline(backend: LLMBackend, prompt_engine, json_parser, schema_validator, semantic_validator, mapper_registry, token_budget_manager, sanitizer)`.
- Метод `invoke(task_type: str, context_data: dict, allow_repair: bool = True) -> DomainResult`.
- Пайплайн:
    - a. Sanitize user input.
    - b. Calculate `evidence_budget` через `TokenBudgetManager.calculate_effective_context()` и `TokenBudgetManager.allocate_quota()`.
    - c. Fit context через `TokenBudgetManager.fit_context()`.
    - d. Build prompt.
    - e. Call `backend.generate()`.
    - f. Parse & repair JSON (с учётом `allow_repair`).
    - g. Validate against schema.
    - h. Semantic/content validation (TASK-06-18).
    - i. Map to domain objects.
    - j. Return `DomainResult(success: bool, data: Any, errors: list[str])`.
- При ошибке на любом шаге: вернуть `DomainResult(success=False, errors=[...])`.
- При `ConfigContextInsufficientError` на шаге b/c: вернуть `DomainResult(success=False, errors=["CONFIG_CONTEXT_INSUFFICIENT"])` без вызова LLM.

TESTS:

- Тест happy path: FakeLLMBackend возвращает валидный JSON → `DomainResult(success=True)`.
- Тест: FakeLLMBackend возвращает JSON с артефактами → repair → success.
- Тест: FakeLLMBackend возвращает невалидный JSON → `DomainResult(success=False)`.
- Тест: JSON не проходит schema validation → `DomainResult(success=False, errors=[...])`.
- Тест: контекст превышает `evidence_budget` → усечение через `TokenBudgetManager`.
- Тест: `ConfigContextInsufficientError` → `DomainResult(success=False)` без вызова LLM.
- Тест: `allow_repair=False` → ремонт не применяется.

ACCEPTANCE: Пайплайн обрабатывает все сценарии, использует `TokenBudgetManager`, возвращает структурированный результат.

STOP_CONDITIONS: Если пайплайн требует более 8 зависимостей в конструкторе → STOP → REPORT (упростить через factory).

---

## TASK-06-16: LLM ↔ Core Authority Integration Test

GOAL: Проверить, что LLM-выводы проходят через Core-валидацию и Core сохраняет только одобренные объекты.

CONTEXT: Gate G-06 требует подтверждения: LLM только предлагает, Core принимает решения.

ALLOWED_FILES: `tests/integration/test_llm_core_authority.py`, `tests/fixtures/fake_llm_backend.py`.

FORBIDDEN: Изменение production кода. Реальная LLM. Реальная сеть.

IMPLEMENTATION DETAILS:

- Настроить `tmp_path` для изолированной БД.
- Инициализировать `LLMPipeline` с `FakeLLMBackend` и `TokenBudgetManager`.
- Сценарий 1: LLM предлагает `ResearchPlan`. Core (через `TaskAcceptor` из EPIC-05) отклоняет дубликат. Проверить, что дубликат не сохранён.
- Сценарий 2: LLM предлагает `Observation`. Core валидирует и сохраняет через `save_study_material` logic. Проверить, что сохранено.
- Сценарий 3: LLM предлагает `Evidence` с невалидным `source_id`. Core отклоняет. Проверить, что не сохранено.
- Сценарий 4: проверка, что `LLM` не может переопределить решение `SufficiencyEvaluator`. Маппер не передаёт «решение о достаточности» от `LLM` в `Core`.
- Все переходы Study/Session FSM — через команды.

TESTS:

- `test_core_rejects_duplicate_plan_task`
- `test_core_accepts_valid_observation`
- `test_core_rejects_evidence_with_invalid_source`
- `test_llm_cannot_override_sufficiency_decision`
- Проверка `LogRecord`: каждое решение Core зафиксировано.

ACCEPTANCE: Core является единственным арбитром. LLM-выводы не обходят валидацию. Решение о достаточности не передаётся от LLM.

STOP_CONDITIONS: Если `TaskAcceptor` или `save_study_material` логика из EPIC-05/02 не доступна → STOP → REPORT.

---

## TASK-06-17: Health FSM Recovery Scenarios Test

GOAL: Покрыть тестами сценарии восстановления LLM-бэкенда, включая сквозной сценарий с участием `ResearchSession`.

CONTEXT: Gate G-06 требует корректной обработки health-сценариев. ТЗ Раздел 1, Секция 2.3 определяет сквозной сценарий аварийного восстановления: `RUNNING → LLM_UNAVAILABLE → SESSION_RESUMING → RUNNING`.

ALLOWED_FILES: `tests/integration/test_health_recovery.py`.

FORBIDDEN: Изменение production кода.

IMPLEMENTATION DETAILS:

- `test_degraded_to_healthy`: бэкенд сначала `DEGRADED`, затем `HEALTHY`. FSM переходит. `LogRecord` зафиксирован.
- `test_unreachable_restart_success`: `UNREACHABLE → RESTARTING → HEALTHY`.
- `test_unreachable_restart_failed`: `UNREACHABLE → RESTARTING → UNREACHABLE`. Проверить, что система не зависает.
- `test_rapid_flapping`: быстрая смена HEALTHY→DEGRADED→HEALTHY→UNREACHABLE. FSM не ломается, все переходы валидны.
- `test_llm_failure_session_recovery`: сквозной сценарий с участием `ResearchSession`:
    - Бэкенд переходит в `UNREACHABLE`.
    - `ResearchSession` переходит в `LLM_UNAVAILABLE` (через команду `LLM_BACKEND_UNAVAILABLE`).
    - Бэкенд восстанавливается (`RESTARTING → HEALTHY`).
    - `ResearchSession` переходит в `SESSION_RESUMING` (через команду `LLM_BACKEND_RECOVERED`), затем в `ACTIVE` (через `RECOVERY_COMPLETE`).
    - Проверить, что `Study.status` остаётся `RUNNING` (ТЗ Раздел 1: «Исследование не обязан останавливаться только из-за временной недоступности LLM backend»).
- Проверить: ни один сценарий не изменяет `ResearchSession.budget_state`.

TESTS:

- Указанные 5 сценариев.
- Проверка 7 полей `LogRecord` для каждого перехода.

ACCEPTANCE: Все health-сценарии проходят, включая сквозной с участием `ResearchSession`. FSM консистентен, `budget_state` не затронут.

STOP_CONDITIONS: Если `LogRecord` writer не поддерживает требуемые поля для health-событий → STOP → REPORT.

---

## TASK-06-18: Semantic/Content Validation

GOAL: Реализовать минимальную семантическую/содержательную валидацию результатов LLM поверх схемы.

CONTEXT: Roadmap v1.2, Раздел 9 определяет: «Помимо schema validation проверяются обязательные ключевые данные, существование ссылок на Evidence/объекты, допустимые диапазоны, соответствие текущей операции и отсутствие очевидного обрыва/зацикливания. Формально валидный, но недопустимо пустой результат отклоняется.»

ALLOWED_FILES: `src/core/llm/semantic_validator.py`, `tests/core/llm/test_semantic_validator.py`.

FORBIDDEN: Использование LLM для семантической валидации. Изменение доменных моделей. Запись в БД.

IMPLEMENTATION DETAILS:

- Создать `SemanticValidator`. Метод `validate(data: dict | list, schema_name: str, study_id: str) -> SemanticValidationResult`.
- `SemanticValidationResult(valid: bool, errors: list[str])`.
- Проверки:
    - Обязательные ключевые данные не пусты: `question` для `ResearchGap`, `text` для `Evidence`, `query` для `SearchTaskDraft` не являются пустыми строками или строками из пробелов.
    - Допустимые диапазоны: `confidence` в [0.0, 1.0], `priority` >= 0, `tokens_used` >= 0.
    - Соответствие текущей операции: `material_type` соответствует ожидаемому типу для данного вызова.
    - Отсутствие очевидного обрыва: текст не заканчивается на неполном слове/предложении (эвристика: последний символ не буква/цифра/знак препинания).
    - Отсутствие зацикливания: повторение одного и того же объекта более 3 раз в списке → ошибка.
- Формально валидный, но недопустимо пустой результат отклоняется (например, `ResearchPlan` с нулевым списком задач).
- Проверка не определяет истинность утверждений — только структурную и содержательную полноту.

TESTS:

- Тест: валидный объект проходит семантическую валидацию.
- Тест: `ResearchGap` с пустым `question` → ошибка.
- Тест: `confidence = 1.5` → ошибка (вне диапазона).
- Тест: `confidence = -0.1` → ошибка (вне диапазона).
- Тест: пустой `ResearchPlan` (ноль задач) → ошибка.
- Тест: текст, обрывающийся на неполном слове → ошибка.
- Тест: список из 5 одинаковых объектов → ошибка зацикливания.
- Тест: `tokens_used = -1` → ошибка.

ACCEPTANCE: Семантическая валидация отклоняет формально валидные, но содержательно пустые или некорректные результаты. Не использует LLM.

STOP_CONDITIONS: Если доменные модели не предоставляют информацию о допустимых диапазонах → STOP → REPORT.

---

## Gate G-06 Acceptance Criteria

- Код реализован: Все компоненты `LLM Integration` написаны и интегрированы.
- Тесты проходят: Unit и Integration тесты зеленые.
- CPU-only: Ни одна зависимость не требует GPU. Только stdlib + pytest.
- Безопасность: Sanitizer работает. Prompt-injection снижена. `eval`/`exec` не используются.
- JSON pipeline: Parse → Repair → Validate → Semantic Validate → Map работает с FakeLLMBackend.
- Разграничение ремонта: Ремонт промежуточных объектов разрешён. Ремонт финального отчёта запрещён.
- Контекстный бюджет: `TokenBudgetManager` реализует формулу, три режима, распределение квот. `ConfigContextInsufficientError` обработан.
- Семантическая валидация: Формально валидные, но пустые результаты отклоняются.
- Два бэкенда: `LMStudioAdapter` и `OllamaAdapter` реализованы.
- Маппер плана: Поля `exclusions` и `expected_material_type` извлекаются.
- Маппер пробелов: Поле `priority` обрабатывается.
- Факт восстановления: `was_repaired` фиксируется в `ValidationResult`.
- Core Authority: LLM только предлагает. Core валидирует, отклоняет, сохраняет.
- Сквозной сценарий: `LLM Failure / Recovery` с участием `ResearchSession` проходит.
- Коды ошибок: `LLM_UNREACHABLE`, `LLM_TIMEOUT`, `LLM_DEGRADED`, `CONFIG_CONTEXT_INSUFFICIENT` обработаны.
- Health FSM: Строго соответствует STATE MACHINE SPECIFICATION v1.1. Не влияет на `budget_state`.
- FSM инвариантность: Ни один тест не использует прямое присваивание `.status`.
- Изоляция: Тесты используют `tmp_path`, не требуют сети и реальной LLM.
- Scope: Не добавлено новых сущностей в БД, не изменены контракты MCP, не изменён GUI.
- Область видимости Router: `Health Monitor` реализован. `LLM Controller`, `Backend Router` — Post-MVP. `Session Resume` — EPIC-09.
- Constrained decoding: Post-MVP. Интерфейс `LLMBackend.generate()` зарезервирован через `response_format`.

Статус EPIC-06: Готов к передаче в разработку.