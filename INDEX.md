# INDEX.md — Навигационный слой ТЗ v2.4

**Назначение:** навигационная карта нормативного корпуса. Позволяет найти норму, сущность, Gate или механизм **не читая весь корпус**. Заменяет последовательное чтение 14 файлов объёмом ~340 КБ адресным чтением 1–2 фрагментов.

**Baseline:** `TZ-2.4 @ 1a26485`, ветка `master`.

**Область индексации:**

| Включено | Не включено |
|---|---|
| Основное ТЗ: `01`–`07` (7 файлов, ~211 КБ) | Карточки `Research_Prompt_Suite_Task_Cards_Astra1` (11 файлов) |
| Приложения: `STATE MACHINE SPEC`, `BUDGET CONTRACT`, `MCP TOOL CONTRACTS`, `EPIC SPECIFICATIONS`, `EPIC → TASK DECOMPOSITION`, `MASTER ROADMAP`, `TASK EXECUTION CONTRACT` (7 файлов) | `замечания GPT6.md`, `SUGGESTIONS.md`, `README`/`CHANGELOG` |
| `ARCHITECTURE.md` (производный, не нормативный) | Папка `корзина/` |

**Проектное решение.** Индекс спроектирован как каркас для последующего перехода к машиночитаемым требованиям (`requirements.yaml`, вариант 2). Ключевое поле каждой нормы — `canonical` (первичный источник). Оно критично, потому что значительная часть норм определена **несколько раз** в разных файлах с разными акцентами. Без явного `canonical` возникает несколько «истин» для одной нормы — класс дефекта, уже проявившийся в противоречии `A-13` ↔ `EPIC-10`.

**Колонки реестров:** `ID` · `Название` · `Первичный источник (canonical)` · `Упоминания` · `Вердикт реестра`. Поле «Вердикт реестра» связывает норму с `REVIEW-REGISTRY.md`.

---

## 0. Протокол работы с индексом (для ИИ-агентов)

> **Перед любой правкой нормативного корпуса загрузить скилл `tz-index-maintenance`.**
> Скилл содержит рабочий процесс, шесть правил правки и обязательную процедуру валидации.

**Обязательное правило:** при правке любого файла `01`–`07`, приложений в `приложения к ТЗ/` или
`ARCHITECTURE.md` — `INDEX.md` обновляется **тем же изменением**. Индекс, отставший от корпуса,
хуже его отсутствия.

**Валидация перед завершением работы:**

```bash
python .workbuddy-ai/skills/tz-index-maintenance/scripts/validate_index.py
```

Ожидаемый результат: `РЕЗУЛЬТАТ: PASS` (код возврата 0). Проверяются: разрешимость ссылок на
файлы, полнота реестра норм, отсутствие фантомных записей, дубли определений, нормы без
определения, покрытие Gate G-01…G-11.

---

## 1. Как пользоваться индексом

| Вопрос | Раздел |
|---|---|
| Где лежит конкретное правило? | §3 Реестр норм A-xx |
| Какая норма отвечает за что? | §3 + §4 Реестр решений Q-xx |
| Что за сущность `SourceRelation` и где она описана? | §5 Карта сущностей данных |
| Где определение Gate G-04? | §6 Карта Gate |
| Какой EPIC отвечает за X? | §7 Карта EPIC |
| Где описан механизм pipeline / FSM / бюджет? | §8 Карта механизмов |
| Какие дефекты уже известны? | §9 Открытые дефекты |
| Где живёт FSM-спецификация? | §7+§8 (STATE MACHINE SPEC) |

---

## 2. Карта разделов основного ТЗ

