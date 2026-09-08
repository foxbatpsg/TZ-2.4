# EPIC-10 — FINAL QA / ACCEPTANCE. TASK BATCH v1.1

Статус: Готов к передаче CODE-агентам.
Зависимости: формально по Dependency Matrix — EPIC-01…EPIC-09. Транзитивно — все предыдущие.
Цель EPIC: Финальное QA и приёмка. Систематическая проверка всех обязательных критериев ТЗ Раздел 7 на всех уровнях тестирования. Подтверждение отсутствия критических известных дефектов.
Уровни тестирования: Unit → Component → Integration → FSM → MCP Contract → E2E → Failure Scenarios → Acceptance.
Gate G-10: Все обязательные критерии ТЗ Раздел 7 выполнены; критических известных дефектов нет.

## Общие инварианты и запреты для всех задач EPIC-10

ALLOWED_FILES (глобально для EPIC):

- `src/qa/` (корневая директория для тестовой инфраструктуры)
- `src/qa/fixtures/` (golden datasets, фейковые адаптеры)
- `src/qa/registry.py`, `src/qa/harness.py`, `src/qa/faults.py`
- `src/qa/golden/` (golden documents, chunks, evidence, reports)
- `tests/qa/` (все тесты)
- `tests/qa/unit/`, `tests/qa/component/`, `tests/qa/integration/`
- `tests/qa/fsm/`, `tests/qa/mcp_contract/`, `tests/qa/e2e/`
- `tests/qa/failure/`, `tests/qa/acceptance/`
- `src/stability/` (стабилизация и релизная подготовка)
- `tests/stability/` (тесты стабилизации и приёмки)
- `src/cli/` (точка запуска)
- `docs/` (runbook, quickstart)

FORBIDDEN (глобально для EPIC):

- Использование реальной сети в тестах.
- Использование реальной LLM в тестах.
- Прямое изменение `status` у доменных сущностей.
- Изменение контрактов из предыдущих EPIC.
- Создание собственных портов, дублирующих реальные интерфейсы.
- Скрытие ошибок или пропуск критических проверок.

Глобальное правило тестирования:
Все автоматические тесты обязаны работать:

- Без доступа к сети Интернет.
- Без реальной локальной ИИ-модели.
- На детерминированных фикстурах и golden datasets.
- С изоляцией через `tmp_path`.

Обязательные компоненты тестовой инфраструктуры (ТЗ Раздел 7, Секция 28):

- `FakeSourceAdapter` — имитация сетевого адаптера.
- `FakeLLM` — имитация локальной ИИ-модели.
- `Recorded HTTP responses` — записанные ответы.
- `Golden documents` — эталонные документы.
- `Golden chunks` — эталонные наборы чанков.
- `Golden Evidence` — эталонные доказательства.
- `Golden Sufficiency decisions` — эталонные решения.
- `Golden reports` — эталонные отчёты.

---

## G1 — Тестовая инфраструктура и фикстуры

### TASK-10-01: Расширенный реестр тестовых сценариев

GOAL: Создать реестр сценариев, покрывающий все обязательные области из ТЗ Раздел 7 и Roadmap Раздел 13.

CONTEXT: ТЗ Раздел 7 определяет 28 секций тестирования. Реестр должен покрывать все обязательные области.

ALLOWED_FILES: `src/qa/registry.py`, `tests/qa/test_registry.py`.

FORBIDDEN: Выполнение сценариев. Сетевые вызовы. Реальная LLM.

IMPLEMENTATION DETAILS:

- `ScenarioSpec` содержит `id`, `title`, `tz_section`, `level`, `components`, `expected`, `severity`.
- Встроенный каталог покрывает все обязательные области:
    - `data_isolation` (ТЗ 7.2)
    - `query_planner` (ТЗ 7.3)
    - `url_normalization` (ТЗ 7.4)
    - `deduplication` (ТЗ 7.5)
    - `ranking` (ТЗ 7.6)
    - `bm25` (ТЗ 7.7)
    - `russian_morphology` (ТЗ 7.7.1)
    - `chunking` (ТЗ 7.8)
    - `evidence` (ТЗ 7.9)
    - `aggregation` (ТЗ 7.10)
    - `claims` (ТЗ 7.11)
    - `contradiction` (ТЗ 7.12)
    - `research_gap` (ТЗ 7.13)
    - `source_independence` (ТЗ 7.14)
    - `adaptive_search` (ТЗ 7.15)
    - `local_first` (ТЗ 7.16)
    - `cache` (ТЗ 7.17)
    - `db_write_layer` (ТЗ 7.18)
    - `mcp` (ТЗ 7.19)
    - `stdout_protection` (ТЗ 7.19.1)
    - `llm_resilience` (ТЗ 7.20)
    - `json_degradation` (ТЗ 7.21)
    - `gui` (ТЗ 7.22)
    - `cooperative_cancellation` (ТЗ 7.22.1)
    - `network_resilience` (ТЗ 7.23)
    - `security` (ТЗ 7.24)
    - `acceptance_criteria` (ТЗ 7.25)
    - `golden_datasets` (ТЗ 7.28)
- Реестр возвращает read-only структуры.

TESTS:

- `test_all_28_tz_sections_covered`
- `test_scenario_ids_are_unique`
- `test_levels_assigned_correctly`
- `test_specs_are_immutable`

ACCEPTANCE: Реестр покрывает все 28 секций ТЗ Раздел 7. Каждый сценарий привязан к уровню тестирования.

STOP_CONDITIONS: Если какая-либо секция ТЗ изменена — остановить задачу.

---

### TASK-10-02: Детерминированные фикстуры и golden datasets

GOAL: Создать обязательные компоненты тестовой инфраструктуры из ТЗ Раздел 7, Секция 28.

CONTEXT: Все тесты должны быть воспроизводимыми без сети и реальной LLM.

ALLOWED_FILES: `src/qa/fixtures/`, `src/qa/golden/`, `tests/qa/test_fixtures.py`.

FORBIDDEN: Сетевые вызовы. Реальная LLM. Не-детерминированные данные.

IMPLEMENTATION DETAILS:

- `FakeSourceAdapter`: имитация сетевого адаптера с предопределёнными результатами. Режимы: `ok`, `timeout`, `rate_limit`, `unavailable`, `parse_error`.
- `FakeLLM`: имитация локальной ИИ-модели с предопределёнными структурированными ответами. Режимы: `ok`, `invalid_json`, `truncated_json`, `empty`, `fail`.
- `Recorded HTTP responses`: набор записанных ответов для воспроизводимого тестирования обработки.
- `Golden documents`: минимум 5 эталонных документов с известным ожидаемым результатом чанкинга. Включая документы с вариациями русских словоформ.
- `Golden chunks`: эталонные наборы чанков с известными свойствами (`overlap_group_id`, `is_overlap`, `heading_path`).
- `Golden Evidence`: эталонные доказательства с известными связями и `evidence_hash`.
- `Golden Sufficiency decisions`: эталонные входные метрики с известным ожидаемым решением (все 5 типов решений).
- `Golden reports`: эталонные отчёты с известной структурой и связями.
- Все фикстуры версионируются и хранятся в репозитории.

TESTS:

