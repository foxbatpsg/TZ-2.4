# EPIC-03 STATE MACHINES — TASK BATCH v1.2
------------------------------
## TASK: E03-T01-FSM-ERRORS

* GOAL: Создать базовые ошибки FSM.
* CONTEXT: Исключает разрозненность исключений. Нужен единый контролируемый набор ошибок для всех автоматов.
* ALLOWED_FILES:
* src/core/fsm/__init__.py
   * src/core/fsm/errors.py
   * tests/fsm/__init__.py
   * tests/fsm/test_errors.py
* FORBIDDEN: Создание бизнес-логики, состояний, переходов или прямая работа с соединениями SQLite.
* IMPLEMENTATION DETAILS:
* Создай пустые __init__.py.
   * В errors.py создай иерархию классов исключений: FSMError(Exception), InvalidTransitionError(FSMError), UnknownTriggerError(FSMError), GuardFailedError(FSMError), InvalidCommandError(FSMError), EntityNotFoundError(FSMError), ConcurrencyConflictError(FSMError).
* TESTS: Написать тесты, проверяющие, что все созданные классы являются строгими наследниками FSMError.
* ACCEPTANCE: Пакет ошибок создан, иерархия наследования корректна.
* STOP_CONDITIONS: Попытка внедрить сюда сетевые или HTTP-коды ошибок.

------------------------------
## TASK: E03-T02-FSM-MODEL

* GOAL: Создать декларативную модель состояний и переходов.
* CONTEXT: Автомат должен быть строго описываемым, исключая хаотичную ручную логику if/else.
* ALLOWED_FILES:
* src/core/fsm/model.py
   * tests/fsm/test_fsm_model.py
* FORBIDDEN: Импорт конкретных сущностей Study или SearchTask, логирование, запись в БД.
* IMPLEMENTATION DETAILS:
* Создай dataclass Transition с полями: from_state: str, to_state: str, trigger: str, guard: Optional[Callable] = None.
   * Создай dataclass StateMachineSpec с полями: name: str, initial_state: str, states: set[str], transitions: list[Transition].
   * Реализуй функцию validate_spec(spec: StateMachineSpec) -> None. Она обязана вызывать ValueError, если initial_state вне states, если переходы ведут в неизвестные состояния или если обнаружен дубликат пары (from_state, trigger).
* TESTS: Проверить прохождение валидации для корректной спецификации. Проверить падение валидатора при дублировании триггеров из одного состояния или при указании фейкового начального состояния.
* ACCEPTANCE: Декларативная модель готова и жестко валидирует структуру автоматов.
* STOP_CONDITIONS: Попытка добавить веса или приоритеты переходов.

------------------------------
## TASK: E03-T03-TRANSITION-LOOKUP

* GOAL: Реализовать детерминированный поиск целевого перехода.
* CONTEXT: Поиск обязан строго разграничивать ситуацию, когда триггер вообще не известен системе, от ситуации, когда переход недопустим из текущей фазы.
* ALLOWED_FILES:
* src/core/fsm/lookup.py
   * tests/fsm/test_lookup.py
* FORBIDDEN: Прямое выполнение переходов, логирование, импорт конкретных спецификаций.
* IMPLEMENTATION DETAILS:
* Реализуй функции внутри lookup.py: known_triggers(spec: StateMachineSpec) -> set[str] и find_transition(spec: StateMachineSpec, current_state: str, trigger: str) -> Transition.
   * Если current_state не входит в spec.states — бросать InvalidTransitionError. Если trigger отсутствует в known_triggers — бросать UnknownTriggerError. Если триггер известен, но перехода из current_state нет — бросать InvalidTransitionError.
* TESTS: Покрыть тестами все три ветки логики: успешный поиск, неизвестный триггер, недопустимый шаг.
* ACCEPTANCE: Движок поиска переходов работает детерминированно и возвращает правильные типы ошибок.
* STOP_CONDITIONS: Попытка внедрить wildcard-переходы (типа from_state="*").

------------------------------
## TASK: E03-T04-GUARD-MECHANISM

* GOAL: Реализовать механизм проверки динамических guard-условий.
* ALLOWED_FILES:
* src/core/fsm/guards.py
   * tests/fsm/test_guards.py
* FORBIDDEN: Прямая работа с SQLite, внедрение хардкод-логики конкретных проверок (бизнес-правил).
* IMPLEMENTATION DETAILS:
* Реализуй функцию evaluate_guard(transition: Transition, context: Optional[dict] = None) -> bool.
   * Если transition.guard равен None, функция обязана вернуть True. Если функция-guard передана — выполнить её, передав context (или пустой словарь), и вернуть строго приведенный bool результат.
* TESTS: Проверить успешный допуск без guard. Проверить успешный пропуск при lambda ctx: True и блокировку при lambda ctx: False.
* ACCEPTANCE: Механизм guards изолирован и корректно интерпретирует контекст вызова.
* STOP_CONDITIONS: Попытка реализовать асинхронные (async/await) guard-функции.

------------------------------
## TASK: E03-T05-COMMAND-MODEL