| Файл | Раздел ТЗ | Объём | Ключевое содержание |
|---|---|---|---|
| `01_Research Analysis Layer.md` | Раздел 1. Слой исследовательского анализа | 36 КБ | Назначение и рамки, разграничение полномочий LLM/Core (A-02), структура ResearchIntent, типы исследовательских задач, эпистемическая цепочка, адаптивный цикл поиска, многомерный бюджет, **Sufficiency Criteria (§7)**, формальная модель независимости источников, совместимость слоёв |
| `02_Архитектура и системные принципы.md` | Раздел 2. Архитектура и системные принципы | 26 КБ | Классы задач, главный архитектурный закон, обязанности LLM (§2.1) и Core (§2.2), архитектурные слои (§3), режимы исследования (§4), **аппаратная независимость (§5, CPU-only baseline)**, контекстная защита + TokenBudgetManager (§6/6a), отказоустойчивость и сохранение состояния (§7), Configuration Contract (§8) |
| `03_Модель данных и хранение.md` | Раздел 3. Модель данных и хранение | 63 КБ | Идентификация операций и идемпотентность (§1a), 26+ сущностей (§2), Project/Study/Intent/SearchTask/SearchResult/Source (§3–8), **SourceRelation (§8a)**, Entity (§8b), **Document (§9) + DocumentSourceOccurrence (§9a)**, StudyDocumentLink (§10), DocumentChunk (§11), Chunking (§12), **Evidence (§13) + EvidenceContextChunk (§13a)**, Observation (§14), Claim (§15) + ClaimEvidence (§15a), Contradiction (§16), ResearchGap (§17) + SufficiencyEvaluation (§17a) + ResearchConfig (§17b) + **бюджетные таблицы (§17c)** + OutboxEvent (§17d), ResearchSession/State (§18), Working Memory (§19), Cache (§20), **DB-write layer (§21)**, индексы (§22), изоляция (§23), жизненный цикл SQLite (§24), **изоляция по проектам и registry.db (§25)**, конфигурация подключений (§26) |
| `04_Search Core.md` | Раздел 4. Поисковое ядро | 73 КБ | Назначение (§1), **конвейер обработки (§2)**, SourceAdapter (§3), RetrievalProvider (§4), Candidate Retrieval (§5), Snippetizer (§6), URL Normalization (§7), **Deduplication (§8)**, Ranking (§9), Domain-Specific Policy (§10), Fetch (§11), сетевые ограничения и вежливость (§12), Document Processing (§13), **BM25 (§14) + RU-морфология (§14.1)** + жизненный цикл индекса (§14a), Evidence Retrieval (§15) + устранение дублирования (§15.1), Aggregation/Review Mode (§16) + ReviewExtractor (§16a), Evidence Research Mode (§17), **Primary Source Search (§18)**, Contradiction Search (§19), **Query Fingerprint (§20) + многофакторная защита (§20.1)**, адаптивный поиск (§21), **условия остановки (§22)**, валидация ResearchGap (§23), локальный EXPAND (§24), кэш (§25), метрики и аудит (§26), **фильтрация контекста ИИ (§27)**, Job-механизм (§28) |
| `05_Взаимодействие с LLM и протокол MCP.md` | Раздел 5. Взаимодействие с LLM и MCP | 48 КБ | **Local LLM (§1)**, **LLM Backend Router (§2)**, **MCP (§3) + защита транспортного слоя (§3.1)**, **список MCP-инструментов (§4) + контракт инструмента (§4a)**, атомарность инструментов (§5), Candidate Retrieval Contract (§6), Working Memory (§7), Dashboard Contract (§8), Plan-and-Solve (§9), **Structured Outputs (§10) + повреждённый JSON (§10.1)**, Context Protection (§11) + бюджет контекста (§11a), **Hallucination Control (§12)**, Paywall (§13), серверная валидация отчётов (§14), Partial Report (§15), **Error Contract (§16)**, **таймауты + Watchdog (§17)**, лимиты ответов инструментов (§18) |
| `06_GUI_UX.md` | Раздел 6. GUI и UX | 10 КБ | Technology (§1), **Main Thread / Worker (§2)**, Study creation (§3), Intent Blueprint Editor (§4), X-Ray Activity Stream (§5), Evidence Explorer (§6), Evidence Tree (§7), **Report Viewer (§8)**, **Graceful Abort (§9: Soft Stop/Hard Stop/кооперативная отмена)**, System Health Monitor (§10), Prompt Sandbox (§11), Research Snapshots (§12), Projects (§13), Offline mode (§14), Review/Aggregation UI (§15), Query preview (§16) |
| `07_QA_Acceptance.md` | Раздел 7. QA и критерии приёмки | 25 КБ | Общие требования (§1), Data isolation (§2), Query Planner (§3), URL normalization (§4), Deduplication (§5), Ranking (§6), BM25 (§7) + RU-морфология (§7.1), Chunking (§8), Evidence (§9), Observation/Aggregation (§10), Claims (§11), Contradiction (§12), Research Gap (§13), **Source independence (§14)**, Adaptive Search (§15), Local-First (§16), Cache (§17), **DB-write layer (§18)**, **MCP (§19) + защита stdout (§19.1)**, LLM resilience (§20), JSON degradation (§21), GUI (§22) + кооперативная отмена (§22.1), Network resilience (§23), Security (§24), **Acceptance Criteria (§25)**, **MVP/Post-MVP (§26)**, Definition of Done (§27) + **CI-контракт (§27.1, S-04)** + **согласованный baseline документов (§27.2, S-09)**, фикстуры и golden datasets (§28) + **Fixtures manifest и общие корпуса (§28.1, S-15)** |

---

## 3. Реестр норм A-01…A-21

> Формат определения в ТЗ единообразен: `Название нормы (A-N): текст`. Поле `canonical` указывает первичный источник; `mentions` — остальные места применения.
> **A-01 восстановлен и внесён в нормативный состав** (2026-09-13): каноническая формулировка найдена в старых файлах проекта, затем внесена в нормативный реестр — `MASTER DEVELOPMENT ROADMAP v1.2 — BASELINE.md` §21.1 (УИ v1.0), с сохранением источника, обоснования и критерия приёмки. См. `REVIEW-REGISTRY.md` §D-4. Статус — `active`.

