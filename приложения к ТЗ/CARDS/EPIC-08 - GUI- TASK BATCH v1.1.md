# EPIC-08 — GUI. TASK BATCH v1.1

Статус: Готов к передаче CODE-агентам.
Зависимости: формально по Dependency Matrix — EPIC-02, EPIC-03, EPIC-04, EPIC-05, EPIC-07. Транзитивно — через EPIC-01 и EPIC-06.
Цель EPIC: Реализовать Windows GUI как тонкий клиент над Core/Application API. Стек: Python + CustomTkinter + SQLite. Браузер не требуется.
Правило: Main Thread не выполняет тяжёлый retrieval, parsing, indexing или orchestration.
Gate G-08: GUI не содержит бизнес-правил; worker независим; UI остаётся отзывчивым; мягкая/жёсткая остановка, оффлайн, снапшот и трассируемость доказательств работают.

---

## Общие инварианты и запреты для всех задач EPIC-08

ALLOWED_FILES (глобально для EPIC):

- `src/gui/` (корневая директория для всех модулей GUI)
- `src/gui/tk/` (ленивый адаптер `customtkinter`)
- `src/gui/toolkit.py`, `src/gui/theme.py`, `src/gui/shell.py`
- `src/gui/navigation.py`, `src/gui/state_snapshot.py`, `src/gui/intents.py`
- `src/gui/control_rules.py`, `src/gui/dashboard.py`, `src/gui/research_form.py`
- `src/gui/source_selector.py`, `src/gui/run_controls.py`, `src/gui/progress.py`
- `src/gui/log_view.py`, `src/gui/log_filter.py`, `src/gui/artifact_table.py`
- `src/gui/artifact_export.py`, `src/gui/mcp_settings.py`, `src/gui/llm_settings.py`
- `src/gui/settings_repo.py`, `src/gui/status_center.py`
- `src/gui/composition.py`, `src/gui/app.py`
- `src/gui/intent_blueprint.py` (Intent Blueprint Editor)
- `src/gui/evidence_explorer.py`, `src/gui/evidence_tree.py`
- `src/gui/report_viewer.py`
- `src/gui/abort_controller.py` (Graceful Abort)
- `src/gui/health_monitor.py`
- `src/gui/prompt_sandbox.py`
- `src/gui/snapshot_view.py` (Research Snapshots)
- `src/gui/projects_view.py`
- `src/gui/offline_mode.py`
- `src/gui/aggregation_dashboard.py`
- `src/gui/query_preview.py`
- `src/gui/study_wizard.py` (Study Creation Wizard)
- `src/gui/thread_coordinator.py` (Main Thread / Worker)
- `src/gui/xray_stream.py` (X-Ray Activity Stream)
- `tests/gui/` (все тесты)
- `tests/fixtures/` (заглушки портов, фейковые данные)

FORBIDDEN (глобально для EPIC):

- Прямое изменение `status` у `Study`, `ResearchSession`, `SearchTask` в обход FSM.
- Выполнение тяжёлого retrieval, parsing, indexing или orchestration в Main Thread.
- Прямые вызовы к БД из GUI (только через порты/адаптеры).
- Хранение бизнес-логики в GUI-компонентах.
- Использование реальных сетевых вызовов в тестах.
- Использование реальной LLM в тестах.
- Создание реального окна в тестах (headless-проверки).
- Импорт `customtkinter` или `tkinter` на уровне модуля (только лениво).

Глобальное правило взаимодействия потоков (ТЗ Раздел 6, Секция 2):

    Main Thread:
    - GUI rendering
    - Events
    - User interaction

    Worker Thread:
    - Постоянный asyncio loop
    - Network operations
    - Orchestration
    - MCP-related operations

    Взаимодействие:
    - `asyncio.run_coroutine_threadsafe()` — отправка задач в worker
    - thread-safe `queue.Queue` — передача событий из worker в GUI
    - `root.after()` — обновление виджетов из worker-потока

Правило: ни один компонент не обходит этот механизм.

---

## G1 — Фундамент GUI и headless-контракт

### TASK-08-01: Контракты GUI и базовый `ViewModel`

GOAL: Создать минимальные контракты GUI без оконного тулкита: `GuiCommand`, `GuiEvent`, `RenderSpec`, `ViewModelBase`.

CONTEXT: GUI обязан быть изолирован от `customtkinter`, FSM и ядра; задача готовит только типы и наблюдаемость.

ALLOWED_FILES: `src/gui/__init__.py`, `src/gui/contracts.py`, `src/gui/view_model.py`, `tests/gui/test_gui_contracts.py`.

FORBIDDEN: Импортировать `customtkinter` или `tkinter`. Изменять `src/state/`. Реализовывать виджеты, окна или рендеринг. Добавлять внешние зависимости.

IMPLEMENTATION DETAILS:

- `GuiCommand` и `GuiEvent` — frozen dataclass с полями `name`, `payload`, `occurred_at`.
- `RenderSpec` — frozen dataclass с полями `screen_id`, `title`, `widgets`, `status_hints`.
- `ViewModelBase` содержит подписчиков, методы `subscribe()`, `invalidate()`, `render()`.
- Все операции только в памяти, без файлового ввода-вывода.

TESTS:

- `test_render_spec_is_immutable`
- `test_view_model_notifies_once_per_invalidate`
- `test_gui_context_uses_tmp_path_workspace`
- Проверить отсутствие `tkinter` и `customtkinter` в `sys.modules` после импорта.

ACCEPTANCE: Контракты не содержат бизнес-логику. Импорт модулей не имеет побочных эффектов.

STOP_CONDITIONS: Если появляются поля сверх минимального контракта — остановить задачу и зафиксировать вопрос.

---

### TASK-08-02: Headless-тулкит и ленивый адаптер `customtkinter`

GOAL: Определить протокол `WidgetToolkit`, headless-реализацию и ленивый production-адаптер для `customtkinter`.

CONTEXT: Последующие экраны описываются через `RenderSpec`, реальный GUI подключается только лениво.

ALLOWED_FILES: `src/gui/toolkit.py`, `src/gui/tk/__init__.py`, `src/gui/tk/customtkinter_toolkit.py`, `tests/gui/test_gui_toolkit.py`.

FORBIDDEN: Создавать реальное окно в тестах. Импортировать `customtkinter` на уровне модуля. Выполнять сетевые вызовы. Менять состояния FSM напрямую.

IMPLEMENTATION DETAILS:

- `WidgetToolkit` описывает `create_frame()`, `create_label()`, `create_button()`, `set_enabled()`, `set_text()`.
- `HeadlessToolkit` записывает операции в память и опционально в JSONL-файл внутри `tmp_path`.
- `CustomTkinterToolkit.is_available()` использует только `importlib.util.find_spec`.
- Реальный импорт `customtkinter` разрешён только внутри ленивой функции.

TESTS:

- `test_headless_records_widget_operations`
- `test_headless_trace_written_to_tmp_path`
- `test_is_available_does_not_import_customtkinter`
- `test_render_spec_applies_without_display`

ACCEPTANCE: Headless-тулкит полностью заменяет GUI в тестах. Production-адаптер не ломает импорт при отсутствии `customtkinter`.

STOP_CONDITIONS: Если API `customtkinter` неоднозначен — реализовать только протокол и headless.

---

### TASK-08-03: Тема GUI и детерминированный стиль

GOAL: Реализовать тему, токены стиля и resolver состояний без привязки к конкретным виджетам.