* GOAL: Создать строгое разделение между понятиями пользовательских команд и системных состояний.
* CONTEXT: Запрещено путать управляющие триггеры (SOFT_STOP, HARD_STOP) с фазами жизни сущностей.
* ALLOWED_FILES:
* src/core/fsm/commands.py
   * tests/fsm/test_commands.py
* FORBIDDEN: Код выполнения остановки процессов или транзакций.
* IMPLEMENTATION DETAILS:
* Создай dataclass Command с полями: name: str, payload: Optional[dict] = None.
   * Зафиксируй константное множество разрешенных команд COMMAND_NAMES = {"SOFT_STOP", "HARD_STOP", "PAUSE", "RESUME", "CANCEL", "ARCHIVE"}.
   * Реализуй функцию validate_command_name(name: str) -> None. Если имя неизвестно — бросать InvalidCommandError.
* TESTS: Убедиться, что все 6 команд проходят валидацию, а случайная строка вызывает ошибку. Подтвердить тестом, что команды не присутствуют в списках состояний.
* ACCEPTANCE: Модель команд изолирована от автоматов.
* STOP_CONDITIONS: Попытка расширить список команд без согласования.

------------------------------
## TASK: E03-T06-AUDIT-LOG-WRITER

* GOAL: Создать функцию записи FSM-переходов в реляционную таблицу LogRecord.
* CONTEXT: Каждый фактический шаг любого автомата обязан оставлять неизменяемый след в аудите.
* ALLOWED_FILES:
* src/core/fsm/audit.py
   * tests/fsm/conftest.py
   * tests/fsm/test_audit.py
* FORBIDDEN: Изменение SQL-схемы таблиц, прямые коммиты внутри функции.
* IMPLEMENTATION DETAILS:
* В файле tests/fsm/conftest.py создай базовую фикстуру conn, которая разворачивает временную БД в tmp_path, накатывает все 4 миграции из src/data/migrations через созданный в EPIC-02 мигратор и закрывает соединение после теста.
   * В audit.py реализуй функцию insert_transition_log(conn, entity_type: str, entity_id: str, from_state: str, to_state: str, trigger: str, component: str, message: Optional[str] = None) -> str.
   * Функция выполняет запись в таблицу LogRecord через низкоуровневый execute_write из EPIC-02. Идентификатор строки генерируется через src.core.identifiers.generate_uuid.
* TESTS: Вызвать функцию записи аудита внутри тестовой транзакции и проверить физическое наличие строки в таблице LogRecord с точным совпадением всех полей.
* ACCEPTANCE: Модуль записи аудита готов и протестирован на реальной схеме данных SQLite.
* STOP_CONDITIONS: Если таблица LogRecord отсутствует в накатываемых миграциях.

------------------------------
## TASK: E03-T07-PERSISTENT-TRANSITION-EXECUTOR

* GOAL: Создать универсальный транзакционный исполнитель переходов для persistent-сущностей БД.
* CONTEXT: Главный защитный контур системы. Гарантирует атомарность смены статуса, запись аудита и защиту от race conditions.
* ALLOWED_FILES:
* src/core/fsm/executor.py
   * tests/fsm/test_executor.py
* FORBIDDEN: Прямое присваивание полей статуса в обход транзакции. Импорт конкретных бизнес-репозиториев.
* IMPLEMENTATION DETAILS:
* Реализуй функцию transition_persistent(conn, spec: StateMachineSpec, entity_type: str, entity_id: str, load_status_fn: Callable, update_status_fn: Callable, trigger: str, context: Optional[dict] = None, component: str = "Core") -> str.
   * Вся логика выполняется строго внутри transaction(conn) (из EPIC-02):
   1. Загрузить текущий статус из базы через load_status_fn(conn, entity_id). Если сущность не найдена — EntityNotFoundError.
      2. Найти целевой переход через find_transition.
      3. Вычислить guard-условие через evaluate_guard. При провале — GuardFailedError.
      4. Вызвать функцию обновления update_status_fn(conn, entity_id, from_state, to_state).
      5. Защита от гонок: Функция update_status_fn обязана выполнять SQL-запрос UPDATE ... SET status = :to_state WHERE id = :entity_id AND status = :from_state и возвращать True только если cursor.rowcount == 1. Если вернулось False — бросать ConcurrencyConflictError (откат транзакции).
      6. Записать аудит через insert_transition_log.
      7. Вернуть строку нового состояния.
   * TESTS: Создать в тесте временную таблицу dummy_entity (id TEXT PRIMARY KEY, status TEXT). Написать для неё фейковые функции load и update. Проверить успешный переход. Проверить полный откат транзакции (отсутствие лога и старый статус) при симуляции race condition (когда update_status_fn возвращает False).
* ACCEPTANCE: Универсальный persistent-исполнитель гарантирует атомарность и безопасность параллельных переходов.
* STOP_CONDITIONS: Попытка вынести запись LogRecord в отдельный поток или отдельный коммит вне общей транзакции.

------------------------------
## TASK: E03-T08-RUNTIME-FSM