- `test_fake_source_adapter_modes`
- `test_fake_llm_modes`
- `test_golden_documents_are_deterministic`
- `test_golden_chunks_have_correct_properties`
- `test_golden_evidence_hashes_are_correct`
- `test_golden_sufficiency_decisions_cover_all_types`
- `test_golden_reports_are_valid`

ACCEPTANCE: Все компоненты из ТЗ Раздел 7, Секция 28 реализованы. Данные детерминированы.

STOP_CONDITIONS: Если golden dataset не обеспечивает достаточного покрытия — расширить набор.

---

### TASK-10-03: Контрактный harness для реальных интерфейсов

GOAL: Реализовать контрактный тест, проверяющий реальные интерфейсы из исправленных EPIC-05…09.

CONTEXT: Все адаптеры и компоненты должны соблюдать контракты. Использовать реальные интерфейсы: `ResearchEngine`, `SearchCore`, `LLMBackend`, `MCPTransport`, `DB-write layer`, `FSM`. Имена интерфейсов не зафиксированы нормативно в ТЗ и требуют обязательной верификации по фактическим реализациям соответствующих EPIC до начала реализации задачи. При несовпадении имён задача останавливается.

ALLOWED_FILES: `src/qa/harness.py`, `tests/qa/test_harness.py`.

FORBIDDEN: Создание собственных портов. Сетевые вызовы. Реальная LLM.

IMPLEMENTATION DETAILS:

- `ContractHarness` проверяет реальные интерфейсы:
    - `ResearchEngine` (EPIC-05): `start()`, `run_iteration()`, `evaluate_sufficiency()`, `finalize()`.
    - `SearchCore` (EPIC-04): `execute_search()`, `fetch_document()`, `chunk_document()`, `index_chunks()`.
    - `LLMBackend` (EPIC-06): `generate()`, `health_check()`, `get_context_info()`.
    - `MCPTransport` (EPIC-07): `run()`, `invoke_tool()`.
    - `DB-write layer` (EPIC-02): `write()`, `read()`, `transaction()`.
    - `StudyFSM`, `ResearchSessionFSM`, `SearchTaskFSM` (EPIC-03): `transition()`, `current_state()`.
- Проверки: наличие методов, типы, обработка ошибок.
- В тестах использовать фейковые реализации.
- Результат: `ContractReport`.
- Перед реализацией верифицировать фактические имена интерфейсов по реализациям EPIC-02…EPIC-07. При несовпадении — остановка задачи.

TESTS:

- `test_research_engine_contract`
- `test_search_core_contract`
- `test_llm_backend_contract`
- `test_mcp_transport_contract`
- `test_db_write_layer_contract`
- `test_fsm_contracts`
- `test_missing_method_fails`

ACCEPTANCE: Все реальные интерфейсы проверены. Нет собственных портов.

STOP_CONDITIONS: Если интерфейс из предыдущего EPIC изменён — остановить задачу. Если фактическое имя класса или метода в реализации отличается от ожидаемого — остановить задачу и передать архитектору. Если `MCPTransport` в реализации EPIC-07 является встроенным в основное приложение (не отдельный класс) — адаптировать контракт через верификацию.

---

### TASK-10-04: Матрица управляемых отказов

GOAL: Реализовать детерминированные профили отказов для всех сценариев из ТЗ Раздел 7.

CONTEXT: Отказоустойчивость проверяется воспроизводимыми сценариями.

ALLOWED_FILES: `src/qa/faults.py`, `tests/qa/test_faults.py`.

FORBIDDEN: Реальные сбои ОС. Сеть. Реальная LLM.

IMPLEMENTATION DETAILS:

- Профили покрывают все сценарии из ТЗ:
    - `llm_unreachable` (ТЗ 7.20)
    - `llm_timeout` (ТЗ 7.20)
    - `llm_degraded` (ТЗ 7.20)
    - `llm_restart` (ТЗ 7.20)
    - `llm_switch` (ТЗ 7.20)
    - `network_timeout` (ТЗ 7.23)
    - `network_rate_limit` (ТЗ 7.23)
    - `source_unavailable` (ТЗ 7.23)
    - `parse_error` (ТЗ 7.23)
    - `invalid_json` (ТЗ 7.21)
    - `truncated_json` (ТЗ 7.21)
    - `db_corrupt` (ТЗ 7.18)
    - `settings_corrupt` (ТЗ Раздел 2, Секция 8 — Конфигурация)
    - `mcp_timeout` (ТЗ 7.19)
    - `budget_exhausted` (ТЗ 1.2.3)
    - `session_crash` (ТЗ 1.2.3)
- Каждый профиль: `FaultProfile(error_code, stage, recoverable)`.
- Активация детерминированная по `fault_id`.

TESTS:

- `test_profiles_have_unique_error_codes`
- `test_recoverable_flags_are_consistent`
- `test_all_tz_scenarios_covered`
- `test_profile_activation_is_deterministic`

ACCEPTANCE: Матрица покрывает все сценарии отказов из ТЗ.

STOP_CONDITIONS: Если профиль требует реального сбоя — не выполнять.

---

## G2 — Обязательные области ТЗ Раздел 7 (уровни Unit/Component)

### TASK-10-05: Data isolation tests

GOAL: Проверить все сценарии изоляции данных из ТЗ Раздел 7, Секция 2.

CONTEXT: ТЗ требует: отсутствие смешивания Studies, корректная работа Project context, `StudyDocumentLink` JOIN-изоляция, глобальный repository, `MATERIALS_ONLY`.

ALLOWED_FILES: `tests/qa/unit/test_data_isolation.py`.

FORBIDDEN: Сеть. Реальная LLM. Прямое изменение статусов.

IMPLEMENTATION DETAILS:

- Тесты:
    - Отсутствие смешивания Studies: данные Study A не видны в Study B.
    - `StudyDocumentLink` JOIN-изоляция: поиск возвращает только документы текущего Study.
    - Project context: данные проекта A не видны в проекте B.
    - Переключение проектов не приводит к потере данных.
    - Кросс-проектный поиск находит документ через реестр.
    - Дедупликация внутри проекта работает (один документ — один файл).
    - Реестр синхронизируется при записи документа.
    - `MATERIALS_ONLY`: сетевые адаптеры заблокированы.

TESTS:

- `test_studies_do_not_mix`
- `test_study_document_link_join_isolation`
- `test_project_context_isolation`
- `test_project_switch_preserves_data`
- `test_cross_project_search_via_registry`
- `test_document_deduplication_within_project`
- `test_registry_sync_on_document_write`
- `test_materials_only_blocks_network`

ACCEPTANCE: Все сценарии изоляции из ТЗ 7.2 проходят.

STOP_CONDITIONS: Если изоляция не работает — зафиксировать как критический дефект.

---

### TASK-10-06: Query Planner, URL normalization, Deduplication tests

GOAL: Проверить сценарии из ТЗ Раздел 7, Секции 3, 4, 5.

CONTEXT: Query Planner, нормализация URL, трёхуровневая дедупликация.

ALLOWED_FILES: `tests/qa/unit/test_query_url_dedup.py`.

FORBIDDEN: Сеть. Реальная LLM.

IMPLEMENTATION DETAILS:

- Query Planner (ТЗ 7.3):
    - Декомпозиция вопроса на задачи.
    - Фильтры и исключения.
    - `expected_material_type`.
    - Отклонение дубликатов.
    - Бюджет.
    - Валидация плана.
    - `ResearchGap` → целевой запрос.
- URL normalization (ТЗ 7.4):
    - `tracking parameters` (utm_*, yclid, gclid, fbclid).
    - `fragments`.
    - `query ordering`.
    - `host case`.
    - `trailing slash`.
    - `encoding`.
- Deduplication (ТЗ 7.5):
    - Дубликаты по URL.
    - Дубликаты по DOI/PMID/arXiv.
    - Дубликаты по `content_hash`.
    - Почти дубликаты контента.
    - `SourceRelation`: COPY, REWRITE, CITATION, SAME_PRIMARY.

TESTS:

- `test_query_planner_decomposition`
- `test_query_planner_duplicate_rejection`
- `test_query_planner_gap_targeted_query`
- `test_url_normalization_tracking_params`
- `test_url_normalization_fragments`
- `test_url_normalization_query_ordering`
- `test_url_normalization_host_case`
- `test_url_normalization_trailing_slash`
- `test_url_normalization_encoding`
- `test_dedup_url_duplicates`
- `test_dedup_identifiers`
- `test_dedup_content_hash`
- `test_dedup_source_relation_types`

ACCEPTANCE: Все сценарии Query Planner, URL normalization и Deduplication проходят.

STOP_CONDITIONS: Если алгоритм нормализации не покрывает все случаи — расширить.

---

### TASK-10-07: Ranking, BM25, Russian morphology tests

GOAL: Проверить сценарии из ТЗ Раздел 7, Секции 6, 7, 7.1.

CONTEXT: Раздельное ранжирование, BM25, русский стемминг. ТЗ Раздел 4, Секция 14.1 определяет требования к стеммеру: единый алгоритм для индексации и поиска, поддержка русского языка, детерминированность, обработка стоп-слов, версионирование. Конкретный алгоритм стемминга/лемматизации является реализационным решением. Допустимые варианты: `rank_bm25` с внешним стеммером, встроенные механизмы `SQLite FTS5` с русским токенизатором, или иная библиотека стемминга, удовлетворяющая требованиям детерминированности и воспроизводимости.

ALLOWED_FILES: `tests/qa/unit/test_ranking_bm25.py`.

FORBIDDEN: Сеть. Реальная LLM. GPU.

IMPLEMENTATION DETAILS:

- Ranking (ТЗ 7.6):
    - `relevance` и `source quality` раздельно.
    - `domain weighting`.
    - `freshness`.
    - Top-K.
    - Изменение source quality policy не меняет relevance неожиданно.
- BM25 (ТЗ 7.7):
    - Top-N.
    - Chunk retrieval.
    - Study isolation.
    - Document isolation.
    - Длинные документы.
    - Пустой запрос.
    - Русский текст.
    - Технические термины.
    - CPU-only.
- Russian morphology (ТЗ 7.7.1):
    - Запрос «отзывы» находит документы с «отзыв», «отзыва», «отзывы», «отзывам».
    - Запрос «цена» находит документы с «цена», «цену», «цены», «цене».
    - Запрос «доставка» находит документы с «доставка», «доставке», «доставку».
    - Критерий: Recall не ниже 0.9 для каждого тестового запроса.
    - Допустимые реализации стеммера: `rank_bm25` с внешним стеммером, `SQLite FTS5` с русским токенизатором, или иная детерминированная библиотека. Конкретный выбор фиксируется в реализации EPIC-04.

TESTS:

- `test_ranking_relevance_separate_from_quality`
- `test_ranking_domain_weighting`
- `test_ranking_freshness`
- `test_ranking_top_k`
- `test_bm25_top_n`
- `test_bm25_study_isolation`
- `test_bm25_document_isolation`
- `test_bm25_long_documents`
- `test_bm25_empty_query`
- `test_bm25_russian_text`
- `test_bm25_technical_terms`
- `test_morphology_otzyvy`
- `test_morphology_tsena`
- `test_morphology_dostavka`
- `test_morphology_recall_above_0_9`
- `test_stemmer_deterministic`
- `test_stemmer_same_for_index_and_search`

ACCEPTANCE: Все сценарии ранжирования, BM25 и морфологии проходят. Recall ≥ 0.9. Стеммер детерминирован и одинаков для индексации и поиска.

STOP_CONDITIONS: Если Recall < 0.9 — зафиксировать как критический дефект.

---

### TASK-10-08: Chunking, Evidence, evidence_hash tests

GOAL: Проверить сценарии из ТЗ Раздел 7, Секции 8, 9.

CONTEXT: Детерминированный чанкинг, overlap, evidence_hash.

ALLOWED_FILES: `tests/qa/unit/test_chunking_evidence.py`.

FORBIDDEN: Сеть. Реальная LLM.

IMPLEMENTATION DETAILS:

- Chunking (ТЗ 7.8):
    - Детерминированный вывод.
    - Стабильные `chunk_id`.
    - Структурные границы.
    - `heading_path`.
    - `overlap`.
    - `overlap_group_id`.
    - `is_overlap` флаг.
    - `numeric_signatures`.
    - Воспроизводимость.
- Evidence (ТЗ 7.9):
    - Связь с документом.
    - Связь с чанком (target + context).
    - `location`.
    - Связь с источником.
    - Предотвращение дублирования через `evidence_hash`.
    - Контекстный чанк (`is_target=FALSE`) не является самостоятельным Evidence.

TESTS:

- `test_chunking_deterministic`
- `test_chunking_stable_ids`
- `test_chunking_structural_boundaries`
- `test_chunking_heading_path`
- `test_chunking_overlap`
- `test_chunking_overlap_group_id`
- `test_chunking_is_overlap_flag`
- `test_chunking_numeric_signatures`
- `test_evidence_document_relation`
- `test_evidence_chunk_target_and_context`
- `test_evidence_hash_prevents_duplicates`
- `test_context_chunk_not_standalone_evidence`

ACCEPTANCE: Все сценарии чанкинга и Evidence проходят.

STOP_CONDITIONS: Если чанкинг не детерминирован — критический дефект.

---

### TASK-10-09: Observation/Aggregation, Claims tests

GOAL: Проверить сценарии из ТЗ Раздел 7, Секции 10, 11.

CONTEXT: Агрегация мнений, утверждения.

ALLOWED_FILES: `tests/qa/unit/test_observation_claims.py`.

FORBIDDEN: Сеть. Реальная LLM.

IMPLEMENTATION DETAILS:

- Observation / Aggregation (ТЗ 7.10):
    - Один отзыв не становится статистическим фактом.
    - Повторный текст не увеличивает число независимых наблюдений.
    - Одинаковые отзывы группируются.
    - `positive`/`negative` аспекты разделяются.
    - Количество источников и количество публикаций различаются.
    - Агрегаты воспроизводимы.
    - Отсутствие достаточной выборки явно маркируется.
- Claims (ТЗ 7.11):
    - Связь с Evidence через `ClaimEvidence`.
    - `status`.
    - `confidence`.
    - Различие FACT/OPINION/INFERENCE/HYPOTHESIS.
    - `insufficient evidence`.

