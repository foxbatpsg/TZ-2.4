---
# STATE MACHINE SPECIFICATION v1.1

**Статус:** Нормативное приложение к ТЗ v2.4  
**Назначение:** Формальное определение конечных автоматов системы и единственных правил изменения состояний.

## 0. Нормативные правила

1. Поле `status` любой persistent-сущности, для которой определён автомат, изменяется **только через соответствующий State Machine**. Прямое присваивание статуса запрещено.
2. Core является единственным исполнителем бизнес-переходов. GUI, LLM, Watchdog и System только инициируют допустимый trigger/command.
3. Каждый фактически выполненный переход фиксируется в `LogRecord`:
   `entity_type`, `entity_id`, `from_state`, `to_state`, `trigger`, `component`, `timestamp`.
4. `SOFT_STOP`, `HARD_STOP`, `PAUSE`, `RESUME`, `CANCEL` и аналогичные пользовательские действия являются **командами/триггерами**, а не состояниями.
5. `PARTIAL_REPORT` и `REPORT_TRUNCATED_PARTIAL` не являются состояниями Study. Это признаки/метаданные результата финализации.
6. MCP Operation и Job являются runtime-объектами исполнения. Их состояние не должно использоваться как замена состояниям Study, ResearchSession или SearchTask.
7. Ни один MCP tool не имеет права самостоятельно обходить State Machine или выполнять прямое изменение `status`.
8. Если переход невозможен из текущего состояния, Core возвращает детерминированную ошибку и не изменяет состояние.
9. Переход должен быть атомарным относительно записи состояния и соответствующего audit LogRecord.

---

## 1. Study

### Состояния

| Состояние | Описание |
|---|---|
| `DRAFT` | Исследование создано, планирование не завершено |
| `PLANNING` | Формируется и корректируется план |
| `READY` | План утверждён, исследование готово к запуску |
| `RUNNING` | Активное выполнение |
| `PAUSED` | Исследование приостановлено |
| `BUDGET_EXHAUSTED` | Обнаружено исчерпание бюджета, решение ещё не зафиксировано |
| `FREEZE_BUDGET_EXHAUSTED` | Новая работа заморожена из-за бюджета |
| `FINALIZING` | Выполняется финализация результата |
| `COMPLETED` | Исследование завершено и результат валиден |
| `FAILED` | Исследование завершено критической невосстановимой ошибкой |
| `USER_STOPPED` | Исследование принудительно остановлено пользователем |
| `ARCHIVED` | Завершённое исследование архивировано |

### Переходы

| Из | В | Trigger | Исполнитель |
|---|---|---|---|
| `DRAFT` | `PLANNING` | `START_PLANNING` | Core |
| `PLANNING` | `READY` | `PLAN_APPROVED` | Core |
| `PLANNING` | `DRAFT` | `CANCEL_PLANNING` | Core |
| `READY` | `RUNNING` | `START_RESEARCH` | Core |
| `RUNNING` | `PAUSED` | `PAUSE` | Core |
| `PAUSED` | `RUNNING` | `RESUME` | Core |
| `RUNNING` | `BUDGET_EXHAUSTED` | `BUDGET_ZERO` | Core |
| `BUDGET_EXHAUSTED` | `FREEZE_BUDGET_EXHAUSTED` | `BUDGET_FREEZE` | Core |
| `BUDGET_EXHAUSTED` | `RUNNING` | `BUDGET_EXTENDED` | Core |
| `FREEZE_BUDGET_EXHAUSTED` | `RUNNING` | `BUDGET_EXTENDED` | Core |
| `FREEZE_BUDGET_EXHAUSTED` | `FINALIZING` | `FINALIZE_PARTIAL` | Core |
| `RUNNING` | `FINALIZING` | `STOP_SUFFICIENT` | Core |
| `RUNNING` | `FINALIZING` | `STOP_NO_INFORMATION_GAIN` | Core |
| `RUNNING` | `FINALIZING` | `STOP_NO_AVAILABLE_SOURCES` | Core |
| `RUNNING` | `FINALIZING` | `SOFT_STOP` | Core |
| `RUNNING` | `USER_STOPPED` | `HARD_STOP` | Core |
| `RUNNING` | `FAILED` | `CRITICAL_ERROR` | Core |
| `FINALIZING` | `COMPLETED` | `REPORT_VALID` | Core |
| `FINALIZING` | `USER_STOPPED` | `HARD_STOP` | Core |
| `FINALIZING` | `FAILED` | `FINALIZATION_ERROR` | Core |
| `COMPLETED` | `ARCHIVED` | `ARCHIVE` | Core |
| `FAILED` | `ARCHIVED` | `ARCHIVE` | Core |
| `USER_STOPPED` | `ARCHIVED` | `ARCHIVE` | Core |

### Важные правила

