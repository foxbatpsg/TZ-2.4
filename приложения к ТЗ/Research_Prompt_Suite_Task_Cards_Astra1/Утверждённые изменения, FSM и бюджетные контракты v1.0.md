# Утверждённые изменения, FSM и бюджетные контракты v1.0

# Утверждённые изменения, FSM и бюджетные контракты v1.0
**Проект:** Research Prompt Suite
**Статус:** Утверждено для реализации
**Основание:** ТЗ v2.4, State Machine Specification v1.1, MCP Tool Contracts v1.1, MASTER DEVELOPMENT ROADMAP v1.2, рабочие решения A-01–A-21 и решения владельца требований от 2026-09-09.

Документ фиксирует архитектурные решения для реализации. Он не означает прохождение Gate: каждый эпик по-прежнему требует код, обязательные тесты, Evidence Bundle и отдельный Acceptance Gate.

## 1\. Правила исполнения
1. Одновременно реализуется один EPIC.
2. Каждая функциональная карточка включает unit-тесты; для SQLite, транспорта, потоков и файлов обязательны component/integration tests.
3. Тесты не используют Интернет, production DB или реальную LLM в стандартном regression suite.
4. Агент меняет только scope текущей карточки. Проблема вне scope фиксируется как `OUT_OF_SCOPE`.
5. Core единолично владеет бизнес-правилами, бюджетом, дедупликацией, SearchTask execution, FSM и DB-write policy.
6. GUI, LLM, MCP и Watchdog не имеют права напрямую изменять persistent status или писать в SQLite в обход Core/DB Writer.
## 2\. Утверждённые решения A-01–A-21
### A-01. Roadmap и зависимости
*   Версия Roadmap трактуется как 1.2.
*   Пропущенные номера подэтапов Search Core не означают пропущенные требования.
*   EPIC-06 не зависит от EPIC-05 на уровне архитектуры, хотя фактический gated-порядок сохраняется.
### A-02. Приоритет нормативной FSM
`SOFT_STOP`, `HARD_STOP`, `PAUSE`, `RESUME`, `CANCEL` являются командами. `PARTIAL_REPORT` и `REPORT_TRUNCATED_PARTIAL` являются метаданными результата. LLM предлагает, Watchdog сигнализирует, Core выполняет переход.
### A-03. Нормализация данных
Связи и фильтруемые списки хранятся в таблицах `EntityAlias`, `IntentEntity`, `IntentInformationNeed`, `IntentConstraint`, `IntentSourcePreference`, `IntentOutputRequirement`, `SourceIdentifier`, `SearchResultIdentifier`, `ChunkNumericSignature`, `BudgetLedger`, `SufficiencyMetric` и `SufficiencyRuleHit`. JSON допустим только как API-serialization или metadata/config snapshot, но не как источник истины для JOIN и фильтрации.
### A-04. Область уникальности
`query_fingerprint` уникален в пределах Study. Идемпотентность включает тип операции и область Project/Study. Одинаковая цитата в разных Studies не блокируется и не раскрывает чужие данные.
### A-05. Evidence и overlap
Контрактный `evidence_hash` сохраняется для совместимости, но каноническая дедупликация дополнительно проверяет Study, неизменяемую версию Document, полуоткрытый интервал `[char_start, char_end)` и точный текст. Одинаковый текст в разных позициях не объединяется автоматически.
### A-06. Интервалы чанков
Склейка контекста выполняется по интервалам исходного документа. `overlap_group_id` является вспомогательным признаком, а `is_overlap=true` не удаляет уникальную неперекрывающуюся часть чанка из анализа.
### A-07. Стабильные идентификаторы
Используется `DocumentChunk.text`. `chunk_id` детерминирован относительно Document identity, версии chunker и позиции. Поисковый normalized text никогда не заменяет исходный текст цитаты.
### A-08. Несколько происхождений Document
Очищенное тело хранится один раз. Каждое обнаруженное URL/Source фиксируется в `DocumentSourceOccurrence`; первоначальный `source_id` не считается полным списком происхождений.
### A-09. Глобальный реестр
Глобальные identity и locations хранятся отдельными строками. Реестр не даёт доступа к содержимому другого Project. Межфайловая согласованность выполняется через outbox по Q-01.
### A-10. Качество и достоверность
`SourceQualityAssessment` scoped к Study/domain/mode/config revision. Класс доказательности `ESTABLISHED|SUPPORTED|PROMISING|EXPERIMENTAL|CONTRADICTED|UNKNOWN` отделён от `Claim.status`. `confidence` не трактуется как калиброванная вероятность без отдельной статистической модели.
### A-11. SQLite
Для MVP применяется `synchronous=FULL`. `foreign_keys=ON` устанавливается на каждом соединении. Backup выполняется через SQLite backup API, а не копированием активного файла. `journal_size_limit` является настройкой, а не гарантированным жёстким пределом размера WAL.
### A-12. Context Budget
`fixed` использует конфигурационное значение; `auto` использует надёжный backend limit или fallback; `auto_with_config_cap` применяет cap к выбранному auto-значению. Неизвестный limit не трактуется как ноль. Отрицательный `evidence_budget` возвращает `CONFIG_CONTEXT_INSUFFICIENT`.
### A-13. Русская морфология
Русская морфология обязательна для MVP acceptance. BasicNormalizer разрешён только как явно диагностируемый degraded fallback и не закрывает этот критерий. Recall должен быть не ниже 0.9 для нормативных запросов.
### A-14. Cooperative cancellation
Работающие Python-потоки не уничтожаются принудительно. Используются cancellation tokens, короткие батчи и, для неотменяемого CPU-кода, дочерний процесс без прямой записи в DB. Поздние результаты отменённой операции отбрасываются по generation marker.
### A-15. Gaps как основание поиска
Начальный план создаёт `MISSING_DATA` gaps. Каждый SearchTaskDraft связан с gap. Primary-source search также начинается с gap. LLM не создаёт persistent SearchTask напрямую.
### A-16. Разделение Core и Research Engine
EPIC-04 предоставляет чистые типизированные coverage/sufficiency/budget primitives. EPIC-05 управляет итерациями и не реализует второй evaluator.
### A-17. Local provenance
Локальный материал получает внутренний source reference, `file_ref`, `content_hash` и координаты. Публичный URL/DOI/PMID не выдумываются. Абсолютные приватные пути не попадают в LLM или публичный отчёт.
### A-18. Версии конфигурации
ResearchConfig хранится как неизменяемая ревизия. Расширение бюджета создаёт новую ревизию и audit record. Backend profile версионируется отдельно от business thresholds.
### A-19. Ошибки MCP
Доменный error code является строковым полем внутри корректного MCP/JSON-RPC envelope; protocol error и execution error не смешиваются.
### A-20. stdout
Непреднамеренный вывод перехватывается так, чтобы не разрушить transport. CI запрещает `print()` и `sys.stdout.write` вне разрешённых мест. Debug, достигший transport channel, является ошибкой теста.
### A-21. Жизненный цикл индекса
Document, на который ссылается Evidence, неизменяем. Новая версия URL создаёт новую версию Document. BM25 rebuild использует staging generation и атомарное переключение. Удаление Study не удаляет общий Document.
## 3\. Решения по критическим вопросам Q-01–Q-05
### Q-01. Project DB и registry.db
**Решение:** принять согласованность через transactional outbox вместо неподдерживаемой межфайловой атомарности.

