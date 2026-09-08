
---

# НАЦИОНАЛЬНОЕ ТЕХНИЧЕСКОЕ ЗАДАНИЕ (ТЗ) v2.4
## Раздел 7. QA и критерии приёмки

**Статус:** нормативная спецификация
**Назначение:** Определение стратегии тестирования, обязательных сценариев проверки, тестовой инфраструктуры и критериев готовности компонентов (Definition of Done).

---

## 1. Общие требования

- Каждый компонент системы имеет автоматические тесты.
- Критерии приёмки должны быть воспроизводимыми и проверяемыми.
- Тестирование не должно зависеть от внешних сетевых ресурсов или реальной работы локальной ИИ-модели (см. раздел 28).

---

## 2. Data isolation

Тестировать:
- отсутствие смешивания Studies;
- корректную работу Project context;
- `StudyDocumentLink` (JOIN-изоляция);
- document/chunk filtering;
- глобальный repository;
- режим `MATERIALS_ONLY`.

- Изоляция между проектами: данные проекта A не видны в проекте B
- Переключение проектов не приводит к потере данных
- Кросс-проектный поиск находит документ в другом проекте через реестр
- Дедупликация внутри проекта работает (один документ — один файл)
- Реестр синхронизируется при записи документа

---

## 3. Query Planner

Тестировать:
- decomposition;
- filters;
- exclusions;
- expected material type;
- duplicate rejection;
- budget;
- plan validation;
- Research Gap → targeted query.

---

## 4. URL normalization

Проверить:
- tracking parameters;
- fragments;
- query ordering;
- host case;
- trailing slash;
- encoding.

---

## 5. Deduplication

Проверить:
- URL duplicates;
- DOI/PMID/arXiv;
- content hash;
- near-duplicate content;
- copied/reprinted materials;
- `SourceRelation` (COPY, REWRITE, CITATION, SAME_PRIMARY).

---

## 6. Ranking

Проверить отдельно:
- relevance;
- source quality;
- domain weighting;
- freshness;
- Top-K.

Изменение source quality policy не должно менять relevance algorithm неожиданно.

---

## 7. BM25

Проверить:
- top-N;
- chunk retrieval;
- study isolation;
- document isolation;
- long documents;
- empty query;
- Russian text;
- technical terms.

MVP должен работать CPU-only.

### 7.1. Морфологическая обработка русского языка

Тестовый набор обязан содержать документы с вариациями словоформ (например, «отзыв», «отзыва», «отзывы», «отзывам») и проверять, что запрос в любой из этих форм находит все релевантные документы.

**Обязательные тестовые сценарии:**

1. Запрос «отзывы» находит документы с «отзыв», «отзыва», «отзывы», «отзывам».
2. Запрос «цена» находит документы с «цена», «цену», «цены», «цене».
3. Запрос «доставка» находит документы с «доставка», «доставке», «доставку».

**Критерий приёмки:** Recall не ниже 0.9 для каждого тестового запроса.

---

## 8. Chunking

Проверить:
- deterministic output;
- stable chunk IDs;
- structural boundaries;
- heading_path;
- overlap;
- overlap_group_id;
- is_overlap flag;
- numeric signatures;
- reproducibility.

---

## 9. Evidence

Проверить:
- document relation;
- chunk relation (target + context);
- location;
- source relation;
- duplicate evidence prevention через `evidence_hash`;
- правило: контекстный чанк (is_target=FALSE) не является самостоятельным Evidence.

---

## 10. Observation / Aggregation

Обязательные тесты:
- один отзыв не становится статистическим фактом;
- повторный текст не увеличивает число независимых наблюдений;
- одинаковые отзывы группируются;
- positive/negative aspects разделяются;
- количество источников и количество публикаций различаются;
- агрегаты воспроизводимы;
- отсутствие достаточной выборки явно маркируется;
- `ReviewExtractor` корректно преобразует разные форматы площадок в `CanonicalReview` (Post-MVP / опционально).

---

## 11. Claims

Проверить:
- Evidence relation (через `ClaimEvidence`);
- status;
- confidence;
- distinction FACT/OPINION/INFERENCE/HYPOTHESIS;
- insufficient evidence.

---

## 12. Contradiction

Проверить:
- numeric (через `numeric_signatures`);
- temporal;
- factual;
- technical;
- recommendation conflicts;
- user-experience conflicts.

Проверить предварительную детерминированную фильтрацию и последующий semantic comparison.

