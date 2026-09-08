# EPIC-04 SEARCH CORE — TASK BATCH v1.3 — BASELINE

Проект: Research Prompt Suite
Статус: BASELINE — Ready for CODE Agent Execution
Целевой агент: локальный AI-агент с ограниченным контекстом

Основание:
- ТЗ v2.4
- MASTER DEVELOPMENT ROADMAP v1.2
- EPIC SPECIFICATIONS v1.0
- EPIC → TASK DECOMPOSITION v1.0
- TASK EXECUTION CONTRACT v1.0 — BASELINE

Зависимости:
- EPIC-01 Foundation
- EPIC-02 Data Layer
- EPIC-03 State Machines

EPIC-01, EPIC-02 и EPIC-03 должны предоставить необходимые контракты,
схему БД и инфраструктуру до начала выполнения соответствующих TASK EPIC-04.

---

## 0. Глобальные правила для CODE-агента

- Одна TASK даёт один проверяемый результат.
- Каждая TASK содержит 8 обязательных секций:
  `GOAL`, `CONTEXT`, `ALLOWED_FILES`, `FORBIDDEN`,
  `IMPLEMENTATION DETAILS`, `TESTS`, `ACCEPTANCE`, `STOP_CONDITIONS`.
- Python 3.11+.
- Для MVP запрещены обязательные внешние зависимости, кроме `pytest`,
  если конкретная TASK явно не разрешает иное.
- Запрещены сеть, реальный LLM, GUI, MCP-сервер, бизнес-логика исследования.
- Все тесты используют `tmp_path` и фиктивные адаптеры.
- Все пути к миграциям в тестах вычисляются относительно файла теста.
- `SourceAdapter` обязан реализовывать контракт ТЗ:
  `search`, `fetch`, `capabilities`, `health`.
- `RetrievalProvider` обязан реализовывать контракт ТЗ:
  `name`, `capabilities`, `search`, `index`, `delete`, `is_available`.
- Поисковый запрос и индексируемый текст проходят через один и тот же
  `RetrievalTextNormalizer`.
- Нормализатор обязан предоставлять:
  `name()`, `version()`, `stopword_version()`,
  `normalize_text()`, `normalize_query()`.
- Русский нормализатор обязан обрабатывать стоп-слова детерминированно.
- Новый запрос допускается только при наличии основания `ResearchGap`.
- FTS-индекс обязан поддерживать:
  `document added`,
  `document deleted`,
  `normalizer changed -> rebuild_all`,
  `study deleted -> cleanup`.
- FTS5 используется как локальный инвертированный индекс кандидатов.
- Финальное BM25-ранжирование MVP выполняется детерминированным кодом Python
  на нормализованных токенах.
- Встроенная SQLite FTS5-функция `bm25()` не используется для финального
  рейтинга MVP.
- Если SQLite собран без FTS5 — `STOP → REPORT → WAIT`.
- Все операции изменения БД выполняются через существующее транзакционное
  управление вызывающего слоя.
- Вложенные сервисы не должны самостоятельно владеть транзакцией вызывающего
  бизнес-операционного потока, если иное явно не разрешено контрактом TASK.
- Все открытые вопросы к архитектору должны быть вынесены в конец документа.
- Открытый вопрос не считается разрешённым только потому, что агент
  предложил собственную реализацию.
- CODE не изменяет scope TASK.
- CODE не рефакторит соседний код без необходимости для текущей TASK.
- При обнаружении проблемы вне scope:
  `STOP → REPORT → WAIT`.

---

## 1. Принятые исправления

- Добавлена трассировка к `EPIC → TASK DECOMPOSITION v1.0`.
- `SourceAdapter` приведён к полному контракту ТЗ, включая `fetch`.
- `BM25RetrievalProvider` приведён к полному контракту `RetrievalProvider`.
- Добавлена обработка стоп-слов в русский нормализатор.
- Добавлена версия стоп-слов через `stopword_version`.
- Модель независимости источников исправлена:
  `COPY`, `REWRITE`, `SAME_PRIMARY` могут объединять независимые кластеры;
  `CITATION` и `UNKNOWN` не участвуют в обычном Union-Find объединении.
- `CITATION` учитывается как зависимость от цитируемого первичного источника.
- `UNKNOWN` исключается из финального расчёта независимых подтверждений.
- Добавлена интеграция `check_query` с основанием `ResearchGap`.
- Добавлена операция `cleanup_study_from_index`.
- Добавлены отдельные тесты консистентности `DocumentChunk` ↔ FTS index.
- Добавлены детерминированные фикстуры.
- Все пути к миграциям переведены на вычисление относительно файла теста.
- Явно зафиксирован способ конкатенации полей в `query_fingerprint`.
- Исправлены склеенные формулировки `dataclassCandidate`,
  `dataclassProviderLimits`, `dataclassDocumentChunk`,
  `dataclassCoverageMetrics`, `dataclassSufficiencyInput`,
  `dataclassSufficiencyDecision` и аналогичные.
- Исправлена опечатка в `E04-T15`.
- Для `BM25IndexMeta` явно указаны типы полей.
- `get_cache_statistics` расширен до полного контракта ТЗ.
- `BM25RetrievalProvider.search` обязан возвращать полностью заполненные
  `DocumentChunk`, включая `numeric_signatures` и `metadata`.
- Операция `deduct_budget` принимает `conn` вызывающего слоя и не владеет
  COMMIT/ROLLBACK родительской транзакции.
- `Snippetizer` использует тот же `RetrievalTextNormalizer`, что и retrieval.
- `check_query` использует унифицированные ошибки Search Core.
- FTS5 используется для candidate retrieval, а не как источник финального
  BM25 score.
- Финальный BM25 score рассчитывается детерминированным Python-кодом.
- Для Python BM25 не добавляется обязательная внешняя библиотека.
- `normalizer_version` является окончательным именем версии нормализатора
  в `BM25IndexMeta`.
- Открытые вопросы, не влияющие на уже утверждённые контракты, вынесены
  в конец документа.

---

## 2. Трассировка относительно EPIC → TASK DECOMPOSITION v1.0

| Декомпозиция | TASK | Комментарий |
|---|---|---|
| E04-T01 SourceAdapter interface | E04-T03-SOURCE-ADAPTER-INTERFACE | Полный контракт |
| E04-T02 provider/domain limits | E04-T05-PROVIDER-LIMITS | Лимиты |
| E04-T03 timeout/retry/backoff | E04-T06-TIMEOUT-RETRY-BACKOFF | Retry |
| E04-T04 provider result normalization | E04-T08-RESULT-NORMALIZATION | Нормализация |
| E04-T05 URL canonicalization | E04-T12-URL-NORMALIZATION | Канонизация |
| E04-T06 source identity normalization | E04-T13-SOURCE-IDENTITY | DOI/PMID/arXiv |
| E04-T07 SourceRelation handling | E04-T14-SOURCE-RELATION-HELPERS | Независимость источников |
| E04-T08 URL/identifier deduplication | E04-T15-DEDUP-URL-IDENTIFIER | Уровень 1/2 |
| E04-T09 content hash deduplication | E04-T16-DEDUP-CONTENT-HASH | Уровень 3 |
| E04-T10 near-duplicate detection | E04-T17-NEAR-DUPLICATE | Jaccard |
| E04-T11 deduplication tests | E04-T15, E04-T16, E04-T17 | Тесты |
| E04-T12 query normalization | E04-T18-QUERY-NORMALIZATION | Нормализация |
| E04-T13 query_fingerprint generation | E04-T19-QUERY-FINGERPRINT | Формула ТЗ |
| E04-T14 duplicate-query protection | E04-T20, E04-T21 | Exact/similarity/coverage |
| E04-T15 fingerprint + budget | E04-T21, E04-T38 | Бюджет |
| E04-T16 fingerprint + ResearchGap | E04-T21, E04-T42 | Основание запроса |
| E04-T17 loop-prevention tests | E04-T21 | Тесты |
| E04-T18 content fetch abstraction | E04-T22 | Транспорт |
| E04-T19 document parsing | E04-T23 | Parse/clean |
| E04-T20 deterministic chunking | E04-T25 | Чанкинг |
| E04-T21 heading_path | E04-T25 | Структура |
| E04-T22 overlap metadata | E04-T26 | Overlap |
| E04-T23 numeric signatures | E04-T27 | Числовые данные |
| E04-T24 chunking tests | E04-T25, E04-T26, E04-T27 | Тесты |
| E04-T25 normalizer interface | E04-T28 | Абстракция |
| E04-T26 BasicNormalizer | E04-T29 | Fallback |
| E04-T27 Russian morphology | E04-T30 | Русский поиск |
| E04-T28 FTS5 schema | E04-T31 | Схема |
| E04-T29 BM25 retrieval | E04-T33 | FTS candidate + Python BM25 |
| E04-T30 study/document isolation | E04-T34 | Изоляция |
| E04-T31 normalizer_version metadata | E04-T31, E04-T32 | Метаданные |
| E04-T32 index metadata | E04-T31, E04-T32 | Метаданные |
| E04-T33 document added | E04-T32 | Индексация |
| E04-T34 normalizer changed | E04-T32, E04-T35 | Rebuild |
| E04-T35 study deleted | E04-T32 | Cleanup |
| E04-T36 FTS consistency | E04-T35 | Консистентность |
| E04-T37 Evidence creation | E04-T36 | Evidence |
| E04-T38 evidence_hash | E04-T36 | Hash |
| E04-T39 target/context | E04-T36 | Контекст |
| E04-T40 provenance | E04-T36 | Provenance |
| E04-T41 Evidence tests | E04-T36 | Тесты |
| E04-T42 cache key/TTL | E04-T37 | Cache |
| E04-T43 cache diagnostics | E04-T37 | Diagnostics |
| E04-T44 cache cleanup | E04-T37 | Cleanup |
| E04-T45 budget model | E04-T38 | Budget |
| E04-T46 atomic budget deduction | E04-T38 | Transaction |
| E04-T47 cache/budget tests | E04-T37, E04-T38 | Тесты |
| E04-T48 CoverageCalculator | E04-T39 | Coverage |
| E04-T49 SufficiencyEvaluator | E04-T40 | Sufficiency |
| E04-T50 information gain | E04-T41 | Gain |
| E04-T51 ResearchGap | E04-T42 | Gap |
| E04-T52 coverage/sufficiency tests | E04-T39, E04-T40, E04-T41 | Тесты |