CONTEXT: GUI должен иметь единый визуальный контракт для статусов, ошибок и активных процессов.

ALLOWED_FILES: `src/gui/theme.py`, `tests/gui/test_gui_theme.py`.

FORBIDDEN: Хранить цвета в виджетах напрямую. Использовать сетевые шрифты или ресурсы. Анимации. Изменять состояние приложения.

IMPLEMENTATION DETAILS:

- `ThemeTokens` с цветами, отступами, типографикой и статусными токенами.
- `resolve_style()` принимает `state`, `enabled`, `severity` и возвращает имя токена.
- Поддерживать состояния `IDLE`, `READY`, `RUNNING`, `ERROR`, `DONE`.
- Сохранить и загрузить тему из JSON в `tmp_path`.

TESTS:

- `test_theme_tokens_are_complete`
- `test_style_resolver_for_running_error_disabled`
- `test_theme_json_roundtrip_in_tmp_path`

ACCEPTANCE: Тема детерминирована и не зависит от ОС. Все статусы имеют различимые токены.

STOP_CONDITIONS: Если дизайн-токены не утверждены — использовать нейтральный grayscale.

---

### TASK-08-04: Модель каркаса приложения и статус-бара

GOAL: Реализовать модель каркаса приложения с навигационными вкладками, областью контента и статус-баром.

CONTEXT: Каркас строится из `RenderSpec`, без прямой вёрстки в этой задаче.

ALLOWED_FILES: `src/gui/shell.py`, `tests/gui/test_gui_shell.py`.

FORBIDDEN: Создавать реальное окно. Менять активную вкладку в обход навигационных интентов. Подмешивать бизнес-команды в состояние представления. Обращаться к сети или реальной LLM.

IMPLEMENTATION DETAILS:

- `ShellViewModel` формирует вкладки `dashboard`, `research`, `logs`, `settings`, `diagnostics`.
- Статус-бар отображает `state`, `active_task`, `warning`, `last_error`.
- Активная вкладка задаётся через `NavigationIntent`, а не прямой мутацией.
- Модель принимает `workspace=tmp_path`, но не обязана писать файлы.

TESTS:

- `test_shell_tabs_are_fixed`
- `test_shell_status_shows_snapshot_state`
- `test_shell_active_tab_changes_only_via_intent`

ACCEPTANCE: Каркас стабилен и детерминирован. Статус-бар читает только проекцию состояния.

STOP_CONDITIONS: Если требуются дополнительные вкладки — остановить задачу.

---

## G2 — FSM-проекция, навигация и команды

### TASK-08-05: Навигационная модель и охранные правила вкладок

GOAL: Реализовать навигацию между экранами с ограничениями по состоянию FSM.

CONTEXT: Навигация презентационная, без изменения реального состояния процесса.

ALLOWED_FILES: `src/gui/navigation.py`, `tests/gui/test_gui_navigation.py`.

FORBIDDEN: Изменять FSM. Открывать недоступные экраны в обход правил. Смешивать команды и состояния. Выполнять долгие операции в навигации.

IMPLEMENTATION DETAILS:

- `NavigationModel` хранит текущий маршрут, историю и список разрешённых маршрутов.
- `request_route()` возвращает `NavigationResult` с признаками `allowed`, `reason`.
- Для `RESEARCH_RUNNING` разрешить `logs`, `dashboard`, запретить редактирование настроек.
- История ограничена фиксированным буфером.

TESTS:

- `test_default_route_is_dashboard`
- `test_settings_blocked_during_running`
- `test_denied_route_does_not_change_current`
- `test_history_is_bounded`

ACCEPTANCE: Навигация детерминирована. Отказ не меняет текущий экран.

STOP_CONDITIONS: Если матрица переходов неоднозначна — реализовать минимальный набор.

---

### TASK-08-06: Проекция состояния FSM в read-only snapshot

GOAL: Реализовать отображение внешнего состояния FSM в `GuiStateSnapshot` без возможности мутации.

CONTEXT: GUI может только читать состояние и отображать его, не вмешиваясь в конечный автомат.

ALLOWED_FILES: `src/gui/state_snapshot.py`, `tests/gui/test_gui_state_snapshot.py`.

FORBIDDEN: Изменять состояние FSM. Отправлять команды из проекции. Смешивать `state` и `command` в одном объекте. Использовать сетевые источники.

IMPLEMENTATION DETAILS:

- `GuiStateSnapshot` содержит `state`, `progress`, `error_code`, `can_start`, `can_stop`, `updated_at`.
- Маппер принимает внешний `StateSnapshotInput` и возвращает frozen dataclass.
- Неизвестное состояние отображать как `UNKNOWN`, без исключения.
- Прогресс ограничивать диапазоном 0–100.

TESTS:

- `test_snapshot_maps_idle_running_error_done`
- `test_unknown_state_maps_to_unknown`
- `test_progress_is_clamped`
- `test_snapshot_is_read_only`

ACCEPTANCE: GUI получает только неизменяемую проекцию. Нет зависимости от конкретного класса FSM.

STOP_CONDITIONS: Если имена состояний отсутствуют в спецификации — использовать адаптер-заглушку.

---

### TASK-08-07: Диспетчер пользовательских интентов

GOAL: Реализовать единый диспетчер, который превращает действия GUI в команды верхнего уровня.

CONTEXT: Кнопки и формы не должны менять статус; они обязаны отправлять интенты в ядро.

ALLOWED_FILES: `src/gui/intents.py`, `tests/gui/test_gui_intents.py`.

FORBIDDEN: Напрямую вызывать сеттеры состояния. Запускать LLM или MCP. Выполнять сетевые запросы. Дублировать бизнес-логику FSM.

IMPLEMENTATION DETAILS:

- Разрешённые команды: `START_RESEARCH`, `STOP_RESEARCH`, `SOFT_STOP`, `HARD_STOP`, `RETRY`, `RESET`, `SAVE_SETTINGS`, `EXPORT_ARTIFACTS`.
- Каждый интент имеет `idempotency_key` и валидируемую полезную нагрузку.
- Диспетчер пишет журнал интентов в файл внутри `tmp_path`.
- Неизвестные команды отклоняются с `IntentError`.
- `SOFT_STOP` и `HARD_STOP` являются командами, а не состояниями (согласно State Machine Spec v1.1).

TESTS:

- `test_valid_start_intent_is_dispatched`
- `test_duplicate_idempotency_key_is_ignored`
- `test_unknown_command_is_rejected`
- `test_soft_stop_and_hard_stop_are_commands_not_states`
- `test_intent_audit_written_to_tmp_path`

ACCEPTANCE: Все действия GUI проходят через интенты. Журнал интентов детерминирован.

STOP_CONDITIONS: Если контракт команд не согласован — ограничиться заглушкой.

---

### TASK-08-08: Матрица доступности контролов

GOAL: Реализовать чистые правила включения/отключения контролов на основе снапшота состояния.

CONTEXT: Кнопки старта, остановки, повтора и экспорта зависят только от состояния и валидности.

ALLOWED_FILES: `src/gui/control_rules.py`, `tests/gui/test_gui_control_rules.py`.

FORBIDDEN: Мутировать состояние. Скрывать фатальные ошибки. Подмешивать сетевые проверки. Хранить бизнес-процесс в UI.

IMPLEMENTATION DETAILS:

- `control_states()` возвращает словарь контролов с `enabled` и `reason`.
- Поддерживать контролы `start`, `stop`, `soft_stop`, `hard_stop`, `retry`, `reset`, `export`, `settings_edit`.
- При фатальной ошибке конфигурации блокировать `start`.
- Правила — чистая функция без побочных эффектов.