| ID | Название | Первичный источник | Упоминания | Связь с реестром |
|---|---|---|---|---|
| **A-01** | Редакционные ошибки Roadmap и граф зависимостей | `приложения к ТЗ/MASTER DEVELOPMENT ROADMAP v1.2 — BASELINE.md` §21.1 (реестр «Реестр утверждённых изменений (УИ v1.0)», внесено 2026-09-13) | EPIC SPEC стр.146; ROADMAP стр.6, 244, 575; EPIC→TASK стр.269; TASK EXEC стр.14 | **D-4 (RESOLVED)** |
| **A-02** | Разграничение ролей при переходах: LLM предлагает, Watchdog сигнализирует, Core выполняет | `01` §2.3, стр. 84 | `02` §3 стр.51; `05` §15 стр.319; `06` §9 стр.157 | — |
| **A-03** | JSON/сериализация — не источник истины; связи только через нормализованные таблицы | `03` §2, стр. 91 | `03` стр.70, 150, 205, 265, 352, 680, 749; `04` §2 стр.103; `05` §10 стр.224; EPIC SPEC стр.67; ROADMAP стр.160, 576 | — |
| **A-04** | Область уникальности и идемпотентности — в пределах Study/Project | `03` §6, стр. 178 | `03` стр.746, 759; `04` §20 стр.534; `07` §2 стр.36 | — |
| **A-05** | Уникальность Evidence: проверка по позиции до `evidence_hash` | `03` §13, стр. 425 (заголовок «Правило уникальности Evidence») | `04` §15 стр.335; `07` §9 стр.148, 149 | — |
| **A-06** | Полуоткрытые интервалы `[char_start, char_end)`; алгоритм склейки overlap | `03` §11, стр. 387 | `03` стр.340; `04` §15.1 стр.341, 350; `07` §8 стр.134, 137, 149 | — |
| **A-07** | Стабильные идентификаторы `chunk_id`; `DocumentChunk.text` (не `content`) | `03` §11, стр. 350 | `03` стр.337, 338; `04` §14a стр.313; `07` §8 стр.135, 136; EPIC SPEC стр.69 | — |
| **A-08** | Одно очищенное тело документа + множество `DocumentSourceOccurrence` | `03` §9a, стр. 293 (заголовок раздела) | `07` §5 стр.75 | — |
| **A-09** | Границы реестра: только идентичность и расположение, без доступа к содержимому | `03` §25.2, стр. 814 | `03` стр.786; `07` §2 стр.34 | — |
| **A-10** | Разделение класса доказательности и оценки качества источника | `03` §15, стр. 500 | `01` стр.155; `03` стр.223, 495; `04` §10 стр.185 | — |
| **A-11** | Durability: `synchronous=FULL`, `foreign_keys=ON`, backup через SQLite Backup API | `03` §24, стр. 770 | `03` стр.771, 860, 862; `07` §18 стр.262; EPIC SPEC стр.73; ROADMAP стр.164, 576 | — |
| **A-12** | Расчёт контекста по режимам `fixed`/`auto`/`auto_with_config_cap` | `02` §6a, стр. 141 | `02` стр.158; `03` стр.594, 598; `05` §11a стр.256 | — |
| **A-13** | **RU-морфология обязательна для MVP**; BasicNormalizer — только degraded fallback | `04` §14.1, стр. 284 | `07` §7.1 стр.118; ROADMAP стр.436, 578 | **D-1 (конфликт с EPIC-10)** |
| **A-14** | Кооперативная отмена; unsafe thread kill запрещён | `04` §28, стр. 695 | `06` стр.171, 185, 199; `07` §22.1 стр.354; ROADMAP стр.410 | — |
| **A-15** | Стартовый план создаёт ResearchGap; запуск поиска через сохранённый gap | `01` §7, стр. 211 | `03` стр.165, 178; `04` §18 стр.447 | — |
| **A-16** | Границы ответственности: Core даёт typed primitives, Engine не дублирует evaluator | `04` §26, стр. 580 | `07` §25 стр.411; EPIC SPEC стр.130, 146; ROADMAP стр.246, 285, 577 | — |
| **A-17** | Приватность локальных источников: пути не передаются LLM и в отчёт | `02` стр. 100 | `03` §9a стр.309 | ✅ S-06 внесено 2026-09-13 (`02` §7) |
| **A-18** | Неизменяемые ревизии `ResearchConfig`; backend версионируется отдельно от порогов | `03` §17b, стр. 583 | `03` стр.588; `05` §2 стр.40; `07` §20 стр.311, 312 | — |
| **A-19** | Protocol error ≠ domain error (JSON-RPC коды vs доменный `code`) | `05` §16, стр. 329 | — | — |
| **A-20** | Runtime stdout protection: перехват постороннего вывода без разрушения транспорта | `05` §3.1, стр. 54 | `07` §19.1 стр.292 | **S-04 (ACCEPT)** |
| **A-21** | Неизменяемость Document; обновление URL/контента создаёт новую версию | `03` §9, стр. 291 | `03` стр.327; `04` §14a стр.312; `07` §17 стр.249 | **S-12 / Q-08 (P0, ACCEPT)** |

**Замечания по реестру:**

- **Дубли с расхождением акцентов:** A-03 (7 определений), A-02 / A-10 / A-21 / Q-04 (по 4). При переходе к `requirements.yaml` поле `canonical` обязательно; остальные вхождения переходят в `mentions`.
- **A-01 — ✅ ВНЕСЕНО В НОРМАТИВНЫЙ СОСТАВ** (2026-09-13). Нормативный реестр «УИ v1.0» создан: `MASTER DEVELOPMENT ROADMAP v1.2 — BASELINE.md` §21, каноническое определение — §21.1. Формулировка внесена дословно из `REVIEW-REGISTRY.md` §D-4, с сохранением всех трёх ранее потерянных частей.
  **Формулировка:** «Редакционные ошибки Roadmap и граф зависимостей» (версия 1.2 vs 1.1; пропуски пунктов 8/10 в Search Core не означают отсутствующие требования, карточки привязаны к названиям подэтапов; техническое ребро EPIC-05 → EPIC-06 удалено, т.к. Change Log разрешает независимый backend; последовательность выдачи эпиков остаётся gated).
  **Диагноз:** не утрата данных, а **дефект миграции** — правило было свёрнуто в `MASTER ROADMAP v1.2` Change Log п.12 с потерей источника, обоснования и критерия приёмки. Все три части восстановлены в §21.1.
  **Приоритет:** входит в пункт 1 `MASTER ROADMAP` §19 (нормативные источники) — выше EPIC-документа.