---

## 13. Research Gap

Проверить:
- создание gap;
- reason (включая `LOW_INDEPENDENCE`);
- missing evidence;
- recommended query;
- closure after new evidence.

---

## 14. Source independence

Тестовый набор должен содержать:
- пять копий одного пресс-релиза;
- пять независимых источников;
- смешанный набор.

Система не должна считать количество URL количеством независимых подтверждений. Подсчёт должен опираться на `SourceRelation` и консервативное правило для `UNKNOWN`.

---

## 15. Adaptive Search

Проверить:
- новый запрос имеет причину;
- duplicate query rejected (Exact Match);
- similar query rejected (Similarity Match);
- already-covered task rejected (Coverage Match);
- budget enforced;
- gap-targeted search;
- termination after no information gain.

---

## 16. Local-First

Проверить:
- локальные материалы используются первыми;
- web search не запускается без выявленного gap при соответствующей настройке (режим `EXPAND`);
- новые web queries направлены на gap.

---

## 17. Cache

Проверить:
- hit;
- miss;
- expired;
- forced refresh;
- source-specific TTL.

---

## 18. DB-write layer

Проверить:
- последовательную запись;
- отсутствие write races;
- rollback;
- recovery;
- сохранность состояния после сбоя;
- применение PRAGMA на каждом подключении через фабрику.

---

## 19. MCP

Проверить:
- schema validation;
- compact output;
- error contract;
- responsiveness;
- отдельные search/read operations;
- отсутствие блокировки transport.

### 19.1. Защита транспортного слоя stdout

**Тестовые сценарии:**

1. **Случайный вывод в stdout:** Внедрение `print("debug")` в произвольное место кода MCP-сервера не должно нарушать JSON-RPC протокол. Вывод должен быть перехвачен и перенаправлен в файл или поток ошибок (`stderr`).

2. **Логгер в stdout:** Настройка логгера на вывод в основной поток не должна нарушать работу транспорта.

3. **Исключение с трассировкой:** Необработанное исключение не должно приводить к выводу трассировки в основной поток. Клиент обязан получить корректный структурированный ответ об ошибке.

**Критерий приёмки:** Ни один сценарий не приводит к нарушению протокола или падению MCP-клиента.

---

## 20. LLM resilience

Симулировать:
- unreachable;
- timeout;
- degraded output;
- backend restart;
- backend switch.

Проверить:
- `LLM_UNREACHABLE`;
- сохранение State;
- `SESSION_RESUMING`;
- отсутствие потери Evidence/Claims;
- корректный пересчёт `TokenBudgetManager` при смене бэкенда.

---

## 21. JSON degradation

Проверить:
- invalid JSON;
- truncated JSON;
- JSON repair для промежуточных объектов (Observation, ResearchGap, Contradiction);
- запрет тихой правки для финального отчёта (`validate_and_save_report`);
- сохранение только валидных завершенных объектов;
- `REPORT_TRUNCATED_PARTIAL`;
- догенерацию только отсутствующих элементов.

---

## 22. GUI

Проверить:
- Main Thread не выполняет тяжелый retrieval;
- Worker loop работает независимо;
- queue batching;
- X-Ray buffer;
- smart scroll;
- Soft Stop;
- Hard Stop;
- snapshot;
- offline mode.

### 22.1. Кооперативная отмена CPU-задач

**Тестовые сценарии:**

1. **Индексация документов:** Запуск индексации набора документов, запрос остановки через короткий интервал. Операция обязана завершиться в течение заданного таймаута, уже обработанные данные сохранены.

2. **Стемминг:** Запуск стемминга большого набора чанков, запрос остановки. Операция обязана завершиться после текущей итерации, состояние сохранено.

3. **Перестроение индекса (Job):** Запуск перестроения BM25-индекса, запрос отмены через `cancel_job`. Операция обязана быть отменена через Job-механизм.

**Критерий приёмки:** Все сценарии завершаются в пределах таймаута, консистентность SQLite сохранена, частичные результаты не потеряны.

---

## 23. Network resilience

Проверить:
- timeout;
- rate limit;
- source unavailable;
- parse error;
- per-domain concurrency;
- exponential/backoff retry;
- отсутствие бесконечных retries.

Система не должна обходить CAPTCHA, paywall или access control.

---

## 24. Security

Проверить:
- локальные документы не уходят во внешний LLM API;
- cloud LLM отсутствует в штатном маршруте;
- source credentials не попадают в report;
- logs не содержат содержимое приватных документов без необходимости.