TESTS:

- `test_idle_allows_start_if_valid`
- `test_running_enables_stop_disables_start`
- `test_error_enables_retry_or_reset`
- `test_disabled_reason_is_present`

ACCEPTANCE: Матрица покрывает основные состояния. Каждый запрет имеет причину.

STOP_CONDITIONS: Если появляются новые контролы — остановить задачу.

---

## G3 — Рабочая область исследования

### TASK-08-09: Модель дашборда и сводки проекта

GOAL: Реализовать дашборд с текущим состоянием, сводкой проекта и быстрыми действиями.

CONTEXT: Дашборд — информационная витрина без прямых запросов к LLM.

ALLOWED_FILES: `src/gui/dashboard.py`, `tests/gui/test_gui_dashboard.py`.

FORBIDDEN: Выполнять исследование. Обращаться к сети. Писать артефакты. Менять статусы напрямую.

IMPLEMENTATION DETAILS:

- `DashboardViewModel` принимает `GuiStateSnapshot` и `ProjectSummaryPort`.
- Карточки: текущий проект, состояние, последний запуск, последняя ошибка.
- Быстрые действия используют `IntentDispatcher`.
- Сводка проекта читается из JSON-файла в `tmp_path`.

TESTS:

- `test_dashboard_shows_empty_project_placeholder`
- `test_dashboard_shows_active_run`
- `test_dashboard_quick_actions_respect_control_rules`
- `test_dashboard_loads_summary_from_tmp_path`

ACCEPTANCE: Дашборд стабилен и читает только проекции. Действия не минуют интенты.

STOP_CONDITIONS: Если схема проектной сводки не определена — использовать placeholder.

---

### TASK-08-10: Модель формы конфигурации исследования

GOAL: Реализовать форму параметров исследования с валидацией и признаками `dirty`/`valid`.

CONTEXT: Форма готовит данные для запуска, но не запускает исследование. Полный процесс создания Study реализован в TASK-08-36 (Study Creation Wizard).

ALLOWED_FILES: `src/gui/research_form.py`, `tests/gui/test_gui_research_form.py`.

FORBIDDEN: Запускать LLM или MCP. Сохранять настройки в обход задачи персистентности. Выполнять сетевые запросы. Менять состояние FSM.

IMPLEMENTATION DETAILS:

- Поля: `title`, `question`, `goal`, `research_mode`, `source_scope`, `filters`, `exclusions`, `max_iterations`, `budget_limits`.
- `research_mode` — Enum: `EVIDENCE`, `AGGREGATION`, `COMPARISON`, `EXPAND`, `MATERIALS_ONLY`.
- `source_scope` — Enum: `WEB`, `LOCAL`, `ALL`.
- Валидация диапазонов и обязательных полей.
- Ошибки формы возвращаются структурой `FormErrors`.

TESTS:

- `test_valid_form_marks_ready`
- `test_invalid_ranges_block_validation`
- `test_dirty_flag_tracks_changes`
- `test_research_mode_enum_validated`

ACCEPTANCE: Некорректная форма блокирует старт через правила контролов. Форма не выполняет побочных действий.

STOP_CONDITIONS: Если появляются дополнительные поля — остановить задачу.

---

### TASK-08-11: Модель выбора локальных источников

GOAL: Реализовать выбор локальных файлов-источников и построение детерминированного манифеста.

CONTEXT: GUI работает только с локальными каталогами, без сетевых ресурсов.

ALLOWED_FILES: `src/gui/source_selector.py`, `tests/gui/test_gui_source_selector.py`.

FORBIDDEN: Сканировать пути вне переданного корня. Использовать сетевые пути. Изменять исходные файлы. Запускать обработку источников.

IMPLEMENTATION DETAILS:

- `SourceSelectorModel` принимает корневой каталог и допустимые расширения `.txt`, `.md`, `.json`, `.csv`.
- Игнорировать скрытые файлы и символические ссылки вне корня.
- Манифест содержит `path`, `size`, `sha256`.
- Все файловые проверки работают только в `tmp_path`.

TESTS:

- `test_lists_supported_files_sorted`
- `test_hidden_files_are_ignored`
- `test_selection_limit_is_enforced`
- `test_manifest_contains_sha256`

ACCEPTANCE: Список источников детерминирован. Манифест пригоден для последующего запуска.

STOP_CONDITIONS: Если нужны внешние базы данных — остановить задачу.

---

### TASK-08-12: Панель управления запуском

GOAL: Реализовать модель панели `Start`/`Stop`/`Retry`/`Reset` с подтверждениями.

CONTEXT: Панель использует снапшот, правила доступности и диспетчер интентов. Полная логика Soft/Hard Stop — в TASK-08-28.

ALLOWED_FILES: `src/gui/run_controls.py`, `tests/gui/test_gui_run_controls.py`.

FORBIDDEN: Запускать реальный процесс. Менять статусы напрямую. Смешивать состояние и команды. Выполнять сетевые вызовы.

IMPLEMENTATION DETAILS:

- `RunControlsViewModel` объединяет `GuiStateSnapshot`, `control_rules`, `IntentDispatcher`.
- Для `STOP` и `RESET` требовать подтверждение.
- Интент отправляется только после подтверждения.
- Отмена подтверждения не меняет состояние.

TESTS:

- `test_start_disabled_when_form_invalid`
- `test_stop_enabled_during_running`
- `test_intent_sent_only_after_confirm`
- `test_cancel_confirm_keeps_state`

ACCEPTANCE: Все действия передаются как интенты. Подтверждения работают без реального модального окна.

STOP_CONDITIONS: Если UX подтверждений не согласован — использовать минимальный stub.

---

### TASK-08-13: Модель прогресса и таймлайна этапов

GOAL: Реализовать отображение прогресса исследования по этапам без реальных таймеров.

CONTEXT: Прогресс приходит событиями, GUI устойчив к позднему или неполному потоку.

ALLOWED_FILES: `src/gui/progress.py`, `tests/gui/test_gui_progress.py`.

FORBIDDEN: Использовать потоки или реальные таймеры в тестах. Выполнять сетевые запросы. Менять состояние FSM. Запускать LLM.

IMPLEMENTATION DETAILS:

- `ProgressTimelineModel` принимает события `stage_started`, `stage_finished`, `progress_updated`.
- Использовать инжектируемые часы для `elapsed`.
- ETA отображать только при стабильной скорости, иначе `None`.
- Этапы имеют детерминированный порядок.

TESTS:

- `test_timeline_orders_stages`
- `test_out_of_order_events_are_ignored`
- `test_eta_is_none_without_stable_rate`
- `test_elapsed_uses_fake_clock`

ACCEPTANCE: Таймлайн детерминирован. Прогресс не ломается при неполных событиях.

STOP_CONDITIONS: Если имена этапов неизвестны — использовать общий шаблон.

---

## G4 — Наблюдаемость: логи и артефакты

### TASK-08-14: X-Ray Activity Stream с типизированными событиями

GOAL: Реализовать X-Ray Activity Stream с конкретными типами событий из ТЗ, кольцевым буфером и передачей через `queue.Queue`.

CONTEXT: ТЗ Раздел 6, Секция 5 определяет конкретные события: поиск, ranking, fetch, parsing, chunking, Evidence extraction, gap detection, ошибки. Логи передаются через `queue.Queue`. UI обновляет батчами через `root.after()`. Циклический буфер: последние 150–300 строк, значение конфигурируемое.