---

## 3. Рекомендуемый порядок выполнения

- E04-T01-SEARCH-ERRORS
- E04-T02-CANDIDATE-MODEL
- E04-T03-SOURCE-ADAPTER-INTERFACE
- E04-T04-FAKE-SOURCE-ADAPTER
- E04-T05-PROVIDER-LIMITS
- E04-T06-TIMEOUT-RETRY-BACKOFF
- E04-T07-SNIPPETIZER
- E04-T08-RESULT-NORMALIZATION
- E04-T09-RELEVANCE-RANKING
- E04-T10-SOURCE-QUALITY-POLICY
- E04-T11-TOPK-SELECTION
- E04-T12-URL-NORMALIZATION
- E04-T13-SOURCE-IDENTITY
- E04-T14-SOURCE-RELATION-HELPERS
- E04-T15-DEDUP-URL-IDENTIFIER
- E04-T16-DEDUP-CONTENT-HASH
- E04-T17-NEAR-DUPLICATE
- E04-T18-QUERY-NORMALIZATION
- E04-T19-QUERY-FINGERPRINT
- E04-T20-QUERY-SIMILARITY
- E04-T21-QUERY-LOOP-PREVENTION
- E04-T22-FETCH-TRANSPORT-ABSTRACTION
- E04-T23-HTML-PARSE-CLEAN
- E04-T24-CHUNKING-CONFIG
- E04-T25-DETERMINISTIC-CHUNKER
- E04-T26-OVERLAP-METADATA
- E04-T27-NUMERIC-SIGNATURES
- E04-T28-NORMALIZER-INTERFACE
- E04-T29-BASIC-NORMALIZER
- E04-T30-RUSSIAN-MORPHOLOGY-NORMALIZER
- E04-T31-FTS-SCHEMA-MIGRATION
- E04-T32-FTS-INDEX-LIFECYCLE
- E04-T33-BM25-RETRIEVAL-PROVIDER
- E04-T34-STUDY-DOCUMENT-ISOLATION-TEST
- E04-T35-FTS-CONSISTENCY-TEST
- E04-T36-EVIDENCE-EXTRACTION
- E04-T37-CACHE-SERVICE
- E04-T38-BUDGET-SERVICE
- E04-T39-COVERAGE-CALCULATOR
- E04-T40-SUFFICIENCY-EVALUATOR
- E04-T41-INFORMATION-GAIN
- E04-T42-RESEARCH-GAP-OPS
- E04-T43-DETERMINISTIC-FIXTURES
- E04-T44-SEARCH-CORE-PIPELINE-INTEGRATION

---

## 4. TASKS

### TASK: E04-T01-SEARCH-ERRORS

- GOAL: Создать унифицированные ошибки Search Core.
- CONTEXT: Ошибки должны быть совместимы с общим контрактом ошибок.
- ALLOWED_FILES:
  - `src/search/__init__.py`
  - `src/search/errors.py`
  - `tests/search/__init__.py`
  - `tests/search/test_errors.py`
- FORBIDDEN:
  - Бизнес-логика.
  - БД.
  - Сетевые вызовы.
- IMPLEMENTATION DETAILS:
  - Создай пустые `__init__.py`.
  - В `src/search/errors.py` создай базовый класс `SearchCoreError`.
  - Добавь наследников:
    `ProviderError`,
    `ProviderTimeoutError`,
    `RateLimitError`,
    `SourceUnavailableError`,
    `FetchError`,
    `ParseError`,
    `ChunkingError`,
    `RetrievalError`,
    `DeduplicationError`,
    `QueryRejectedError`,
    `BudgetExhaustedError`,
    `CacheError`.
  - Ошибки должны быть пригодны для последующего преобразования
    верхним адаптером в стандартный JSON-RPC Error.
- TESTS:
  - Проверь, что все ошибки являются наследниками `SearchCoreError`.
- ACCEPTANCE:
  - Иерархия ошибок создана.
- STOP_CONDITIONS:
  - Если хочется добавить ошибку вне утверждённого контракта:
    `STOP → REPORT → WAIT`.

---

### TASK: E04-T02-CANDIDATE-MODEL

- GOAL: Создать модель кандидата поисковой выдачи.
- CONTEXT: Кандидат — компактная карточка, не полный документ.
- ALLOWED_FILES:
  - `src/search/models.py`
  - `tests/search/test_models.py`
- FORBIDDEN:
  - Fetch.
  - Parse.
  - Chunking.
- IMPLEMENTATION DETAILS:
  - Создай замороженный `dataclass` `Candidate`.
  - Обязательные поля:
    `url`, `title`, `snippet`, `source`, `identifiers`, `date`, `metadata`.
  - `identifiers` и `metadata` по умолчанию пустые словари.
  - Не добавляй поле полного текста.
- TESTS:
  - Проверь создание кандидата.
  - Проверь значения по умолчанию.
  - Проверь иммутабельность.
- ACCEPTANCE:
  - Модель кандидата готова.
- STOP_CONDITIONS:
  - Если хочется добавить `full_text`:
    `STOP → REPORT → WAIT`.

---

### TASK: E04-T03-SOURCE-ADAPTER-INTERFACE

- GOAL: Создать полный интерфейс `SourceAdapter` по ТЗ.
- CONTEXT: Контракт включает `search`, `fetch`, `capabilities`, `health`.
- ALLOWED_FILES:
  - `src/search/adapters/__init__.py`
  - `src/search/adapters/base.py`
  - `tests/search/test_adapter_base.py`
- FORBIDDEN:
  - Реальные сетевые вызовы.
  - Бизнес-логика Study.
- IMPLEMENTATION DETAILS:
  - Создай `RawDocument`:
    `url`, `canonical_url`, `status`, `content_type`, `body`, `metadata`.
  - Создай `AdapterCapabilities`.
  - Создай `AdapterHealthStatus`.
  - Создай абстрактный класс `SourceAdapter`.
  - Абстрактные методы:
    `search(query, filters, limit)`,
    `fetch(url)`,
    `capabilities()`,
    `health()`.
  - `fetch` обязан возвращать `RawDocument`.
- TESTS:
  - Проверь невозможность инстанцирования абстрактного класса.
  - Проверь минимальный наследник.
  - Проверь все четыре метода.
- ACCEPTANCE:
  - Интерфейс соответствует ТЗ.
- STOP_CONDITIONS:
  - Если хочется вынести `fetch` из `SourceAdapter`:
    `STOP → REPORT → WAIT`.

---

### TASK: E04-T04-FAKE-SOURCE-ADAPTER

- GOAL: Создать детерминированный `FakeSourceAdapter`.
- CONTEXT: Все тесты EPIC-04 работают без сети.
- ALLOWED_FILES:
  - `src/search/adapters/fake_adapter.py`
  - `tests/search/test_fake_adapter.py`
- FORBIDDEN:
  - Сеть.
  - Случайные данные.
- IMPLEMENTATION DETAILS:
  - Реализуй `FakeSourceAdapter`.
  - `search` возвращает детерминированный срез кандидатов.
  - `fetch` возвращает подготовленный `RawDocument`.
  - Неизвестный URL вызывает согласованную ошибку.
  - `capabilities` и `health` возвращают фиксированные значения.
- TESTS:
  - `search` с `limit`.
  - `fetch` известного URL.
  - Ошибка неизвестного URL.
- ACCEPTANCE:
  - Fake adapter детерминирован.
- STOP_CONDITIONS:
  - Если хочется использовать случайные данные:
    `STOP → REPORT → WAIT`.

---

### TASK: E04-T05-PROVIDER-LIMITS

- GOAL: Создать модель лимитов провайдера/домена.
- CONTEXT: Нужны лимиты кандидатов, таймаутов, повторов и concurrency.
- ALLOWED_FILES:
  - `src/search/limits.py`
  - `tests/search/test_limits.py`
- FORBIDDEN:
  - Реальная сеть.
  - Потоки.
- IMPLEMENTATION DETAILS:
  - Создай `ProviderLimits`.
  - Поля:
    `max_candidates`,
    `timeout_seconds`,
    `max_retries`,
    `per_domain_concurrency`,
    `min_delay_ms`.
  - Добавь валидацию.
- TESTS:
  - Валидные значения.
  - Недопустимые значения.
- ACCEPTANCE:
  - Лимиты валидируются.
- STOP_CONDITIONS:
  - Если хочется разрешить безлимитные значения:
    `STOP → REPORT → WAIT`.

---

### TASK: E04-T06-TIMEOUT-RETRY-BACKOFF

- GOAL: Создать детерминированный retry helper.
- CONTEXT: Retry должен тестироваться без реального времени.
- ALLOWED_FILES:
  - `src/search/retry.py`
  - `tests/search/test_retry.py`
- FORBIDDEN:
  - Реальные сетевые вызовы.
  - `time.sleep` без подмены.