**Структурная заметка по §21 `MASTER ROADMAP`.** Раздел «21. Реестр утверждённых изменений (УИ v1.0)» содержит полное каноническое определение только для `A-01` (§21.1) — это единственная норма состава «УИ v1.0», у которой в корпусе не было собственного определения. Для `A-02…A-21` и `Q-01…Q-05` там приведена адресная таблица «норма → где определено → краткое содержание»; формулировки не дублируются, первичным источником остаются разделы ТЗ `01`–`07` (см. поле `Первичный источник` выше). Это осознанное решение: вносить полные тексты ~26 норм в приложение означало бы создать вторую «истину» и увеличить масштаб дефекта D-4 (дубли определений), а не устранить его.

---

## 4. Реестр решений Q-01…Q-08, Q-13

| ID | Тема | Первичный источник | Упоминания | Статус |
|---|---|---|---|---|
| **Q-01** | Синхронизация Project DB → `registry.db` через transactional outbox | `03` §25.3, стр. 816 | — | закрыто |
| **Q-02** | Независимость источников на уровне Claim (claim-scoped) | `01` §7, стр. 341 | `03` §8a стр.246; `07` §14 стр.213 | ✅ **N-02 закрыт** (ADR-003, 2026-09-14); ожидание `S-11` снято |
| **Q-03** | Strategy profiles и пороги остановки (EVIDENCE / AGGREGATION) | `04` §22, стр. 578 | `01` §7 стр.255 | закрыто |
| **Q-04** | Бюджет: `reserve`/`commit`/`release` в одной транзакции | `03` §17c, стр. 644 | `04` §22 стр.576, §25 стр.619 | закрыто |
| **Q-05** | Межавтоматная policy при восстановлении после recovery | `01` §2.3, стр. 115 | — | закрыто |
| **Q-06…Q-07** | ⟂ **ПРОПУСК НУМЕРАЦИИ** | — | не найдены в корпусе | `status: gap` — см. §9 D-2 |
| **Q-08** | Версионирование Document при смене URL (механизм A-21) | `03` §9b (ADR-002, принят 2026-09-14) | `07` §17 стр.249; `04` §25; `MCP TOOL CONTRACTS` §3 | ✅ **CLOSED** (ADR-002, 2026-09-14) — S-12 RESOLVED |
| **Q-13** | Administrator diagnostic token | `EPIC SPECIFICATIONS v1.0` §12, `MASTER ROADMAP v1.2` §14, `EPIC→TASK` §13 | — | ✅ **CLOSED** (2026-09-13) — **не вводится в MVP** |

> **О нумерации.** Решения с номерами между `Q-05` и `Q-13` в нормативном корпусе отсутствуют (тот же класс, что `D-2`). Единственное фактическое вхождение `Q-13` — вне нормативного корпуса, в карточках Astra1 (5 упоминаний как «блокер»), которые в область индекса не входят и не правятся. `Q-13` введён в реестр решением архитектора (2026-09-13) — см. ниже.

> **Решение `Q-13` (архитектор, 2026-09-13):** privileged administrator diagnostic token **не вводится в MVP**. Локальная диагностика обязана работать без специального скрытого доступа. Любой будущий привилегированный/удалённый механизм диагностики оформляется отдельным архитектурным решением с полным контрактом: кто выдаёт, кто может использовать, срок действия, область полномочий, хранение, отзыв, аудит. Механизм скрытого административного доступа не создаётся только потому, что он присутствовал в раннем roadmap.
> **Следствие в корпусе:** `EPIC-11` Scope — `administrator diagnostic token` исключён (`EPIC SPEC` стр.238, `MASTER ROADMAP` стр.446); `E11-T09` снят (`EPIC→TASK` стр.568), ID не переиспользуется. `E11-T10` (user-facing diagnostics) остаётся.

---

## 5. Карта сущностей данных

> Полный реестр — `03` §3. Ниже — только точки входа для наиболее связанных сущностей.

| Сущность | Раздел | Ключевые правила | Связи |
|---|---|---|---|
| `Project` | `03` §3 | Изоляция: отдельный файл SQLite на проект | 1→* Study |
| `Study` | `03` §4 | `status` — только через Study FSM | → Project, → ResearchConfig |
| `ResearchIntent` | `03` §5 | Перечислимые поля — в нормализованных таблицах (A-03) | 1→1 Study |
| `SearchTask` | `03` §6 | `query_fingerprint` UNIQUE в пределах Study (A-04); `gap_id` (A-15) | → Study, → ResearchGap |
| `SearchResult` | `03` §7 | Идентификаторы в `SearchResultIdentifier` (A-03) | *→1 Source |
| `Source` | `03` §8 | `canonical_url` UNIQUE; качество — в `SourceQualityAssessment` (A-10) | *↔* Source |
| **`SourceRelation`** | `03` §8a | COPY/REWRITE/CITATION/SAME_PRIMARY/UNKNOWN; два частичных UNIQUE-индекса + FK на `Claim` (N-02, ADR-003) | *↔* Source, → Claim |
| `Entity` | `03` §8b | Алиасы в `EntityAlias` (A-03) | — |
| **`Document`** | `03` §9 | `content_hash` UNIQUE; неизменяемость (A-21); механизм версионирования — `03` §9b (Q-08 ✅ CLOSED, ADR-002) | *↔* Study via StudyDocumentLink |
| `DocumentSourceOccurrence` | `03` §9a | 5 копий → 1 тело + 5 происхождений (A-08) | → Document, → Source |
| `DocumentChunk` | `03` §11 | `chunk_id` детерминирован (A-07); интервалы (A-06) | 1→* Evidence |
| `Evidence` | `03` §13 | `evidence_hash` UNIQUE; проверка по позиции (A-05) | *↔* Chunk, → Source |
| `EvidenceContextChunk` | `03` §13a | Контекстное окружение ±1 чанк | → Evidence, → DocumentChunk |
| `Observation` | `03` §14 | — | → Study |
| `Claim` | `03` §15 | `evidence_class` ≠ качество источника (A-10) | *↔* Evidence via ClaimEvidence |
| `ClaimEvidence` | `03` §15a | Сквозная доказательность M2M | — |
| `Contradiction` | `03` §16 | Пара Claim↔Claim | → Claim |
| `ResearchGap` | `03` §17 | → породившая SearchTask | → Study |
| `SufficiencyEvaluation` | `03` §17a | Журнал решений + метрики + rule hits | → Study, → ResearchConfig |
| `ResearchConfig` | `03` §17b | Неизменяемые ревизии (A-18) | → Study/ResearchSession |
| `Budget*` (`Limit`/`Counter`/`Reservation`/`Ledger`) | `03` §17c | 7 dimensions; reserve/commit/release (Q-04) | → ResearchConfig |
| `OutboxEvent` | `03` §17d | Синхронизация → registry.db (Q-01) | → registry.db |
| `ResearchSession` / `ResearchState` | `03` §18 | Только скалярные значения (A-03) | → Study |
| `WorkingMemory` | `03` §19 | — | → Study |
| `CacheEntry` | `03` §20 | TTL, source-specific | → Project |
| `LogRecord` | `03` §2 | Audit всех переходов FSM | → (entity_type, entity_id) |
| `Job` | `03` §2 | FSM Job; кооперативная отмена (A-14) | → Study |

