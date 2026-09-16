---
# BUDGET CONTRACT v1.0

**Статус:** Нормативное приложение к ТЗ v2.6
**Назначение:** Формальное определение модели исследовательского бюджета `ResearchBudget`, API резервирования/коммита/освобождения/расширения, тарификации 7 dimension и test matrix для бюджетного Gate.
**База:** Утверждённые изменения v1.0 (раздел 5), ТЗ v2.6 §6a, решение Q-04.

Документ фиксирует единую границу расходов: все billable operation проходят через `reserve → commit/release`; `extend_budget` — единственный способ изменить лимит. Никаких silent budget increases, изменений лимитов «на лету» или списаний в MCP adapter.

---

## 1. Модель (УИ v1.0 §5.1)

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

`ResearchConfig` хранится как неизменяемая ревизия. Расширение бюджета создаёт новую ревизию и `LogRecord`. Backend profile версионируется отдельно от business thresholds.

---

## 2. API ядра (УИ v1.0 §5.2)

```plain
reserve(operation_id, dimensions) -> Reservation | BudgetRejected
commit(reservation_id, actual_usage) -> BudgetState
release(reservation_id) -> BudgetState
extend_budget(study_id, explicit_user_command, new_limits) -> ConfigRevision
```

`reserve` и изменение счётчиков выполняются в одной SQLite transaction. Повторный вызов с тем же `operation_id`/`idempotency key` не создаёт второй debit. `actual_usage` не может быть отрицательным и не может превышать зарезервированный объём без отдельного Core-approved overflow path.

---

## 3. Тарификация (УИ v1.0 §5.3)

| Dimension | Единица списания | Когда commit |
| ---| ---| --- |
| step | начатая SearchTask execution/итерация | после начала подтверждённой работы |
| network | фактически отправленная внешняя request attempt | после отправки/завершения attempt |
| fetch | успешно сохранённый полный Document/Transcript | после atomic persistence |
| tool_call | MCP вызов после schema validation | после принятия Core operation |
| llm_call | фактически начатый LLM call | после начала call |
| llm_token | input + output tokens | после получения usage/оценки |
| time | активное monotonic time | при checkpoint/finalization |

Cache hit, preview, read-only diagnostics, cancel и recovery reads не потребляют research dimensions, если конкретный strategy profile явно не включит их.

---

## 4. Нулевой бюджет и расширение (УИ v1.0 §5.4)

При `available == 0` Core не начинает новую billable operation. Study проходит `BUDGET_EXHAUSTED → FREEZE_BUDGET_EXHAUSTED`. После `BUDGET_FREEZE` новые SearchTask получают `REJECTED_BUDGET`. Partial finalization не требует нового LLM call, если доступен уже сохранённый валидный материал.

Явное расширение:

```text
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

Никаких silent budget increases, изменений лимитов «на лету» без revision или списания в MCP adapter.

---

## 5. Бюджетные тесты Gate (УИ v1.0 §5.5)

Обязательны: конкурентная reservation, rollback после ошибки, retry network, cache hit, timeout LLM, missing token usage, pause/resume time, zero budget, explicit extension, duplicate operation, crash после reserve и recovery reconciliation.

---

**Конец BUDGET CONTRACT v1.0**
