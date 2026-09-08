# EPIC-05 — RESEARCH ENGINE. TASK BATCH v1.1

Статус: Готов к передаче CODE-агентам.
Зависимости: EPIC-01 (Foundation), EPIC-02 (Data Layer), EPIC-03 (State Machines), EPIC-04 (Search Core).
Цель EPIC: Реализовать Core-оркестрацию исследовательского цикла. Управляемый переход от `ResearchIntent` к финальному отчету через итеративный поиск, извлечение доказательств, оценку достаточности и контроль бюджета.
Gate G-05: Mock-LLM end-to-end цикл `intent → plan → tasks → retrieval → evidence → gap → next task → sufficiency → finalize` проходит. Решение о завершении принимает исключительно Core.

---

## Общие инварианты и запреты для всех задач EPIC-05

ALLOWED_FILES (глобально для EPIC):

- `src/core/research_engine/` (новая директория для оркестратора)
- `src/core/models/` (только чтение/расширение доменных моделей, если не нарушает EPIC-02)
- `tests/core/research_engine/`
- `tests/fixtures/` (добавление mock-LLM и fake-адаптеров для тестов)

FORBIDDEN (глобально для EPIC):

- Прямое изменение `status` у `Study`, `ResearchSession`, `SearchTask` (только через команды/триггеры FSM из EPIC-03).
- Изменение схемы SQLite, миграций или DB-write layer (EPIC-02).
- Изменение контрактов MCP (EPIC-07) или GUI (EPIC-08).
- Использование реальной сети или реальной LLM в тестах.
- Прямой вызов сетевых адаптеров в обход `Search Core` (EPIC-04).
- Смешивание команд FSM и состояний FSM.

Глобальное правило идентификации операций:

- Каждая создаваемая сущность (`SearchTask`, `ResearchGap`, `Contradiction`, `SufficiencyEvaluation`, `Claim`) обязана содержать ссылку на `operation_id` операции, которая её создала.
- Каждая операция, создающая сущность, обязана формировать `idempotency_key` для предотвращения дублей при повторном вызове.
- При восстановлении после сбоя (`SESSION_RESUMING`) ядро проверяет `idempotency_key` для предотвращения дублирования.

---

## TASK-05-01: ResearchIntent & ResearchConfig Validation

GOAL: Реализовать валидацию входящего `ResearchIntent` и инициализацию `ResearchConfig` для нового исследования.

CONTEXT: Исследование начинается с вопроса пользователя. Core должен преобразовать его в строгий `ResearchIntent` и загрузить/проверить `ResearchConfig`.

ALLOWED_FILES: `src/core/research_engine/intent_validator.py`, `src/core/research_engine/config_loader.py`, `tests/core/research_engine/test_intent_config.py`.

FORBIDDEN: Изменение таблиц БД, создание FSM-переходов.

IMPLEMENTATION DETAILS:

- Создать класс `IntentValidator`. Метод `validate(intent: ResearchIntent) -> bool`.
- Проверить заполненность обязательных полей:
    - `goal` (Enum: SELECT, COMPARE, ESTIMATE, EXPLAIN, DISCOVER, REVIEW, SUMMARIZE, EVALUATE, IDENTIFY)
    - `target_entities` (Enum/Справочник: PRODUCT, PERSON, ORGANIZATION, METHOD, TECHNOLOGY, PAPER, MEDICAL_INTERVENTION, EVENT, SOFTWARE)
    - `information_needs` (PRICE, PERFORMANCE, USER_EXPERIENCE, RELIABILITY, MECHANISM, CLINICAL_EVIDENCE, EXPERIMENTAL_STATUS, ADVANTAGES, LIMITATIONS, FREQUENCY, TREND, CONTRADICTION)
    - `constraints` (DATE_RANGE, GEOGRAPHY, LANGUAGE, BUDGET_LIMITS, PRODUCT_TYPE, TECHNICAL_REQUIREMENTS, EXCLUDE_TERMS)
    - `source_preferences` (USER_REVIEWS, OFFICIAL_SOURCES, ACADEMIC, CLINICAL, PRIMARY_RESEARCH, TECHNICAL_DOCUMENTATION)
    - `analysis_strategy` (REVIEW_AGGREGATION, EVIDENCE_SYNTHESIS, COMPARISON, RANKING, TREND_ANALYSIS, FACT_FINDING, TECHNICAL_ANALYSIS)
    - `output_requirements` (RANKED_LIST, STATISTICS, SHORT_SUMMARY, EVIDENCE_TABLE, COMPARISON_TABLE, RESEARCH_GAPS, CONFIDENCE_SCORE)