* GOAL: Создать базовый класс рантайм-автомата для объектов в памяти.
* CONTEXT: Применяется для сущностей, не требующих реляционной фиксации каждого шага (операции MCP, бэкенд ЛЛМ).
* ALLOWED_FILES:
* src/core/fsm/runtime.py
   * tests/fsm/test_runtime_fsm.py
* FORBIDDEN: Прямая запись в БД или вызовы логгеров внутри базового runtime-класса.
* IMPLEMENTATION DETAILS:
* Реализуй класс RuntimeFSM. Конструктор принимает spec: StateMachineSpec и опциональный entity_id: Optional[str] = None.
   * Конструктор инициализирует внутреннее поле _current_state = spec.initial_state.
   * Реализуй метод trigger(trigger_name: str, context: Optional[dict] = None) -> str. Метод ищет переход, проверяет guard и мутирует приватное поле _current_state, возвращая новое значение. При провале guard бросает GuardFailedError.
* TESTS: Убедиться в корректности смены состояний в памяти и вызове исключений при запрещенных шагах.
* ACCEPTANCE: Базовый рантайм-автомат готов к спецификации доменных объектов.
* STOP_CONDITIONS: Попытка тайно прикрутить сюда автоматическую запись в SQLite.

------------------------------
## TASK: E03-T09-STUDY-SPEC

* GOAL: Создать полную декларативную спецификацию жизненного цикла исследования (Study).
* CONTEXT: Это только декларативная карта переходов согласно Спецификации FSM v1.1. Без логики апдейтов.
* ALLOWED_FILES:
* src/core/fsm/specs/__init__.py
   * src/core/fsm/specs/study.py
   * tests/fsm/test_study_spec.py
* FORBIDDEN: Код модификации таблиц, внедрение запрещенных ТЗ состояний (типа SOFT_STOP или PARTIAL_REPORT в качестве статусов).
* IMPLEMENTATION DETAILS:
* Создай src/core/fsm/specs/__init__.py.
   * В study.py объяви объект STUDY_SPEC: StateMachineSpec.
   * Начальное состояние: DRAFT.
   * Множество состояний: DRAFT, PLANNING, READY, RUNNING, PAUSED, BUDGET_EXHAUSTED, FREEZE_BUDGET_EXHAUSTED, FINALIZING, COMPLETED, FAILED, USER_STOPPED, ARCHIVED.
   * Запиши полный перечень из 23 разрешенных переходов согласно разделу 1 Спецификации FSM (включая все бюджетные стоп-триггеры BUDGET_ZERO, BUDGET_FREEZE и финализацию).
* TESTS: Запустить validate_spec(STUDY_SPEC). Явно проверить тестом, что строки SOFT_STOP, HARD_STOP, PARTIAL_REPORT, REPORT_TRUNCATED_PARTIAL отсутствуют в списке разрешенных состояний (spec.states).
* ACCEPTANCE: Декларативный контракт Study State Machine полностью валиден и соответствует ТЗ.
* STOP_CONDITIONS: Обнаружение любого кастомного или промежуточного состояния, запрещенного ТЗ.

------------------------------
## TASK: E03-T10-STUDY-FSM

* GOAL: Реализовать Study State Machine поверх реляционной таблицы Study.
* ALLOWED_FILES:
* src/core/fsm/machines/__init__.py
   * src/core/fsm/machines/study.py
   * tests/fsm/test_study_fsm.py
* FORBIDDEN: Публичные методы прямого переключения статусов. Изменение колонок вне транзакции.
* IMPLEMENTATION DETAILS:
* Создай src/core/fsm/machines/__init__.py.
   * В study.py реализуй локальную функцию чтения _load_study_status(conn, study_id) -> str (делает точечный SELECT status FROM Study WHERE study_id = ?).
   * Реализуй локальную функцию записи _update_study_status(conn, study_id, from_state, to_state) -> bool. Она обязана выполнять: UPDATE Study SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE study_id = ? AND status = ? и проверять cursor.rowcount == 1.
   * Реализуй класс StudyStateMachine, имеющий единственный публичный метод выполнения перехода: execute_transition(conn, study_id: str, trigger: str, context: Optional[dict] = None, component: str = "Core") -> str. Метод перенаправляет вызов в универсальный transition_persistent.
* TESTS: На реальной временной базе данных создать проект и исследование. Прогнать цепочку: START_PLANNING -> PLAN_APPROVED -> START_RESEARCH. Убедиться, что статус стал RUNNING, а в таблице LogRecord появились три соответствующие записи аудита. Проверить вызов InvalidTransitionError при попытке сделать некорректный шаг.
* ACCEPTANCE: Автомат Study интегрирован со схемой данных и защищен от несанкционированных мутаций.
* STOP_CONDITIONS: Наличие методов вида set_status или прямых SQL-апдейтов статуса в коде машины.

------------------------------
## TASK: E03-T11-RESEARCH-SESSION-SPEC

* GOAL: Создать спецификацию автомата сессии взаимодействия (ResearchSession).
* ALLOWED_FILES:
* src/core/fsm/specs/research_session.py
   * tests/fsm/test_research_session_spec.py