ALLOWED_FILES: `src/gui/xray_stream.py`, `tests/gui/test_xray_stream.py`.

FORBIDDEN: Писать логи на диск вне тестовой изоляции. Блокировать поток интерфейса. Выполнять сетевые вызовы. Изменять исходные записи.

IMPLEMENTATION DETAILS:

- `XRayStreamModel` хранит кольцевой буфер настраиваемого размера (150–300 строк).
- Определить типы событий (согласно ТЗ Раздел 6, Секция 5):

        SEARCH — начало поиска
        RANKING — ранжирование кандидатов
        FETCH — скачивание документа
        PARSING — парсинг и очистка
        CHUNKING — нарезка на чанки
        EVIDENCE_EXTRACTION — извлечение доказательств
        GAP_DETECTION — обнаружение пробелов
        ERROR — ошибка любого типа

- Каждая запись имеет `seq`, `level`, `event_type`, `source`, `message`, `timestamp`.
- Передача событий через `queue.Queue` из worker-потока.
- Обработка событий в GUI через `root.after()` батчами.
- Использовать `threading.Lock` для безопасности.
- Переполнение удаляет самые старые записи.

TESTS:

- `test_ring_buffer_trims_oldest`
- `test_sequence_is_monotonic`
- `test_all_event_types_are_defined`
- `test_append_from_queue_is_thread_safe`
- `test_batch_update_via_after_callback`
- `test_buffer_size_is_configurable`

ACCEPTANCE: X-Ray отображает все 8 типов событий из ТЗ. Буфер ограничен и конфигурируем. Передача через `queue.Queue`.

STOP_CONDITIONS: Если `root.after()` не доступен в тестах — использовать заглушку таймера.

---

### TASK-08-15: Модель фильтрации логов и пресеты

GOAL: Реализовать фильтрацию логов по уровню, источнику и подстроке с сохранением пресетов.

CONTEXT: Фильтрация применяется к копии потока, не изменяя исходные записи.

ALLOWED_FILES: `src/gui/log_filter.py`, `tests/gui/test_gui_log_filter.py`.

FORBIDDEN: Мутировать оригинальные записи. Использовать небезопасные регулярные выражения. Читать файлы вне `tmp_path`. Выполнять сетевые запросы.

IMPLEMENTATION DETAILS:

- `LogFilterModel` поддерживает уровень, источник, тип события и подстроку.
- Подстрока экранируется через `re.escape`.
- Пресеты сохраняются в JSON в `tmp_path`.
- Ограничить число пресетов десятью.

TESTS:

- `test_filter_by_level_and_source`
- `test_filter_by_event_type`
- `test_substring_is_escaped`
- `test_preset_roundtrip_in_tmp_path`

ACCEPTANCE: Фильтрация детерминирована. Пресеты восстанавливаются без ошибок.

STOP_CONDITIONS: Если нужны сложные регулярные выражения — остановить задачу.

---

### TASK-08-16: Модель таблицы артефактов

GOAL: Реализовать read-only таблицу артефактов с сортировкой и пагинацией.

CONTEXT: Таблица отображает метаданные артефактов, не открывая содержимое.

ALLOWED_FILES: `src/gui/artifact_table.py`, `tests/gui/test_gui_artifact_table.py`.

FORBIDDEN: Изменять артефакты. Выполнять экспорт. Читать содержимое файлов без отдельной задачи. Обращаться к сети.

IMPLEMENTATION DETAILS:

- `ArtifactTableModel` принимает строки с `id`, `kind`, `name`, `size`, `created_at`, `state`.
- Сортировка по `created_at` с стабильным tie-break по `id`.
- Размер страницы 100 строк.
- Тесты используют manifest JSON в `tmp_path`.

TESTS:

- `test_sort_by_created_desc`
- `test_stable_tie_break_by_id`
- `test_pagination_metadata`
- `test_empty_state_is_explicit`

ACCEPTANCE: Таблица детерминирована. Выбор артефакта хранится в модели представления.

STOP_CONDITIONS: Если требуется предпросмотр — остановить задачу.

---

### TASK-08-17: Модель экспорта выбранных артефактов

GOAL: Реализовать безопасный экспорт выбранных артефактов в локальный каталог.

CONTEXT: Экспорт выполняется только над выбранными элементами и только локально.

ALLOWED_FILES: `src/gui/artifact_export.py`, `tests/gui/test_gui_artifact_export.py`.

FORBIDDEN: Загружать артефакты в сеть. Изменять исходные артефакты. Обходить FSM. Записывать файлы вне целевого каталога.

IMPLEMENTATION DETAILS:

- `ArtifactExportModel` принимает `selection`, `target_dir`, `overwrite_policy`.
- Санитизация имён запрещает `..`, абсолютные пути и недопустимые символы.
- Существующие файлы пропускаются без флага `overwrite`.
- Результат содержит списки `exported`, `skipped`, `failed`.

TESTS:

- `test_export_copies_bytes`
- `test_existing_file_skipped_without_overwrite`
- `test_overwrite_flag_replaces_file`
- `test_path_traversal_is_rejected`

ACCEPTANCE: Экспорт идемпотентен при повторном запуске без `overwrite`. Все операции в `tmp_path`.

STOP_CONDITIONS: Если требуется архивация — остановить задачу.

---

## G5 — Конфигурация и настройки

### TASK-08-18: Форма настроек MCP-сервера `stdio`

GOAL: Реализовать валидацию конфигурации MCP-сервера для транспорта `stdio` без запуска процесса.

CONTEXT: Настройки соответствуют `MCP TOOL CONTRACTS v1.1`, но не исполняются в тестах.

ALLOWED_FILES: `src/gui/mcp_settings.py`, `tests/gui/test_gui_mcp_settings.py`.

FORBIDDEN: Запускать процесс. Использовать сетевые транспорты. Хранить секреты в открытом виде без пометки. Выполнять реальные MCP-вызовы.

IMPLEMENTATION DETAILS:

- Поля: `name`, `command`, `args`, `env`, `timeout_ms`.
- `command` не пустой, без символов командного интерпретатора.
- Ключи `env` соответствуют правилам переменных окружения.
- `timeout_ms` от 100 до 60000.
- Дубликаты имён отклоняются.

TESTS:

- `test_valid_stdio_config_accepted`
- `test_shell_metacharacters_rejected`
- `test_env_key_validation`
- `test_duplicate_name_rejected`

ACCEPTANCE: Форма выводит черновик `McpConfigDraft`. Запуск процесса не требуется.

STOP_CONDITIONS: Если нужен транспорт отличный от `stdio` — остановить задачу.

---

### TASK-08-19: Форма профиля локальной CPU-only LLM

GOAL: Реализовать валидацию профиля локальной LLM для CPU-режима без загрузки и запуска модели.

CONTEXT: Профиль безопасен для локального использования и не допускает удалённых эндпоинтов.

ALLOWED_FILES: `src/gui/llm_settings.py`, `tests/gui/test_gui_llm_settings.py`.

FORBIDDEN: Скачивать модели. Вызывать LLM. Использовать GPU-флаги. Обращаться к удалённым API.

IMPLEMENTATION DETAILS:

- Поля: `profile_name`, `backend`, `model_path`, `context_size`, `threads`.
- `backend` — только `LM_STUDIO`, `OLLAMA`, `LOCAL_STUB`.
- `model_path` должен существовать внутри `allowed_root`.
- `threads` от 1 до `os.cpu_count()`.
- `context_size` от 512 до 32768.