- При повторной валидации того же `study_id` проверять инкремент поля `version`.
- Создать класс `ResearchConfigLoader`. Метод `load_or_create(study_id, config_data) -> ResearchConfig`.
- Валидация `ResearchConfig`: проверка диапазонов для `budget_limits`, `threshold_settings`, `timeout_settings`.
- При ошибке валидации выбрасывать `DomainValidationError` (из EPIC-01).

TESTS:

- Тест успешной валидации полного `ResearchIntent` со всеми семью обязательными полями.
- Тест отбрасывания `ResearchIntent` с пустым `goal` или невалидным Enum.
- Тест отбрасывания `ResearchIntent` с пустым `information_needs`.
- Тест отбрасывания `ResearchIntent` с пустым `output_requirements`.
- Тест загрузки дефолтного `ResearchConfig` при отсутствии пользовательского.
- Тест отклонения `ResearchConfig` с отрицательным бюджетом.
- Тест инкремента `version` при повторной валидации.

ACCEPTANCE: Все тесты проходят. Валидатор не пропускает некорректные данные. Все семь полей `ResearchIntent` проверяются.

STOP_CONDITIONS: Если требуется изменение структуры `ResearchIntent` из EPIC-02 → STOP → REPORT.

---

## TASK-05-02: Research Plan Representation & Drafting

GOAL: Реализовать структуру `ResearchPlan` и механизм его формирования (Draft Plan) на основе `ResearchIntent`.

CONTEXT: План состоит из набора `SearchTaskDraft`. В EPIC-05 Core принимает предложения от LLM (в тестах — от Mock-LLM) и нормализует их.

ALLOWED_FILES: `src/core/research_engine/plan.py`, `tests/core/research_engine/test_plan.py`.

FORBIDDEN: Создание реальных `SearchTask` в БД (это делает TASK-05-03).

IMPLEMENTATION DETAILS:

- Определить dataclass `SearchTaskDraft` со следующими полями:
    - `query: str`
    - `purpose: str`
    - `source_scope: str`
    - `filters: str`
    - `exclusions: str`
    - `expected_material_type: str`
    - `priority: int`
- Определить dataclass `ResearchPlan` (study_id, list[SearchTaskDraft], created_at).
- Реализовать `PlanNormalizer.normalize(llm_proposed_tasks) -> ResearchPlan`.
- Нормализация включает: очистку query, приведение source_scope к Enum, установку дефолтных приоритетов, валидацию наличия `exclusions` и `expected_material_type`.
- Обеспечить, что все поля `SearchTaskDraft` достаточны для расчёта `query_fingerprint` по формуле:

        query_fingerprint = SHA256(
            normalized_query_text +
            source_scope +
            task_purpose +
            applied_filters +
            exclusion_terms +
            time_range_constraint +
            geography_constraint +
            expected_material_type
        )

TESTS:

- Тест нормализации сырого списка задач от Mock-LLM в валидный `ResearchPlan`.
- Тест отбрасывания задач с пустым `query`.
- Тест отбрасывания задач с пустым `exclusions`.
- Тест отбрасывания задач с пустым `expected_material_type`.
- Тест сериализации/десериализации `ResearchPlan`.

ACCEPTANCE: `ResearchPlan` корректно формируется и сериализуется/десериализуется. Все поля для `query_fingerprint` присутствуют.

STOP_CONDITIONS: Если структура `SearchTaskDraft` противоречит EPIC-02 → STOP → REPORT.

---

## TASK-05-03: Core Task Acceptance & Duplicate/Similarity Check

GOAL: Реализовать механизм принятия `SearchTaskDraft` в исполнение с проверкой на дубликаты, сходство и бюджет через `query_fingerprint`.

CONTEXT: Новые задачи создаются только после проверки Core. Используется `query_fingerprint` из EPIC-04.

ALLOWED_FILES: `src/core/research_engine/task_acceptor.py`, `tests/core/research_engine/test_task_acceptor.py`.

FORBIDDEN: Прямая запись в БД в обход DB-write layer. Прямое присваивание `SearchTask.status = QUEUED`.

IMPLEMENTATION DETAILS:

- Создать `TaskAcceptor`. Метод `accept(study_id, draft: SearchTaskDraft, operation_id) -> SearchTask`.
- Вычислить `query_fingerprint` (через интерфейс из EPIC-04).
- Проверить `query_fingerprint` на наличие в БД (Exact Match).
- Проверить сходство запроса (Similarity Match) через `QuerySimilarityProvider` (EPIC-04). Порог сходства из `ResearchConfig.threshold_settings.query_similarity_threshold`.
- Проверить покрытие (Coverage Match) через `CoverageCalculator` (EPIC-04).
- Проверить доступность бюджета для данной операции (Budget Check). Если соответствующий компонент бюджета равен нулю — отклонить.
- Если все проверки пройдены: создать `SearchTask` через DB-write layer со статусом `CREATED`, привязать `operation_id` и `idempotency_key`, затем отправить команду `VALIDATE_TASK` (FSM EPIC-03) для перехода в `QUEUED`.
- Если проверка провалена: вернуть статус отклонения:
    - `REJECTED_DUPLICATE` (Exact Match)
    - `REJECTED_SIMILAR` (Similarity Match)
    - `REJECTED_COVERAGE` (Coverage Match)
    - `REJECTED_BUDGET` (Budget Check)
- При отклонении вернуть детерминированную причину отказа и рекомендуемое направление модификации.

TESTS:

- Тест успешного принятия уникальной задачи (переход CREATED → QUEUED).
- Тест отклонения точного дубликата (REJECTED_DUPLICATE).
- Тест отклонения похожей задачи (REJECTED_SIMILAR).
- Тест отклонения задачи, покрывающей уже закрытый gap (REJECTED_COVERAGE).
- Тест отклонения задачи при нулевом бюджете (REJECTED_BUDGET).
- Тест наличия `operation_id` и `idempotency_key` у созданной задачи.

ACCEPTANCE: Задачи создаются только после прохождения всех фильтров. FSM переводится строго через команды. Четыре типа отклонения работают.

STOP_CONDITIONS: Если алгоритм fingerprint не доступен из EPIC-04 → STOP → REPORT.

---

## TASK-05-04: SearchTask Execution Loop & Iteration State

GOAL: Реализовать цикл выполнения поисковых задач и управление итерациями `ResearchSession`.

CONTEXT: Core должен запускать задачи, ждать результатов и обновлять состояние сессии.

ALLOWED_FILES: `src/core/research_engine/execution_loop.py`, `tests/core/research_engine/test_execution_loop.py`.

FORBIDDEN: Блокировка main thread. Прямое изменение `ResearchSession.status`.

IMPLEMENTATION DETAILS:

- Создать `ExecutionLoop`. Метод `run_iteration(session_id, tasks: list[SearchTask])`.
- Для каждой задачи отправить команду `TASK_STARTED` (FSM).
- Вызвать `Search Core` (EPIC-04) для выполнения задачи (ретривал, парсинг, чанкинг).
- По завершении отправить команду `RESULTS_SAVED` (FSM).
- Обновить `ResearchSession.iteration` через DB-write layer.
- Обработать ошибки выполнения: отправить `EXECUTION_ERROR` (FSM), не прерывая весь цикл, если ошибка не критическая.
- Определить условие завершения итерации: все задачи батча достигли терминального состояния (`COMPLETED`, `FAILED`, `CANCELLED`).
- Каждая создаваемая сущность в рамках итерации привязывается к `operation_id`.

TESTS:

- Тест успешного выполнения батча задач (переходы QUEUED → RUNNING → COMPLETED).
- Тест обработки сбоя одной задачи (переход в FAILED, цикл продолжается).
- Тест обновления номера итерации в `ResearchSession`.
- Тест определения завершения итерации при достижении всеми задачами терминального состояния.

ACCEPTANCE: Цикл выполняет задачи, корректно реагирует на ошибки, обновляет итерации, определяет завершение батча.

STOP_CONDITIONS: Если `Search Core` не предоставляет интерфейс для синхронного/асинхронного запуска → STOP → REPORT.

---

## TASK-05-05: Coverage & Sufficiency Integration

GOAL: Интегрировать `CoverageCalculator` и `SufficiencyEvaluator` в цикл исследования для принятия решения о продолжении/остановке.

CONTEXT: После каждой итерации Core должен оценивать, достаточно ли данных. Решение принимает исключительно детерминированный модуль ядра.

ALLOWED_FILES: `src/core/research_engine/sufficiency_controller.py`, `tests/core/research_engine/test_sufficiency.py`.

FORBIDDEN: Использование LLM для принятия решения о достаточности.

IMPLEMENTATION DETAILS:

- Создать `SufficiencyController`. Метод `evaluate_and_decide(study_id, iteration) -> SufficiencyDecision`.
- Вызвать `CoverageCalculator` (EPIC-04) для получения шести входных метрик:
    - `independent_source_count` — число независимых источников
    - `attribute_coverage` — покрытие целевых характеристик
    - `question_coverage` — покрытие информационных потребностей
    - `information_gain` — дельта прироста за последнюю итерацию
    - `evidence_count` — число верифицированных доказательств
    - `contradiction_count` — число неразрешённых противоречий
- Передать метрики в `SufficiencyEvaluator` (EPIC-04).
- Получить одно из ПЯТИ решений:
    - `CONTINUE`
    - `STOP_SUFFICIENT`
    - `STOP_BUDGET`
    - `STOP_NO_INFORMATION_GAIN`
    - `STOP_NO_AVAILABLE_SOURCES`
- При получении `STOP_BUDGET`: инициировать отправку команды `BUDGET_ZERO` в Study FSM.
- Записать результат в `SufficiencyEvaluation` (EPIC-02) через DB-write layer, привязать `operation_id`.
- Вернуть решение оркестратору вместе со структурированным обоснованием (список сработавших правил).

TESTS:

- Тест принятия решения `CONTINUE` при низком покрытии.
- Тест принятия решения `STOP_SUFFICIENT` при достижении порогов.
- Тест принятия решения `STOP_BUDGET` при исчерпании лимита.
- Тест принятия решения `STOP_NO_INFORMATION_GAIN` при падении дельты ниже 5%.
- Тест принятия решения `STOP_NO_AVAILABLE_SOURCES` при тотальной недоступности.
- Тест сохранения `SufficiencyEvaluation` в БД с полным набором метрик.

ACCEPTANCE: Решения принимаются детерминированно по пяти статусам, логируются в БД с обоснованием, LLM не участвует.

STOP_CONDITIONS: Если `SufficiencyEvaluator` из EPIC-04 не возвращает ожидаемый Enum из пяти значений → STOP → REPORT.

---

## TASK-05-06: ResearchGap Lifecycle & Targeted Query Generation

GOAL: Реализовать управление жизненным циклом `ResearchGap` и механизм генерации целевых запросов на их основе.

CONTEXT: Новые поисковые циклы легитимны только при наличии открытых `ResearchGap`.

ALLOWED_FILES: `src/core/research_engine/gap_manager.py`, `tests/core/research_engine/test_gap_manager.py`.

FORBIDDEN: Создание `SearchTask` напрямую из текста LLM без привязки к `ResearchGap`.

IMPLEMENTATION DETAILS:

- Создать `GapManager`. Методы: `register_gap(...)`, `close_gap(gap_id)`, `exhaust_gap(gap_id)`, `get_open_gaps(study_id)`.
- `register_gap`: валидация полей (`question`, `reason`, `missing_evidence`, `recommended_query`, `priority`), запись в БД (статус `OPEN`), привязка `operation_id`.
- Поддерживать три статуса жизненного цикла:
    - `OPEN` — пробел активен, требует закрытия
    - `CLOSED` — пробел успешно закрыт
    - `EXHAUSTED` — все попытки закрыть пробел исчерпаны (например, исчерпан `step_budget` для данного gap или N неудачных попыток)
- Определить условия перехода `OPEN → EXHAUSTED`: количество неудачных попыток закрытия превышает порог из `ResearchConfig.threshold_settings`.
- При генерации нового `SearchTaskDraft` (в mock-LLM или оркестраторе) требовать привязки к `gap_id`.
- При успешном закрытии потребности: обновить статус `ResearchGap` на `CLOSED`.
- Для сценария низкой независимости: создавать `ResearchGap` с `reason = LOW_INDEPENDENCE` и выставлять статус достоверности `INSUFFICIENT_EVIDENCE` для связанных утверждений.
- Обеспечить защиту от создания дублей gap (проверка по хэшу `question` + `study_id`).

TESTS:

- Тест регистрации и сохранения `ResearchGap` со статусом `OPEN`.
- Тест отклонения дублирующего gap.
- Тест закрытия gap (`OPEN → CLOSED`) и проверки, что он не возвращается в `get_open_gaps`.
- Тест исчерпания gap (`OPEN → EXHAUSTED`) после N неудачных попыток.
- Тест создания gap с `reason = LOW_INDEPENDENCE`.
- Тест наличия `operation_id` у созданного gap.

ACCEPTANCE: Gap'ы строго учитываются, дубли блокируются, три статуса жизненного цикла работают, сценарий низкой независимости обрабатывается.