* FORBIDDEN: Смешивание рантайм-состояния ЛЛМ со статусом сессии в базе.
* IMPLEMENTATION DETAILS:
* Объяви RESEARCH_SESSION_SPEC. Начальное состояние: INITIALIZING.
   * Состояния: INITIALIZING, ACTIVE, LLM_UNAVAILABLE, SESSION_RESUMING, SUSPENDED, CLOSING, CLOSED.
   * Настрой 12 разрешенных переходов согласно разделу 2 Спецификации FSM (включая сценарии аварийного падения нейросети LLM_BACKEND_UNAVAILABLE, реанимацию LLM_BACKEND_RECOVERED и выходы из инициализации).
* TESTS: Валидация спецификации проходит успешно. Команды управления не входят в состав фаз.
* ACCEPTANCE: Спецификация сессионного автомата готова к интеграции.
* STOP_CONDITIONS: Попытка добавить состояния RETRYING или STARTED.

------------------------------
## TASK: E03-T12-RESEARCH-SESSION-FSM

* GOAL: Реализовать ResearchSession State Machine с фиксацией времени окончания.
* ALLOWED_FILES:
* src/core/fsm/machines/research_session.py
   * tests/fsm/test_research_session_fsm.py
* FORBIDDEN: Модификация полей таблицы Study из кода данного автомата.
* IMPLEMENTATION DETAILS:
* Реализуй класс ResearchSessionStateMachine по аналогии со Study-машиной.
   * Локальная функция _update_session_status имеет критическое отличие: при переходе в финальное состояние CLOSED SQL-оператор обязан атомарно зафиксировать системное время окончания сессии: UPDATE ResearchSession SET status = ?, ended_at = CURRENT_TIMESTAMP WHERE session_id = ? AND status = ?.
* TESTS: Создать сессию со статусом INITIALIZING. Провести по маршруту INIT_COMPLETE -> STUDY_FINISHING -> SESSION_CLOSED. Проверить, что итоговый статус равен CLOSED, а поле ended_at заполнено таймстампом. Проверить также ветку аварийного восстановления RECOVERY_REQUIRED -> RECOVERY_COMPLETE.
* ACCEPTANCE: Сессионный автомат корректно управляет периодом активности сессий в БД.
* STOP_CONDITIONS: Автоматическая простановка ended_at на промежуточных фазах (допускается строго при переходе в CLOSED).

------------------------------
## TASK: E03-T13-SEARCH-TASK-SPEC

* GOAL: Создать спецификацию автомата поисковых подзадач (SearchTask).
* ALLOWED_FILES:
* src/core/fsm/specs/search_task.py
   * tests/fsm/test_search_task_spec.py
* FORBIDDEN: Интеграция логики расчета цифровых отпечатков или списания лимитов сети в спецификацию.
* IMPLEMENTATION DETAILS:
* Объяви SEARCH_TASK_SPEC. Начальное состояние: CREATED.
   * Состояния: CREATED, VALIDATING, QUEUED, RUNNING, COMPLETED, FAILED, REJECTED_DUPLICATE, REJECTED_SIMILAR, REJECTED_COVERAGE, REJECTED_BUDGET, CANCELLED.
   * Опиши 11 переходов согласно разделу 3 Спецификации FSM, включая жесткую отбраковку Core-валидатором на фазе VALIDATING по причинам совпадения хэшей, перегрузки бюджета или закрытия потребности (BUDGET_REJECT, EXACT_MATCH и т.д.).
* TESTS: Спецификация успешно проходит проверку validate_spec.
* ACCEPTANCE: Контракт жизненного цикла поисковых задач зафиксирован.
* STOP_CONDITIONS: Попытка добавить состояние RETRYING (подзадача либо выполняется, либо падает/отменяется, логика ретраев лежит выше).

------------------------------
## TASK: E03-T14-SEARCH-TASK-FSM

* GOAL: Реализовать SearchTask State Machine с фиксацией времени завершения.
* ALLOWED_FILES:
* src/core/fsm/machines/search_task.py
   * tests/fsm/test_search_task_fsm.py
* FORBIDDEN: Изменение таблиц результатов поиска (SearchResult) или запуск сетевой активности.
* IMPLEMENTATION DETAILS:
* Реализуй класс SearchTaskStateMachine.
   * Множество терминальных состояний, при переходе в которые СУБД обязана зафиксировать completed_at: COMPLETED, FAILED, CANCELLED, REJECTED_DUPLICATE, REJECTED_SIMILAR, REJECTED_COVERAGE, REJECTED_BUDGET.
   * SQL-оператор обновления: UPDATE SearchTask SET status = ?, completed_at = CASE WHEN ? IN ('COMPLETED', 'FAILED', 'CANCELLED', 'REJECTED_DUPLICATE', 'REJECTED_SIMILAR', 'REJECTED_COVERAGE', 'REJECTED_BUDGET') THEN CURRENT_TIMESTAMP ELSE completed_at END WHERE task_id = ? AND status = ?. Проверка cursor.rowcount == 1 обязательна.