---

## 6. Карта Gate G-01…G-11

> Определения — `EPIC SPECIFICATIONS v1.0 — BASELINE.md`, стр. 26–244.
> Колонка `Fixtures` — какие тестовые наборы требует Gate. Полный перечень — `07` §28 (8 компонентов) + §28.1 (manifest, fake clock, общие корпуса); статус — `S-15` (✅ внесено 2026-09-14).

| Gate | EPIC | Критерий прохождения | Fixtures |
|---|---|---|---|
| **G-01** | EPIC-01 Foundation | Запуск, конфигурация, изоляция тестов, errors, logging, package boundaries, базовые тесты | `E01-T13` (stdout/logging isolation fixture) |
| **G-02** | EPIC-02 Data Layer | Migrations, CRUD, rollback, FK, isolation, document reuse, idempotency, concurrent read/write, WAL, DB-write layer, deterministic fixtures, FTS5 readiness, WAL-safe snapshot/backup | **deterministic fixtures** (`E02-T28`) |
| **G-03** | EPIC-03 State Machines | Разрешённые/запрещённые переходы, mandatory scenarios | FSM-сценарии (`E03-T2x`) |
| **G-04** | EPIC-04 Search Core | Детерминизм retrieval, deduplication, query fingerprint, FTS5/BM25 ↔ DocumentChunk, lifecycle индекса, evidence provenance, budget, cache, normalizer versioning | **fixtures без реальной LLM** (`A-16`); RU-корпус, копии/цитаты/UNKNOWN |
| **G-05** | EPIC-05 Research Engine | Mock-LLM E2E: `intent → plan → tasks → retrieval → evidence → gap → next task → sufficiency → finalize` | **`FakeLLM`** (mock-LLM E2E) |
| **G-06** | EPIC-06 LLM Backend | Unreachable, timeout, invalid/truncated JSON, degraded response, restart, backend switch, context budget, schema/semantic validation, constrained decoding, repair fallback, state preservation | **`FakeLLM`** + malformed tool calls |
| **G-07** | EPIC-07 MCP | Все 23 tools зарегистрированы, проходят contract tests | contract tests (`E07-T2x`) |
| **G-08** | EPIC-08 GUI | Business rules не в GUI, workers, UI responsive, cancellation, project switching, offline, snapshot, evidence traceability | traceability view (`E08-T11`) |
| **G-09** | EPIC-09 Integration & Resilience | Recovery не теряет валидные данные, не создаёт дубликаты, не нарушает FSM, сохраняет audit trail, восстанавливает session/job state | **fault injection**: crash после reserve |
| **G-10** | EPIC-10 Final QA | Все обязательные критерии ТЗ, критических известных дефектов нет | golden-снапшоты; **adversarial fixtures** (`N-03`) |
| **G-11** | EPIC-11 Packaging/Portable | Запуск на целевой Windows без IDE + понятная диагностика отсутствующих компонентов | env-checker stubs; missing-dependency fixtures |

---

## 7. Карта EPIC-01…EPIC-11

> Спецификации — `EPIC SPECIFICATIONS v1.0`, стр. 18–244. Порядок — `MASTER ROADMAP v1.2` §3.
> Колонка `TASK` — диапазон задач из `EPIC → TASK DECOMPOSITION v1.0` (всего 283). Колонка `ADR` — архитектурные решения, от которых EPIC зависит.