TESTS:

- `test_one_review_not_statistical_fact`
- `test_repeated_text_not_increase_observations`
- `test_identical_reviews_grouped`
- `test_positive_negative_aspects_separated`
- `test_source_count_differs_from_publication_count`
- `test_aggregates_reproducible`
- `test_insufficient_sample_marked`
- `test_claim_evidence_relation`
- `test_claim_status_and_confidence`
- `test_claim_types_distinction`
- `test_insufficient_evidence`

ACCEPTANCE: Все сценарии агрегации и утверждений проходят.

STOP_CONDITIONS: Если правило «один отзыв ≠ факт» нарушено — критический дефект.

---

### TASK-10-10: Contradiction, Research Gap, Source independence tests

GOAL: Проверить сценарии из ТЗ Раздел 7, Секции 12, 13, 14.

CONTEXT: Противоречия, пробелы, независимость источников.

ALLOWED_FILES: `tests/qa/unit/test_contradiction_gap_independence.py`.

FORBIDDEN: Сеть. Реальная LLM.

IMPLEMENTATION DETAILS:

- Contradiction (ТЗ 7.12):
    - Числовые противоречия (через `numeric_signatures`).
    - Временные.
    - Фактологические.
    - Технические.
    - Конфликты рекомендаций.
    - Конфликты пользовательского опыта.
    - Детерминированная фильтрация + семантическое сравнение.
- Research Gap (ТЗ 7.13):
    - Создание gap.
    - `reason` (включая `LOW_INDEPENDENCE`).
    - `missing_evidence`.
    - `recommended_query`.
    - Закрытие после новых данных.
- Source independence (ТЗ 7.14):
    - Пять копий одного пресс-релиза → 1 независимый источник.
    - Пять независимых источников → 5 независимых источников.
    - Смешанный набор.
    - Подсчёт через `SourceRelation` и консервативное правило для `UNKNOWN`.

TESTS:

- `test_numeric_contradiction_via_signatures`
- `test_temporal_contradiction`
- `test_factual_contradiction`
- `test_research_gap_creation`
- `test_research_gap_low_independence`
- `test_research_gap_closure`
- `test_five_copies_equal_one_source`
- `test_five_independent_equal_five_sources`
- `test_mixed_sources_independence`
- `test_unknown_does_not_increase_independence`

ACCEPTANCE: Все сценарии противоречий, пробелов и независимости проходят.

STOP_CONDITIONS: Если пять копий считаются пятью источниками — критический дефект.

---

### TASK-10-11: Adaptive Search, Local-First, Cache tests

GOAL: Проверить сценарии из ТЗ Раздел 7, Секции 15, 16, 17.

CONTEXT: Адаптивный поиск, локальный приоритет, кэш.

ALLOWED_FILES: `tests/qa/unit/test_adaptive_cache.py`.

FORBIDDEN: Сеть. Реальная LLM.

IMPLEMENTATION DETAILS:

- Adaptive Search (ТЗ 7.15):
    - Новый запрос имеет причину.
    - Дубликат отклоняется (Exact Match).
    - Похожий запрос отклоняется (Similarity Match).
    - Уже покрытая задача отклоняется (Coverage Match).
    - Бюджет соблюдается.
    - Gap-targeted search.
    - Остановка при отсутствии информационного прироста.
- Local-First (ТЗ 7.16):
    - Локальные материалы используются первыми.
    - Веб-поиск не запускается без выявленного gap.
    - Новые запросы направлены на gap.
- Cache (ТЗ 7.17):
    - `hit`.
    - `miss`.
    - `expired`.
    - `forced refresh`.
    - Source-specific TTL.

TESTS:

- `test_new_query_has_reason`
- `test_duplicate_query_rejected_exact`
- `test_similar_query_rejected`
- `test_covered_task_rejected`
- `test_budget_enforced`
- `test_gap_targeted_search`
- `test_termination_on_no_gain`
- `test_local_materials_first`
- `test_cache_hit_miss_expired`
- `test_forced_refresh`
- `test_source_specific_ttl`

ACCEPTANCE: Все сценарии адаптивного поиска, локального приоритета и кэша проходят.

STOP_CONDITIONS: Если адаптивный поиск запускается без причины — критический дефект.

---

### TASK-10-12: DB-write layer, MCP, stdout protection tests

GOAL: Проверить сценарии из ТЗ Раздел 7, Секции 18, 19, 19.1.

CONTEXT: Единый слой записи, MCP контракты, защита stdout. ТЗ Раздел 3, Секция 26 определяет критическое правило: `PRAGMA foreign_keys=ON` не сохраняется между подключениями и обязана выставляться на каждом новом соединении.

ALLOWED_FILES: `tests/qa/unit/test_db_mcp_stdout.py`.

FORBIDDEN: Сеть. Реальная LLM. Прямая запись в обход `DB-write layer`.

IMPLEMENTATION DETAILS:

- DB-write layer (ТЗ 7.18):
    - Последовательная запись.
    - Отсутствие write races.
    - Rollback.
    - Recovery.
    - Сохранность состояния после сбоя.
    - Применение PRAGMA на каждом подключении через фабрику.
    - Отдельная проверка: `PRAGMA foreign_keys=ON` выставляется на каждом новом соединении (не сохраняется между подключениями).
- MCP (ТЗ 7.19):
    - Валидация схем.
    - Компактный вывод.
    - Контракт ошибок.
    - Отзывчивость.
    - Раздельные `search`/`read` операции.
    - Отсутствие блокировки транспорта.
- Stdout protection (ТЗ 7.19.1):
    - Случайный вывод `print("debug")` не нарушает протокол.
    - Логгер в `stdout` не нарушает работу.
    - Исключение с трассировкой не попадает в `stdout`.
    - Клиент получает корректный структурированный ответ об ошибке.

TESTS:

- `test_db_write_sequential`
- `test_db_write_no_races`
- `test_db_rollback`
- `test_db_recovery`
- `test_db_pragma_on_each_connection`
- `test_db_foreign_keys_on_each_new_connection`
- `test_mcp_schema_validation`
- `test_mcp_compact_output`
- `test_mcp_error_contract`
- `test_stdout_print_blocked`
- `test_stdout_logger_blocked`
- `test_stdout_exception_blocked`

ACCEPTANCE: Все сценарии DB-write, MCP и stdout protection проходят. Ни один сценарий не нарушает протокол. `PRAGMA foreign_keys=ON` проверяется на каждом новом соединении.

STOP_CONDITIONS: Если stdout защита не работает — критический дефект. Если `PRAGMA foreign_keys=ON` не выставляется на каждом новом соединении — критический дефект.

---

### TASK-10-13: LLM resilience, JSON degradation tests

GOAL: Проверить сценарии из ТЗ Раздел 7, Секции 20, 21.

CONTEXT: Отказоустойчивость LLM, деградация JSON.

ALLOWED_FILES: `tests/qa/unit/test_llm_json_resilience.py`.

FORBIDDEN: Сеть. Реальная LLM.

IMPLEMENTATION DETAILS:

- LLM resilience (ТЗ 7.20):
    - Симуляция: `unreachable`, `timeout`, `degraded output`, `backend restart`, `backend switch`.
    - Проверка: `LLM_UNREACHABLE`, сохранение State, `SESSION_RESUMING`, отсутствие потери Evidence/Claims, корректный пересчёт `TokenBudgetManager` при смене бэкенда.
- JSON degradation (ТЗ 7.21):
    - `invalid JSON`.
    - `truncated JSON`.
    - JSON repair для промежуточных объектов (Observation, ResearchGap, Contradiction).
    - Запрет тихой правки для финального отчёта (`validate_and_save_report`).
    - Сохранение только валидных завершённых объектов.
    - `REPORT_TRUNCATED_PARTIAL`.
    - Догенерация только отсутствующих элементов.

TESTS:

- `test_llm_unreachable`
- `test_llm_timeout`
- `test_llm_degraded_output`
- `test_llm_backend_restart`
- `test_llm_backend_switch`
- `test_token_budget_recalculation_on_switch`
- `test_invalid_json_handled`
- `test_truncated_json_handled`
- `test_json_repair_for_intermediate_objects`
- `test_json_no_repair_for_final_report`
- `test_report_truncated_partial`
- `test_regeneration_only_missing_elements`

ACCEPTANCE: Все сценарии отказоустойчивости LLM и деградации JSON проходят.

STOP_CONDITIONS: Если тихая правка финального отчёта обнаружена — критический дефект.

---

### TASK-10-14: GUI, cooperative cancellation tests

GOAL: Проверить сценарии из ТЗ Раздел 7, Секции 22, 22.1.

CONTEXT: Отзывчивость GUI, кооперативная отмена.

ALLOWED_FILES: `tests/qa/unit/test_gui_cancellation.py`.

FORBIDDEN: Реальный дисплей. Сеть. Реальная LLM.

IMPLEMENTATION DETAILS:

- GUI (ТЗ 7.22):
    - Main Thread не выполняет тяжёлый retrieval.
    - Worker loop работает независимо.
    - `queue batching`.
    - X-Ray buffer.
    - Smart scroll.
    - Soft Stop.
    - Hard Stop.
    - Snapshot.
    - Offline mode.
- Cooperative cancellation (ТЗ 7.22.1):
    - Индексация: запуск, запрос остановки, завершение в пределах таймаута, данные сохранены.
    - Стемминг: запуск, запрос остановки, завершение после текущей итерации.
    - Перестроение индекса (Job): отмена через `cancel_job`.
    - Все сценарии завершаются в пределах таймаута, консистентность SQLite сохранена, частичные результаты не потеряны.

TESTS:

- `test_main_thread_no_heavy_retrieval`
- `test_worker_loop_independent`
- `test_queue_batching`
- `test_xray_buffer`
- `test_smart_scroll`
- `test_soft_stop`
- `test_hard_stop`
- `test_snapshot`
- `test_offline_mode`
- `test_indexing_cooperative_cancellation`
- `test_stemming_cooperative_cancellation`
- `test_job_cancellation_via_cancel_job`
- `test_partial_results_preserved`

ACCEPTANCE: Все сценарии GUI и кооперативной отмены проходят. Консистентность SQLite сохранена.

STOP_CONDITIONS: Если кооперативная отмена не завершается в пределах таймаута — критический дефект.

---

### TASK-10-15: Network resilience, Security tests

GOAL: Проверить сценарии из ТЗ Раздел 7, Секции 23, 24.

CONTEXT: Сетевая отказоустойчивость, безопасность.

ALLOWED_FILES: `tests/qa/unit/test_network_security.py`.

FORBIDDEN: Реальная сеть. Реальная LLM.

IMPLEMENTATION DETAILS:

- Network resilience (ТЗ 7.23):
    - `timeout`.
    - `rate limit`.
    - `source unavailable`.
    - `parse error`.
    - `per-domain concurrency`.
    - `exponential/backoff retry`.
    - Отсутствие бесконечных retries.
    - Система не обходит CAPTCHA, paywall, access control.
- Security (ТЗ 7.24):
    - Локальные документы не уходят во внешний LLM API.
    - Cloud LLM отсутствует в штатном маршруте.
    - `source credentials` не попадают в отчёт.
    - Логи не содержат содержимое приватных документов без необходимости.

TESTS:

- `test_network_timeout`
- `test_rate_limit`
- `test_source_unavailable`
- `test_parse_error`
- `test_per_domain_concurrency`
- `test_exponential_backoff`
- `test_no_infinite_retries`
- `test_no_captcha_bypass`
- `test_no_paywall_bypass`
- `test_local_docs_not_sent_to_external_llm`
- `test_no_cloud_llm_in_default_route`
- `test_credentials_not_in_report`
- `test_logs_no_private_content`

ACCEPTANCE: Все сценарии сетевой отказоустойчивости и безопасности проходят.

STOP_CONDITIONS: Если локальные документы передаются внешнему LLM — критический дефект.

---

### TASK-10-16: MATERIALS_ONLY, Offline, CPU-only tests

GOAL: Проверить сценарии `MATERIALS_ONLY`, offline mode, CPU-only из обязательных областей.

CONTEXT: ТЗ Раздел 7, Секция 25 критерий 15: «`MATERIALS_ONLY` работает без сети».

ALLOWED_FILES: `tests/qa/unit/test_materials_offline_cpu.py`.

FORBIDDEN: Сеть. Реальная LLM. GPU.

IMPLEMENTATION DETAILS:

- MATERIALS_ONLY:
    - Полностью автономный режим.
    - Сетевые адаптеры физически блокированы.
    - Локальный поиск по `StudyDocumentLink` работает.
    - Исследование завершается без сети.
- Offline mode:
    - Локальный поиск работает.
    - Просмотр Evidence работает.
    - Анализ Study работает.
    - Создание отчёта работает.
    - Экспорт результата работает.
- CPU-only:
    - Нет обязательной зависимости от GPU.
    - Нет обязательной зависимости от embeddings.
    - Нет обязательной зависимости от vector DB.
    - BM25 работает на CPU.
    - Русский стемминг работает на CPU.

TESTS:

- `test_materials_only_no_network`
- `test_materials_only_local_search`
- `test_materials_only_completes_research`
- `test_offline_local_search`
- `test_offline_evidence_viewing`
- `test_offline_report_creation`
- `test_offline_export`
- `test_cpu_only_no_gpu_dependency`
- `test_cpu_only_no_embeddings_dependency`
- `test_cpu_only_no_vector_db_dependency`
- `test_bm25_cpu_only`
- `test_russian_stemming_cpu_only`

ACCEPTANCE: Все сценарии `MATERIALS_ONLY`, offline и CPU-only проходят.

STOP_CONDITIONS: Если обнаружена обязательная зависимость от GPU — критический дефект.

---

## G3 — FSM, MCP Contract, E2E

### TASK-10-17: FSM contract tests — все автоматы

GOAL: Проверить все допустимые и запрещённые переходы для всех шести автоматов.

CONTEXT: ТЗ Раздел 7, Секция 19 и State Machine Spec v1.1. Уровень: FSM.

ALLOWED_FILES: `tests/qa/fsm/test_all_fsm.py`.