* TESTS: Создать задачу, провести через VALIDATE_TASK -> VALIDATION_PASSED -> TASK_STARTED -> RESULTS_SAVED. Проверить статус COMPLETED и заполнение поля completed_at. Проверить также сценарий мгновенной отмены CANCEL со стадии ожидания в очереди.
* ACCEPTANCE: Автомат подзадач гарантирует фиксацию времени закрытия поисковых веток.
* STOP_CONDITIONS: Если простановка таймстампа completed_at не срабатывает для статусов категории REJECTED_*.

------------------------------
## TASK: E03-T15-JOB-SPEC

* GOAL: Создать спецификацию автомата фоновых задач (Job).
* ALLOWED_FILES:
* src/core/fsm/specs/job.py
   * tests/fsm/test_job_spec.py
* FORBIDDEN: Логика потоков воркеров, операции импорта или индексации внутри спецификации.
* IMPLEMENTATION DETAILS:
* Объяви JOB_SPEC. Начальное состояние: QUEUED.
   * Состояния: QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED.
   * Переходы: QUEUED -> RUNNING (по JOB_STARTED), RUNNING -> COMPLETED (JOB_COMPLETED), RUNNING -> FAILED (JOB_FAILED), а также кооперативная отмена по триггеру JOB_CANCEL_CONFIRMED со стадий очереди или выполнения.
* TESTS: Спецификация валидируется без ошибок. Лишние рантайм-статусы отсутствуют.
* ACCEPTANCE: Декларативный контракт фоновых Jobs зафиксирован.
* STOP_CONDITIONS: Попытка объединить команду cancel_job со статусом CANCELLED напрямую (отмена должна быть подтверждена воркером).

------------------------------
## TASK: E03-T16-JOB-FSM

* GOAL: Реализовать Job State Machine поверх реляционной таблицы Job.
* ALLOWED_FILES:
* src/core/fsm/machines/job.py
   * tests/fsm/test_job_fsm.py
* FORBIDDEN: Прямое управление флагами threading.Event или логика отмены CPU-потоков.
* IMPLEMENTATION DETAILS:
* Реализуй класс JobStateMachine.
   * При переходе в терминальные состояния (COMPLETED, FAILED, CANCELLED) SQL-оператор обязан зафиксировать время завершения задачи в колонке completed_at таблицы Job.
   * Безопасность параллельных изменений контролируется строгим условием WHERE job_id = ? AND status = ?.
* TESTS: Накатить миграцию, создать задачу в статусе QUEUED. Прогнать успешный цикл выполнения и сценарий подтвержденной отмены JOB_CANCEL_CONFIRMED. Проверить появление записей в аудите.
* ACCEPTANCE: Автомат Jobs надежно управляет состояниями долгих асинхронных операций в базе данных.
* STOP_CONDITIONS: Обновление статуса без жесткой проверки rowcount == 1.

------------------------------
## TASK: E03-T17-MCP-OPERATION-SPEC

* GOAL: Создать рантайм-спецификацию автомата вызова инструментов (MCP Operation) с защитой от бесконечных ретраев.
* CONTEXT: Это рантайм-автомат в памяти. Переход повтора (TIMED_OUT -> EXECUTING) блокируется при исчерпании лимита ретраев.
* ALLOWED_FILES:
* src/core/fsm/specs/mcp_operation.py
   * tests/fsm/test_mcp_operation_spec.py
* FORBIDDEN: Транспортный слой протокола MCP, JSON-RPC, запись переходов в таблицы БД.
* IMPLEMENTATION DETAILS:
* Объяви MCP_OPERATION_SPEC. Начальное состояние: REQUESTED.
   * Состояния: REQUESTED, VALIDATING, EXECUTING, COMPLETED, FAILED, TIMED_OUT, CANCELLED.
   * Переходы согласно разделу 4 Спецификации FSM.
   * Защита от бесконечных повторов: На переходе TIMED_OUT -> EXECUTING по триггеру RETRY_ALLOWED закрепи guard-функцию: lambda ctx: ctx.get("retry_count", 0) < ctx.get("max_retries", 3).
* TESTS: Проверить, что при retry_count = 1 при лимите 3 переход RETRY_ALLOWED разрешен, а при retry_count = 3 — блокируется (вызывает ошибку guard), вынуждая внешнюю логику вызвать триггер RETRY_EXHAUSTED для ухода в FAILED.
* ACCEPTANCE: Рантайм-контракт операций MCP защищен от зацикливания при таймаутах.
* STOP_CONDITIONS: Попытка убрать guard-проверку количества попыток с перехода.

------------------------------
## TASK: E03-T18-LLM-BACKEND-SPEC

* GOAL: Создать рантайм-спецификацию автомата состояний доступности ИИ-нейросети (LLM Backend).
* ALLOWED_FILES:
* src/core/fsm/specs/llm_backend.py
   * tests/fsm/test_llm_backend_spec.py
* FORBIDDEN: Вызовы реальных локальных серверов Ollama или LM Studio.
* IMPLEMENTATION DETAILS:
* Объяви LLM_BACKEND_SPEC. Начальное состояние: HEALTHY.
   * Состояния: HEALTHY, DEGRADED, UNREACHABLE, RESTARTING.
   * Опиши 8 разрешенных переходов согласно разделу 5 Спецификации FSM, фиксирующих деградацию отклика, полную недоступность и перезапуск бэкенда.