TESTS:

- `test_missing_model_path_rejected`
- `test_gpu_flag_rejected`
- `test_context_bounds_enforced`
- `test_threads_clamped_to_cpu_count`

ACCEPTANCE: Профиль готов к сохранению. Нет сетевых зависимостей.

STOP_CONDITIONS: Если требуется удалённый LLM-эндпоинт — остановить задачу.

---

## G6 — Персистентность, ошибки и сборка

### TASK-08-20: Репозиторий настроек с атомарной записью

GOAL: Реализовать сохранение и загрузку настроек GUI в JSON с атомарной записью и версией схемы.

CONTEXT: Настройки MCP и LLM переживают перезапуск приложения без обращения к базе состояния.

ALLOWED_FILES: `src/gui/settings_repo.py`, `tests/gui/test_gui_settings_repo.py`.

FORBIDDEN: Писать файлы вне `tmp_path` в тестах. Обновлять статусы FSM. Хранить секреты в логах. Смешивать настройки с состоянием исследования.

IMPLEMENTATION DETAILS:

- `SettingsRepository` использует `schema_version = 1`.
- Запись через временный файл и `os.replace`.
- Повреждённый JSON возвращает дефолт и `warning`.
- Валидация вызывает формы из TASK-08-18 и TASK-08-19.

TESTS:

- `test_save_load_roundtrip`
- `test_corrupt_file_returns_defaults`
- `test_invalid_payload_rejected`
- `test_atomic_replace_keeps_previous_file_on_error`

ACCEPTANCE: Настройки восстанавливаются после перезапуска. Повреждение файла не приводит к падению.

STOP_CONDITIONS: Если требуется хранение в SQLite — остановить задачу.

---

### TASK-08-21: Центр ошибок и локальной диагностики

GOAL: Реализовать модель баннера ошибок и локальной диагностики окружения без изменения состояния.

CONTEXT: Пользователь видит причину ошибки и доступное действие: `RETRY`, `RESET`, `OPEN_SETTINGS`.

ALLOWED_FILES: `src/gui/status_center.py`, `tests/gui/test_gui_status_center.py`.

FORBIDDEN: Сбрасывать ошибку FSM напрямую. Скрывать фатальные ошибки. Выполнять сетевую диагностику. Запускать LLM или MCP.

IMPLEMENTATION DETAILS:

- `StatusCenterViewModel` маппит коды ошибок на сообщения и действия.
- Диагностика проверяет наличие файла настроек, существование модели и `journal_mode` SQLite через read-only подключение.
- Все файлы создаются только в `tmp_path`.
- Неизвестная ошибка отображается нейтральным сообщением с кодом.

TESTS:

- `test_known_error_maps_to_retry_action`
- `test_unknown_error_shows_generic_message`
- `test_sqlite_wal_diagnostic`
- `test_missing_model_path_is_reported`

ACCEPTANCE: Ошибки имеют действия восстановления. Диагностика локальна и безопасна.

STOP_CONDITIONS: Если требуется телеметрия — остановить задачу.

---

### TASK-08-22: Корень композиции и headless smoke-сборка

GOAL: Собрать все модели GUI в единый композиционный корень и проверить запуск без реального окна.

CONTEXT: Задача связывает тему, оболочку, навигацию, формы, логи, артефакты и статусный центр.

ALLOWED_FILES: `src/gui/composition.py`, `src/gui/app.py`, `src/gui/tk/app_window.py`, `tests/gui/test_gui_composition.py`.

FORBIDDEN: Запускать реальное исследование. Требовать дисплей в тестах. Изменять статусы в обход FSM. Выполнять сетевые вызовы.

IMPLEMENTATION DETAILS:

- `build_gui(workspace, toolkit='headless')` создаёт все модели.
- Production-окно создаётся только лениво при наличии `customtkinter`.
- Композиция возвращает `GuiCompositionReport` со списком созданных моделей.
- При отсутствии файла настроек создаётся дефолтный файл в `tmp_path`.

TESTS:

- `test_headless_build_registers_all_view_models`
- `test_build_creates_default_settings_file`
- `test_build_does_not_import_customtkinter`
- `test_smoke_report_lists_all_tasks`

ACCEPTANCE: Один входной файл собирает весь GUI-контур. Тесты проходят в headless-режиме.

STOP_CONDITIONS: Если интеграция с реальным ядром недоступна — использовать фейковые порты.

---

## G7 — Специализированные экраны из ТЗ Раздел 6

### TASK-08-23: Архитектура потоков и координация событий

GOAL: Реализовать механизм взаимодействия между Main Thread и Worker Thread через `asyncio.run_coroutine_threadsafe()`, thread-safe queue и `root.after()`.

CONTEXT: ТЗ Раздел 6, Секция 2 определяет: Main Thread — GUI, events, rendering. Worker Thread — asyncio loop, network, orchestration, MCP. Взаимодействие строго через три механизма.

ALLOWED_FILES: `src/gui/thread_coordinator.py`, `tests/gui/test_thread_coordinator.py`.

FORBIDDEN: Выполнять тяжёлые операции в Main Thread. Блокировать GUI-поток. Использовать прямые вызовы между потоками без очереди.

IMPLEMENTATION DETAILS:

- Создать `ThreadCoordinator` с методами:
    - `dispatch_to_worker(coro)` — обёртка над `asyncio.run_coroutine_threadsafe(coro, loop)`.
    - `dispatch_to_gui(event)` — помещение события в `queue.Queue` для обработки в GUI-потоке.
    - `start_worker()` — запуск asyncio loop в отдельном потоке.
    - `stop_worker()` — корректное завершение.
- Очередь событий обрабатывается в GUI через `root.after(poll_interval, process_queue)`.
- `process_queue()` извлекает все накопленные события батчем и обновляет ViewModel.
- При остановке: ожидать завершения текущих операций с таймаутом.

TESTS:

- `test_dispatch_to_worker_executes_coroutine`
- `test_dispatch_to_gui_queues_event`
- `test_batch_processing_of_queued_events`
- `test_worker_stop_is_graceful`
- `test_gui_update_does_not_block`

ACCEPTANCE: Main Thread не выполняет тяжёлых операций. Все взаимодействия через очередь и `root.after()`.

STOP_CONDITIONS: Если `asyncio.run_coroutine_threadsafe` не работает в целевой среде — остановить задачу.

---

### TASK-08-24: Intent Blueprint Editor

GOAL: Реализовать редактор плана поиска, позволяющий пользователю просматривать и корректировать задачи до запуска.

CONTEXT: ТЗ Раздел 6, Секция 4 определяет: отображение `task`, `purpose`, `query`, `source`, `filters`, `exclusions`, `expected material type`, `priority`, `estimated budget`. Пользователь может изменить query, отключить task, изменить priority, изменить source, сохранить вариант.

ALLOWED_FILES: `src/gui/intent_blueprint.py`, `tests/gui/test_intent_blueprint.py`.

FORBIDDEN: Запускать исследование. Менять `SearchTask` в БД напрямую. Обходить `PlanNormalizer`.

IMPLEMENTATION DETAILS:

- `IntentBlueprintViewModel` отображает список `SearchTaskDraft` из `ResearchPlan`.
- Каждое поле редактируемое:
    - `query` — текстовое поле
    - `priority` — числовое поле
    - `source_scope` — выбор из списка
    - `enabled` — чекбокс для отключения задачи