FORBIDDEN: Прямое изменение статусов. Сеть. Реальная LLM.

IMPLEMENTATION DETAILS:

- Для каждого автомата (`Study`, `ResearchSession`, `SearchTask`, `MCP Operation`, `LLM Backend`, `Job`):
    - Все допустимые переходы из таблицы проходят.
    - Все недопустимые переходы выбрасывают `InvalidStateTransition`.
    - Каждый переход фиксируется в `LogRecord` (7 полей).
    - Переход + `LogRecord` атомарны.
- Команды не превращены в состояния.
    - `PARTIAL_REPORT`, `REPORT_TRUNCATED_PARTIAL`, `SOFT_STOP`, `HARD_STOP`, `STARTED`, `ALREADY_RUNNING`, `RETRYING` не являются состояниями.

TESTS:

- `test_study_all_valid_transitions`
- `test_study_all_invalid_transitions`
- `test_session_all_valid_transitions`
- `test_session_all_invalid_transitions`
- `test_search_task_all_valid_transitions`
- `test_search_task_all_invalid_transitions`
- `test_mcp_operation_all_valid_transitions`
- `test_mcp_operation_all_invalid_transitions`
- `test_llm_backend_all_valid_transitions`
- `test_llm_backend_all_invalid_transitions`
- `test_job_all_valid_transitions`
- `test_job_all_invalid_transitions`
- `test_commands_not_states`
- `test_partial_report_not_state`
- `test_log_record_on_every_transition`

ACCEPTANCE: Все переходы проверены для всех шести автоматов. Недопустимые переходы невозможны. Команды не превращены в состояния. Покрытие валидных и невалидных переходов полное для каждого автомата.

STOP_CONDITIONS: Если прямой `.status =` возможен через публичный API — критический дефект.

---

### TASK-10-18: MCP Contract tests — все 23 инструмента

GOAL: Проверить контракты всех 23 инструментов из MCP Tool Contracts v1.1.

CONTEXT: Уровень: MCP Contract. Каждый инструмент проверяется на соответствие контракту.

ALLOWED_FILES: `tests/qa/mcp_contract/test_all_tools.py`.

FORBIDDEN: Реальная сеть. Реальная LLM.

IMPLEMENTATION DETAILS:

- Для каждого из 23 инструментов проверить:
    - `INPUT`: обязательные поля, типы, диапазоны.
    - `OUTPUT`: структура, лимиты.
    - `ERRORS`: все коды ошибок из контракта.
    - `LIMITS`: `max_output_bytes`, `max_items`, `max_text_length`.
    - `TIMEOUT`: корректный таймаут.
    - `RETRY`: правила повторных попыток.
    - `SIDE EFFECTS`: корректные побочные эффекты.
    - `IDEMPOTENCY`: повтор не создаёт дубли.
    - `CANCELLATION`: механизм отмены.
    - `AUTHORITY`: решение принимает Core.
- `task_id` обязателен для `search_*` и `save_study_material` (для Evidence).
- `file_ref` для `add_local_document`, не произвольный путь.

TESTS:

- `test_all_23_tools_registered`
- `test_input_schemas_valid`
- `test_output_limits_enforced`
- `test_error_codes_match_contract`
- `test_timeouts_match_contract`
- `test_retry_policies_match_contract`
- `test_idempotency_all_stateful_tools`
- `test_authority_is_core`
- `test_task_id_required_for_search_tools`
- `test_file_ref_not_arbitrary_path`

ACCEPTANCE: Все 23 инструмента соответствуют контрактам. Все правила соблюдены.

STOP_CONDITIONS: Если какой-либо инструмент не соответствует контракту — зафиксировать дефект.

---

### TASK-10-19: E2E happy path

GOAL: Сквозной сценарий полного цикла исследования на фейковых адаптерах.

CONTEXT: Уровень: E2E. Gate G-05 цикл: `intent → plan → tasks → retrieval → evidence → gap → next task → sufficiency → finalize`.

ALLOWED_FILES: `tests/qa/e2e/test_happy_path.py`.

FORBIDDEN: Сеть. Реальная LLM. Реальный дисплей.

IMPLEMENTATION DETAILS:

- Полный цикл:
    - `intent` — создание `ResearchIntent`.
    - `plan` — генерация `ResearchPlan` через `plan_research`.
    - `tasks` — создание `SearchTask` через `TaskAcceptor`.
    - `retrieval` — выполнение поиска через `SearchCore`.
    - `evidence` — извлечение `Evidence`.
    - `gap` — выявление `ResearchGap`.
    - `next task` — создание новой задачи на основе gap.
    - `sufficiency` — оценка через `SufficiencyEvaluator` → `STOP_SUFFICIENT`.
    - `finalize` — финализация и сохранение отчёта.
- Проверка начальных переходов: `Study.status` перешёл `DRAFT → PLANNING → READY → RUNNING` перед началом цикла.
- Проверка: `Study.status` перешёл в `FINALIZING`, затем в `COMPLETED`.
- Проверка: все переходы залогированы в `LogRecord`.
- Проверка: `Evidence` и `Claim` сохранены корректно.

TESTS:

- `test_full_cycle_completes`
- `test_study_initial_transitions_draft_to_running`
- `test_sufficiency_returns_stop_sufficient`
- `test_study_reaches_completed`
- `test_evidence_and_claims_saved`
- `test_all_transitions_logged`

ACCEPTANCE: Полный цикл из Gate G-05 проходит. Решение о завершении принимает Core. Начальные переходы `DRAFT → PLANNING → READY → RUNNING` проверены.

STOP_CONDITIONS: Если цикл не завершается — критический дефект.

---

## G4 — Сквозные сценарии и финальная приёмка

### TASK-10-20: Сквозной сценарий — Аварийное восстановление

GOAL: Проверить сквозной сценарий из ТЗ Раздел 1, Секция 2.3: `RUNNING → LLM_UNAVAILABLE → SESSION_RESUMING → RUNNING`.

CONTEXT: Уровень: Failure Scenarios.

ALLOWED_FILES: `tests/qa/failure/test_llm_failure_recovery.py`.

FORBIDDEN: Сеть. Реальная LLM.

IMPLEMENTATION DETAILS:

- Сквозной сценарий:
    - `Study` в состоянии `RUNNING`.
    - LLM Backend переходит в `UNREACHABLE`.
    - `ResearchSession` переходит в `LLM_UNAVAILABLE`.
    - LLM Backend восстанавливается.
    - `ResearchSession` переходит в `SESSION_RESUMING`, затем в `ACTIVE`.
    - `Study` остаётся в `RUNNING`.
- Проверка: `Evidence` и `Claim` не теряются.
- Проверка: все переходы залогированы.

TESTS:

- `test_llm_failure_cross_scenario`
- `test_study_remains_running`
- `test_evidence_preserved`
- `test_claims_preserved`
- `test_session_resumes_to_active`

ACCEPTANCE: Сквозной сценарий из ТЗ проходит. Данные не теряются.

STOP_CONDITIONS: Если данные теряются при восстановлении — критический дефект.

---

### TASK-10-21: Сквозной сценарий — Остановка пользователем