- IMPLEMENTATION DETAILS:
  - `compute_backoff_seconds(attempt, base, factor)`.
  - `run_with_retry(fn, max_retries, retryable_exceptions, sleep_fn)`.
  - При исчерпании повторов пробрасывай последнее исключение.
- TESTS:
  - Успешный повтор.
  - `max_retries=0`.
  - Последовательность задержек.
- ACCEPTANCE:
  - Retry работает детерминированно.
- STOP_CONDITIONS:
  - Бесконечные retries запрещены.

---

### TASK: E04-T07-SNIPPETIZER

- GOAL: Создать детерминированный Keyword-Density Snippetizer.
- CONTEXT:
  - Сниппет используется только для оценки релевантности.
  - Сниппет не является Evidence.
  - Нормализация сниппета должна быть согласована с retrieval.
- ALLOWED_FILES:
  - `src/search/snippetizer.py`
  - `tests/search/test_snippetizer.py`
- FORBIDDEN:
  - LLM.
  - Сохранение Evidence.
  - Создание собственной независимой морфологической логики.
- IMPLEMENTATION DETAILS:
  - Реализуй:
    `make_snippet(text, query, normalizer=None, max_length=200)`.
  - Если `normalizer` передан, используй его для нормализации:
    - запроса;
    - предложений текста;
    - расчёта смысловой плотности.
  - Если `normalizer` не передан, используй детерминированную базовую
    токенизацию как fallback.
  - Разбей текст на предложения.
  - Для каждого предложения оцени плотность нормализованных токенов запроса.
  - Выбери предложение с максимальной плотностью.
  - При равенстве используй стабильный порядок исходного текста.
  - Если совпадений нет, верни начало текста.
  - Обрежь результат до `max_length`.
- TESTS:
  - Проверь выбор предложения с ключевым словом.
  - Проверь совпадение словоформ через переданный normalizer.
  - Проверь отсутствие совпадения.
  - Проверь пустой запрос.
  - Проверь ограничение длины.
- ACCEPTANCE:
  - Snippetizer использует тот же normalizer-контракт, что и retrieval,
    если normalizer передан.
- STOP_CONDITIONS:
  - Если хочется считать сниппет Evidence:
    `STOP → REPORT → WAIT`.

---

### TASK: E04-T08-RESULT-NORMALIZATION

- GOAL: Создать нормализацию поисковых кандидатов.
- CONTEXT: Кандидаты должны иметь единый канонический вид до дедупликации.
- ALLOWED_FILES:
  - `src/search/normalize_result.py`
  - `tests/search/test_normalize_result.py`
- FORBIDDEN:
  - Изменение БД.
  - Fetch.
- IMPLEMENTATION DETAILS:
  - Реализуй `normalize_candidate(candidate)`.
  - Очисти `title` и `snippet`.
  - Ключи `identifiers` приведи к нижнему регистру.
  - Не изменяй смысл URL.
- TESTS:
  - Пробелы.
  - Identifier keys.
- ACCEPTANCE:
  - Нормализация детерминирована.
- STOP_CONDITIONS:
  - Если хочется выполнять fetch:
    `STOP → REPORT → WAIT`.

---

### TASK: E04-T09-RELEVANCE-RANKING

- GOAL: Реализовать раздельную оценку релевантности.
- CONTEXT: Relevance и Source Quality считаются отдельно.
- ALLOWED_FILES:
  - `src/search/ranking_relevance.py`
  - `tests/search/test_ranking_relevance.py`
- FORBIDDEN:
  - Оценка качества источника.
- IMPLEMENTATION DETAILS:
  - `score_relevance(candidate, query)`.
  - Учитывай совпадения токенов в title/snippet.
  - DOI/PMID/arXiv могут давать бонус согласно утверждённому контракту.
  - Результат `[0.0, 1.0]`.
- TESTS:
  - Совпадение в title повышает score.
  - Пустой запрос → `0.0`.
- ACCEPTANCE:
  - Relevance score детерминирован.
- STOP_CONDITIONS:
  - Не смешивать relevance и quality.

---

### TASK: E04-T10-SOURCE-QUALITY-POLICY

- GOAL: Реализовать базовую политику качества источника.
- CONTEXT: Качество зависит от типа источника и режима.
- ALLOWED_FILES:
  - `src/search/ranking_quality.py`
  - `tests/search/test_ranking_quality.py`
- FORBIDDEN:
  - Изменение ResearchIntent.
  - Решение о завершении исследования.
- IMPLEMENTATION DETAILS:
  - `score_source_quality(source_type, domain, research_mode)`.
  - Результат `[0.0, 1.0]`.
  - `ACADEMIC`, `CLINICAL`, `PRIMARY_RESEARCH` получают высокий балл
    в `EVIDENCE`.
  - `USER_REVIEWS`, `FORUM` получают высокий балл в `AGGREGATION`.
  - `UNKNOWN` получает низкий балл.
- TESTS:
  - Приоритеты EVIDENCE.
  - Приоритеты AGGREGATION.
- ACCEPTANCE:
  - Quality policy детерминирована.
- STOP_CONDITIONS:
  - Не создавать универсальную шкалу вне контракта.

---

### TASK: E04-T11-TOPK-SELECTION

- GOAL: Реализовать Top-K selection.
- CONTEXT: Fetch применяется только к лидерам.
- ALLOWED_FILES:
  - `src/search/topk.py`
  - `tests/search/test_topk.py`
- FORBIDDEN:
  - Fetch.
  - Parse.
- IMPLEMENTATION DETAILS:
  - `select_top_k(candidates, query, k, relevance_fn, quality_fn)`.
  - Итоговый score:
    `0.7 * relevance + 0.3 * quality`.
  - Не более `k`.
  - Стабильный порядок при равенстве.
- TESTS:
  - Top-K.
  - Stable ordering.
- ACCEPTANCE:
  - Top-K selection работает.
- STOP_CONDITIONS:
  - Не скачивать автоматически всех кандидатов.

---

### TASK: E04-T12-URL-NORMALIZATION

- GOAL: Реализовать канонизацию URL.
- CONTEXT: URL-дубликаты блокируются до fetch.
- ALLOWED_FILES:
  - `src/search/url_normalize.py`
  - `tests/search/test_url_normalize.py`
- FORBIDDEN:
  - Сеть.
- IMPLEMENTATION DETAILS:
  - Нижний регистр схемы/хоста.
  - Удаление стандартных портов.
  - Удаление fragment.
  - Сортировка query parameters.
  - Удаление `utm_*`, `yclid`, `gclid`, `fbclid`.
  - Унификация trailing slash.
  - Нормализация percent-encoding.
- TESTS:
  - Fragment/tracking.
  - Query sorting.
  - Trailing slash.
- ACCEPTANCE:
  - URL normalization работает.
- STOP_CONDITIONS:
  - Не считать fragment частью identity без разрешения.

---

### TASK: E04-T13-SOURCE-IDENTITY

- GOAL: Нормализация идентификаторов.
- CONTEXT: DOI/PMID/arXiv используются для dedup.
- ALLOWED_FILES:
  - `src/search/source_identity.py`
  - `tests/search/test_source_identity.py`
- FORBIDDEN:
  - БД.
  - LLM.
- IMPLEMENTATION DETAILS:
  - `normalize_identifier(key, value)`.
  - `extract_identifiers(raw)`.
  - Поддержать DOI/PMID/arXiv.
- TESTS:
  - DOI.
  - Неизвестные ключи.
- ACCEPTANCE:
  - Идентификаторы нормализованы.
- STOP_CONDITIONS:
  - Не добавлять новые identity types вне контракта.

---

### TASK: E04-T14-SOURCE-RELATION-HELPERS

- GOAL:
  Создать вспомогательные функции `SourceRelation` и консервативного
  подсчёта независимых источников.

- CONTEXT:
  Независимость должна считаться консервативно.

  Правила:
  - `COPY`, `REWRITE`, `SAME_PRIMARY` могут объединять источники
    в один зависимый кластер.
  - `CITATION` означает зависимость от цитируемого первоисточника.
  - `UNKNOWN` не является доказательством независимости и не объединяет
    источники через Union-Find.

- ALLOWED_FILES:
  - `src/search/source_relations.py`
  - `tests/search/test_source_relations.py`

- FORBIDDEN:
  - Изменение схемы БД.
  - Изменение модели SourceRelation.
  - Произвольное повышение independent_source_count.

- IMPLEMENTATION DETAILS:
  - Создай:
    `INDEPENDENCE_MERGING_RELATIONS = {COPY, REWRITE, SAME_PRIMARY}`.
  - Реализуй `is_dependent_relation(relation_type)`.
  - Реализуй:
    `count_independent_sources(source_ids, relations)`.
  - Union-Find разрешено использовать только для:
    `COPY`, `REWRITE`, `SAME_PRIMARY`.
  - `CITATION` не участвует в обычном Union-Find объединении.
  - Для `CITATION` учитывай направление зависимости:
    зависимый документ не создаёт дополнительное независимое подтверждение.
  - Если цитируемый primary source присутствует в пуле,
    зависимый источник не увеличивает независимый count сверх primary.
  - Если цитируемый primary source отсутствует,
    `CITATION`-источник не должен автоматически считаться новым
    независимым подтверждением.
  - `UNKNOWN` полностью игнорируется при вычислении
    финального `independent_source_count`.
  - Неизвестный тип relation не должен автоматически считаться
    независимым или зависимым без явного правила контракта.
  - Функция должна возвращать число независимых подтверждений
    после применения этих правил.