- Поля только для чтения: `purpose`, `filters`, `exclusions`, `expected_material_type`, `estimated_budget`.
- Кнопка «Сохранить вариант» отправляет интент через `IntentDispatcher`.
- Изменения не применяются к БД до подтверждения Core.

TESTS:

- `test_blueprint_displays_all_fields`
- `test_query_is_editable`
- `test_task_can_be_disabled`
- `test_priority_is_changeable`
- `test_save_sends_intent_not_direct_write`
- `test_readonly_fields_are_not_editable`

ACCEPTANCE: Пользователь видит и корректирует план. Изменения применяются только через интенты.

STOP_CONDITIONS: Если структура `SearchTaskDraft` не определена в EPIC-05 — остановить задачу.

---

### TASK-08-25: Evidence Explorer

GOAL: Реализовать боковую панель для детального просмотра Evidence с полной цепочкой трассируемости.

CONTEXT: ТЗ Раздел 6, Секция 6 определяет: клик по Evidence открывает side panel: Claim → Evidence → Document → Source. Показываются: точный текст, location, source, document metadata.

ALLOWED_FILES: `src/gui/evidence_explorer.py`, `tests/gui/test_evidence_explorer.py`.

FORBIDDEN: Изменять Evidence или связанные сущности. Выполнять поиск. Обходить порты данных.

IMPLEMENTATION DETAILS:

- `EvidenceExplorerViewModel` принимает `evidence_id` и загружает цепочку через порт.
- Отображение:
    - `Claim.text` — утверждение, к которому привязано доказательство.
    - `Evidence.text` — точный текст цитаты.
    - `Evidence.location` — позиция в документе.
    - `Document.title`, `Document.content_type` — метаданные документа.
    - `Source.canonical_url`, `Source.domain` — данные источника.
- Если цепочка неполная (например, нет `Claim`) — показать только имеющиеся уровни.
- Данные загружаются через `EvidencePort` (заглушка в тестах).

TESTS:

- `test_full_chain_displayed`
- `test_partial_chain_shows_available_levels`
- `test_evidence_text_is_exact`
- `test_source_url_is_displayed`

ACCEPTANCE: Полная цепочка трассируемости отображается. Данные только через порты.

STOP_CONDITIONS: Если порт не предоставляет данные о цепочке — остановить задачу.

---

### TASK-08-26: Evidence Tree

GOAL: Реализовать дерево связей Evidence с цветовой индикацией статусов.

CONTEXT: ТЗ Раздел 6, Секция 7 определяет дерево: Claim → Evidence → Source, Contradiction. Цветовая индикация — визуальное отображение статуса, не отдельная логика.

ALLOWED_FILES: `src/gui/evidence_tree.py`, `tests/gui/test_evidence_tree.py`.

FORBIDDEN: Изменять связи. Выполнять валидацию. Хранить бизнес-логику.

IMPLEMENTATION DETAILS:

- `EvidenceTreeViewModel` строит дерево из данных `EvidencePort`.
- Структура узла: `claim_id` → `evidence_id` → `source_id`, плюс `contradiction_id` при наличии.
- Цветовая индикация по статусу: `SUPPORTED`, `CONTRADICTED`, `INSUFFICIENT_EVIDENCE`.
- Цвета определяются через `ThemeTokens` из TASK-08-03.
- Дерево строится детерминированно из входных данных.

TESTS:

- `test_tree_structure_matches_input`
- `test_contradiction_node_displayed`
- `test_color_maps_to_status`
- `test_empty_data_shows_placeholder`

ACCEPTANCE: Дерево корректно отображает связи. Цветовая индикация соответствует статусам.

STOP_CONDITIONS: Если порт не предоставляет дерево связей — остановить задачу.

---

### TASK-08-27: Report Viewer с Smart Scroll

GOAL: Реализовать просмотрщик отчётов с умной прокруткой.

CONTEXT: ТЗ Раздел 6, Секция 8 определяет: если пользователь читает выше конца, auto-scroll отключается. Отображается кнопка перехода к концу.

ALLOWED_FILES: `src/gui/report_viewer.py`, `tests/gui/test_report_viewer.py`.

FORBIDDEN: Изменять содержимое отчёта. Записывать данные. Выполнять валидацию.

IMPLEMENTATION DETAILS:

- `ReportViewerViewModel` отображает текст отчёта.
- `auto_scroll` — флаг: если пользователь в конце, новые данные автоматически прокручиваются.
- Если пользователь прокрутил вверх — `auto_scroll` отключается.
- Кнопка «Перейти к концу» возвращает `auto_scroll = True`.
- Метод `append_content(new_text)` добавляет текст и при `auto_scroll` прокручивает.
- Отображение `REPORT_TRUNCATED_PARTIAL` как метаданных (не состояние).

TESTS:

- `test_auto_scroll_when_at_bottom`
- `test_auto_scroll_disabled_on_manual_scroll_up`
- `test_button_restores_auto_scroll`
- `test_append_content_triggers_scroll_only_when_enabled`
- `test_truncated_partial_shown_as_metadata`

ACCEPTANCE: Smart scroll работает детерминированно. Кнопка перехода к концу отображается.

STOP_CONDITIONS: Если механизм прокрутки не доступен в тестах — использовать заглушку.

---

### TASK-08-28: Graceful Abort и кооперативная отмена

GOAL: Реализовать полный механизм мягкого и жёсткого останова с кооперативной отменой CPU-задач.

CONTEXT: ТЗ Раздел 6, Секция 9 определяет два режима:
- **Soft Stop**: новые сетевые запросы не запускаются; текущие безопасно завершаются; разрешается финальный synthesis; создаётся partial report.
- **Hard Stop**: новые операции запрещаются; asyncio tasks отменяются; cancellation кооперативная; состояние фиксируется checkpoint'ом; SQLite остаётся консистентной.

Кооперативная отмена: флаг через `threading.Event`; точки проверки: чанкинг, индексация, стемминг, перестроение индекса.

ALLOWED_FILES: `src/gui/abort_controller.py`, `tests/gui/test_abort_controller.py`.

FORBIDDEN: Мгновенно уничтожать потоки. Повреждать SQLite. Обходить checkpoint.

IMPLEMENTATION DETAILS:

- `AbortController` с методами `soft_stop()`, `hard_stop()`.
- `soft_stop()`:
    - Установить флаг «не запускать новые операции».
    - Дождаться завершения текущих операций.
    - Разрешить финальный synthesis.
    - Отправить интент `SOFT_STOP` в `IntentDispatcher`.
- `hard_stop()`:
    - Установить флаг «запретить все операции».
    - Отменить asyncio tasks (кооперативно).
    - Установить `threading.Event` для CPU-задач.
    - Если операция не завершилась за таймаут (5 сек) — принудительное прерывание с фиксацией checkpoint.
    - Отправить интент `HARD_STOP` в `IntentDispatcher`.
- Кооперативная отмена: каждая долгая операция проверяет `threading.Event` на каждой итерации.
- Точки проверки: после каждого чанка (чанкинг), после каждого батча (индексация), после каждого документа (стемминг).
- При любом типе остановки: уже обработанные данные сохраняются; фиксируется контрольная точка.

TESTS:

- `test_soft_stop_allows_current_operations_to_finish`
- `test_soft_stop_creates_partial_report`
- `test_hard_stop_cancels_asyncio_tasks`
- `test_hard_stop_sets_threading_event`
- `test_hard_stop_timeout_forces_interruption`
- `test_cooperative_check_after_each_chunk`
- `test_cooperative_check_after_each_batch`
- `test_checkpoint_is_created_on_stop`
- `test_sqlite_remains_consistent_after_hard_stop`