- `SOFT_STOP` означает: прекратить создание новой работы, безопасно завершить уже выполняемые операции и перейти к финализации.
- `HARD_STOP` означает: запросить отмену активных Jobs/операций и немедленно перейти в `USER_STOPPED`.
- При `BUDGET_ZERO` Core сначала переводит Study в `BUDGET_EXHAUSTED`, затем выполняет `BUDGET_FREEZE`.
- `FREEZE_BUDGET_EXHAUSTED → FINALIZING` означает финализацию с имеющимися данными. Результат помечается как partial, но Study после успешной финализации получает `COMPLETED`.
- `PARTIAL` не является состоянием Study.

### Запись

При каждом переходе изменяются `Study.status`, `Study.updated_at` и создаётся `LogRecord`.

---

## 2. ResearchSession

### Состояния

| Состояние | Описание |
|---|---|
| `INITIALIZING` | Создание/загрузка состояния сессии |
| `ACTIVE` | Сессия активна |
| `LLM_UNAVAILABLE` | Текущий LLM backend недоступен |
| `SESSION_RESUMING` | Восстановление после сбоя |
| `SUSPENDED` | Сессия приостановлена вместе с Study |
| `CLOSING` | Завершение сессии |
| `CLOSED` | Сессия закрыта |

### Переходы

| Из | В | Trigger | Исполнитель |
|---|---|---|---|
| `INITIALIZING` | `ACTIVE` | `INIT_COMPLETE` | Core |
| `INITIALIZING` | `SESSION_RESUMING` | `RECOVERY_REQUIRED` | Core |
| `SESSION_RESUMING` | `ACTIVE` | `RECOVERY_COMPLETE` | Core |
| `SESSION_RESUMING` | `CLOSED` | `RECOVERY_FAILED` | Core |
| `ACTIVE` | `LLM_UNAVAILABLE` | `LLM_BACKEND_UNAVAILABLE` | Core |
| `LLM_UNAVAILABLE` | `SESSION_RESUMING` | `LLM_BACKEND_RECOVERED` | Core |
| `LLM_UNAVAILABLE` | `CLOSED` | `RECOVERY_TIMEOUT` | Core |
| `ACTIVE` | `SUSPENDED` | `STUDY_PAUSED` | Core |
| `SUSPENDED` | `ACTIVE` | `STUDY_RESUMED` | Core |
| `ACTIVE` | `CLOSING` | `STUDY_FINISHING` | Core |
| `SUSPENDED` | `CLOSING` | `STUDY_FINISHING` | Core |
| `CLOSING` | `CLOSED` | `SESSION_CLOSED` | Core |

`ResearchSession.status` отражает состояние конкретной сессии. Состояние LLM backend не хранится в `budget_state`.

### Запись

`ResearchSession.status`, `ended_at` и `LogRecord`.

---

## 3. SearchTask

### Состояния

| Состояние | Описание |
|---|---|
| `CREATED` | Задача создана |
| `VALIDATING` | Проверяется Core |
| `QUEUED` | Валидна и ожидает выполнения |
| `RUNNING` | Выполняется |
| `COMPLETED` | Результаты получены и сохранены |
| `FAILED` | Выполнение завершилось ошибкой |
| `REJECTED_DUPLICATE` | Exact duplicate |
| `REJECTED_SIMILAR` | Критически похожий запрос |
| `REJECTED_COVERAGE` | Информационная потребность уже покрыта |
| `REJECTED_BUDGET` | Недостаточно бюджета |
| `CANCELLED` | Отменена |

### Переходы

| Из | В | Trigger | Исполнитель |
|---|---|---|---|
| `CREATED` | `VALIDATING` | `VALIDATE_TASK` | Core |
| `VALIDATING` | `QUEUED` | `VALIDATION_PASSED` | Core |
| `VALIDATING` | `REJECTED_DUPLICATE` | `EXACT_MATCH` | Core |
| `VALIDATING` | `REJECTED_SIMILAR` | `SIMILARITY_MATCH` | Core |
| `VALIDATING` | `REJECTED_COVERAGE` | `COVERAGE_MATCH` | Core |
| `VALIDATING` | `REJECTED_BUDGET` | `BUDGET_REJECT` | Core |
| `QUEUED` | `RUNNING` | `TASK_STARTED` | Core |
| `QUEUED` | `CANCELLED` | `CANCEL` | Core |
| `RUNNING` | `COMPLETED` | `RESULTS_SAVED` | Core |
| `RUNNING` | `FAILED` | `EXECUTION_ERROR` | Core |
| `RUNNING` | `CANCELLED` | `CANCEL` | Core |

`SearchResult.task_id` всегда указывает на соответствующий SearchTask.

### Query Fingerprint

Единый алгоритм определяется Search Core:

```text
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
```

MCP layer не рассчитывает альтернативный fingerprint и не переопределяет его.

### Запись

`SearchTask.status`, `completed_at` и `LogRecord`.

---

## 4. MCP Operation

### Назначение

Runtime state machine для конкретного вызова MCP tool. `MCP Operation` не является persistent domain entity и не заменяет состояния бизнес-сущностей.

### Состояния