* TESTS: Убедиться, что спецификация успешно проходит внутреннюю валидацию validate_spec.
* ACCEPTANCE: Декларативная карта состояний ИИ-интерфейса зафиксирована в памяти.
* STOP_CONDITIONS: Попытка добавить состояние RETRYING.

------------------------------
## TASK: E03-T19-COMMAND-DISPATCHER

* GOAL: Создать диспетчер команд пользователя для безопасной трансляции управляющих воздействий в триггеры автоматов.
* CONTEXT: Внешний мир (GUI/MCP) общается с системой командами, диспетчер проверяет их применимость к конкретному классу автоматов.
* ALLOWED_FILES:
* src/data/repositories/__init__.py (если требуется экспортировать функции)
   * src/core/fsm/command_dispatcher.py
   * tests/fsm/test_command_dispatcher.py
* FORBIDDEN: Код реального прерывания асинхронных задач или CPU-потоков.
* IMPLEMENTATION DETAILS:
* Реализуй функцию command_to_trigger(machine_name: str, command_name: str) -> str.
   * Маппинг для Study: PAUSE -> PAUSE, RESUME -> RESUME, SOFT_STOP -> SOFT_STOP, HARD_STOP -> HARD_STOP, ARCHIVE -> ARCHIVE.
   * Маппинг для SearchTask: CANCEL -> CANCEL.
   * Маппинг для Job: CANCEL -> JOB_CANCEL_CONFIRMED.
   * Если комбинация machine_name и command_name не поддерживается — выбрасывать InvalidCommandError.
* TESTS: Проверить успешный маппинг SOFT_STOP для Study. Проверить, что отправка команды SOFT_STOP в автомат SearchTask падает с InvalidCommandError.
* ACCEPTANCE: Диспетчер команд изолирует логику внешних запросов интерфейса от системных триггеров.
* STOP_CONDITIONS: Попытка разрешить здесь фейковую команду PARTIAL_REPORT в качестве триггера.

------------------------------
## TASK: E03-T20-DIRECT-STATUS-UPDATE-PREVENTION

* GOAL: Создать автоматический тест архитектурного контроля, полностью запрещающий прямые обновления колонок status в обход пакета FSM.
* CONTEXT: Это критически важный тест-линтер для защиты целостности Gate G-01/G-02.
* ALLOWED_FILES:
* tests/fsm/test_direct_status_update_prevention.py
* FORBIDDEN: Изменение продуктового кода системы.
* IMPLEMENTATION DETAILS:
* Тест сканирует все .py файлы проекта (корень src/).
   * Исключения: Каталог src/core/fsm полностью исключается из проверки (там эти операции разрешены). Также исключается сам каталог tests.
   * Для всех остальных файлов тест проверяет текст на наличие подстрок вида UPDATE <сущность> SET status (без учета регистра и лишних пробелов). При обнаружении совпадений тест обязан упасть, указав имя файла.
* ACCEPTANCE: Архитектурная монополия пакета FSM на мутацию состояний защищена автоматическим AST/текстовым тестом.
* STOP_CONDITIONS: Если обнаружено несанкционированное исключение из правил, не подтвержденное Архитектором.

------------------------------
## TASK: E03-T21-RACE-CONDITION-TEST

* GOAL: Создать тест параллельного исполнения переходов для подтверждения защиты persistent-автоматов от гонок.
* CONTEXT: Это исключительно тестовая задача. Продуктовый код менять запрещено.
* ALLOWED_FILES:
* tests/fsm/test_race_condition.py
* FORBIDDEN: Модификация исполнителя переходов executor.py.
* IMPLEMENTATION DETAILS:
* Разверни изолированную БД, создай исследование в статусе READY.
   * Используя threading.Thread, запусти одновременно два параллельных потока, которые пытаются вызвать StudyStateMachine.execute_transition с триггером START_RESEARCH для одного и того же study_id.
* ACCEPTANCE: Тест успешно проходит, если: ровно один поток смог выполнить переход (вернул статус RUNNING), а второй поток упал с ошибкой гонки (ConcurrencyConflictError), при этом в таблице LogRecord создана ровно одна запись аудита.
* STOP_CONDITIONS: Если при тесте оба потока рапортуют об успехе или в базе двоится аудит.

------------------------------
## TASK: E03-T22-SOFT-STOP-SCENARIO-TEST

* GOAL: Создать сквозной интеграционный тест системного сценария контролируемой остановки (Soft Stop).
* ALLOWED_FILES:
* tests/fsm/test_soft_stop_scenario.py
* FORBIDDEN: Изменение файлов в пакете src/.
* IMPLEMENTATION DETAILS:
* На детерминированных фикстурах подготовь активный контур: Study в состоянии RUNNING, сессия в ACTIVE, поисковая задача в RUNNING.
   * Имитируй поступление сигнала Soft Stop через диспетчер команд и провери последовательное переключение состояний persistent-автоматов:
   1. Study переходит в FINALIZING (по триггеру SOFT_STOP). Active-задачи дорабатывают.
      2. Поисковая задача успешно сохраняет результаты и переходит в COMPLETED.
      3. Сессия переходит в CLOSING (STUDY_FINISHING).
      4. Итоговый отчет валидируется: Study уходит в COMPLETED (REPORT_VALID), сессия гаснет в CLOSED.
   * TESTS: Весь сценарий проверяется последовательными утверждениями assert на статусных полях таблиц БД.