| EPIC | Название | Gate | Задачи (TASK) | ADR | Файлы модулей (ARCHITECTURE §2) |
|---|---|---|---|---|---|
| **EPIC-01** | FOUNDATION | G-01 | `E01-T01…T14` | — | `app/`, `infra/`, `tests/` |
| **EPIC-02** | DATA LAYER | G-02 | `E02-T01…T29` | **ADR-003** (частично: `SourceRelation`) | `db/` (connection_factory, migrations, write_layer, repositories, registry, backup, fts) |
| **EPIC-03** | STATE MACHINES | G-03 | `E03-T01…T24` | — | `core/state_machines/` (6 FSM) |
| **EPIC-04** | SEARCH CORE | G-04 | `E04-T01…T52` | **ADR-003** (частично: `independent_source_count`) | `core/retrieval/`, `core/evidence/`, `core/analysis/`, `core/budget/` |
| **EPIC-05** | RESEARCH ENGINE | G-05 | `E05-T01…T28` | **ADR-001** | `core/research_engine/`, `core/config/` |
| **EPIC-06** | LLM BACKEND | G-06 | `E06-T01…T25` | **ADR-001** | `llm/` (provider, router, structured_output, token_budget_manager, prompt) |
| **EPIC-07** | MCP | G-07 | `E07-T01…T34` | **ADR-001** | `mcp_server/` (server, transport_guard, tools, schemas) |
| **EPIC-08** | GUI | G-08 | `E08-T01…T22` | — | `gui/` (views, widgets, viewmodels, bridge) |
| **EPIC-09** | INTEGRATION & RESILIENCE | G-09 | `E09-T01…T18` | — | сквозной (recovery, reconciliation, outbox replay) |
| **EPIC-10** | FINAL QA / ACCEPTANCE | G-10 | `E10-T01…T19` | — | `tests/` (golden, integration) |
| **EPIC-11** | PACKAGING / PORTABLE | G-11 | `E11-T01…T18` | — | `packaging/`, env checker |

**ADR-контур:**

| ADR | Предмет | Блокер | Влияет на |
|---|---|---|---|
| **ADR-001** ✅ Accepted 2026-09-14 | MCP-host и владелец агентного цикла: два профиля — desktop orchestration (по умолчанию, Orchestrator в процессе приложения, единый ToolDispatcher) и headless `--mcp-stdio` (цикл ведёт внешний MCP-клиент); MCP — не протокол инференса; один Core на Project DB, `PROJECT_LOCKED` | `N-01` (P0) → **CLOSED** | EPIC-05, EPIC-06, EPIC-07 — ✅ unblocked |
| **ADR-002** ✅ Accepted 2026-09-14 | Идентичность Document при смене URL: идемпотентное окно 24ч, флаг `refresh=true` в `read_url_content`, Evidence фиксирует версию (A-21), `CONTENT_UNCHANGED` при совпадении hash | `S-12` / `Q-08` (P0) → **CLOSED** | EPIC-02, EPIC-04 (E02-T10, E02-T20, E04-T33/34/35 — ✅ unblocked) |
| **ADR-003** ✅ Accepted 2026-09-14 | `SourceRelation` UNIQUE vs `claim_id`: два частичных UNIQUE-индекса (claim-specific и общий) + FK на `Claim` | `N-02` (P0) → **CLOSED** | EPIC-02, EPIC-04 (E02-T09, E02-T17, E04-T07 — ✅ unblocked) |

> ADR-001, ADR-002 и ADR-003 приняты 2026-09-14. Открытых P0-блокеров не осталось; зависимые задачи разблокированы (см. §9.1).

**Нормативные приложения по EPIC:**

| Приложение | Файл | Покрывает |
|---|---|---|
| State Machine Specification | `STATE MACHINE SPECIFICATION v1.2.md` | 6 FSM: Study, ResearchSession, SearchTask, MCP Operation, LLM Backend, Job |
| Budget Contract | `BUDGET CONTRACT v1.0.md` | 7 dimensions, reserve/commit/release/extend_budget |
| MCP Tool Contracts | `MCP TOOL CONTRACTS v1.1.md` | 23 инструмента, полные контракты |
| Epic Specifications | `EPIC SPECIFICATIONS v1.0 — BASELINE.md` | Границы, интерфейсы, DoD, Gate G-01…G-11 |
| Epic → Task Decomposition | `EPIC → TASK DECOMPOSITION v1.0 — BASELINE.md` | Декомпозиция EPIC в TASK |
| Master Roadmap | `MASTER DEVELOPMENT ROADMAP v1.2 — BASELINE.md` | Последовательность, правила R-01…R-09 |
| Task Execution Contract | `TASK EXECUTION CONTRACT v1.0 — BASELINE.md` | Context Header, STOP→REPORT→WAIT, формат сдачи |

---

## 8. Карта механизмов (сквозной поиск)