STOP_CONDITIONS: Если структура `ResearchGap` в EPIC-02 не поддерживает требуемые поля → STOP → REPORT.

---

## TASK-05-07: Budget Control & Completion Decision

GOAL: Реализовать контроль многомерного бюджета и инициирование переходов FSM при его исчерпании.

CONTEXT: Бюджет контролируется исключительно Core. При исчерпании исследование должно переходить в состояние финализации.

ALLOWED_FILES: `src/core/research_engine/budget_orchestrator.py`, `tests/core/research_engine/test_budget_orchestrator.py`.

FORBIDDEN: Прямое изменение `Study.status = BUDGET_EXHAUSTED`.

IMPLEMENTATION DETAILS:

- Создать `BudgetOrchestrator`. Метод `check_and_deduct(study_id, operation_type)`.
- Реализовать явный маппинг типов операций на компоненты бюджета:
    - `SEARCH_QUERY` → `network_budget`
    - `FETCH_PAGE` → `fetch_budget`
    - `MCP_TOOL_CALL` → `tool_call_budget`
    - `LLM_CALL` → `llm_call_budget`
    - `LLM_TOKENS` → `llm_token_budget`
    - `ITERATION` → `step_budget`
    - `TIME_ELAPSED` → `time_budget`
- Перед операцией проверить остаток соответствующего компонента бюджета через интерфейс EPIC-04.
- Если бюджет > 0: списать атомарно (через DB-write layer EPIC-04) в рамках единой транзакции SQLite.
- Если бюджет == 0: отправить команду `BUDGET_ZERO` в Study FSM (EPIC-03).
- Обработать переход `BUDGET_EXHAUSTED` → `FREEZE_BUDGET_EXHAUSTED` (через команду `BUDGET_FREEZE`).
- Реализовать метод `request_budget_extension(study_id, user_action)` для команды `BUDGET_EXTENDED`.
- Расширение бюджета допускается только по явному действию пользователя через GUI с фиксацией в `ResearchConfig`.
- Текущее состояние бюджета сохраняется в `ResearchSession.budget_state`, лимиты — в `ResearchConfig.budget_limits`.

TESTS:

- Тест успешного списания бюджета для каждого из семи типов операций.
- Тест блокировки операции при нулевом бюджете и отправки `BUDGET_ZERO`.
- Тест перехода Study в `FREEZE_BUDGET_EXHAUSTED`.
- Тест расширения бюджета и возврата в `RUNNING`.
- Тест атомарности списания (единая транзакция).
- Тест независимого контроля каждого из семи компонентов.

ACCEPTANCE: Бюджет списывается атомарно по семи компонентам, FSM переводится строго через команды, блокировки работают, расширение только через явное действие.

STOP_CONDITIONS: Если атомарное списание в EPIC-04 не гарантировано → STOP → REPORT.

---

## TASK-05-08: MATERIALS_ONLY & EXPAND Modes

GOAL: Реализовать логику переключения и контроля режимов `MATERIALS_ONLY` и `EXPAND`.

CONTEXT: Режимы меняют поведение поискового ядра и оркестратора.

ALLOWED_FILES: `src/core/research_engine/mode_controller.py`, `tests/core/research_engine/test_modes.py`.

FORBIDDEN: Изменение контрактов `SourceAdapter` (EPIC-04).

IMPLEMENTATION DETAILS:

- Создать `ModeController`.
- Для `MATERIALS_ONLY`:
    - Заблокировать любые вызовы внешних `SourceAdapter` (web, academic, github, stackoverflow, community).
    - Разрешить только локальный поиск по `StudyDocumentLink`.
    - Блокировка реализуется на уровне `ModeController`: проверка режима перед вызовом `ExecutionLoop`, возврат детерминированной ошибки при попытке сетевого вызова.
- Для `EXPAND`:
    - Локальный этап: сканирование, индексация и BM25-поиск по всем материалам прошлых исследований.
    - Аналитический этап: анализ полноты, выявление точечных пробелов.
    - Сетевой этап: разрешён строго и исключительно для закрытия конкретных выявленных пробелов.
    - Блокировка повторного сбора информации, уже присутствующей в локальном репозитории.
- Интегрировать проверки в `ExecutionLoop` (TASK-05-04) перед вызовом `Search Core`.
- Каждая операция в режиме `MATERIALS_ONLY` не списывает `network_budget` и `fetch_budget`.

TESTS:

- Тест `MATERIALS_ONLY`: попытка вызвать web-адаптер возвращает ошибку/блокируется.
- Тест `MATERIALS_ONLY`: локальный поиск работает корректно.
- Тест `EXPAND`: сетевой запрос блокируется, если локальные материалы закрывают gap.
- Тест `EXPAND`: сетевой запрос разрешен, если gap открыт и не закрыт локальными данными.
- Тест `EXPAND`: повторный сбор уже имеющихся данных блокируется.

ACCEPTANCE: Режимы строго соблюдают ограничения на сетевую активность. `MATERIALS_ONLY` физически не допускает сетевых вызовов.

STOP_CONDITIONS: Если `Search Core` не предоставляет флаг изоляции сети → STOP → REPORT.

---

## TASK-05-09: Primary-Source Search & Contradiction Pipeline

GOAL: Реализовать оркестрацию поиска первоисточников и детерминированного выявления противоречий.

CONTEXT: Core должен автоматически запускать доп. задачи для поиска primary source и сверять `numeric_signatures`.

ALLOWED_FILES: `src/core/research_engine/primary_source_tracker.py`, `src/core/research_engine/contradiction_detector.py`, `tests/core/research_engine/test_pipeline.py`.

FORBIDDEN: Использование LLM для первичного поиска числовых противоречий.

IMPLEMENTATION DETAILS:

- `PrimarySourceTracker`:
    - При извлечении Evidence из вторичного источника создавать `ResearchGap` с `reason = PRIMARY_SOURCE_REQUIRED`. Генерировать `SearchTaskDraft` для поиска оригинала.
    - По результатам выполнения задачи поиска первоисточника фиксировать один из трёх статусов:
        - `PRIMARY_FOUND` — первоисточник найден, скачан, связан реляционной ссылкой
        - `PRIMARY_UNAVAILABLE` — идентифицирован, но доступ заблокирован (paywall, 403)
        - `PRIMARY_NOT_IDENTIFIED` — невозможно точно идентифицировать документ-источник
    - Хранить `provenance_status` в метаданных связанного `Evidence`.
    - Статус происхождения напрямую влияет на итоговый `confidence` утверждения в отчёте.
- `ContradictionDetector`:
    - После каждой итерации сканировать `numeric_signatures` в `DocumentChunk` (EPIC-02/04).
    - Правила сравнения: только записи с одинаковыми `type` и `unit`. Сравнение детерминированное, без LLM.
    - При нахождении расхождений создавать сущность `Contradiction` (статус `DETECTED`), привязать `operation_id`.
    - Определить структуру `ContradictionCandidate`:
        - `chunk_a_id`, `chunk_b_id`
        - `value_a`, `value_b`, `unit`, `type`
        - `evidence_a_id`, `evidence_b_id`
        - `contradiction_type` (NUMERIC, TEMPORAL, FACTUAL, METHODOLOGICAL)
    - Передать список `ContradictionCandidate` в LLM-слой для семантического подтверждения через интерфейс `save_study_material` с `material_type = CONTRADICTION`.
    - LLM привлекается только для семантического подтверждения на втором этапе, не для первичного обнаружения.

TESTS:

- Тест создания gap для поиска первоисточника.
- Тест фиксации статуса `PRIMARY_FOUND` при успешном нахождении.
- Тест фиксации статуса `PRIMARY_UNAVAILABLE` при блокировке доступа.
- Тест фиксации статуса `PRIMARY_NOT_IDENTIFIED` при невозможности идентификации.
- Тест обнаружения числового противоречия (разные цены) по `numeric_signatures`.
- Тест отсутствия противоречий при совпадающих данных.
- Тест корректной структуры `ContradictionCandidate`.
- Тест, что детерминированный этап не вызывает LLM.

ACCEPTANCE: Первичные источники отслеживаются с тремя статусами, числовые противоречия выявляются детерминированно, семантический этап отделён.

STOP_CONDITIONS: Если `numeric_signatures` не сохраняются в EPIC-04 → STOP → REPORT.

---

## TASK-05-10: Aggregation & Evidence Modes

GOAL: Настроить веса и правила валидации в зависимости от `analysis_strategy` (REVIEW_AGGREGATION vs EVIDENCE_SYNTHESIS).

CONTEXT: Режимы влияют на то, как Core оценивает качество данных и формирует Claims.

ALLOWED_FILES: `src/core/research_engine/strategy_adapter.py`, `tests/core/research_engine/test_strategies.py`.

FORBIDDEN: Изменение базовых таблиц Evidence/Claim.

IMPLEMENTATION DETAILS:

- Создать `StrategyAdapter`.
- Для `REVIEW_AGGREGATION` реализовать полную цепочку валидации:
    - Проверка, что `Observation` ссылается на валидный `Evidence` (`Observation.evidence_id` → `Evidence` существует).
    - Проверка, что `Evidence` ссылается на валидный `Document` (`Evidence.document_id` → `Document` существует).
    - Проверка, что `Document` ссылается на валидный `Source` (`Document.source_id` → `Source` существует).
    - Проверка уникальности `source_id` / автора в наборе наблюдений (один отзыв ≠ статистический факт).
    - Требование наличия `Entity` и `Observation` перед созданием `Claim`.
    - Для формирования `Claim` требуется `count > 1` уникальных наблюдений.
    - Расчёт математических величин (count, ratio, percentage, mean, median) только на основе верифицированных уникальных авторов.
- Для `EVIDENCE_SYNTHESIS`:
    - Требовать жесткой привязки к `Source` с высоким `quality_profile`.
    - Проверять шкалу достоверности: ESTABLISHED, SUPPORTED, PROMISING, EXPERIMENTAL, CONTRADICTED, UNKNOWN.
    - Классификация базируется на типе источника и его авторитетности.
- Интегрировать адаптер в процесс валидации сохраняемых материалов (перед записью в БД).
- Каждая создаваемая сущность привязывается к `operation_id`.

TESTS:

- Тест отклонения `Claim` в режиме агрегации без привязки к `Observation`.
- Тест отклонения `Claim` в режиме агрегации при единственном наблюдении (count = 1).
- Тест отклонения `Claim` при отсутствии ссылки `Evidence` → `Document`.
- Тест отклонения `Claim` при отсутствии ссылки `Document` → `Source`.
- Тест корректной агрегации при наличии нескольких уникальных авторов.
- Тест отклонения `Claim` в режиме доказательств, если источник имеет низкий `quality_profile`.
- Тест корректного применения шкалы достоверности в режиме доказательств.

ACCEPTANCE: Стратегии применяют специфичные правила валидации. Полная реляционная цепочка проверяется в режиме агрегации.

STOP_CONDITIONS: Если `quality_profile` не рассчитывается в EPIC-04 → STOP → REPORT.

---

## TASK-05-11: Partial & Final Finalization & Report Handoff

GOAL: Реализовать процедуру финализации исследования, включая частичные отчеты и передачу данных в LLM.

CONTEXT: Завершение исследования требует строгого FSM-перехода и подготовки компактного контекста.

ALLOWED_FILES: `src/core/research_engine/finalizer.py`, `tests/core/research_engine/test_finalizer.py`.

FORBIDDEN: Прямое присваивание `Study.status = COMPLETED`. Тихая правка отчета.

IMPLEMENTATION DETAILS:

- Создать `Finalizer`. Метод `initiate_finalization(study_id, trigger)`.
- Отправить команду `STOP_SUFFICIENT` / `SOFT_STOP` / `FINALIZE_PARTIAL` в Study FSM.
- Собрать компактный контекст для отчета: валидные `Claim`, `Evidence`, `Contradiction`, `ResearchGap`.
- Если произошел сбой до финализации:
    - Пометить результат как `REPORT_TRUNCATED_PARTIAL` (metadata, не состояние).
    - Сформировать перечень недостающих элементов через метод `get_missing_elements(study_id) -> list[str]`.
    - Перечень передаётся в промпт при догенерации для дописывания только отсутствующих элементов.
- Подготовить данные для `validate_and_save_report` (MCP EPIC-07).
- Проверить, что в контекст не попали сырые HTML, полные страницы или длинные логи.
- Привязать `operation_id` к операции финализации.

TESTS:

- Тест успешной финализации (переход в FINALIZING).
- Тест частичной финализации при сбое (сохранение валидных данных, метаданные partial).
- Тест формирования перечня недостающих элементов при `REPORT_TRUNCATED_PARTIAL`.
- Тест сборки компактного контекста (проверка, что сырой HTML не попал в контекст).
- Тест, что `REPORT_TRUNCATED_PARTIAL` не является состоянием Study.

ACCEPTANCE: FSM переводится корректно, контекст для отчета компактен и валиден, перечень недостающих элементов формируется.

STOP_CONDITIONS: Если FSM не поддерживает триггер `FINALIZE_PARTIAL` → STOP → REPORT.

---

## TASK-05-12: Mock-LLM End-to-End Research Loop Test

GOAL: Создать комплексный интеграционный тест полного цикла исследования с использованием Mock-LLM и FakeSourceAdapter.

CONTEXT: Gate G-05 требует подтверждения работоспособности всего цикла без реальной сети и LLM.

