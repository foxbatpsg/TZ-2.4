# TASK EXECUTION CONTRACT v1.0 --- BASELINE

**Проект:** Research Prompt Suite\
**Статус:** нормативный контракт выполнения TASK\
**Назначение:** единые правила передачи, выполнения, проверки и
завершения технической TASK AI-агентами.

## 1. Назначение

TASK Execution Contract определяет границу полномочий AI-агента при
выполнении одной TASK.

Контракт применяется к каждой изолированной TASK и является операционным
дополнением к ТЗ, Утверждённым изменениям v1.0 (A-01…A-21, Q-01…Q-05),
State Machine Specification v1.2, BUDGET CONTRACT v1.0, MCP Tool Contracts,
MASTER DEVELOPMENT ROADMAP, EPIC Specification и конкретной TASK.

Контракт не изменяет требования этих документов.

## 2. Главный принцип

**Агент выполняет назначенную TASK, а не «улучшает проект».**

``` text
TASK → READ → UNDERSTAND → PLAN → IMPLEMENT → TEST → VERIFY → REPORT
```

Обнаруженная проблема не является автоматически частью текущей TASK.

## 3. Иерархия полномочий

``` text
ТЗ
 ↓
State Machine / MCP Contracts
 ↓
Roadmap
 ↓
EPIC Specification
 ↓
TASK
 ↓
Agent implementation
```

При конфликте нижестоящего документа с вышестоящим:

**STOP → REPORT → WAIT.**

Агент не исправляет конфликт самостоятельно.

## 4. TASK Context Header

Каждая TASK передаётся с компактным Context Header:

``` text
TASK-ID:
TYPE:
ROLE:
EPIC:
GOAL:
SCOPE:
ALLOWED_FILES:
FORBIDDEN_FILES:
BASELINE_ID:
INPUTS:
OUTPUTS:
CONTRACT:
DEPENDENCIES:
TESTS:
ACCEPTANCE:
STOP_CONDITIONS:
```

**`BASELINE_ID` (S-09):** идентификатор согласованного набора версий нормативных документов, с которым выполняется задача. Поле обязательно во всех TASK.

- До введения baseline в проекте (набор версий и хешей нормативных документов ещё не зафиксирован) в поле указывается переходное значение `PRE-BASELINE`.
- После введения baseline указывается только реальный идентификатор. Значение `PRE-BASELINE` после этого не допускается.
- Задача, несущая `BASELINE_ID`, несовместимый с текущим baseline проекта, не запускается: **BLOCKED / STOP** (см. §4).

Если обязательной информации нет и без неё нельзя безопасно выполнить
TASK:

**BLOCKED / STOP.**

## 5. Scope

Агент изменяет только то, что явно входит в `SCOPE` или `ALLOWED_FILES`.

Запрещено автоматически расширять функциональность, архитектуру, API,
модель данных, зависимости, публичные контракты, тестовую политику,
конфигурацию или структуру проекта.

## 6. Minimal Change Principle

Агент обязан делать минимально необходимое изменение.

Без необходимости текущей TASK запрещено: - форматировать соседний
код; - переименовывать соседние функции, классы или переменные; -
выполнять незапрошенный refactoring; - менять стиль существующего
кода; - исправлять соседние дефекты; - удалять существующий код; -
заменять работающую реализацию; - менять API; - менять архитектурные
границы.

Большой diff не является доказательством качества.

## 7. CODE ≠ Architect

CODE-агент реализует заданное решение и может выбирать локальный способ
реализации в пределах TASK.

CODE не принимает архитектурных решений за пределами TASK и не изменяет
архитектурные контракты.

Если реализация требует архитектурного изменения:

**STOP → REPORT → WAIT.**

## 8. CODE не создаёт новые TASK

Критическое правило:

> **CODE не имеет права самостоятельно превращать обнаруженную проблему
> в новую TASK.**

``` text
Обнаружена проблема
        ↓
Входит в текущий SCOPE?
   ↙              ↘
 ДА                НЕТ
 ↓                   ↓
Исправить          STOP
                     ↓
                   REPORT
                     ↓
                   WAIT
```

Если проблема вне scope, агент только фиксирует её в отчёте.

## 9. Работа с неоднозначностью

При противоречии, отсутствующем обязательном входе, неясном acceptance
criterion, неизвестном контракте или невозможном требовании агент не
выбирает вариант самостоятельно, если выбор меняет архитектуру, контракт
или ожидаемое поведение.

Статус:

**BLOCKED**

Формат:

``` text
УТОЧНЕНИЕ:
[точный вопрос]

КОНФЛИКТ:
[что противоречит чему]

ВЛИЯНИЕ:
[почему нельзя безопасно продолжить]
```

## 10. Работа с существующим кодом

Перед изменением агент обязан: 1. найти существующую реализацию; 2.
прочитать затрагиваемый код; 3. проверить связанные интерфейсы; 4.
определить существующие тесты; 5. проверить ограничения TASK.

Не переписывать код только потому, что другой вариант кажется лучше.

## 11. Production code

Для CODER: - только текущая TASK; - только разрешённый scope; -
минимальный diff; - обязательные tests; - сохранение существующих
контрактов.

TESTER, REVIEWER, REQUIREMENTS_VALIDATOR и ARCHITECTURE_GUARDIAN не
изменяют production code, если это не является отдельной явно
назначенной TASK.

## 12. Тесты

Каждая функциональная TASK должна иметь проверяемые acceptance cases.

``` text
TEST-01: valid input → expected output
TEST-02: empty input → expected error/value
TEST-03: invalid input → expected error
TEST-04: duplicate input → expected idempotent result
TEST-05: boundary condition → expected result
```

Агент не ослабляет и не удаляет тесты для получения PASS.

## 13. TESTER

TESTER проверяет acceptance criteria, позитивные/негативные случаи,
границы и regression; использует fixtures/mocks и фиксирует
воспроизводимый FAIL.

Обычные тесты не зависят от внешней сети или реальной локальной LLM,
если TASK явно не определяет live test.

## 14. REVIEWER

REVIEWER проверяет requirements, diff, tests, regression, architecture,
security и DoD.

REVIEWER не исправляет код.

Каждый FAIL привязывается к конкретному критерию.

## 15. DEBUGGER

DEBUGGER исправляет только подтверждённую причину FAIL.

Не изменяет требования, не ослабляет tests, не расширяет scope.

Если причина требует архитектурного изменения или изменения TASK:

**STOP → REPORT → WAIT.**

## 16. Правило «не чинить по пути»

Обнаружение проблемы во время работы не означает разрешение на её
исправление.

Исключение: проблема непосредственно препятствует выполнению текущей
TASK и её исправление явно необходимо для acceptance criteria. Изменение
должно оставаться минимальным и быть отражено в отчёте.

## 17. Зависимости

Агент не создаёт новые зависимости самостоятельно.

Добавление библиотеки, внешнего сервиса или системного компонента
допускается только если разрешено TASK/EPIC/ТЗ.

## 18. Изменение схемы БД

Изменение таблиц, колонок, индексов, constraints, migrations или
persistence contracts не допускается без явного разрешения текущей TASK.

Необходимость изменения схемы:

**STOP → REPORT → WAIT.**

## 19. Архитектурные изменения

К ним относятся изменение dependency direction, Core authority, FSM, MCP
contracts, DB model, module boundaries, public API, persistence strategy
или security boundary.

Такие изменения выполняются только через соответствующий EPIC/TASK и,
если требуется, ADR.

## 20. Git / Diff discipline

Перед завершением агент обязан проверить:

``` text
changed files
diff
untracked files
tests
```

Все изменённые файлы перечисляются в итоговом отчёте.

## 21. Verification

``` text
Implementation
 ↓
Tests
 ↓
Relevant checks
 ↓
Diff inspection
 ↓
Acceptance verification
 ↓
Report
```

Фраза «должно работать» не является доказательством.

## 22. Definition of Done

TASK считается выполненной только если: 1. GOAL реализован; 2. scope
соблюдён; 3. запрещённые области не изменены; 4. tests
созданы/обновлены; 5. tests проходят; 6. acceptance criteria проверены;
7. diff проверен; 8. нет незаявленных изменений; 9. архитектурные
ограничения соблюдены; 10. результат передан в установленном формате.

## 23. STOP Conditions

Агент обязан остановиться при: - конфликте с ТЗ; - конфликте с State
Machine/MCP Contract; - неоднозначном обязательном требовании; -
необходимости архитектурного изменения; - необходимости изменения DB
schema вне TASK; - необходимости изменения public API вне TASK; -
отсутствии критического входа; - невозможности выполнить acceptance
criteria; - неизвестном критическом состоянии; - попытке TASK
расшириться за пределы scope.

``` text
STOP ≠ FAILURE
STOP = CONTROLLED ESCALATION
```

## 24. Repair Loop

``` text
CODE → TEST
          ↓
        FAIL?
       ↙     ↘
     NO       YES
     ↓         ↓
   REVIEW    DEBUG
               ↓
             TEST
```

Максимум **3 repair iterations**. После лимита:

**NEEDS_HUMAN.**

## 25. Evidence Bundle

Завершённая TASK возвращает: - TASK-ID; - status; - changed files; -
краткое описание; - выполненные tests/checks; - результаты tests; -
acceptance result; - known limitations; - проблемы вне scope; - blocking
issues.

Completion message агента не является самостоятельным доказательством;
результат подтверждается diff и tests.

## 26. Handoff Format

``` yaml
task_id: TASK-XXX
status: DONE|FAIL|BLOCKED|NEEDS_HUMAN

changed_files:
  - path/to/file.py

tests:
  passed: 0
  failed: 0
  skipped: 0

checks:
  - name: pytest
    status: PASS

acceptance:
  status: PASS|FAIL

scope_check:
  status: PASS|FAIL

architecture_check:
  status: PASS|FAIL|NOT_REQUIRED

out_of_scope_issues:
  - description: ...

blocking_issues:
  - description: ...

known_limitations:
  - description: ...

next_action: ...
```

## 27. TASK Statuses

``` text
READY → RUNNING → TESTING → REVIEW → DONE
```

Альтернативы:

``` text
RUNNING → BLOCKED
TESTING → FAIL
REVIEW → FAIL
FAIL → DEBUG
DEBUG → TESTING
BLOCKED → READY
```

`BLOCKED` = безопасное продолжение невозможно.

`FAIL` = результат не соответствует критерию.

`NEEDS_HUMAN` = решение требует человека/архитектора/вышестоящего
агента.

## 28. Role Boundaries

  ------------------------------------------------------------------------
  Role                     Делает                  Не делает
  ------------------------ ----------------------- -----------------------
  ORCHESTRATOR             state, dependencies,    production code
                           handoff, escalation     

  REQUIREMENTS_VALIDATOR   проверяет TASK          молча исправляет
                                                   требования

  CODER                    production              архитектура, scope
                           implementation +        expansion
                           требуемые tests         

  TESTER                   tests, fixtures,        production fixes
                           reports                 

  DEBUGGER                 минимальный fix причины изменение
                           FAIL                    требований/tests

  REVIEWER                 проверка результата     исправление кода

  ARCHITECTURE_GUARDIAN    архитектурная проверка  незапрошенный refactor
  ------------------------------------------------------------------------

## 29. Compact Agent Instruction

``` text
Ты CODE Agent проекта Research Prompt Suite.

Твоя единственная цель — выполнить текущую TASK.

1. Прочитай TASK, Context Header и применимые нормативные документы.
2. Не выдумывай требования.
3. Работай только внутри SCOPE и ALLOWED_FILES.
4. Делай минимальный diff.
5. Не рефактори соседний код без необходимости TASK.
6. Не меняй архитектуру, API, FSM, MCP contracts или DB schema без явного разрешения.
7. CODE не создаёт новые TASK.
8. Проблема вне TASK:
   STOP → REPORT → WAIT.
9. При неоднозначности:
   BLOCKED → запрос уточнения.
10. Напиши/обнови требуемые tests.
11. Не ослабляй tests для получения PASS.
12. Выполни проверки.
13. Проверь diff и список изменённых файлов.
14. Верни Evidence Bundle.
15. Не заявляй DONE без проверяемого результата.

Главное правило:

TASK scope > желание улучшить код.

Обнаруженная проблема не становится новой задачей автоматически.
```

## 30. Минимальный TASK Template

``` text
TASK-ID: TASK-XXX
TYPE: XS|S|M
ROLE: CODER|TESTER|DEBUGGER|...
EPIC: EPIC-XX

GOAL:
[один проверяемый результат]

SCOPE:
[что изменить]

ALLOWED_FILES:
[file list]

FORBIDDEN:
[что нельзя менять]

INPUTS:
[необходимые входы]

OUTPUTS:
[ожидаемый результат]

CONTRACT:
[входы / выходы / ошибки / инварианты]

DEPENDENCIES:
[разрешённые зависимости]

TESTS:
[конкретные проверки]

ACCEPTANCE:
[измеримые критерии]

STOP_CONDITIONS:
[когда остановиться]

DONE:
[что должно быть доказано]

ESCALATION:
[куда передать проблему]
```

## 31. Baseline Rule

Изменение этого документа требует новой версии:

``` text
TASK EXECUTION CONTRACT v1.1 — DRAFT
        ↓
review
        ↓
TASK EXECUTION CONTRACT v1.1 — BASELINE
```

Текущая версия:

**TASK EXECUTION CONTRACT v1.0 --- BASELINE**

------------------------------------------------------------------------

**Конец документа**