- TESTS:
  - 5 полностью независимых источников → `5`.
  - 4 копии одного источника → `1`.
  - `COPY` между двумя источниками → `1`.
  - `REWRITE` между двумя источниками → `1`.
  - `SAME_PRIMARY` между двумя источниками → `1`.
  - `CITATION` с присутствующим primary → зависимый источник
    не увеличивает independent count.
  - `CITATION` без присутствующего primary → источник не становится
    автоматически независимым подтверждением.
  - `UNKNOWN` не увеличивает independent count.
  - `UNKNOWN` не объединяет два независимых источника.
  - Смешанный набор независимых и зависимых источников.
  - Повторный вызов даёт тот же результат.

- ACCEPTANCE:
  Модель независимости соответствует консервативному правилу ТЗ.
  Ни `CITATION`, ни `UNKNOWN` не могут искусственно увеличить
  число независимых подтверждений.

- STOP_CONDITIONS:
  - Если требуется считать каждый URL независимым источником:
    `STOP → REPORT → WAIT`.
  - Если для корректной обработки `CITATION` требуется изменение схемы:
    `STOP → REPORT → WAIT`.

---

### TASK: E04-T15-DEDUP-URL-IDENTIFIER

- GOAL: Дедупликация по URL и идентификаторам.
- CONTEXT: Первый уровень dedup до fetch.
- ALLOWED_FILES:
  - `src/search/dedup.py`
  - `tests/search/test_dedup_url_identifier.py`
- FORBIDDEN:
  - Content hash.
- IMPLEMENTATION DETAILS:
  - `deduplicate_candidates(candidates, seen_urls, seen_identifiers)`.
  - Используй `normalize_url`.
  - Используй DOI/PMID/arXiv.
  - Явно зафиксируй обновление входных множеств.
- TESTS:
  - Один canonical URL → один кандидат.
  - Один DOI → один кандидат.
- ACCEPTANCE:
  - URL/identifier dedup работает.
- STOP_CONDITIONS:
  - Не применять semantic dedup здесь.

---

### TASK: E04-T16-DEDUP-CONTENT-HASH

- GOAL: Content-hash dedup.
- CONTEXT: Дубликат документа не сохраняется повторно.
- ALLOWED_FILES:
  - `src/search/content_hash.py`
  - `tests/search/test_content_hash.py`
- FORBIDDEN:
  - Изменение Document schema.
- IMPLEMENTATION DETAILS:
  - `compute_content_hash(clean_text)`.
  - Хэшировать очищенный текст.
  - `is_duplicate_content(content_hash, existing_hashes)`.
- TESTS:
  - Одинаковый текст.
  - Разный текст.
- ACCEPTANCE:
  - Content hash работает.
- STOP_CONDITIONS:
  - Не хэшировать raw HTML.

---

### TASK: E04-T17-NEAR-DUPLICATE

- GOAL: Детерминированный near-duplicate.
- CONTEXT: Копии должны связываться как зависимые источники.
- ALLOWED_FILES:
  - `src/search/near_duplicate.py`
  - `tests/search/test_near_duplicate.py`
- FORBIDDEN:
  - Внешние ML-библиотеки.
- IMPLEMENTATION DETAILS:
  - `jaccard_similarity(text_a, text_b)`.
  - `is_near_duplicate(text_a, text_b, threshold=0.9)`.
  - Токенизация lowercase + небуквенные разделители.
- TESTS:
  - Идентичные тексты → `1.0`.
  - Разные → низкий score.
  - Threshold `0.9`.
- ACCEPTANCE:
  - Near-duplicate детерминирован.
- STOP_CONDITIONS:
  - Embeddings запрещены.

---

### TASK: E04-T18-QUERY-NORMALIZATION

- GOAL: Нормализация поискового запроса.
- CONTEXT: Используется fingerprint/similarity.
- ALLOWED_FILES:
  - `src/search/query_normalize.py`
  - `tests/search/test_query_normalize.py`
- FORBIDDEN:
  - БД.
  - LLM.
- IMPLEMENTATION DETAILS:
  - lowercase.
  - удалить лишние пробелы/пунктуацию.
  - сортировать токены.
  - вернуть строку токенов через пробел.
- TESTS:
  - Детерминированность.
  - Повторный вызов.
- ACCEPTANCE:
  - Query normalization работает.
- STOP_CONDITIONS:
  - Не сохранять исходный порядок как часть fingerprint без разрешения.

---

### TASK: E04-T19-QUERY-FINGERPRINT

- GOAL: Реализовать `query_fingerprint`.
- CONTEXT: Fingerprint строго соответствует ТЗ.
- ALLOWED_FILES:
  - `src/search/query_fingerprint.py`
  - `tests/search/test_query_fingerprint.py`
- FORBIDDEN:
  - Альтернативные алгоритмы.
- IMPLEMENTATION DETAILS:
  - Параметры:
    `normalized_query_text`,
    `source_scope`,
    `task_purpose`,
    `applied_filters`,
    `exclusion_terms`,
    `time_range_constraint`,
    `geography_constraint`,
    `expected_material_type`.
  - Каждый параметр приводится к строке и trim.
  - Разделитель `|`.
  - `payload = "|".join([...])`.
  - SHA256.
- TESTS:
  - Одинаковые параметры.
  - Изменение каждого параметра.
  - Trim.
- ACCEPTANCE:
  - Fingerprint соответствует ТЗ.
- STOP_CONDITIONS:
  - Не менять порядок полей.

---

### TASK: E04-T20-QUERY-SIMILARITY

- GOAL: QuerySimilarityProvider.
- CONTEXT: Многофакторная защита от похожих запросов.
- ALLOWED_FILES:
  - `src/search/query_similarity.py`
  - `tests/search/test_query_similarity.py`
- FORBIDDEN:
  - LLM.
  - Embeddings.
- IMPLEMENTATION DETAILS:
  - Абстрактный `QuerySimilarityProvider`.
  - `TokenJaccardQuerySimilarity`.
  - Нормализованные токены.
  - `[0.0, 1.0]`.
- TESTS:
  - Идентичные → `1.0`.
  - Полностью разные → `0.0`.
- ACCEPTANCE:
  - Similarity provider работает.
- STOP_CONDITIONS:
  - Не добавлять ML dependency.

---

### TASK: E04-T21-QUERY-LOOP-PREVENTION

- GOAL:
  Реализовать многофакторную проверку повторных/похожих запросов
  с обязательным основанием `ResearchGap`.

- CONTEXT:
  Отказ Core должен использовать унифицированную иерархию ошибок.
  Текстовые статусы не являются транспортным Error Contract.

- ALLOWED_FILES:
  - `src/search/query_loop.py`
  - `tests/search/test_query_loop.py`

- FORBIDDEN:
  - Реальное выполнение поиска.
  - Прямое формирование JSON-RPC.
  - Собственная транспортная обработка ошибок.

- IMPLEMENTATION DETAILS:
  - `QueryCheckResult` может использоваться только для успешного
    положительного результата проверки, если это соответствует
    контракту вызывающего слоя.
  - Для блокирующих условий `check_query` обязан выбрасывать
    соответствующее исключение `SearchCoreError`.
  - Не использовать значения вроде:
    `QUERY_REJECTED`,
    `BUDGET`,
    `NO_OPEN_RESEARCH_GAP`
    как замену стандартному Core Error.
  - Если основание отсутствует:
    `QueryRejectedError`.
  - Если fingerprint уже выполнен:
    `QueryRejectedError`
    с внутренней причиной `QUERY_ALREADY_EXECUTED`.
  - Если similarity выше порога:
    `QueryRejectedError`
    с внутренней причиной `QUERY_TOO_SIMILAR`.
  - Если покрытие уже существует:
    `QueryRejectedError`
    с внутренней причиной `QUERY_COVERAGE_ALREADY_EXISTS`.
  - Если бюджет недоступен:
    `BudgetExhaustedError`.
  - Если `CONFIG_CONTEXT_INSUFFICIENT` является требуемым отказом
    согласно общему Error Contract, использовать соответствующий
    стандартизированный Core Error.
  - Ошибка должна содержать machine-readable системный код/причину,
    пригодную для дальнейшего преобразования в JSON-RPC Error.
  - MCP/transport layer не реализуется в этой TASK.
  - `check_query` не имеет права самостоятельно формировать JSON-RPC.

- TESTS:
  - Отказ при отсутствии ResearchGap.
  - Разрешение при наличии open gap.
  - Отказ exact duplicate.
  - Отказ similar query.
  - Отказ coverage already exists.
  - `BudgetExhaustedError` при нулевом бюджете.
  - Проверка типа исключения.
  - Проверка machine-readable системного кода/причины.
  - Проверка отсутствия JSON-RPC логики в Search Core.

- ACCEPTANCE:
  Loop prevention работает, использует ResearchGap и возвращает
  стандартизированные Core Errors для блокирующих условий.

- STOP_CONDITIONS:
  - Если для изменения контракта требуется изменение MCP:
    `STOP → REPORT → WAIT`.
  - Если хочется вернуть произвольные текстовые статусы вместо Core Errors:
    `STOP → REPORT → WAIT`.

---

### TASK: E04-T22-FETCH-TRANSPORT-ABSTRACTION

- GOAL: Создать абстракцию скачивания документов.
- CONTEXT: Fetch отделён от транспорта.
- ALLOWED_FILES:
  - `src/search/fetch.py`
  - `tests/search/test_fetch.py`
- FORBIDDEN:
  - Реальная сеть.
- IMPLEMENTATION DETAILS:
  - `FetchTransport.fetch(url) -> RawDocument`.
  - `FakeFetchTransport`.
- TESTS:
  - Подготовленный результат.
  - Ошибка неизвестного URL.
- ACCEPTANCE:
  - Fetch abstraction готова.
- STOP_CONDITIONS:
  - CAPTCHA обход запрещён.