---

## 25. Acceptance Criteria

Система принимается, если:
- локальная 12–14B LLM может выполнить исследование через MCP;
- Search Core принимает окончательное решение о выполнении запросов;
- LLM не обязана помнить историю tool calls;
- Candidate Retrieval не выполняет массовый fetch;
- дубликаты удаляются (URL, DOI, content_hash, SourceRelation);
- relevance и quality разделены;
- snippet не считается Evidence;
- Claim связан с Evidence через `ClaimEvidence`;
- система различает независимые и производные источники;
- система ищет противоречия (детерминированно + семантически);
- Research Gaps приводят к целевым запросам;
- повторные и сходные запросы блокируются;
- aggregation-задачи считают наблюдения, а не просто URL;
- evidence-задачи сохраняют проверяемую source base;
- `MATERIALS_ONLY` работает без сети;
- ошибки одного источника не останавливают Study;
- report содержит проверяемые источники;
- JSON валидируется (с repair для промежуточных объектов);
- CPU + BM25 + русский стемминг достаточно для базового запуска;
- новый RetrievalProvider подключается без изменения Study API;
- единый DB-write layer сохраняет целостность;
- LLM restart не уничтожает Study;
- Hard Stop не повреждает SQLite (кооперативная отмена);
- локальные документы не передаются внешним LLM;
- MCP stdout защищён от случайного вывода.

---

## 26. MVP / Post-MVP

**MVP:**
- web retrieval;
- local documents;
- BM25 (с русским стеммингом);
- Evidence (с evidence_hash);
- Observation;
- Claims;
- Research Gaps;
- contradiction candidates;
- Project;
- global repository;
- MCP (с stdout защитой);
- GUI (с кооперативной отменой);
- reports;
- diagnostics;
- LLM resilience;
- TokenBudgetManager;
- State Machines (формальные автоматы);
- SourceRelation (базовая модель независимости);
- Job-механизм (для массовых операций);
- ReviewExtractor (опционально, как доменный адаптер).

**Post-MVP:**
- embeddings;
- hybrid retrieval;
- reranker;
- advanced PDF/EPUB;
- OCR;
- graph visualization;
- advanced provenance;
- trend analyzer;
- additional academic adapters;
- DocumentBodyStore (вынос тяжёлых тел документов из SQLite).

---

## 27. Definition of Done

Компонент считается готовым только при наличии:
- реализации;
- unit tests;
- integration tests при наличии внешнего контракта;
- acceptance test;
- диагностики ошибок;
- документации интерфейса;
- резервной фиксации в Git.

Кодер не имеет права самостоятельно превращать обнаруженную проблему в новую задачу. Проблема, выходящая за границы текущей карточки, фиксируется как `OUT_OF_SCOPE` и передается оператору/архитектору.

---

## 28. Детерминированные фикстуры и golden datasets

Тестирование системы обязано быть воспроизводимым и не зависеть от внешних сетевых ресурсов или реальной работы локальной ИИ-модели.

**Обязательные компоненты тестовой инфраструктуры:**

1. **FakeSourceAdapter** — имитация сетевого адаптера, возвращающая предопределённые результаты без сетевых запросов.
2. **FakeLLM** — имитация локальной ИИ-модели, возвращающая предопределённые структурированные ответы.
3. **Recorded HTTP responses** — записанные ответы реальных серверов для воспроизводимого тестирования обработки.
4. **Golden documents** — эталонные документы с известным ожидаемым результатом чанкинга.
5. **Golden chunks** — эталонные наборы чанков с известными свойствами.
6. **Golden Evidence** — эталонные доказательства с известными связями.
7. **Golden Sufficiency decisions** — эталонные входные метрики с известным ожидаемым решением SufficiencyEvaluator.
8. **Golden reports** — эталонные отчёты с известной структурой и связями.

**Правила:**

1. Все автоматические тесты обязаны работать без доступа к сети Интернет.
2. Все автоматические тесты обязаны работать без реальной локальной ИИ-модели.
3. Тесты с реальными сетевыми запросами или реальной ИИ-моделью (live tests) НЕ входят в стандартный набор регрессионных тестов.
4. Каждый компонент, принимающий внешние данные, обязан иметь фикстуры для тестирования.
5. Фикстуры версионируются и хранятся в репозитории.

---

**Конец Раздела 7.**

---