`REQUESTED`, `VALIDATING`, `EXECUTING`, `COMPLETED`, `FAILED`, `TIMED_OUT`, `CANCELLED`.

### Переходы

| Из | В | Trigger | Исполнитель |
|---|---|---|---|
| `REQUESTED` | `VALIDATING` | `REQUEST_RECEIVED` | Core |
| `VALIDATING` | `EXECUTING` | `INPUT_VALID` | Core |
| `VALIDATING` | `FAILED` | `INVALID_INPUT` | Core |
| `EXECUTING` | `COMPLETED` | `TOOL_SUCCESS` | Core |
| `EXECUTING` | `FAILED` | `TOOL_ERROR` | Core |
| `EXECUTING` | `TIMED_OUT` | `OPERATION_TIMEOUT` | Watchdog/Core |
| `EXECUTING` | `CANCELLED` | `CANCEL_REQUESTED` | Core |
| `TIMED_OUT` | `EXECUTING` | `RETRY_ALLOWED` | Core |
| `TIMED_OUT` | `FAILED` | `RETRY_EXHAUSTED` | Core |

Retry не должен бесконечно переводить операцию между `TIMED_OUT` и `EXECUTING`.

`operation_id` создаётся при начале операции и используется для трассировки, логирования и связи создаваемых сущностей.

---

## 5. LLM Backend

### Состояния

`HEALTHY`, `DEGRADED`, `UNREACHABLE`, `RESTARTING`.

### Переходы

| Из | В | Trigger | Исполнитель |
|---|---|---|---|
| `HEALTHY` | `DEGRADED` | `HEALTH_DEGRADED` | Watchdog |
| `HEALTHY` | `UNREACHABLE` | `HEALTH_FAILED` | Watchdog |
| `DEGRADED` | `HEALTHY` | `HEALTH_RECOVERED` | Watchdog |
| `DEGRADED` | `UNREACHABLE` | `HEALTH_FAILED` | Watchdog |
| `UNREACHABLE` | `RESTARTING` | `RESTART_REQUESTED` | Watchdog |
| `UNREACHABLE` | `HEALTHY` | `BACKEND_RECOVERED` | Watchdog |
| `RESTARTING` | `HEALTHY` | `RESTART_SUCCESS` | Watchdog |
| `RESTARTING` | `UNREACHABLE` | `RESTART_FAILED` | Watchdog |

Состояние LLM backend является runtime/operational state. Оно не хранится в `ResearchSession.budget_state`. Переходы фиксируются в `LogRecord` и диагностике.

---

## 6. Job

Job-механизм определён в Search Core и применяется только для действительно долгих операций:

- массовая индексация;
- перестроение BM25-индекса;
- крупный импорт локальных файлов;
- длительная пакетная обработка.

Состояния:

`QUEUED → RUNNING → COMPLETED | FAILED | CANCELLED`.

Кооперативная отмена выполняется через `cancel_job`. Job не блокирует MCP transport.

При аварийном завершении незавершённый Job переводится Core в `FAILED`, если механизм восстановления не может безопасно продолжить его.

---

## 7. Сквозные сценарии

### Soft Stop

```text
Study:
RUNNING → FINALIZING → COMPLETED

ResearchSession:
ACTIVE → CLOSING → CLOSED

SearchTask:
RUNNING → COMPLETED
```

Для активных операций допускается завершение текущего атомарного шага перед финализацией.

### Hard Stop

```text
Study:
RUNNING → USER_STOPPED

ResearchSession:
ACTIVE → CLOSING → CLOSED

SearchTask:
RUNNING → CANCELLED

MCP Operation:
EXECUTING → CANCELLED

Job:
RUNNING → CANCELLED
```

### Budget Exhaustion

```text
Study:
RUNNING
  → BUDGET_EXHAUSTED
  → FREEZE_BUDGET_EXHAUSTED
  → FINALIZING
  → COMPLETED
```

Новые SearchTask при нулевом бюджете:

```text
CREATED → VALIDATING → REJECTED_BUDGET
```

Итоговый отчёт помечается как partial через metadata/result status, но `PARTIAL_REPORT` не становится состоянием Study.

### LLM Failure / Recovery

```text
LLM Backend:
HEALTHY → UNREACHABLE → RESTARTING → HEALTHY

ResearchSession:
ACTIVE → LLM_UNAVAILABLE → SESSION_RESUMING → ACTIVE

Study:
RUNNING
```

Study не обязан останавливаться только из-за временной недоступности LLM backend.

---

## 8. Запрещённые конструкции

Запрещено создавать состояния:

- `SOFT_STOP`;
- `HARD_STOP`;
- `PARTIAL_REPORT`;
- `REPORT_TRUNCATED_PARTIAL`;
- `STARTED`;
- `ALREADY_RUNNING`;
- `RETRYING`.

Это commands, result statuses или runtime outcomes, а не состояния Study/ResearchSession/SearchTask.

**Конец State Machine Specification v1.1**