GOAL: Проверить сквозные сценарии из ТЗ Раздел 1, Секция 2.3: Soft Stop и Hard Stop.

CONTEXT: Уровень: Failure Scenarios.

ALLOWED_FILES: `tests/qa/failure/test_user_stop.py`.

FORBIDDEN: Сеть. Реальная LLM.

IMPLEMENTATION DETAILS:

- Soft Stop: `RUNNING → FINALIZING → COMPLETED`. Текущие операции завершаются. `Partial report` создаётся.
- Hard Stop: `RUNNING → USER_STOPPED`. Кооперативная отмена. `SQLite` консистентна.
- Проверка: `ResearchSession` → `CLOSING → CLOSED`.
- Проверка: `SearchTask` → `COMPLETED` (Soft) или `CANCELLED` (Hard).
- Проверка: кооперативная отмена CPU-задач.

TESTS:

- `test_soft_stop_cross_scenario`
- `test_hard_stop_cross_scenario`
- `test_soft_stop_allows_current_to_finish`
- `test_hard_stop_cancels_all`
- `test_sqlite_consistent_after_hard_stop`
- `test_cooperative_cancellation_works`

ACCEPTANCE: Оба сценария из ТЗ проходят. Кооперативная отмена работает.

STOP_CONDITIONS: Если Hard Stop повреждает SQLite — критический дефект.

---

### TASK-10-22: Сквозной сценарий — Исчерпание бюджета

GOAL: Проверить сквозной сценарий из ТЗ Раздел 1, Секция 2.3: `RUNNING → BUDGET_EXHAUSTED → FREEZE_BUDGET_EXHAUSTED → PARTIAL_REPORT`.

CONTEXT: Уровень: Failure Scenarios.

ALLOWED_FILES: `tests/qa/failure/test_budget_exhaustion.py`.

FORBIDDEN: Сеть. Реальная LLM.

IMPLEMENTATION DETAILS:

- Сквозной сценарий:
    - `Study` в состоянии `RUNNING`.
    - Бюджет исчерпан.
    - `Study` переходит в `BUDGET_EXHAUSTED`.
    - `Study` переходит в `FREEZE_BUDGET_EXHAUSTED`.
    - `Study` переходит в `FINALIZING`.
    - `Study` переходит в `COMPLETED`.
- Отчёт помечается как `REPORT_TRUNCATED_PARTIAL` (метаданные, не состояние).
- Проверка: новые `SearchTask` отклоняются при нулевом бюджете (`REJECTED_BUDGET`).

TESTS:

- `test_budget_exhaustion_cross_scenario`
- `test_partial_report_is_metadata`
- `test_new_tasks_rejected_on_zero_budget`
- `test_all_transitions_logged`

ACCEPTANCE: Сквозной сценарий из ТЗ проходит. `PARTIAL_REPORT` — метаданные.

STOP_CONDITIONS: Если `PARTIAL_REPORT` является состоянием `Study` — критический дефект.

---

## G5 — Стабилизация и релизная подготовка

### TASK-10-23: Стабилизация — целостность данных и восстановление

GOAL: Проверить целостность данных, восстановление БД, атомарность записи.

CONTEXT: Уровень: Acceptance preparation. Покрытие ТЗ 7.18, 7.25.

ALLOWED_FILES: `src/stability/db_guard.py`, `src/stability/workspace_check.py`, `tests/stability/test_data_integrity.py`.

FORBIDDEN: Удаление данных. Сеть. Реальная LLM.

IMPLEMENTATION DETAILS:

- Проверка структуры рабочей директории и проектной структуры из ТЗ Раздел 3, Секция 25.
- `PRAGMA integrity_check`.
- Подтверждение `journal_mode=WAL`.
- Проверка доменной схемы: наличие всех обязательных таблиц из ТЗ Раздел 3. Ожидаемые таблицы:
    - `Project`, `Study`, `ResearchIntent`, `SearchTask`, `SearchResult`
    - `Source`, `SourceRelation`, `Entity`, `Document`, `StudyDocumentLink`
    - `DocumentChunk`, `Evidence`, `EvidenceContextChunk`, `Observation`, `Claim`
    - `ClaimEvidence`, `Contradiction`, `ResearchGap`, `SufficiencyEvaluation`, `ResearchConfig`
    - `ResearchSession`, `ResearchState`, `WorkingMemory`, `CacheEntry`, `LogRecord`
    - `Job` (ТЗ Раздел 4, Секция 28)
- Проверка индексов и внешних ключей.
- План восстановления при повреждении.
- Проверка атомарности транзакций.
- Проверка сохранения данных после сбоя.

TESTS:

- `test_workspace_structure_matches_tz`
- `test_wal_mode_enabled`
- `test_domain_schema_complete`
- `test_indexes_present`
- `test_foreign_keys_enabled`
- `test_integrity_check_passes`
- `test_recovery_plan_on_corrupt`
- `test_atomic_transactions`
- `test_data_preserved_after_crash`

ACCEPTANCE: Целостность данных подтверждена. Восстановление работает. Все 26 таблиц доменной схемы проверены явно.

STOP_CONDITIONS: Если данные теряются при восстановлении — критический дефект.

---

### TASK-10-24: Стабилизация — ресурсные ограничения

GOAL: Проверить ресурсные ограничения, производительность, буферы.

CONTEXT: Уровень: Acceptance preparation. CPU-only, детерминированные пороги.

ALLOWED_FILES: `src/stability/resource_guard.py`, `src/stability/perf_budget.py`, `tests/stability/test_resources.py`.

FORBIDDEN: GPU. Реальная LLM. Сеть.

IMPLEMENTATION DETAILS:

- Проверка CPU-бюджета: `threads` не превышает `os.cpu_count()`.
- Проверка буферов: логи, прогресс, артефакты ограничены.
- Детерминированные пороги производительности.
- Проверка отсутствия обязательных зависимостей от GPU/embeddings/vector DB.
- Формирование `PerfReport`.

TESTS:

- `test_threads_clamped_to_cpu_count`
- `test_buffers_limited`
- `test_perf_budget_deterministic`
- `test_no_gpu_dependency`
- `test_no_embeddings_dependency`
- `test_no_vector_db_dependency`

ACCEPTANCE: Ресурсные ограничения соблюдены. Нет скрытых зависимостей.

STOP_CONDITIONS: Если обнаружена обязательная зависимость от GPU — критический дефект.

---

### TASK-10-25: Стабилизация — безопасность выполнения

GOAL: Проверить безопасность команд, устойчивость к гонкам, кооперативную отмену.

CONTEXT: Уровень: Acceptance preparation. Покрытие ТЗ 7.22.1.

ALLOWED_FILES: `src/stability/command_guard.py`, `src/stability/shutdown.py`, `tests/stability/test_safety.py`.

FORBIDDEN: Прямое изменение статусов. Сеть. Реальная LLM.

IMPLEMENTATION DETAILS:

- `CommandGuard`: проверка `idempotency_key`, защита от дублей и устаревших команд.
- Привязка к реальным триггерам из State Machine Spec v1.1.
- Координатор безопасного завершения.
- Проверка, что `SOFT_STOP` и `HARD_STOP` являются командами, а не состояниями.
- Кооперативная отмена через `threading.Event`.