* ACCEPTANCE: Сквозной маршрут Soft Stop подтверждает корректность каскадного затухания процессов в Core.
* STOP_CONDITIONS: Использование сетевых или ЛЛМ заглушек, сценарий работает CPU-only на уровне СУБД.

------------------------------
## TASK: E03-T23-HARD-STOP-SCENARIO-TEST

* GOAL: Создать сквозной интеграционный тест аварийной мгновенной остановки (Hard Stop).
* ALLOWED_FILES:
* tests/fsm/test_hard_stop_scenario.py
* FORBIDDEN: Изменение продуктового кода пакетов src/.
* IMPLEMENTATION DETAILS:
* Собери контур: Study в RUNNING, сессия в ACTIVE, подзадача поиска в RUNNING, фоновый Job в RUNNING, рантайм-операция MCP в EXECUTING.
   * Запусти команду Hard Stop и проверь мгновенную принудительную терминацию:
   1. Study переходит строго в USER_STOPPED (по триггеру HARD_STOP).
      2. Сессия гаснет в CLOSED.
      3. Поисковая задача принудительно обрывается в CANCELLED.
      4. Фоновый Job подтверждает отмену и уходит в CANCELLED.
      5. Рантайм-операция MCP сбрасывается в CANCELLED.
   * TESTS: Убедиться, что ни один автомат не завис на промежуточных фазах, а строка HARD_STOP нигде не записалась в поле статуса.
* ACCEPTANCE: Сценарий Hard Stop гарантирует мгновенную безопасную фиксацию контрольной точки системы при обрывах.
* STOP_CONDITIONS: Наличие незавершенных или подвисших в состоянии RUNNING подзадач в базе по окончании теста.

------------------------------
## TASK: E03-T24-BUDGET-EXHAUSTION-SCENARIO-TEST

* GOAL: Создать тест сценария принудительной заморозки при исчерпании многомерного бюджета.
* ALLOWED_FILES:
* tests/fsm/test_budget_exhaustion_scenario.py
* FORBIDDEN: Подключение реальных модулей калькуляции токенов или сетевых лимитов.
* IMPLEMENTATION DETAILS:
* Посади Study в состояние RUNNING.
   * Симулируй триггер исчерпания ресурсов от Core: Study переходит в BUDGET_EXHAUSTED (по триггеру BUDGET_ZERO), а затем автоматически замораживается в FREEZE_BUDGET_EXHAUSTED (BUDGET_FREEZE).
   * Создай новую подзадачу SearchTask в статусе CREATED. Попытайся отправить её на валидацию. Так как бюджет заморожен, Core-валидатор обязан отклонить задачу, переведя её по траектории CREATED -> VALIDATING -> REJECTED_BUDGET.
   * Запусти частичную финализацию: Study уходит в FINALIZING (по триггеру FINALIZE_PARTIAL) и успешно закрывается в COMPLETED.
* ACCEPTANCE: Бюджетные блокировки на уровне автоматов состояний работают корректно, защищая ресурсы системы.
* STOP_CONDITIONS: Если заблокированный автомат Study позволяет перевести SearchTask в состояние QUEUED.

------------------------------
## TASK: E03-T25-LLM-FAILURE-RECOVERY-SCENARIO-TEST

* GOAL: Создать тест сценария падения и восстановления рантайм-бэкенда ЛЛМ с процедурой реанимации сессии (Session Resume).
* ALLOWED_FILES:
* tests/fsm/test_llm_failure_recovery_scenario.py
* FORBIDDEN: Использование реальных HTTP-клиентов или живых серверов Ollama.
* IMPLEMENTATION DETAILS:
* Инициализируй рантайм-автомат ЛЛМ в HEALTHY, а сессию в базе переведи в ACTIVE.
   * Симулируй падение: бэкенд уходит в UNREACHABLE (HEALTH_FAILED), сессия в базе атомарно реагирует и переключается в LLM_UNAVAILABLE (LLM_BACKEND_UNAVAILABLE). Исследование Study при этом остается в RUNNING (оно не обязано падать из-за временных сетевых проблем сети).
   * Симулируй подъем нейросети: бэкенд проходит через RESTARTING -> HEALTHY, сессия переходит в SESSION_RESUMING (LLM_BACKEND_RECOVERED) и после проверок консистентности возвращается в ACTIVE (RECOVERY_COMPLETE).
* ACCEPTANCE: Сценарий восстановления подтверждает живучесть и непрерывность сессий рандайма ИИ.
* STOP_CONDITIONS: Изменение статуса Study на FAILED или USER_STOPPED во время падения ЛЛМ бэкенда.