Project DB является источником истины. В той же транзакции DB Writer записывает outbox event с `event_id`, типом, project\_id, identity, payload hash, schema version и retry state. Registry Writer идемпотентно применяет событие к `registry.db`. До применения события Project считается сохранённым, но global registry может быть временно stale. Reconciliation job повторяет события и формирует alert после исчерпания retry.

Snapshot нескольких файлов фиксирует общий snapshot manifest и версии всех БД. Нельзя объявлять multi-file snapshot crash-atomic; восстановление проверяет manifest и outbox reconciliation.

**Тестовый минимум:** crash между project commit и registry apply; повтор event; registry отстаёт; повреждённый payload; два проекта с одним hash; восстановление outbox.
### Q-02. Независимость источников
**Решение:** считать независимость на уровне `Claim`/исследовательского вывода, а не только сайта.
*   `COPY`, `REWRITE`, `SAME_PRIMARY` объединяются в один provenance cluster.
*   `CITATION` делает источник зависимым от cited primary по конкретному Claim.
*   `UNKNOWN` не увеличивает independent\_source\_count.
*   Источник без установленной связи считается независимым только если у него иной canonical identity/domain и нет evidence of shared primary.
*   Отношения, применимые к одному Claim, не превращают весь Source в зависимый для всех Claims.
*   При недостатке данных итоговый статус: `INSUFFICIENT_EVIDENCE`, а не искусственное увеличение confidence.