---

### TASK: E04-T23-HTML-PARSE-CLEAN

- GOAL: HTML clean/parser.
- CONTEXT: Raw HTML не должен попадать в LLM/Evidence.
- ALLOWED_FILES:
  - `src/search/parse.py`
  - `tests/search/test_parse.py`
- FORBIDDEN:
  - Внешние парсеры.
  - LLM.
- IMPLEMENTATION DETAILS:
  - Стандартный `html.parser`.
  - `ParsedDocument(title, text)`.
  - Игнорировать `script`, `style`, `noscript`.
  - Извлекать `p`, `li`, `h1`…`h6`, `td`.
  - title из `<title>`.
  - Нормализовать пробелы/переводы строк.
- TESTS:
  - Script не попадает в текст.
  - Title.
  - Пустой HTML.
- ACCEPTANCE:
  - Parse/clean работает.
- STOP_CONDITIONS:
  - Raw HTML не становится Evidence.

---

### TASK: E04-T24-CHUNKING-CONFIG

- GOAL: Конфигурация чанкинга.
- CONTEXT: Параметры конфигурируемы.
- ALLOWED_FILES:
  - `src/search/chunking_config.py`
  - `tests/search/test_chunking_config.py`
- FORBIDDEN:
  - Сам алгоритм чанкинга.
- IMPLEMENTATION DETAILS:
  - `ChunkingConfig`.
  - `min_tokens`,
    `max_tokens`,
    `overlap_tokens`,
    `context_window`.
  - Валидация диапазонов.
- TESTS:
  - Валидные значения.
  - Недопустимый overlap.
- ACCEPTANCE:
  - Конфигурация валидна.
- STOP_CONDITIONS:
  - Не разрешать неподдерживаемые значения.

---

### TASK: E04-T25-DETERMINISTIC-CHUNKER

- GOAL: Детерминированный структурный чанкинг.
- CONTEXT: Стабильные chunk_id.
- ALLOWED_FILES:
  - `src/search/chunker.py`
  - `tests/search/test_chunker.py`
- FORBIDDEN:
  - LLM.
  - Semantic chunking.
- IMPLEMENTATION DETAILS:
  - `DocumentChunk`.
  - Поля:
    `chunk_id`,
    `document_id`,
    `text`,
    `token_estimate`,
    `char_start`,
    `char_end`,
    `heading_path`,
    `page_number`,
    `position_index`,
    `overlap_group_id`,
    `is_overlap`,
    `numeric_signatures`,
    `metadata`.
  - `estimate_tokens(text)`.
  - `chunk_text(document_id, text, config)`.
  - Разбиение по пустым строкам и логическим блокам.
  - Markdown heading_path.
  - `chunk_id = SHA256(document_id + ":" + position_index + ":" + text)`.
  - Детерминированный overlap_group_id.
- TESTS:
  - Стабильный chunk_id.
  - Пустой текст.
  - heading_path.
- ACCEPTANCE:
  - Чанкинг детерминирован.
- STOP_CONDITIONS:
  - UUID для chunk_id запрещён.

---

### TASK: E04-T26-OVERLAP-METADATA

- GOAL: Реализовать overlap metadata.
- CONTEXT: Перекрытие фиксируется явно.
- ALLOWED_FILES:
  - `src/search/overlap.py`
  - `tests/search/test_overlap.py`
- FORBIDDEN:
  - Изменение исходных чанков.
- IMPLEMENTATION DETAILS:
  - `create_overlap_segments(chunks, overlap_tokens)`.
  - Связанные сегменты получают:
    `overlap_group_id`,
    `is_overlap=True`.
  - Оригинальные чанки не изменяются.
- TESTS:
  - Соседние чанки.
  - `is_overlap`.
  - `overlap_group_id`.
- ACCEPTANCE:
  - Overlap metadata работает.
- STOP_CONDITIONS:
  - Не удалять оригинальные чанки.

---

### TASK: E04-T27-NUMERIC-SIGNATURES

- GOAL: Извлечение числовых подписей.
- CONTEXT: Детерминированные данные для contradiction analysis.
- ALLOWED_FILES:
  - `src/search/numeric_signatures.py`
  - `tests/search/test_numeric_signatures.py`
- FORBIDDEN:
  - LLM.
- IMPLEMENTATION DETAILS:
  - `extract_numeric_signatures(text)`.
  - Поля:
    `value`, `unit`, `raw`, `type`.
  - Типы:
    `PRICE`, `PERCENT`, `DATE`, `DOSAGE`, `SPEED`, `COUNT`, `OTHER`.
  - Детерминированная сортировка.
- TESTS:
  - Цена.
  - Процент.
  - Дата.
- ACCEPTANCE:
  - Numeric signatures работают.
- STOP_CONDITIONS:
  - Не использовать LLM.

---

### TASK: E04-T28-NORMALIZER-INTERFACE

- GOAL: Создать `RetrievalTextNormalizer`.
- CONTEXT: Query и Document должны проходить согласованную нормализацию.
- ALLOWED_FILES:
  - `src/search/normalizer/__init__.py`
  - `src/search/normalizer/base.py`
  - `tests/search/test_normalizer_base.py`
- FORBIDDEN:
  - Конкретные реализации.
- IMPLEMENTATION DETAILS:
  - Абстрактный `RetrievalTextNormalizer`.
  - Методы:
    `name()`,
    `version()`,
    `stopword_version()`,
    `normalize_text(text)`,
    `normalize_query(query)`.
- TESTS:
  - Нельзя инстанцировать абстрактный класс.
- ACCEPTANCE:
  - Интерфейс готов.
- STOP_CONDITIONS:
  - Не привязывать к одной библиотеке.

---

### TASK: E04-T29-BASIC-NORMALIZER

- GOAL: Реализовать `BasicNormalizer`.
- CONTEXT: Fallback normalizer.
- ALLOWED_FILES:
  - `src/search/normalizer/basic.py`
  - `tests/search/test_basic_normalizer.py`
- FORBIDDEN:
  - Русская морфология.
- IMPLEMENTATION DETAILS:
  - `name() = basic`.
  - `version() = 1.0.0`.
  - `stopword_version() = none`.
  - lowercase.
  - удаление пунктуации.
  - split по пробелам.
  - удаление пустых токенов.
- TESTS:
  - Базовая нормализация.
  - Детерминированность.
- ACCEPTANCE:
  - BasicNormalizer работает.
- STOP_CONDITIONS:
  - Не использовать скрытые словари.

---

### TASK: E04-T30-RUSSIAN-MORPHOLOGY-NORMALIZER

- GOAL: Реализовать детерминированный русский normalizer.
- CONTEXT:
  Русский поиск должен находить базовые словоформы без сети
  и обязательной тяжёлой зависимости.
- ALLOWED_FILES:
  - `src/search/normalizer/russian.py`
  - `tests/search/test_russian_normalizer.py`
- FORBIDDEN:
  - Недетерминированные модели.
  - Сетевые вызовы.
- IMPLEMENTATION DETAILS:
  - `RussianMorphologyNormalizer`.
  - `name() = russian_suffix`.
  - `version() = 1.0.0`.
  - `stopword_version() = ru-stopwords-1.0.0`.
  - Детерминированный набор русских стоп-слов.
  - Базовая токенизация.
  - Удаление стоп-слов.
  - Детерминированный суффиксный стек.
  - Если слово после удаления короче 3 символов,
    суффикс не удаляется.
- TESTS:
  - Стоп-слова.
  - `"отзывы"` → `"отзыв"`.
  - `"цена"` и `"цену"`.
  - `"доставка"` и `"доставке"`.
- ACCEPTANCE:
  - Русский normalizer детерминирован.
- STOP_CONDITIONS:
  - Если тест требует неутверждённую внешнюю библиотеку:
    `STOP → REPORT → WAIT`.

---

### TASK: E04-T31-FTS-SCHEMA-MIGRATION

- GOAL:
  Создать миграцию FTS5 и метаданных индекса.

- CONTEXT:
  Миграция добавляет Search Core readiness к EPIC-02.

- ALLOWED_FILES:
  - `src/data/migrations/005_search_fts.sql`
  - `tests/search/conftest.py`
  - `tests/search/test_fts_schema.py`

- FORBIDDEN:
  - Изменение предметных таблиц EPIC-02 без отдельного разрешения.

- IMPLEMENTATION DETAILS:
  - Создай `BM25IndexMeta`.
  - Поля:
    - `index_key TEXT PRIMARY KEY`
    - `normalizer_version TEXT NOT NULL`
    - `index_version INTEGER NOT NULL DEFAULT 0`
    - `language TEXT NOT NULL`
    - `stopword_version TEXT NOT NULL`
    - `updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`
  - Имя `normalizer_version` является утверждённым контрактом.
  - Не заменять его на `tokenizer_version`.
  - Создай `DocumentChunkFTS`.
  - Поля:
    - `normalized_text`
    - `chunk_id UNINDEXED`
    - `document_id UNINDEXED`
  - FTS5 используется как индекс поиска кандидатов.
  - Финальное BM25-ранжирование не должно зависеть от
    встроенной функции SQLite `bm25()`.
  - Создай `search_conn`.
  - Пути к миграциям вычисляй относительно файла теста.

- TESTS:
  - `BM25IndexMeta` существует.
  - `DocumentChunkFTS` существует.
  - `normalizer_version` существует.
  - FTS5 доступен.
  - Если FTS5 отсутствует, тест падает с понятной причиной.

- ACCEPTANCE:
  - FTS5 schema готова.
  - Метаданные соответствуют утверждённому контракту.