| Механизм | Раздел ТЗ | Приложение | Реестр |
|---|---|---|---|
| Многомерный бюджет (7 dimensions) | `01` §6a; `03` §17c | BUDGET CONTRACT v1.0 | Q-04 |
| Sufficiency Criteria и пороги остановки | `01` §7; `04` §22 | — | Q-03 |
| Независимость источников | `01` §7 (стр.331+); `07` §14 | — | Q-02 (`N-02` ✅ CLOSED, ADR-003); `S-11` ✅ CLOSED (2026-09-14) |
| Формальные FSM (6 автоматов) | `01` §2.3; `02` §3 | STATE MACHINE SPEC v1.2 | — |
| Профили исполнения и владелец агентного цикла | `02` §3a; `05` §3 | — | **N-01 ✅ CLOSED (ADR-001, 2026-09-14)** |
| MCP-транспорт и 23 инструмента | `05` §3–4 | MCP TOOL CONTRACTS v1.1 | **N-01 ✅ CLOSED (ADR-001, 2026-09-14)** |
| Egress policy (недоверенные адреса) | `05` §3.2; `07` §24 | — | **N-03 ✅ CLOSED (2026-09-14)** |
| Query Fingerprint и защита от дублей | `04` §20 | — | A-04 |
| Дедупликация (3 уровня) | `04` §8 | — | — |
| Chunking и overlap | `03` §11–12; `04` §13 | — | A-06, A-07 |
| Evidence extraction и provenance | `03` §13; `04` §15 | — | A-05 |
| BM25 и RU-морфология | `04` §14/14.1 | — | **A-13 (D-1)** |
| TokenBudgetManager | `02` §6a; `05` §11a | — | A-12 |
| Structured output (2 уровня валидации) | `05` §10 | — | **N-03 ✅ CLOSED (2026-09-14)** |
| Error Contract | `05` §16 | — | A-19 |
| Watchdog и таймауты | `02` §7; `05` §17 | — | **S-10 ✅ CLOSED (2026-09-14)** |
| Кооперативная отмена | `06` §9; `04` §28 | — | A-14 |
| DB-write layer | `03` §21 | — | **S-17** |
| registry.db и outbox | `03` §25.2–25.3 | — | Q-01, A-09 |
| Reconcile / recovery | `02` §7 | — | Q-05, G-09 |
| Приватная диагностика сбоев | `02` §7 (полная норма); `07` §24 | — | **S-06 (ACCEPT, 2026-09-13)** |
| Административный диагностический доступ | `02` §8 (ссылка на решение) | EPIC SPECIFICATIONS §12 | **Q-13 (CLOSED, 2026-09-13) — не вводится в MVP** |
| Согласованный baseline документов | `07` §27.2 | — | **S-09 (ACCEPT, 2026-09-14)** |
| Partial report / FULL-PARTIAL | `05` §15; `06` §8 | STATE MACHINE SPEC §1 | **S-08 ✅ CLOSED (2026-09-14)** |
| stdout protection | `05` §3.1; `07` §19.1 | — | A-20, **S-04** |
| Post-MVP список (отложенные механизмы) | `07` §26 | — | **S-03** (хранение API-ключей, `DEFER`) |
| Версионирование Document (механизм A-21) | `03` §9b; `04` §25 | MCP TOOL CONTRACTS v1.1 §3 | **Q-08 (CLOSED, ADR-002, 2026-09-14)** |

---

## 9. Открытые дефекты корпуса

| ID | Дефект | Место | Статус |
|---|---|---|---|
| **D-1** | `A-13` (RU-морфология обязательна) ↔ `EPIC-10` Coverage: «Russian morphology **если включена**» | `EPIC SPECIFICATIONS v1.0` стр. 228 | ✅ **CLOSED** (2026-09-13) — приведено к формулировке `A-13`/`MASTER ROADMAP` §13 |
| **D-2** | Q-06, Q-07 отсутствуют — пропуск нумерации без пояснения | весь корпус | требует пояснения (по аналогии с `MASTER ROADMAP` стр.244) |
| **D-3** | `A-01` входил в нормативный набор «УИ v1.0» без определения | приложения, 5 примечаний | ✅ **CLOSED** (2026-09-13) — формулировка внесена в нормативный состав: `MASTER ROADMAP v1.2` §21.1. См. D-4 |
| — | ~~**Q-08** — версионирование Document при смене URL~~ | ~~`07` §17 стр.249~~ | ✅ **CLOSED** (ADR-002, 2026-09-14: черновик Q-08 утверждён; механизм в `03` §9b, `04` §25, `MCP TOOL CONTRACTS` §3; A-21 не изменён); S-12 |
| **D-4** | ⚠ Дубли определений: A-03 (×7), A-02/A-10/A-21/Q-04 (×4) — расхождение акцентов | `03`, `04`, `05`, `01` | требует назначения `canonical` при переходе к варианту 2 |
| **D-5** | `Q-13` использовался вне нормативного корпуса (карточки Astra1) как блокер, но в реестре `Q-01…Q-08` отсутствовал | карточки Astra1: 5 упоминаний | ✅ **CLOSED** (2026-09-13) — решение принято, diagnostic token снят из MVP. См. §4 `Q-13` |
| — | ~~**N-01** — MCP-host не определён~~ | ~~`05` §2–3~~ | ✅ **CLOSED** (ADR-001, 2026-09-14: два профиля исполнения и владелец агентного цикла; норма внесена в `02` §3a) |
| — | ~~**N-02** — SourceRelation UNIQUE vs `claim_id`~~ | ~~`03` §8a~~ | ✅ **CLOSED** (ADR-003, 2026-09-14: два частичных UNIQUE-индекса + FK на `Claim`; норма внесена в `03` §8a) |
| — | ~~**N-03** — граница гарантий: уровни валидации и недоверенные данные~~ | ~~`05` §12, §14~~ | ✅ **CLOSED** (2026-09-14: норма «Контроль доказательности» с явной границей гарантий в `05` §12; exact-match цитаты в `05` §14; Egress policy + журналирование нарушений в `05` §3.2; canary в `07` §24) |

### 9.1. Задачи, заблокированные P0-блокерами (`S-14`)

Связи зафиксированы **только там, где зависимость явно следует из названия задачи, состава группы или прямого указания реестра**. Задачи, зависимость которых неочевидна без дополнительного анализа, в список не включены.

| Блокер | ADR | Заблокированные задачи | Основание |
|---|---|---|---|
| ~~**S-12 / Q-08**~~ — Document identity при смене URL | ~~ADR-002~~ | ✅ **СНЯТО** (ADR-002 принят 2026-09-14) | `E02-T10` — ✅ unblocked · `E02-T20` — ✅ unblocked · `E04-T33` — ✅ unblocked · `E04-T34` — ✅ unblocked · `E04-T35` — ✅ unblocked |
| ~~**N-01**~~ — MCP-host не определён | ~~ADR-001~~ | ✅ **СНЯТО** (ADR-001 принят 2026-09-14) | EPIC-07 целиком (`E07-T01…T34`) — ✅ unblocked · EPIC-05 (`E05-T01…T28`) — ✅ unblocked · EPIC-06 (`E06-T01…T25`) — ✅ unblocked |
| ~~**N-02**~~ — SourceRelation UNIQUE vs `claim_id` | ~~ADR-003~~ | ✅ **СНЯТО** (ADR-003 принят 2026-09-14) | `E02-T09` — ✅ unblocked · `E02-T17` — ✅ unblocked · `E04-T07` — ✅ unblocked |