Формула:

```plain
independent_source_count(claim)
= число provenance-кластеров, связанных с Claim,
  которые не являются COPY, REWRITE, SAME_PRIMARY,
  не являются зависимыми CITATION и не имеют UNKNOWN relation.
```

### Q-03. SufficiencyEvaluator
**Решение:** использовать консервативные strategy profiles и детерминированный порядок решений.

Базовые MVP-пороги для `EVIDENCE`:
*   `question_coverage = 1.0`;
*   `attribute_coverage = 1.0` для обязательных attributes;
*   `min_independent_sources = 2`;
*   `min_verified_evidence = 3`;
*   `contradiction_count = 0`;
*   `information_gain_threshold = 0.05`.

Для `AGGREGATION` обязательные attributes также должны быть покрыты полностью; минимум уникальных верифицированных авторов задаётся отдельным профилем. Анонимные/неверифицированные авторы не закрывают этот минимум.

`information_gain` за итерацию:

```plain
gain = new_verified_evidence_count /
       max(1, verified_evidence_count_before_iteration)
```

Для первой итерации знаменатель равен 1. `STOP_NO_INFORMATION_GAIN` применяется после двух последовательных завершённых итераций с gain < 0.05, если нет открытого критического gap с доступным бюджетом. Приоритет решения:

```plain
STOP_BUDGET
> STOP_NO_AVAILABLE_SOURCES
> STOP_NO_INFORMATION_GAIN
> STOP_SUFFICIENT
> CONTINUE
```

`STOP_SUFFICIENT` запрещён при неразрешённых противоречиях или если любой обязательный threshold не выполнен. Каждая проверка пишет `SufficiencyEvaluation`, snapshot metrics и `SufficiencyRuleHit`.
### Q-04. Бюджет
**Решение:** использовать reserve → commit/release и журнал фактического потребления.
*   `network_budget`: каждый фактически отправленный внешний сетевой request attempt, включая retry; cache hit сеть не потребляет.
*   `fetch_budget`: каждый успешно сохранённый полный Document/Transcript; неуспешный ответ fetch не списывает fetch unit.
*   `tool_call_budget`: каждый MCP вызов после базовой transport/schema validation; malformed JSON до Core не списывает исследовательский бюджет.
*   `llm_call_budget`: каждый фактически начатый вызов LLM; отменённый после начала вызов считается потреблённым.
*   `llm_token_budget`: сумма фактических input/prompt и output/completion tokens; если backend usage отсутствует, применяется детерминированная оценка и диагностический флаг.
*   `step_budget`: каждая реально начатая SearchTask execution или итерация, по утверждённому профилю; preview не списывает.
*   `time_budget`: monotonic elapsed time активного исследования; PAUSED и подтверждённое ожидание восстановления не списываются.

Перед операцией Core резервирует все необходимые dimensions одной SQLite-транзакцией. После операции фактическое потребление commit-ится, неиспользованный reserve освобождается. Любой нулевой доступный dimension блокирует операцию и ведёт к `BUDGET_EXHAUSTED → FREEZE_BUDGET_EXHAUSTED`. Диагностика, cancel и recovery-read операции не требуют research budget, но имеют transport timeout.