------------------------------
## TASK: E03-T26-TIMEOUT-RETRY-CANCELLATION-TEST

* GOAL: Проверить изоляцию и лимиты сценариев таймаутов, повторных попыток инструментов и отмены Jobs.
* ALLOWED_FILES:
* tests/fsm/test_timeout_retry_cancellation.py
* FORBIDDEN: Использование живых асинхронных таймеров (тесты должны быть мгновенными и детерминированными).
* IMPLEMENTATION DETAILS:
* Разверни рантайм-автомат MCP Operation в EXECUTING.
   * Симулируй таймаут: OPERATION_TIMEOUT -> TIMED_OUT. Передай в контекст retry_count=0, max_retries=2. Вызови триггер RETRY_ALLOWED — автомат успешно возвращается в EXECUTING. Нарасти счетчик ретраев до 2. Симулируй повторный таймаут. Теперь вызов RETRY_ALLOWED обязан упасть с ошибкой GuardFailedError. Вызови триггер RETRY_EXHAUSTED — автомат уходит в FAILED.
   * Проверь отмену Job: перевод из RUNNING строго в CANCELLED по триггеру JOB_CANCEL_CONFIRMED.
* ACCEPTANCE: Ограничение циклов ретраев и логика отмены Jobs верифицированы.
* STOP_CONDITIONS: Появление бесконечного цикла переходов между состояниями таймаута и выполнения.

------------------------------
## TASK: E03-T27-ATOMICITY-AND-INVALID-TRANSITION-TEST

* GOAL: Создать жесткие негативные тесты для проверки неделимости (атомарности) транзакций и блокировки некорректных триггеров.
* ALLOWED_FILES:
* tests/fsm/test_atomicity_and_invalid_transitions.py
* FORBIDDEN: Изменение кода исполнителя переходов.
* IMPLEMENTATION DETAILS:
* Напиши две группы проверок:
   1. Недопустимый триггер: Посади Study в DRAFT. Отправь триггер RESUME. Убедись, что выбрасывается InvalidTransitionError, статус в базе железно остался DRAFT, а в таблице LogRecord не появилось ни одной новой строчки.
      2. Обрыв на середине: Используя monkeypatch, подмени функцию insert_transition_log внутри src.core.fsm.executor так, чтобы она безусловно бросала RuntimeError. Попытайся выполнить легитимный переход Study DRAFT -> PLANNING. Убедись, что наружу вылетает RuntimeError, но благодаря откату транзакции статус Study в базе остался DRAFT.
   * ACCEPTANCE: Атомарность контура гарантирует отсутствие "полураспада" данных при авариях.
* STOP_CONDITIONS: Если при падении записи лога статус в таблице Study успевает измениться.

------------------------------
## TASK: E03-T28-FSM-INTEGRATION-TEST

* GOAL: Финальный сквозной интеграционный тест слоя управления состояниями (Gate G-03).
* CONTEXT: Проверяет совместное функционирование автоматов, логгера аудита и диспетчера записи DbWriter из EPIC-02.
* ALLOWED_FILES:
* tests/fsm/test_fsm_integration.py
* FORBIDDEN: Внедрение реального контента документов или эвристик разбора текстов.
* IMPLEMENTATION DETAILS:
* Разверни временную БД, запусти DbWriter.
   * Через DbWriter.submit() отправь пачку последовательных доменных переходов для созданного исследования Study: от первичной инициализации до старта поискового цикла (RUNNING).
   * Проверь, что все статусы синхронно обновились в файле БД, а таблица LogRecord содержит непрерывную цепочку аудита. Убедись с помощью инспекции класса StudyStateMachine, что у него полностью отсутствуют публичные мутаторы вроде set_status.
* ACCEPTANCE: Слой автоматов состояний полностью готов и успешно прошел интеграционный Gate G-03.
* STOP_CONDITIONS: Если для работы теста требуется задействовать сетевые ресурсы или логику ЛЛМ.

------------------------------
## 3. Критерии готовности (Definition of Done) для EPIC-03

* Все 5 persistent-автоматов (Study, ResearchSession, SearchTask, Job) и 2 runtime-спецификации (MCP Operation, LLM Backend) полностью описаны и валидированы.
* Мутация состояний в БД происходит строго атомарно (смена статуса + инсерт LogRecord) внутри одной транзакции СУБД.
* Реализована надежная защита от race conditions за счет SQL-условия WHERE id = ? AND status = ? и обязательной проверки rowcount == 1.
* Публичный API пакета src/core/fsm полностью исключает методы прямого назначения статуса (типа set_status).
* Автоматический AST-тест гарантирует отсутствие сырых операторов UPDATE ... SET status за пределами пакета автоматов.
* Понятия управляющих команд (SOFT_STOP, HARD_STOP и т.д.) жестко отделены от фаз жизни объектов на уровне спецификаций.
* Рантайм-автомат MCP защищен от бесконечных циклов таймаута через guard-лимит ретраев.
* Все тесты изолированы, не используют сеть/Таймеры/ЛЛМ и проходят успешно.

Конец спецификации EPIC-03 STATE MACHINES — TASK BATCH v1.2 FINAL
------------------------------