TESTS:

- `test_duplicate_command_ignored`
- `test_stale_command_rejected`
- `test_commands_mapped_to_real_triggers`
- `test_shutdown_plan_ordered`
- `test_cooperative_cancellation_via_threading_event`
- `test_soft_hard_stop_are_commands_not_states`

ACCEPTANCE: Безопасность выполнения подтверждена. Команды не превращены в состояния.

STOP_CONDITIONS: Если команда может изменить состояние напрямую — критический дефект.

---

### TASK-10-26: Документация и runbook

GOAL: Создать операционный runbook и документацию для релиз-кандидата.

CONTEXT: Релиз должен иметь понятный локальный сценарий эксплуатации.

ALLOWED_FILES: `docs/operator_runbook.md`, `docs/quickstart.md`, `tests/stability/test_documentation.py`.

FORBIDDEN: Сетевые инструкции. Описание удалённого LLM. Непроверенные шаги.

IMPLEMENTATION DETAILS:

- Runbook: старт, диагностика, восстановление настроек, восстановление БД, остановка.
- Каждый сбой: причина, проверка, действие.
- Quickstart: команда запуска, ожидаемый результат.
- Проверка наличия обязательных разделов.
- Проверка отсутствия небезопасных инструкций.

TESTS:

- `test_required_sections_present`
- `test_recovery_steps_present`
- `test_no_network_instructions`
- `test_no_real_llm_instructions`

ACCEPTANCE: Документация пригодна для локальной эксплуатации. Нет небезопасных инструкций.

STOP_CONDITIONS: Если runbook содержит сетевые инструкции — исправить.

---

### TASK-10-27: Релизный манифест и точка запуска

GOAL: Сформировать манифест релиз-кандидата и локальную точку запуска.

CONTEXT: Релиз должен иметь единый источник информации о составе сборки. Точка запуска `local_entry.run_headless(workspace)` используется в EPIC-11 TASK-11-03 как зависимость. Интерфейс должен быть согласован до передачи в EPIC-11.

ALLOWED_FILES: `src/stability/release_manifest.py`, `src/cli/local_entry.py`, `tests/stability/test_release.py`.

FORBIDDEN: Сеть. Реальная LLM. Невыполненные проверки в манифесте.

IMPLEMENTATION DETAILS:

- `ReleaseManifest`: `version`, `components`, `checks`, `generated_at`.
- Обязательные проверки: `workspace`, `db`, `settings`, `fsm_guard`, `perf_budget`, `stdout_protection`, `cooperative_cancellation`.
- `local_entry.run_headless(workspace)`: минимальный локальный сценарий без GUI.
- Атомарная запись манифеста.

TESTS:

- `test_manifest_contains_required_components`
- `test_checks_are_complete`
- `test_headless_run_finishes_ok`
- `test_no_network_used`

ACCEPTANCE: Манифест однозначно описывает релиз. Точка запуска воспроизводима. Интерфейс `run_headless` согласован с EPIC-11.

STOP_CONDITIONS: Если проверка не может быть выполнена — не включать в манифест. Если интерфейс `run_headless` изменяется после согласования с EPIC-11 — остановить задачу и передать архитектору для обновления зависимости в EPIC-11 TASK-11-03.

---

### TASK-10-28: Финальный приёмочный гейт — все 25 критериев

GOAL: Систематически проверить все 25 критериев приёмки из ТЗ Раздел 7, Секция 25.

CONTEXT: Gate G-10: «Все обязательные критерии Раздела 07 ТЗ выполнены; критических известных дефектов нет».

ALLOWED_FILES: `src/stability/acceptance_gate.py`, `tests/stability/test_acceptance_gate.py`.

FORBIDDEN: Сеть. Реальная LLM. Пропуск ошибок.

IMPLEMENTATION DETAILS:

- `AcceptanceGate.run()` проверяет каждый из 25 критериев:
    1. Локальная 12–14B LLM может выполнить исследование через MCP.
    2. Search Core принимает окончательное решение о выполнении запросов.
    3. LLM не обязана помнить историю tool calls.
    4. Candidate Retrieval не выполняет массовый fetch.
    5. Дубликаты удаляются (URL, DOI, content_hash, SourceRelation).
    6. Relevance и quality разделены.
    7. Snippet не считается Evidence.
    8. Claim связан с Evidence через `ClaimEvidence`.
    9. Система различает независимые и производные источники.
    10. Система ищет противоречия (детерминированно + семантически).
    11. Research Gaps приводят к целевым запросам.
    12. Повторные и сходные запросы блокируются.
    13. Aggregation-задачи считают наблюдения, а не просто URL.
    14. Evidence-задачи сохраняют проверяемую source base.
    15. `MATERIALS_ONLY` работает без сети.
    16. Ошибки одного источника не останавливают Study.
    17. Report содержит проверяемые источники.
    18. JSON валидируется (с repair для промежуточных объектов).
    19. CPU + BM25 + русский стемминг достаточно для базового запуска.
    20. Новый RetrievalProvider подключается без изменения Study API.
    21. Единый DB-write layer сохраняет целостность.
    22. LLM restart не уничтожает Study.
    23. Hard Stop не повреждает SQLite (кооперативная отмена).
    24. Локальные документы не передаются внешним LLM.
    25. MCP stdout защищён от случайного вывода.
- Формирует `rc_signoff.json` с итогом `PASS` или `FAIL`.
- Любая критическая ошибка приводит к `FAIL`.

TESTS:

- `test_all_25_criteria_checked`
- `test_pass_on_healthy_environment`
- `test_fail_on_critical_defect`
- `test_signoff_report_written`
- `test_no_direct_state_changes`

ACCEPTANCE: Все 25 критериев проверены. Результат `PASS` или `FAIL` детерминирован.

STOP_CONDITIONS: Если хотя бы один критерий не может быть проверен — зафиксировать и передать архитектору.

---

## Gate G-10 Acceptance Criteria

- Все 28 секций ТЗ Раздел 7 проверены на соответствующих уровнях тестирования.
- Все 25 критериев ТЗ Раздел 7, Секция 25 проверены систематически.
- Все уровни тестирования выполнены: Unit → Component → Integration → FSM → MCP Contract → E2E → Failure Scenarios → Acceptance.
- Все три сквозных сценария из ТЗ Раздел 1, Секция 2.3 проходят: Аварийное восстановление, Остановка пользователем, Исчерпание бюджета.
- Все шесть автоматов состояний проверены: допустимые и недопустимые переходы, атомарность `LogRecord`.
- Все 23 инструмента соответствуют контрактам из MCP Tool Contracts v1.1.
- Golden datasets реализованы: FakeSourceAdapter, FakeLLM, Golden documents/chunks/Evidence/Sufficiency/reports.
- Русская морфология: Recall ≥ 0.9 для каждого тестового запроса.
- Кооперативная отмена: все сценарии завершаются в пределах таймаута, консистентность сохранена.
- Нет критических известных дефектов.
- Нет реальных сетевых вызовов в тестах.
- Нет реальной LLM в тестах.
- Нет прямого изменения `.status` в тестах.
- Критических дефектов нет.

Статус EPIC-10: Готов к передаче в разработку.