Расширение бюджета возможно только явной GUI/Core command, создаёт новую ResearchConfig revision и LogRecord. `validate_and_save_report` не списывает `llm_call_budget`, если сам не запускал LLM.
### Q-05. Дополнения FSM
**Решение:** добавить только следующие переходы, не превращая команды в states.
*   Study: `PAUSED → USER_STOPPED` по `HARD_STOP`.
*   Study: `FREEZE_BUDGET_EXHAUSTED → USER_STOPPED` по `HARD_STOP`.
*   Study: `READY → PLANNING` по `EDIT_PLAN`, только без активной session.
*   Study: `USER_STOPPED → FINALIZING` по `FINALIZE_PARTIAL`.
*   Study: `FINALIZING → USER_STOPPED` по `PARTIAL_REPORT_VALID`.
*   SearchTask: `CREATED → CANCELLED` и `VALIDATING → CANCELLED` по `CANCEL`.
*   SearchTask: `VALIDATING → FAILED` по `VALIDATION_ERROR` для технической ошибки, не являющейся duplicate/similarity/coverage/budget rejection.
*   SearchTask: `FAILED → QUEUED` по `RETRY_APPROVED`, если fingerprint и config revision совместимы и Core выделил новый operation\_id.
*   Job: `QUEUED → CANCELLED` по `CANCEL_CONFIRMED` от Job runner.

После recovery timeout Core по межавтоматному policy переводит ResearchSession в `CLOSED`; Study получает `FAILED`, если нет безопасного fallback. Hard Stop всегда завершает активные SearchTask/Jobs кооперативной отменой, а пользовательский partial report сохраняет Study в `USER_STOPPED`, не в `COMPLETED`.
## 4\. Обновлённая FSM
### 4.1. Нормативные инварианты
1. Только Core выполняет business transitions.
2. Каждый переход атомарен со своей `LogRecord`.
3. Команда не является состоянием.
4. Runtime MCP Operation, LLM Backend и Job не заменяют Study/Session/SearchTask.
5. Невозможный переход не меняет состояние.
6. Все status mutations проходят через State Machine API; публичного setter status нет.
### 4.2. Study
**States:** `DRAFT`, `PLANNING`, `READY`, `RUNNING`, `PAUSED`, `BUDGET_EXHAUSTED`, `FREEZE_BUDGET_EXHAUSTED`, `FINALIZING`, `COMPLETED`, `FAILED`, `USER_STOPPED`, `ARCHIVED`.

**Transitions:**

| From | To | Trigger | Guard/meaning |
| ---| ---| ---| --- |
| DRAFT | PLANNING | START\_PLANNING | Core starts planning |
| PLANNING | READY | PLAN\_APPROVED | validated plan |
| PLANNING | DRAFT | CANCEL\_PLANNING | planning cancelled |
| READY | PLANNING | EDIT\_PLAN | no active session |
| READY | RUNNING | START\_RESEARCH | plan ready, budget available |
| RUNNING | PAUSED | PAUSE | Core confirms pause |
| PAUSED | RUNNING | RESUME | checkpoint valid |
| RUNNING | BUDGET\_EXHAUSTED | BUDGET\_ZERO | any billable dimension unavailable |
| BUDGET\_EXHAUSTED | FREEZE\_BUDGET\_EXHAUSTED | BUDGET\_FREEZE | no new work allowed |
| BUDGET\_EXHAUSTED | RUNNING | BUDGET\_EXTENDED | explicit approved extension |
| FREEZE\_BUDGET\_EXHAUSTED | RUNNING | BUDGET\_EXTENDED | explicit approved extension |
| FREEZE\_BUDGET\_EXHAUSTED | FINALIZING | FINALIZE\_PARTIAL | partial finalization requested |
| RUNNING | FINALIZING | STOP\_SUFFICIENT / STOP\_NO\_INFORMATION\_GAIN / STOP\_NO\_AVAILABLE\_SOURCES / SOFT\_STOP | Core decision |
| RUNNING | USER\_STOPPED | HARD\_STOP | immediate user stop |
| PAUSED | USER\_STOPPED | HARD\_STOP | stop while paused |
| FREEZE\_BUDGET\_EXHAUSTED | USER\_STOPPED | HARD\_STOP | stop while frozen |
| RUNNING | FAILED | CRITICAL\_ERROR | unrecoverable Study error |
| FINALIZING | COMPLETED | REPORT\_VALID | complete report valid |
| FINALIZING | FAILED | FINALIZATION\_ERROR | finalization failed |
| FINALIZING | USER\_STOPPED | PARTIAL\_REPORT\_VALID | partial report after hard stop |
| USER\_STOPPED | FINALIZING | FINALIZE\_PARTIAL | explicit partial finalization |
| COMPLETED / FAILED / USER\_STOPPED | ARCHIVED | ARCHIVE | terminal archive |