ACCEPTANCE: Оба режима работают корректно. Данные не теряются. `SQLite` консистентна. Кооперативная отмена покрывает все точки проверки.

STOP_CONDITIONS: Если `threading.Event` не доступен в целевой среде — остановить задачу.

---

### TASK-08-29: System Health Monitor

GOAL: Реализовать монитор здоровья системы с отображением ключевых метрик.

CONTEXT: ТЗ Раздел 6, Секция 10 определяет: `LLM status`, `backend`, `queue size`, `active tasks`, `DB size`, `disk free space`, `network/source errors`.

ALLOWED_FILES: `src/gui/health_monitor.py`, `tests/gui/test_health_monitor.py`.

FORBIDDEN: Изменять состояние системы. Выполнять диагностику через сеть. Хранить бизнес-логику.

IMPLEMENTATION DETAILS:

- `HealthMonitorViewModel` с периодическим опросом через порт.
- Отображение метрик:
    - `llm_status` — `HEALTHY`, `DEGRADED`, `UNREACHABLE`, `RESTARTING`
    - `backend` — имя активного бэкенда
    - `queue_size` — размер очереди операций
    - `active_tasks` — число активных задач
    - `db_size` — размер текущей проектной БД
    - `registry_size` — размер реестра
    - `disk_free` — свободное место на диске
    - `network_errors` — число сетевых ошибок
- Данные через `HealthPort` (заглушка в тестах).
- Обновление через `root.after()`.

TESTS:

- `test_all_metrics_displayed`
- `test_llm_status_maps_correctly`
- `test_db_size_read_only`
- `test_update_via_after_callback`

ACCEPTANCE: Все метрики отображаются. Данные только через порты. Обновление через `root.after()`.

STOP_CONDITIONS: Если порт не предоставляет метрики — остановить задачу.

---

### TASK-08-30: Prompt Sandbox

GOAL: Реализовать изолированную среду для тестирования промптов без изменения состояния исследования.

CONTEXT: ТЗ Раздел 6, Секция 11 определяет: выбрать Evidence, применить prompt, получить пробный результат, не изменять Study.

ALLOWED_FILES: `src/gui/prompt_sandbox.py`, `tests/gui/test_prompt_sandbox.py`.

FORBIDDEN: Изменять `Study`, `ResearchSession`, `Evidence`. Записывать данные в БД. Выполнять реальное исследование.

IMPLEMENTATION DETAILS:

- `PromptSandboxViewModel` с полями: `evidence_selection`, `prompt_template`, `result_preview`.
- Выбор Evidence из списка (через порт).
- Применение шаблона промпта к выбранному Evidence.
- Пробный вывод отображается в `result_preview` без сохранения.
- Кнопка «Применить» — только предпросмотр, без записи.
- Изоляция: песочница не влияет на реальное состояние `Study`.

TESTS:

- `test_evidence_selection_works`
- `test_prompt_applied_to_evidence`
- `test_result_not_saved_to_db`
- `test_study_state_unchanged`

ACCEPTANCE: Песочница полностью изолирована. Результат не сохраняется. `Study` не изменяется.

STOP_CONDITIONS: Если порт не предоставляет данные Evidence — остановить задачу.

---

### TASK-08-31: Research Snapshots

GOAL: Реализовать управление снапшотами исследования с возможностью отката.

CONTEXT: ТЗ Раздел 6, Секция 12 определяет: снапшот содержит `ResearchState`, `Claims`, `Evidence references`, `Working Memory`, `task state`. Откат не должен разрушать глобальный Document Repository.

ALLOWED_FILES: `src/gui/snapshot_view.py`, `tests/gui/test_snapshot_view.py`.

FORBIDDEN: Разрушать `Document Repository`. Изменять данные при откате без подтверждения. Обходить порты.

IMPLEMENTATION DETAILS:

- `SnapshotViewModel` отображает список снапшотов.
- Создание снапшота: отправка интента через `IntentDispatcher`.
- Откат: отправка интента с подтверждением.
- Отображение метаданных снапшота: `created_at`, `iteration`, `claim_count`, `evidence_count`.
- При откате: `Document Repository` не затрагивается (только состояние исследования).

TESTS:

- `test_snapshot_list_displayed`
- `test_create_snapshot_sends_intent`
- `test_rollback_requires_confirmation`
- `test_rollback_does_not_affect_document_repository`

ACCEPTANCE: Снапшоты создаются и отображаются. Откат безопасен для `Document Repository`.

STOP_CONDITIONS: Если порт не поддерживает снапшоты — остановить задачу.

---

### TASK-08-32: Управление проектами

GOAL: Реализовать полный цикл управления проектами: создание, переключение, архивация, удаление, передача Study.

CONTEXT: ТЗ Раздел 6, Секция 13 определяет: `create`, `rename`, `archive`, `delete with confirmation`, `transfer Study`. Переключение проектов = переключение активной БД. Создание проекта = создание нового `.db` файла + записи в реестре. Архивация = смена статуса в реестре.

ALLOWED_FILES: `src/gui/projects_view.py`, `tests/gui/test_projects_view.py`.

FORBIDDEN: Удалять файлы БД без подтверждения. Менять статус в реестре напрямую. Обходить `ProjectRegistry`.

IMPLEMENTATION DETAILS:

- `ProjectsViewModel` отображает список проектов из `ProjectRegistry`.
- Действия:
    - `create` — создание нового `.db` файла + записи в реестре (через порт).
    - `rename` — переименование в реестре.
    - `archive` — смена статуса в реестре, файл сохраняется.
    - `delete` — с обязательным подтверждением.
    - `transfer_study` — перенос Study между проектами.
- Переключение проекта: выбор из списка → отправка интента `SWITCH_PROJECT`.
- Отображение статуса: `active`, `archived`.

TESTS:

- `test_project_list_displayed`
- `test_create_project_sends_intent`
- `test_switch_project_sends_intent`
- `test_archive_changes_status_only`
- `test_delete_requires_confirmation`
- `test_transfer_study_between_projects`

ACCEPTANCE: Все операции управления проектами работают через интенты. Подтверждения для деструктивных операций.

STOP_CONDITIONS: Если `ProjectRegistry` не доступен через порт — остановить задачу.

---

### TASK-08-33: Offline Mode

GOAL: Реализовать режим работы без сети с доступом к локальным материалам.

CONTEXT: ТЗ Раздел 6, Секция 14 определяет: при отсутствии сети пользователь может искать по локальным материалам, просматривать Evidence, анализировать Study, создавать report, экспортировать результат.

ALLOWED_FILES: `src/gui/offline_mode.py`, `tests/gui/test_offline_mode.py`.

FORBIDDEN: Выполнять сетевые запросы. Обходить `ModeController` (EPIC-05). Хранить бизнес-логику в GUI.

IMPLEMENTATION DETAILS:

- `OfflineModeController` определяет статус сети (через порт).
- При отсутствии сети:
    - Разрешить: локальный поиск, просмотр Evidence, анализ Study, создание отчёта, экспорт.
    - Заблокировать: сетевые запросы (отображение предупреждения).
- Отображение баннера «Оффлайн режим».
- Индикатор доступных функций.
- Переход в онлайн при восстановлении сети (через событие из порта).

TESTS:

- `test_offline_mode_blocks_network_operations`
- `test_offline_mode_allows_local_search`
- `test_offline_mode_allows_evidence_viewing`
- `test_offline_mode_allows_report_creation`
- `test_offline_banner_displayed`
- `test_transition_to_online_on_recovery`

ACCEPTANCE: Все функции работают в оффлайне. Сетевые операции заблокированы. Баннер отображается.

STOP_CONDITIONS: Если порт не предоставляет статус сети — остановить задачу.

---

### TASK-08-34: Review / Aggregation Dashboard

GOAL: Реализовать дашборд для режима агрегации мнений с отображением статистики.

CONTEXT: ТЗ Раздел 6, Секция 15 определяет: число обработанных отзывов/наблюдений, число уникальных источников, основные аспекты, положительные/отрицательные паттерны, распределение наблюдений, аномальные группы, ограничения выборки.

ALLOWED_FILES: `src/gui/aggregation_dashboard.py`, `tests/gui/test_aggregation_dashboard.py`.

FORBIDDEN: Выполнять расчёты в GUI. Изменять данные. Обходить порты.

IMPLEMENTATION DETAILS:

- `AggregationDashboardViewModel` отображает данные через `AggregationPort`.
- Метрики:
    - `observation_count` — число обработанных наблюдений.
    - `unique_source_count` — число уникальных источников.
    - `aspects[]` — основные аспекты.
    - `positive_patterns[]` — положительные паттерны.
    - `negative_patterns[]` — отрицательные паттерны.
    - `distribution` — распределение наблюдений.
    - `anomalous_groups[]` — аномальные группы.
    - `limitations[]` — ограничения выборки.
- Отображение предупреждения, если выборка недостаточна (ТЗ: «Один отзыв не является статистическим фактом»).

TESTS:

- `test_all_metrics_displayed`
- `test_insufficient_sample_warning`
- `test_distribution_chart_data`
- `test_anomalous_groups_highlighted`

ACCEPTANCE: Все метрики отображаются. Предупреждение при малой выборке. Данные через порты.

STOP_CONDITIONS: Если порт не предоставляет данные агрегации — остановить задачу.

---

### TASK-08-35: Query Preview перед запуском

GOAL: Реализовать обязательный предпросмотр всех `SearchTask` перед запуском исследования.

CONTEXT: ТЗ Раздел 6, Секция 16 определяет: перед запуском пользователь видит все `SearchTask`. Запуск без превью допускается только после явной настройки.

ALLOWED_FILES: `src/gui/query_preview.py`, `tests/gui/test_query_preview.py`.

FORBIDDEN: Запускать исследование без превью (если не отключено в настройках). Изменять задачи в БД.

IMPLEMENTATION DETAILS:

- `QueryPreviewViewModel` отображает список `SearchTask` из `ResearchPlan`.
- Для каждой задачи: `query`, `purpose`, `source_scope`, `priority`, `estimated_budget`.
- Возможность редактирования: изменить запрос, отключить задачу, изменить приоритет.
- Кнопка «Запустить» отправляет интент `START_RESEARCH`.
- Флаг `skip_preview` в настройках: если `true`, превью пропускается (по умолчанию `false`).
- Если `skip_preview = false` — запуск невозможен без просмотра превью.

TESTS:

- `test_all_tasks_displayed`
- `test_query_is_editable`
- `test_task_can_be_disabled`
- `test_launch_blocked_without_preview_if_not_skipped`
- `test_launch_allowed_with_skip_preview_flag`

ACCEPTANCE: Превью отображается перед запуском. Запуск заблокирован без превью (если не отключено).

STOP_CONDITIONS: Если структура `ResearchPlan` не определена — остановить задачу.

---

### TASK-08-36: Мастер создания исследования (Study Creation Wizard)

GOAL: Реализовать многошаговый мастер создания исследования, покрывающий полный процесс из ТЗ Раздел 6, Секция 3.

CONTEXT: ТЗ Раздел 6, Секция 3 определяет: создать Project, создать Study, ввести question/goal, выбрать research mode, выбрать source scope, задать filters/exclusions, подключить Project/архив, добавить local documents, просмотреть план, изменить запросы, запустить/остановить исследование.

ALLOWED_FILES: `src/gui/study_wizard.py`, `tests/gui/test_study_wizard.py`.

FORBIDDEN: Создавать `Study` в БД напрямую. Запускать исследование из мастера. Обходить порты.

IMPLEMENTATION DETAILS:

- `StudyWizardViewModel` — многошаговый мастер с шагами:
    1. **Выбор проекта**: текущий проект, отдельные Studies, отдельные documents, весь локальный архив.
    2. **Вопрос и цель**: `question`, `goal`, `domain`.
    3. **Режим исследования**: `research_mode` (EVIDENCE, AGGREGATION, COMPARISON, EXPAND, MATERIALS_ONLY).
    4. **Область источников**: `source_scope`, `filters`, `exclusions`.
    5. **Локальные документы**: выбор файлов (интеграция с TASK-08-11).
    6. **Превью плана**: отображение `SearchTask` (интеграция с TASK-08-35).
    7. **Подтверждение и запуск**.
- Каждый шаг валидируется. Переход назад разрешён.
- Запуск через интент `START_RESEARCH`.
- Мастер не создаёт `Study` в БД — только формирует данные для отправки в ядро.

TESTS:

- `test_wizard_has_seven_steps`
- `test_each_step_validates`
- `test_navigation_back_and_forward`
- `test_project_selection_options`
- `test_research_mode_selection`
- `test_local_documents_integration`
- `test_plan_preview_integration`
- `test_launch_sends_start_research_intent`

ACCEPTANCE: Полный процесс создания исследования покрыт. Каждый шаг валидируется. Запуск через интент.

STOP_CONDITIONS: Если структура `ResearchIntent` не определена в EPIC-02 — остановить задачу.

---

## Gate G-08 Acceptance Criteria

- GUI не содержит бизнес-правил: все решения принимает Core.
- Worker независим: тяжёлые операции в Worker Thread, GUI в Main Thread.
- UI остаётся отзывчивым: блокирующие операции отсутствуют в Main Thread.
- Soft Stop работает: текущие операции завершаются, создаётся partial report.
- Hard Stop работает: asyncio tasks отменяются, `threading.Event` устанавливается, SQLite консистентна.
- Кооперативная отмена: чанкинг, индексация, стемминг проверяют флаг.
- Offline mode работает: локальный поиск, просмотр, отчёт, экспорт.
- Research Snapshots: создание, откат без разрушения `Document Repository`.
- Evidence traceability: полная цепочка Claim → Evidence → Document → Source.
- Projects management: создание, переключение, архивация, удаление, передача.
- X-Ray Activity Stream: все 8 типов событий из ТЗ, буфер 150–300, `queue.Queue`.
- Intent Blueprint Editor: редактирование запросов, отключение задач.
- Query Preview: обязательный перед запуском (если не отключено).
- Report Viewer: smart scroll, кнопка перехода к концу.
- System Health Monitor: все метрики из ТЗ.
- Prompt Sandbox: изолированный, не изменяет Study.
- Aggregation Dashboard: все метрики из ТЗ.
- Study Creation Wizard: полный процесс из ТЗ Раздел 6, Секция 3.
- Headless-тесты: все тесты проходят без реального окна.
- Нет реальных сетевых вызовов в тестах.
- Нет реальной LLM в тестах.
- Нет прямого изменения `.status` в тестах.
- Нет импорта `customtkinter` на уровне модуля.

Статус EPIC-08: Готов к передаче в разработку.