ALLOWED_FILES: `tests/integration/test_e2e_research_loop.py`, `tests/fixtures/mock_llm.py`, `tests/fixtures/fake_adapter.py`.

FORBIDDEN: Использование реальной сети. Изменение production кода.

IMPLEMENTATION DETAILS:

- Настроить `tmp_path` для изолированной БД.
- Инициализировать `ResearchEngine` с `MockLLM` (возвращает предзаданные `ResearchPlan`, `Observation`, `ResearchGap`) и `FakeSourceAdapter` (возвращает записанные HTML/тексты).
- Запустить цикл: `intent → plan → tasks → retrieval → evidence → gap → next task → sufficiency → finalize`.
- Проверить, что `SufficiencyEvaluator` в итоге вернул `STOP_SUFFICIENT`.
- Проверить, что `Study.status` перешел в `FINALIZING`, а затем в `COMPLETED`.
- Проверить полноту `LogRecord` для каждого FSM-перехода:
    - Каждый `LogRecord` содержит все 7 обязательных полей: `entity_type`, `entity_id`, `from_state`, `to_state`, `trigger`, `component`, `timestamp`.
    - Количество записей `LogRecord` соответствует количеству фактических переходов.

TESTS:

- `test_e2e_happy_path`: полный успешный цикл.
- Проверка отсутствия дублей `SearchTask`.
- Проверка корректного списания бюджета.
- Проверка полноты и корректности `LogRecord` для каждого перехода.

ACCEPTANCE: Тест проходит полностью, все FSM-переходы зафиксированы в `LogRecord` с 7 полями, БД консистентна.

STOP_CONDITIONS: Если для теста требуется мокирование более 3 слоев архитектуры → STOP → REPORT (упростить тест).

---

## TASK-05-13: Budget, Sufficiency & Recovery Integration Tests

GOAL: Покрыть тестами edge-cases: исчерпание бюджета, отсутствие информационного прироста, восстановление после сбоев.

CONTEXT: Система должна быть отказоустойчивой и строго соблюдать лимиты.

ALLOWED_FILES: `tests/integration/test_resilience_and_limits.py`.

FORBIDDEN: Изменение production кода.

IMPLEMENTATION DETAILS:

- `test_budget_exhaustion`: настроить `FakeSourceAdapter` так, чтобы бюджет закончился на 3-й итерации. Проверить переход в `FREEZE_BUDGET_EXHAUSTED` и генерацию partial report.
- `test_no_information_gain`: настроить адаптер так, чтобы все итерации возвращали одинаковый контент. Проверить срабатывание `STOP_NO_INFORMATION_GAIN`.
- `test_recovery_after_crash`: прервать выполнение на середине итерации через `pytest.raises` или принудительный вызов исключения в mock-объекте. Перезапустить `ResearchEngine` с той же БД. Проверить, что сессия перешла в `SESSION_RESUMING`, а затем в `ACTIVE`, и цикл продолжился без дублей.
- Проверка атомарности транзакций при сбое.
- Проверка, что `idempotency_key` предотвращает дублирование при восстановлении.

TESTS:

- Указанные выше сценарии.
- Проверка атомарности транзакций при сбое.
- Проверка отсутствия дублей после восстановления.

ACCEPTANCE: Все сценарии проходят, данные не теряются, FSM не нарушается, `idempotency_key` защищает от дублей.

STOP_CONDITIONS: Если механизм восстановления (checkpoint) не реализован в EPIC-02/03 → STOP → REPORT.

---

## Gate G-05 Acceptance Criteria

- Код реализован: Все компоненты `Research Engine` написаны и интегрированы.
- Тесты проходят: Unit и Integration тесты (включая E2E Mock-LLM) зеленые.
- FSM инвариантность: Ни один тест не использует прямое присваивание `.status`. Все переходы через команды.
- Core Authority: LLM (Mock) только предлагает. Core валидирует, списывает бюджет, принимает решения о stop/continue.
- Изоляция: Тесты используют `tmp_path`, не требуют сети и реальной LLM.
- Scope: Не добавлено новых сущностей в БД, не изменены контракты MCP.
- Идентификация: Все создаваемые сущности привязаны к `operation_id`.
- Бюджет: Все семь компонентов многомерного бюджета контролируются независимо.
- Достаточность: Пять решений `SufficiencyEvaluator` обрабатываются корректно.
- Первоисточники: Три статуса верификации происхождения фиксируются.

Статус EPIC-05: Готов к передаче в разработку.