`PARTIAL_REPORT`, `REPORT_TRUNCATED_PARTIAL` и `STARTED` не являются Study states.
### 4.3. ResearchSession
**States:** `INITIALIZING`, `ACTIVE`, `LLM_UNAVAILABLE`, `SESSION_RESUMING`, `SUSPENDED`, `CLOSING`, `CLOSED`.

**Transitions:** сохраняются из v1.1: INIT\_COMPLETE, RECOVERY\_REQUIRED, RECOVERY\_COMPLETE, RECOVERY\_FAILED, LLM\_BACKEND\_UNAVAILABLE, LLM\_BACKEND\_RECOVERED, RECOVERY\_TIMEOUT, STUDY\_PAUSED, STUDY\_RESUMED, STUDY\_FINISHING, SESSION\_CLOSED.

Policy: `RECOVERY_FAILED` или `RECOVERY_TIMEOUT` закрывает Session и передаёт Core межавтоматное решение Study согласно Q-05; LLM backend status не хранится в budget\_state.
### 4.4. SearchTask
**States:** `CREATED`, `VALIDATING`, `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `REJECTED_DUPLICATE`, `REJECTED_SIMILAR`, `REJECTED_COVERAGE`, `REJECTED_BUDGET`, `CANCELLED`.

Добавленные переходы:

| From | To | Trigger |
| ---| ---| --- |
| CREATED | CANCELLED | CANCEL |
| VALIDATING | CANCELLED | CANCEL |
| VALIDATING | FAILED | VALIDATION\_ERROR |
| FAILED | QUEUED | RETRY\_APPROVED |

`RETRY_APPROVED` требует совместимых fingerprint/config revision и нового operation\_id. `SearchResult.task_id` всегда ссылается на конкретный SearchTask.
### 4.5. MCP Operation
**States:** `REQUESTED`, `VALIDATING`, `EXECUTING`, `COMPLETED`, `FAILED`, `TIMED_OUT`, `CANCELLED`.

Retry ограничен `max_attempts` из operation policy. После исчерпания retries переход `TIMED_OUT → FAILED`; бесконечный цикл запрещён.
### 4.6. LLM Backend
**States:** `HEALTHY`, `DEGRADED`, `UNREACHABLE`, `RESTARTING`.

Переходы выполняет Watchdog через Core command/event boundary. Backend switch не меняет историю Study и thresholds; новый context profile фиксируется до следующего LLM call.
### 4.7. Job
**States:** `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`.

`cancel_job` сначала устанавливает cancellation request. Фактический переход в `CANCELLED` выполняет runner после безопасной точки и commit checkpoint.
## 5\. Бюджетный контракт v1.0
### 5.1. Модель

```plain
ResearchBudget
├── step_budget
├── network_budget
├── fetch_budget
├── tool_call_budget
├── llm_call_budget
├── llm_token_budget
└── time_budget
```

Для каждой dimension хранятся:

```plain
BudgetState
├── limit
├── consumed
├── reserved
├── available = limit - consumed - reserved
├── config_revision
└── updated_at
```

Каждая reservation содержит `reservation_id`, `operation_id`, `dimension`, `amount`, `status`, `created_at`, `committed_at` и фактическое потребление.
### 5.2. API ядра

```plain
reserve(operation_id, dimensions) -> Reservation | BudgetRejected
commit(reservation_id, actual_usage) -> BudgetState
release(reservation_id) -> BudgetState
extend_budget(study_id, explicit_user_command, new_limits) -> ConfigRevision
```

`reserve` и изменение счётчиков выполняются в одной SQLite transaction. Повторный вызов с тем же operation\_id/idempotency key не создаёт второй debit. Actual usage не может быть отрицательным и не может превышать зарезервированный объём без отдельного Core-approved overflow path.
### 5.3. Тарификация

| Dimension | Единица списания | Когда commit |
| ---| ---| --- |
| step | начатая SearchTask execution/итерация | после начала подтверждённой работы |
| network | фактически отправленная внешняя request attempt | после отправки/завершения attempt |
| fetch | успешно сохранённый полный Document/Transcript | после atomic persistence |
| tool\_call | MCP вызов после schema validation | после принятия Core operation |
| llm\_call | фактически начатый LLM call | после начала call |
| llm\_token | input + output tokens | после получения usage/оценки |
| time | активное monotonic time | при checkpoint/finalization |

Cache hit, preview, read-only diagnostics, cancel и recovery reads не потребляют research dimensions, если конкретный strategy profile явно не включит их.
### 5.4. Нулевой бюджет и расширение
При `available == 0` Core не начинает новую billable operation. Study проходит `BUDGET_EXHAUSTED → FREEZE_BUDGET_EXHAUSTED`. После `BUDGET_FREEZE` новые SearchTask получают `REJECTED_BUDGET`. Partial finalization не требует нового LLM call, если доступен уже сохранённый валидный материал.

Явное расширение:

```plain
GUI command
  ↓