- STOP_CONDITIONS:
  - Если SQLite не поддерживает FTS5:
    `STOP → REPORT → WAIT`.
  - Если требуется изменить имя `normalizer_version`:
    `STOP → REPORT → WAIT`.

---

### TASK: E04-T32-FTS-INDEX-LIFECYCLE

- GOAL:
  Реализовать жизненный цикл FTS5 candidate index.

- CONTEXT:
  Индекс должен быть согласован с DocumentChunk и metadata.

- ALLOWED_FILES:
  - `src/search/fts_index.py`
  - `tests/search/test_fts_index_lifecycle.py`

- FORBIDDEN:
  - Прямая запись в обход транзакционного управления.
  - Финальное BM25-ранжирование.
  - Встроенный SQLite `bm25()` как обязательный score.

- IMPLEMENTATION DETAILS:
  - `index_chunks(conn, chunks, normalizer, language)`.
  - `delete_document_from_index(conn, document_id)`.
  - `rebuild_all(conn, chunks, normalizer, language)`.
  - `cleanup_study_from_index(conn, study_id)`.
  - `get_index_meta(conn, index_key)`.
  - `index_chunks` использует:
    `normalize_text`,
    `version`,
    `stopword_version`.
  - Перед вставкой удаляются строки соответствующих chunk_id.
  - `BM25IndexMeta.index_version` увеличивается.
  - Обновляются:
    `normalizer_version`,
    `index_version`,
    `language`,
    `stopword_version`.
  - `cleanup_study_from_index` удаляет только строки документов,
    принадлежащих указанному Study через `StudyDocumentLink`.
  - Все операции используют транзакцию вызывающего слоя.
  - TASK не должна самостоятельно вводить внешний transaction manager.

- TESTS:
  - Добавление чанка.
  - Повторная индексация без дублей.
  - Удаление документа.
  - `rebuild_all`.
  - `cleanup_study_from_index`.
  - Обновление всех metadata.
  - Перестроение при смене normalizer version.
  - Изоляция Study.

- ACCEPTANCE:
  - FTS lifecycle работает.
  - Индекс соответствует нормализованному тексту.
  - Метаданные версии корректны.

- STOP_CONDITIONS:
  - Отдельный index file вне SQLite запрещён.
  - Если требуется изменение EPIC-02 schema:
    `STOP → REPORT → WAIT`.

---

### TASK: E04-T33-BM25-RETRIEVAL-PROVIDER

- GOAL:
  Реализовать `BM25RetrievalProvider` по контракту `RetrievalProvider`.

- CONTEXT:
  MVP retrieval должен работать CPU-only.
  FTS5 используется для быстрого извлечения кандидатов.
  Финальный BM25 score рассчитывается детерминированным Python-кодом.

- ALLOWED_FILES:
  - `src/search/bm25_provider.py`
  - `tests/search/test_bm25_provider.py`

- FORBIDDEN:
  - Embeddings.
  - Vector DB.
  - GPU.
  - Обязательные внешние ML-библиотеки.
  - Использование встроенного SQLite `bm25(DocumentChunkFTS)`
    как финального рейтинга MVP.

- IMPLEMENTATION DETAILS:
  - Создай замороженный `dataclass` `ProviderCapabilities`.
  - Реализуй `BM25RetrievalProvider`.
  - Конструктор принимает:
    `normalizer`,
    `language`.
  - Методы:
    `name()`,
    `capabilities()`,
    `search(conn, study_id, query, filters, limit)`,
    `index(conn, chunks)`,
    `delete(conn, document_id)`,
    `is_available()`.
  - `search` обязан нормализовать запрос тем же normalizer,
    которым индексировался текст.
  - Построй безопасный FTS5 candidate query:
    каждый нормализованный токен экранируется,
    токены объединяются через `OR`.
  - FTS5 используется только для получения множества кандидатов.
  - Не использовать результат SQLite `bm25()` как финальный score.
  - После получения кандидатов извлеки нормализованный текст,
    необходимый для финального расчёта.
  - Реализуй детерминированную BM25-функцию в Python.
  - Формула должна соответствовать стандартной BM25:
    `score(D,Q) = Σ IDF(q) * ((f(q,D) * (k1 + 1)) /
    (f(q,D) + k1 * (1 - b + b * |D| / avgdl)))`
  - Значения `k1` и `b` должны быть фиксированными и задокументированными
    внутри реализации.
  - IDF и средняя длина документа рассчитываются детерминированно
    на текущем наборе допустимых candidate chunks.
  - В расчёт не должны попадать документы/чанки вне текущего Study.
  - Для фильтра `document_id` применять дополнительную фильтрацию.
  - Финальная сортировка выполняется Python BM25 score.
  - При равенстве score использовать стабильный deterministic tie-breaker,
    например `chunk_id`.
  - `search` возвращает полностью заполненные `DocumentChunk`.
  - `numeric_signatures` корректно восстанавливаются.
  - `metadata` корректно восстанавливается.
  - Повреждённые `numeric_signatures` → `[]`.
  - Повреждённые `metadata` → `{}`.
  - `index` делегирует `fts_index.index_chunks`.
  - `delete` делегирует `fts_index.delete_document_from_index`.
  - `cleanup_study` делегирует `fts_index.cleanup_study_from_index`.
  - Пустой запрос возвращает пустой список.

- TESTS:
  - Все методы контракта существуют.
  - Индексация.
  - FTS candidate retrieval.
  - Финальный Python BM25 score.
  - Проверка, что SQLite `bm25()` не используется как источник
    финального score.
  - Поиск по русской словоформе.
  - Изоляция Study.
  - Фильтр Document.
  - Удаление.
  - Cleanup Study.
  - Пустой запрос.
  - Полностью заполненный `DocumentChunk`.
  - Детерминированный порядок при одинаковом score.
  - Проверка BM25 на небольшом заранее рассчитанном fixture.
  - Проверка стабильности score при повторном запуске.
  - Проверка отсутствия внешней BM25/ML dependency.

- ACCEPTANCE:
  `BM25RetrievalProvider`:
  - соответствует `RetrievalProvider`;
  - использует FTS5 для candidate retrieval;
  - рассчитывает финальный BM25 score в Python;
  - детерминирован;
  - CPU-only;
  - изолирован по Study/Document.

- STOP_CONDITIONS:
  - Если для корректного retrieval требуется embeddings:
    `STOP → REPORT → WAIT`.
  - Если предлагается использовать SQLite `bm25()` как финальный score:
    `STOP → REPORT → WAIT`.
  - Если требуется C-extension tokenizer:
    `STOP → REPORT → WAIT`.
  - Если требуется внешняя библиотека, не утверждённая Baseline:
    `STOP → REPORT → WAIT`.

---

### TASK: E04-T34-STUDY-DOCUMENT-ISOLATION-TEST

- GOAL:
  Создать отдельные тесты изоляции поиска по Study и Document.

- CONTEXT:
  Тестовая TASK. Исходный код не менять.

- ALLOWED_FILES:
  - `tests/search/test_study_document_isolation.py`

- FORBIDDEN:
  - Изменение исходного кода.

- IMPLEMENTATION DETAILS:
  - Создай два Study в одном Project.
  - Создай два Document.
  - Каждый Document привяжи только к своему Study.
  - Проиндексируй оба.
  - Выполни поиск Study A.
  - Проверь отсутствие Document B.
  - Проверь фильтрацию `document_id`.

- TESTS:
  - Только тестовый файл.

- ACCEPTANCE:
  - Изоляция поиска подтверждена.

- STOP_CONDITIONS:
  - Если тест требует изменения schema:
    `STOP → REPORT → WAIT`.

---

### TASK: E04-T35-FTS-CONSISTENCY-TEST

- GOAL:
  Создать тесты консистентности DocumentChunk и FTS candidate index.

- CONTEXT:
  Тестовая TASK. Исходный код не менять.

- ALLOWED_FILES:
  - `tests/search/test_fts_consistency.py`

- FORBIDDEN:
  - Изменение исходного кода.

- IMPLEMENTATION DETAILS:
  - После `index` каждый DocumentChunk имеет соответствующую FTS запись.
  - Повторный index не создаёт дублей.
  - `delete(document_id)` удаляет связанные FTS rows.
  - `rebuild_all` не оставляет stale rows.
  - `cleanup_study_from_index` удаляет только нужный Study.
  - Смена normalizer version отражается в `BM25IndexMeta`.
  - FTS index содержит нормализованный текст.
  - Финальный BM25 score не является предметом этой TASK.

- TESTS:
  - Только тестовый файл.

- ACCEPTANCE:
  - DocumentChunk ↔ FTS candidate index консистентны.

- STOP_CONDITIONS:
  - Если тест требует изменения migration:
    `STOP → REPORT → WAIT`.

---

### TASK: E04-T36-EVIDENCE-EXTRACTION

- GOAL:
  Реализовать детерминированное создание Evidence из найденных чанков.

- CONTEXT:
  Evidence создаётся из target chunk и контекстных чанков.

- ALLOWED_FILES:
  - `src/search/evidence_builder.py`
  - `tests/search/test_evidence_builder.py`

- FORBIDDEN:
  - LLM.
  - Изменение report validation.

- IMPLEMENTATION DETAILS:
  - `compute_evidence_hash(text, target_chunk_id, document_id)`.
  - `build_context_window(chunks, target_chunk_id, context_window=1)`.
  - Контекст:
    previous + target + next.
  - Возвращай:
    `chunk_id`,
    `text`,
    `is_target`.
  - Context chunk не является самостоятельным Evidence.
- TESTS:
  - `[-1, target, +1]`.
  - Детерминированный hash.
  - Duplicate hash.
- ACCEPTANCE:
  - Target/context различаются.