> ✅ **Все P0-блокеры сняты 2026-09-14** (`ADR-001`, `ADR-002`, `ADR-003` приняты). Таблица сохраняется как история блокировок; перечисленные задачи разблокированы.

> `S-11` (`independent_source_count`) — ожидание `ADR-003` **снято 2026-09-14**: формула `independent_source_count(claim)` уже определена в `01` §7, требование к подсчёту — в `07` §14. Отдельной задачи в декомпозиции не имеет — алгоритм реализуется в составе `E04-T48` (`CoverageCalculator`). Явного указания на это в задаче нет, поэтому связь не фиксируется (`S-14`, вариант «только явные связи»).

---

## 10. Задел под вариант 2 (`requirements.yaml`)

Структура записи, готовая к переносу:

```yaml
- id: A-13
  canonical: "04_Search Core.md §14.1 стр.284"
  title: "Обязательность RU-морфологии для MVP"
  text: "Полная морфологическая обработка русского языка обязательна..."
  mentions:
    - "07_QA_Acceptance.md §7.1 стр.118"
    - "MASTER ROADMAP v1.2 стр.436, 578"
  conflicts:
    - "EPIC SPECIFICATIONS v1.0 стр.228 — ✅ исправлено 2026-09-13: «Russian morphology (обязательна для MVP, A-13)»"
  gates: [G-04, G-10]
  epics: [EPIC-04, EPIC-10]
  status: active
  verdict: null

- id: A-01
  canonical: "приложения к ТЗ/MASTER DEVELOPMENT ROADMAP v1.2 — BASELINE.md §21.1 (реестр «УИ v1.0»); внесено 2026-09-13"
  title: "Редакционные ошибки Roadmap и граф зависимостей"
  text: "Версия Roadmap — 1.2, не 1.1; пропуски пунктов 8/10 в Search Core не означают отсутствующие требования (карточки привязаны к названиям подэтапов); техническое ребро EPIC-05 → EPIC-06 удалено, т.к. Change Log разрешает независимый backend; последовательность выдачи эпиков остаётся gated."
  source: "Roadmap, заголовок, §7, §15, Change Log"
  rationale: "Change Log п.8 и строка зависимостей EPIC-06 разрешают независимый backend; пропуски 8/10 — техническое следствие ревизии нумерации"
  acceptance: "граф ацикличен; заявленные зависимости и обратные связи согласованы"
  mentions: [ "EPIC SPECIFICATIONS стр.146", "ROADMAP стр.6, 244, 575", "EPIC→TASK стр.269", "TASK EXEC стр.14" ]
  conflicts: []
  gates: []
  epics: [EPIC-06]
  status: active
  verdict: "D-4 (RESOLVED) — внесено в нормативный состав 2026-09-13, включая источник, обоснование и критерий приёмки"

- id: Q-08
  canonical: "03_Модель данных и хранение.md §9b (ADR-002, принят 2026-09-14)"
  title: "Версионирование Document при смене URL"
  text: "Идемпотентное окно 24 часа; флаг refresh=true в read_url_content (MCP TOOL CONTRACTS §3) — явный механизм принудительного обновления (отдельный refresh-tool не вводится); Evidence фиксирует версию Document (A-21); EXPAND использует последнюю доступную версию; при совпадении content_hash новая версия не создаётся (CONTENT_UNCHANGED). A-21 не изменён — механизм операционализирует его нормативную формулировку."
  mentions: [ "07_QA_Acceptance.md §17", "04_Search Core.md §25", "MCP TOOL CONTRACTS v1.1 §3" ]
  conflicts: []
  gates: [G-04, G-07]
  epics: [EPIC-02, EPIC-04, EPIC-07]
  status: closed
  verdict: "S-12 (RESOLVED) — ADR-002 принят 2026-09-14, черновик Q-08 из корзины утверждён; A-21 согласован"

- id: Q-13
  canonical: "EPIC SPECIFICATIONS v1.0 §12 стр.238 (исключение из Scope); MASTER ROADMAP v1.2 §14 стр.446; EPIC→TASK §13 стр.568"
  title: "Administrator diagnostic token"
  text: "Privileged administrator diagnostic token не вводится в MVP. Локальная диагностика работает без скрытого привилегированного доступа. Будущий привилегированный/удалённый механизм — только отдельным архитектурным решением с полным контрактом (выдача, область полномочий, срок, хранение, отзыв, аудит)."
  removed: [ "E11-T09 (ID не переиспользуется)" ]
  kept: [ "E11-T10 — user-facing diagnostics" ]
  status: closed
  verdict: "решение архитектора 2026-09-13 — принять вариант A, diagnostic token убрать из MVP"
```

**Правила перехода:**
1. Поле `canonical` заполняется **одним** источником; все прочие вхождения уходят в `mentions`.
2. `conflicts` заполняется только для подтверждённых расхождений (сейчас: A-13).
3. `status`: `active` | `open` | `defect` | `post-mvp`.
4. `verdict` ссылается на `REVIEW-REGISTRY.md`, не дублирует его содержание.

---

*Индекс является навигационным слоем и не заменяет ТЗ и нормативные приложения. При расхождении приоритет имеет ТЗ. При правке нормативного текста индекс обновляется тем же изменением.*