Core validates actor, Study state and new limits
  ↓
new ResearchConfig revision + LogRecord
  ↓
BudgetState limit update
  ↓
BUDGET_EXTENDED transition
```

Никаких silent budget increases, изменения лимитов «на лету» без revision или списания в MCP adapter.
### 5.5. Бюджетные тесты Gate
Обязательны: конкурентная reservation, rollback после ошибки, retry network, cache hit, timeout LLM, missing token usage, pause/resume time, zero budget, explicit extension, duplicate operation, crash после reserve и recovery reconciliation.
## 6\. Порядок дальнейшей реализации
1. Обновить нормативные документы и генератор карточек этими решениями.
2. Реализовать EPIC-01 и пройти G-01.
3. В EPIC-02 сначала сделать local Project DB, migrations, writer и outbox; registry sync — только по этому контракту.
4. Закрыть component tests SQLite и G-02.
5. Реализовать EPIC-03 и проверить всю утверждённую FSM матрицу.
6. Перед EPIC-04 отдельно зафиксировать strategy profiles в config fixtures.
7. Q-06–Q-13 остаются следующими блокерами соответствующих эпиков и не могут быть замаскированы mock-тестами.
## 7\. Обязательные документы, которые ещё должны быть обновлены
*   `STATE MACHINE SPECIFICATION v1.2` с таблицами переходов из раздела 4.
*   `BUDGET CONTRACT v1.0` с тарификацией, reservation API и test matrix из раздела 5.
*   `MCP TOOL CONTRACTS v1.2` после решения Q-06/Q-07/Q-08.
*   EPIC/TASK карточки, чтобы они ссылались на версии контрактов, а не на устаревшие Q-01–Q-05.

**Статус:** A-01–A-21 утверждены. Q-01–Q-05 решены настоящим документом. Q-06–Q-13 остаются открытыми до отдельных архитектурных решений.