- STOP_CONDITIONS:
  - Evidence без chunk provenance запрещён.

---

### TASK: E04-T37-CACHE-SERVICE

- GOAL:
  Реализовать CacheService и полную статистику.

- CONTEXT:
  Используется `CacheEntry` из EPIC-02.

- ALLOWED_FILES:
  - `src/search/cache_service.py`
  - `tests/search/test_cache_service.py`

- FORBIDDEN:
  - Реальная сеть.

- IMPLEMENTATION DETAILS:
  - `CacheService`.
  - `hit_count`.
  - `miss_count`.
  - `make_cache_key`.
  - `get_entry`.
  - `record_miss`.
  - `put_entry`.
  - `cleanup_expired`.
  - `get_statistics`.
  - Статистика:
    `total_entries`,
    `hit_count`,
    `miss_count`,
    `expired_count`,
    `total_size_bytes`,
    `oldest_entry`,
    `newest_entry`.
  - `total_size_bytes` по response.
  - oldest/newest по created_at.

- TESTS:
  - Save/read.
  - Expired.
  - Hit.
  - Miss.
  - Cleanup.
  - Все семь полей статистики.

- ACCEPTANCE:
  - Cache service работает.

- STOP_CONDITIONS:
  - Внешние cache files запрещены.

---

### TASK: E04-T38-BUDGET-SERVICE

- GOAL:
  Реализовать атомарное списание многомерного бюджета.

- CONTEXT:
  Бюджет хранится в `ResearchSession.budget_state`.
  Списание является частью более крупной бизнес-операции.

- ALLOWED_FILES:
  - `src/search/budget_service.py`
  - `tests/search/test_budget_service.py`

- FORBIDDEN:
  - Изменение схемы БД.
  - LLM.
  - Самостоятельный `COMMIT`.
  - Самостоятельный `ROLLBACK`.
  - Создание отдельной транзакции поверх транзакции вызывающего слоя.

- IMPLEMENTATION DETAILS:
  - Компоненты:
    `step_budget`,
    `network_budget`,
    `fetch_budget`,
    `tool_call_budget`,
    `llm_call_budget`,
    `llm_token_budget`,
    `time_budget`.
  - `load_budget(conn, session_id)`.
  - `save_budget(conn, session_id, budget_state)`.
  - `deduct_budget(conn, session_id, component, amount)`.
  - `conn` является соединением вызывающего слоя.
  - `deduct_budget` работает внутри уже открытой транзакции
    вызывающей бизнес-операции.
  - Проверка остатка и изменение состояния выполняются атомарно
    в рамках этой транзакции.
  - Budget Service НЕ имеет права самостоятельно делать COMMIT.
  - Budget Service НЕ имеет права самостоятельно делать ROLLBACK.
  - Владелец транзакции — вызывающий слой.
  - При нехватке бюджета бросай `BudgetExhaustedError`.

- TESTS:
  - Достаточный лимит.
  - Нулевой лимит.
  - Повторное списание.
  - Проверка, что service не завершает транзакцию самостоятельно.
  - Проверка rollback вызывающего слоя отменяет списание.
  - Проверка commit вызывающего слоя сохраняет списание.

- ACCEPTANCE:
  Budget deduction атомарно входит в транзакцию вызывающей операции
  и не нарушает transaction ownership.

- STOP_CONDITIONS:
  - Если для реализации требуется самостоятельный COMMIT:
    `STOP → REPORT → WAIT`.
  - Если требуется отдельная транзакция:
    `STOP → REPORT → WAIT`.

---

### TASK: E04-T39-COVERAGE-CALCULATOR

- GOAL: Детерминированный CoverageCalculator.
- CONTEXT: Используется SufficiencyEvaluator.
- ALLOWED_FILES:
  - `src/search/coverage.py`
  - `tests/search/test_coverage.py`
- FORBIDDEN:
  - LLM.
- IMPLEMENTATION DETAILS:
  - `CoverageMetrics`.
  - `calculate_coverage`.
  - `independent_source_count` через `count_independent_sources`.
  - Данные текущего Study.
  - `evidence_count`.
  - `contradiction_count`.
  - attribute/question coverage.
- TESTS:
  - Пустой Study.
  - Evidence count.
  - Пять копий → independent count `1`.
  - `UNKNOWN` не увеличивает independent count.
  - `CITATION` не создаёт ложное независимое подтверждение.
- ACCEPTANCE:
  - CoverageCalculator детерминирован.
- STOP_CONDITIONS:
  - LLM для coverage запрещён.

---

### TASK: E04-T40-SUFFICIENCY-EVALUATOR

- GOAL: Детерминированный SufficiencyEvaluator.
- CONTEXT: Только Core принимает решение продолжать/останавливать.
- ALLOWED_FILES:
  - `src/search/sufficiency.py`
  - `tests/search/test_sufficiency.py`
- FORBIDDEN:
  - LLM.
  - Переопределение Core decision.
- IMPLEMENTATION DETAILS:
  - `SufficiencyInput`.
  - `SufficiencyDecision`.
  - `evaluate_sufficiency`.
  - `budget_exhausted=True` → `STOP_BUDGET`.
  - `available_sources == 0` → `STOP_NO_AVAILABLE_SOURCES`.
  - Низкий information gain → `STOP_NO_INFORMATION_GAIN`.
  - Достаточное покрытие → `STOP_SUFFICIENT`.
  - Иначе `CONTINUE`.
  - `save_sufficiency_evaluation`.
- TESTS:
  - Все stop states.
  - Сохранение.
- ACCEPTANCE:
  - SufficiencyEvaluator детерминирован.
- STOP_CONDITIONS:
  - LLM override запрещён.

---

### TASK: E04-T41-INFORMATION-GAIN

- GOAL: Расчёт information gain.
- CONTEXT: Остановка бесперспективного поиска.
- ALLOWED_FILES:
  - `src/search/information_gain.py`
  - `tests/search/test_information_gain.py`
- FORBIDDEN:
  - LLM.
- IMPLEMENTATION DETAILS:
  - `calculate_information_gain(previous_metrics, current_metrics)`.
  - Учитывай:
    `evidence_count`,
    `independent_source_count`.
  - Пустые previous + непустые current → `1.0`.
  - Нет прироста → `0.0`.
  - Диапазон `[0.0, 1.0]`.
- TESTS:
  - Положительный gain.
  - Нулевой gain.
- ACCEPTANCE:
  - Information gain работает.
- STOP_CONDITIONS:
  - Недетерминированность запрещена.

---

### TASK: E04-T42-RESEARCH-GAP-OPS

- GOAL: Операции с ResearchGap.
- CONTEXT: Только открытый ResearchGap является основанием нового поиска.
- ALLOWED_FILES:
  - `src/search/research_gap_ops.py`
  - `tests/search/test_research_gap_ops.py`
- FORBIDDEN:
  - LLM.
  - Автоматический запуск сети.
- IMPLEMENTATION DETAILS:
  - `create_research_gap`.
  - `close_research_gap`.
  - `list_open_gaps`.
  - `list_open_gap_ids`.
  - Валидация обязательных полей.
  - Новый статус `OPEN`.
- TESTS:
  - Создание.
  - Закрытие.
  - Список.
  - gap_id.
- ACCEPTANCE:
  - ResearchGap operations работают.
- STOP_CONDITIONS:
  - SearchTask без проверки gap запрещён.

---

### TASK: E04-T43-DETERMINISTIC-FIXTURES

- GOAL: Детерминированные тестовые фикстуры.
- CONTEXT: Нет сети и случайных данных.
- ALLOWED_FILES:
  - `tests/search/deterministic_fixtures.py`
  - `tests/search/test_deterministic_fixtures.py`
- FORBIDDEN:
  - Случайные идентификаторы.
  - Сеть.
- IMPLEMENTATION DETAILS:
  - Fixed IDs:
    Project,
    Study,
    Source,
    Document,
    DocumentChunk,
    SearchTask,
    Evidence,
    ResearchGap.
  - Функции вставки.
  - Идемпотентность.
- TESTS:
  - Повторное применение.
  - Нет дублей.
- ACCEPTANCE:
  - Fixtures воспроизводимы.
- STOP_CONDITIONS:
  - Random values запрещены.

---

### TASK: E04-T44-SEARCH-CORE-PIPELINE-INTEGRATION

- GOAL:
  Создать финальный интеграционный тест CPU-only Search Core pipeline.

- CONTEXT:
  Тестовая TASK. Исходный код не менять.

- ALLOWED_FILES:
  - `tests/search/test_search_core_integration.py`

- FORBIDDEN:
  - Изменение исходного кода.
  - Реальный интернет.
  - Реальный LLM.
  - Изменение EPIC-05 бизнес-логики.

- IMPLEMENTATION DETAILS:
  - Подготовить временную БД.
  - Применить migrations.
  - Использовать deterministic fixtures.
  - Создать:
    Project,
    Study,
    SearchTask,
    ResearchSession,
    ResearchGap.
  - Использовать:
    FakeSourceAdapter,
    FakeFetchTransport,
    RussianMorphologyNormalizer,
    BM25RetrievalProvider,
    CacheService.
  - Сценарий:
    - FakeSourceAdapter.search;
    - result normalization;
    - URL/identifier dedup;
    - relevance/quality;
    - Top-1;
    - cache miss;
    - cache hit;
    - FakeSourceAdapter.fetch;
    - HTML parse/clean;
    - content hash;
    - Source;
    - Document;
    - StudyDocumentLink;
    - DocumentChunk;
    - BM25 indexing;
    - check_query с ResearchGap;
    - FTS candidate retrieval;
    - Python BM25 ranking;
    - Evidence;
    - budget deduction внутри транзакции;
    - CoverageMetrics;
    - SufficiencyEvaluator.
  - Проверь:
    - нужный chunk найден;
    - Study isolation;
    - Document isolation;
    - no duplicate;
    - Python BM25 score детерминирован;
    - budget уменьшен;
    - rollback отменяет budget change;
    - Evidence hash;
    - Sufficiency decision;
    - cache statistics.
  - Проверить поиск русской словоформы:
    запрос `"отзывы"` должен находить текст,
    нормализованный эквивалентно `"отзыв"`.

- TESTS:
  - Только тестовый файл.

- ACCEPTANCE:
  Полный CPU-only Search Core pipeline проходит без LLM и сети,
  а финальный retrieval score рассчитывается Python BM25.

- STOP_CONDITIONS:
  - Если требуется бизнес-логика EPIC-05:
    `OUT_OF_SCOPE → STOP → REPORT → WAIT`.
  - Если для BM25 требуется embeddings:
    `STOP → REPORT → WAIT`.
  - Если требуется внешний ML dependency:
    `STOP → REPORT → WAIT`.

---

## 5. Definition of Done — Gate G-04

EPIC-04 считается завершённым только если выполнены все условия:

- Полный Search Core pipeline работает без LLM и GUI.
- `SourceAdapter` реализует:
  `search`,
  `fetch`,
  `capabilities`,
  `health`.
- `RetrievalProvider` реализует:
  `name`,
  `capabilities`,
  `search`,
  `index`,
  `delete`,
  `is_available`.
- URL normalization блокирует дубликаты.
- DOI/PMID/arXiv dedup работает.
- `content_hash` предотвращает повторное сохранение документов.
- `query_fingerprint` соответствует формуле ТЗ.
- Повторные и слишком похожие запросы блокируются.
- Новый запрос допускается только при наличии `ResearchGap`.
- Блокирующие условия возвращают стандартизированные Core Errors.
- `BudgetExhaustedError` используется для budget exhaustion.
- Budget Service не владеет транзакцией вызывающего слоя.
- Budget deduction атомарно входит в родительскую транзакцию.
- Модель независимости:
  - `COPY` учитывается;
  - `REWRITE` учитывается;
  - `SAME_PRIMARY` учитывается;
  - `CITATION` не создаёт ложное независимое подтверждение;
  - `UNKNOWN` не увеличивает independent count.
- Чанкинг детерминирован.
- `heading_path` присутствует.
- `overlap_group_id` присутствует.
- `is_overlap` присутствует.
- `numeric_signatures` присутствуют.
- Русский normalizer детерминирован.
- Стоп-слова обрабатываются.
- `stopword_version` сохраняется.
- `normalizer_version` сохраняется.
- `normalizer_version` является окончательным именем поля.
- FTS5 candidate index работает.
- FTS lifecycle:
  - document added;
  - document deleted;
  - normalizer changed → rebuild_all;
  - study deleted → cleanup.
- FTS index согласован с DocumentChunk.
- `BM25RetrievalProvider` использует FTS5 только для candidate retrieval.
- Финальный BM25 score вычисляется детерминированным Python-кодом.
- SQLite встроенный `bm25()` не используется как обязательный финальный score.
- BM25 не требует GPU.
- BM25 не требует embeddings.
- BM25 не требует vector DB.
- BM25 не требует обязательной внешней ML-библиотеки.
- Поиск изолирован по Study.
- Поиск изолирован по Document.
- При одинаковом score порядок детерминирован.
- `DocumentChunk` возвращается полностью заполненным.
- `numeric_signatures` и `metadata` корректно восстанавливаются.
- Evidence builder различает target/context.
- Cache поддерживает hit/miss/expired cleanup.
- Cache statistics соответствуют контракту.
- CoverageCalculator детерминирован.
- SufficiencyEvaluator детерминирован.
- Information gain детерминирован.
- ResearchGap operations работают.
- Все тесты используют фиктивные адаптеры.
- Все тесты работают с временной БД.
- Нет зависимости от сети.
- Нет зависимости от реального LLM.
- Нет зависимости от GUI.
- Нет обязательной зависимости от GPU.
- Нет обязательной зависимости от embeddings.
- Нет обязательной зависимости от vector DB.
- Нет нарушения transaction ownership.
- Все тесты проходят.

---

## 6. Контроль архитектурных границ

### Search Core имеет право

- нормализовать запросы;
- нормализовать retrieval text;
- искать кандидатов;
- рассчитывать deterministic relevance;
- рассчитывать deterministic quality;
- выполнять dedup;
- выполнять fetch через абстракцию;
- parse/clean;
- chunk;
- индексировать FTS;
- извлекать FTS candidates;
- рассчитывать Python BM25;
- создавать Evidence;
- контролировать budget;
- рассчитывать coverage;
- оценивать sufficiency;
- управлять ResearchGap operations.

### Search Core не имеет права

- самостоятельно менять FSM;
- самостоятельно создавать JSON-RPC responses;
- самостоятельно управлять MCP transport;
- самостоятельно запускать LLM;
- самостоятельно принимать архитектурные решения;
- считать UNKNOWN независимым подтверждением;
- считать CITATION независимым подтверждением;
- использовать SQLite `bm25()` как обязательный финальный score;
- добавлять embeddings;
- добавлять vector DB;
- требовать GPU;
- менять EPIC-02 schema без отдельного разрешения;
- менять контракты других EPIC без разрешения.

---

## 7. Error Boundary

Архитектурная граница ошибок:

Search Core operation
        ↓
SearchCoreError
        ↓
Core/Application layer
        ↓
MCP adapter
        ↓
JSON-RPC Error

Search Core TASK не должна формировать JSON-RPC напрямую.

Для блокирующих операций используются machine-readable Core Errors.

Примеры:

- `QueryRejectedError`
- `BudgetExhaustedError`
- `ProviderTimeoutError`
- `SourceUnavailableError`
- `FetchError`
- `ParseError`
- `RetrievalError`

Внутренняя причина может быть передана как структурированное поле,
но не должна заменять тип стандартизированной ошибки.

---

## 8. BM25 Architecture Contract

MVP использует двухступенчатый retrieval:

1. Normalization

Query
↓
RetrievalTextNormalizer
↓
normalized query

Document
↓
RetrievalTextNormalizer
↓
normalized document text

2. Candidate retrieval

normalized query
↓
SQLite FTS5
↓
candidate chunks

3. Final scoring

candidate chunks
↓
Python BM25
↓
deterministic score
↓
stable sorting
↓
Top-K

SQLite FTS5 является индексом кандидатов.

Python является источником истины для финального BM25 score.

Встроенный SQLite `bm25()` не является частью обязательного
финального scoring contract MVP.

---

## 9. Source Independence Contract

Для целей `independent_source_count`:

### Independent clustering

Union-Find разрешён только для:

- `COPY`
- `REWRITE`
- `SAME_PRIMARY`

### CITATION

`CITATION` обозначает зависимость от цитируемого источника.

`CITATION` не объединяет произвольные вторичные источники между собой.

Если primary source присутствует, citation source не создаёт дополнительное
независимое подтверждение.

Если primary source отсутствует, citation source не получает автоматически
статус независимого подтверждения.

### UNKNOWN

`UNKNOWN`:

- не объединяет источники;
- не создаёт независимость;
- не увеличивает `independent_source_count`;
- не используется как основание для повышения confidence.

---

## 10. Transaction Ownership Contract

Для Search Core:

- transaction owner определяется вызывающей бизнес-операцией;
- вложенные сервисы используют переданный `conn`;
- Budget Service не делает COMMIT;
- Budget Service не делает ROLLBACK;
- FTS lifecycle не должен обходить transaction boundary;
- изменение состояния и связанные бюджетные операции должны иметь
  единый атомарный transaction boundary там, где это требуется ТЗ.

Если реализация требует изменения transaction ownership:

`STOP → REPORT → WAIT`.

---

## 11. Открытые вопросы

### Вопрос 1 — Russian morphology engine

Подтвердить окончательную реализацию `RussianMorphologyNormalizer`.

Рабочий Baseline:

`russian_suffix`

с детерминированным суффиксным стеком и фиксированным словарём стоп-слов.

Если впоследствии будет выбран внешний стеммер/лемматизатор,
это должно быть отдельным архитектурным решением.

### Вопрос 2 — ResearchGap identity

Требование `open_gap_id` и/или `has_open_gap` должно соответствовать
финальному контракту EPIC-03/EPIC-05.

Текущий Search Core способен поддерживать оба режима через `GapPolicy`,
но окончательное решение о том, какой режим является обязательным,
должно приниматься на уровне общего контракта.

### Вопрос 3 — окончательно закрыт

Имя поля версии нормализатора:

`normalizer_version`

Используется в:

- `BM25IndexMeta`;
- FTS lifecycle;
- `rebuild_all`;
- тестах;
- metadata index.

`tokenizer_version` не используется в текущем Baseline.

---

## 12. Финальное правило для CODE Agent

Если реализация TASK требует изменения:

- ТЗ;
- State Machine;
- MCP Contract;
- EPIC scope;
- transaction ownership;
- public API другого EPIC;
- DB schema другого EPIC;
- утверждённого Error Contract;
- BM25 architecture contract;

CODE-агент НЕ должен самостоятельно принимать решение.

Он обязан:

`STOP → REPORT → WAIT`

---

## 13. Baseline Declaration

Этот документ является:

`EPIC-04 SEARCH CORE — TASK BATCH v1.3 — BASELINE`

После утверждения архитектором он становится рабочим контрактом
для подготовки и исполнения TASK EPIC-04.

Изменение Baseline выполняется только через новую версию документа.

Конец документа.