# EPIC-11 — PACKAGING / PORTABLE. TASK BATCH v1.1

Статус: Готов к передаче CODE-агентам.
Зависимости: формально по Dependency Matrix — EPIC-10. Транзитивно — через все предыдущие (01–09).
Цель EPIC: Эксплуатационный MVP. Портативная структура папок, конфигурация, обработка локальной БД, проверка окружения, диагностика зависимостей, администраторский диагностический токен, проверки при запуске, логирование, инструкции резервного копирования и восстановления. Приложение запускается на целевой Windows-среде без IDE.
Не входит в MVP: полноценный Android runtime, отдельный Linux UX, embeddings, vector DB, reranker. Архитектурная совместимость сохраняется.
Ограничение: В MVP не допускаются скрытые обязательные зависимости от `embeddings`, `vector search`, `vector DB` или `GPU`.
Gate G-11: Приложение запускается на целевой Windows-среде без IDE и выдаёт понятную диагностику отсутствующих компонентов.

## Общие инварианты и запреты для всех задач EPIC-11

ALLOWED_FILES (глобально для EPIC):

- `src/packaging/` (корневая директория для модулей упаковки)
- `src/packaging/__init__.py`
- `src/packaging/bundler.py`, `src/packaging/build_spec.py`
- `src/packaging/llm_assets.py`, `src/packaging/mcp_assets.py`
- `src/packaging/text_assets.py`, `src/packaging/asset_manifest.py`
- `src/packaging/first_run.py`, `src/packaging/hardware_check.py`
- `src/packaging/asset_extractor.py`, `src/packaging/cleanup.py`
- `src/packaging/smoke_test.py`, `src/packaging/network_isolation.py`
- `src/packaging/llm_smoke.py`, `src/packaging/mcp_smoke.py`
- `src/packaging/release_archive.py`, `src/packaging/release_manifest.py`
- `src/packaging/db_bootstrap.py` (Local DB Bootstrap)
- `src/packaging/dependency_diagnostic.py` (Dependency Diagnostics)
- `src/packaging/diagnostic_token.py` (Administrator Diagnostic Token)
- `src/packaging/logging_config.py` (Logging Configuration)
- `src/packaging/backup_instructions.py` (Backup & Recovery)
- `src/packaging/hidden_deps_check.py` (No Hidden Dependencies)
- `src/packaging/missing_components.py` (Missing Components Diagnostics)
- `src/packaging/target_env_test.py` (Target Environment Test)
- `src/packaging/portable_structure.py` (Portable Folder)
- `src/cli/packaged_entry.py` (Headless CLI)
- `docs/operator_runbook.md`, `docs/quickstart.md`, `docs/backup_recovery.md`
- `requirements.lock`, `build_env.spec`, `build.spec`
- `tests/packaging/` (все тесты)
- `tests/fixtures/` (фейковые ассеты, заглушки)

FORBIDDEN (глобально для EPIC):

- Использование реальной сети в тестах.
- Использование реальной LLM в тестах.
- Прямое изменение `status` у доменных сущностей в обход FSM.
- Использование GPU в любых проверках.
- Скачивание моделей, библиотек или любых ресурсов из сети.
- Обращение к сетевым индексам пакетов (PyPI) в рантайме.
- Включение скрытых обязательных зависимостей от `embeddings`, `vector search`, `vector DB` или `GPU`.
- Запись файлов вне `tmp_path` в тестах.

Глобальное правило портативности:
Приложение должно работать как портативная папка (портативный дистрибутив) без установки в реестр, системные директории или переменные окружения. Все пути определяются относительно директории исполняемого файла или рабочей папки.

---

## G1 — Система сборки и фиксация зависимостей

### TASK-11-01: Детерминированный lockfile и проверка запрещённых зависимостей

GOAL: Создать зафиксированный lockfile зависимостей с проверкой отсутствия запрещённых библиотек.

CONTEXT: Оффлайн-дистрибутив требует жёсткой фиксации всех библиотек. В MVP не допускаются скрытые обязательные зависимости от `embeddings`, `vector search`, `vector DB` или `GPU`. Хэши пакетов генерируются однократно на этапе подготовки окружения сборки (build-setup time) с использованием сетевого доступа. В рантайме и в тестах проверка выполняется исключительно локально по уже зафиксированным хэшам без какого-либо сетевого доступа.

ALLOWED_FILES: `requirements.lock`, `build_env.spec`, `tests/packaging/test_build_env.py`.

FORBIDDEN: Использование сетевых индексов в рантайме. Включение запрещённых зависимостей. Скачивание пакетов в тестах.

IMPLEMENTATION DETAILS:

- `requirements.lock` содержит точные версии и хэши всех пакетов.
- Хэши генерируются однократно на этапе подготовки окружения сборки (вне рантайма). Проверка в рантайме и в тестах выполняется локально по зафиксированным хэшам.
- `build_env.spec` описывает целевую ОС, архитектуру и минимальную версию Python 3.11.
- Проверка отсутствия запрещённых зависимостей в `requirements.lock`:
    - `torch`, `tensorflow`, `jax` (GPU-фреймворки)
    - `faiss`, `chromadb`, `qdrant`, `milvus` (vector DB)
    - `sentence-transformers`, `openai` (embeddings / cloud LLM)
    - `cuda`, `cudnn` и любые CUDA-зависимости
- При обнаружении запрещённой зависимости — блокировка сборки с ошибкой.
- Проверка, что все импортируемые модули присутствуют в lockfile.
- Все проверки выполняются локально без скачивания пакетов.

TESTS:

- `test_lockfile_contains_all_imports`
- `test_build_spec_matches_target_os`
- `test_no_network_required_for_validation`
- `test_lockfile_format_is_valid`
- `test_no_forbidden_dependencies_present`
- `test_forbidden_dependency_blocks_build`
- `test_hashes_verified_locally_without_network`

ACCEPTANCE: Список зависимостей полон и детерминирован. Запрещённые зависимости отсутствуют. Спецификация сборки согласована. Хэши проверяются локально.

STOP_CONDITIONS: Если обнаружена запрещённая зависимость в коде — остановить задачу и передать архитектору.

---

### TASK-11-02: Спецификация сборки автономного исполняемого файла и портативная структура

GOAL: Реализовать конфигурацию упаковщика для создания standalone-исполняемого файла и портативной структуры папок.

CONTEXT: Пользователь должен запускать MVP без предустановленного интерпретатора Python. Roadmap Раздел 14 включает `portable folder`. Файл `build.spec` определяет конфигурацию упаковщика (скрытые импорты, исключения, точки входа). Файл `build_env.spec` (TASK-11-01) определяет целевую ОС и версию Python. Это два разных файла с разными назначениями.

ALLOWED_FILES: `build.spec`, `src/packaging/__init__.py`, `src/packaging/bundler.py`, `src/packaging/portable_structure.py`, `tests/packaging/test_bundler_config.py`.

FORBIDDEN: Запуск реального процесса упаковки в тестах. Отладочные символы в релизной сборке. Сетевые вызовы.

IMPLEMENTATION DETAILS:

- `build.spec` настраивает скрытый импорт `customtkinter`, `sqlite3` и внутренних модулей.
- `bundler.py` валидирует spec-файл на наличие обязательных секций.
- Исключаются тестовые директории и документация из финального бинарника.
- `PortableStructure` определяет портативную структуру папок:

        portable_root/
        ├── bin/           (исполняемый файл)
        ├── assets/        (ассеты, шаблоны, промпты)
        ├── data/          (рабочие данные, проектные БД)
        ├── logs/          (логи)
        ├── settings/      (настройки)
        └── docs/          (документация)

- Все пути определяются относительно корня портативной папки.
- Не требуется установка в реестр или системные директории.
- Тесты используют мок-объекты упаковщика.

TESTS:

- `test_spec_contains_required_hidden_imports`
- `test_spec_contains_sqlite3_hidden_import`
- `test_spec_contains_customtkinter_hidden_import`
- `test_test_directories_excluded`
- `test_bundler_validates_spec_structure`
- `test_no_debug_symbols_flagged`
- `test_portable_structure_is_correct`
- `test_no_system_registry_required`

ACCEPTANCE: Конфигурация упаковщика готова. Портативная структура определена. Не требуется установка. `sqlite3` и `customtkinter` включены как скрытые импорты.

STOP_CONDITIONS: Если требуется кросс-компиляция для других ОС — остановить задачу.

---

### TASK-11-03: Headless CLI точка входа для packaged-бандла

GOAL: Реализовать консольную точку входа, интегрированную с `local_entry` из исправленного EPIC-10 v1.1.

CONTEXT: Упакованное приложение должно корректно определять пути к ресурсам и работать в headless-режиме. Интеграция с `TASK-10-27` из EPIC-10 v1.1. Если `local_entry` из EPIC-10 v1.1 не доступен или имеет иной интерфейс — задача останавливается.

ALLOWED_FILES: `src/cli/packaged_entry.py`, `tests/packaging/test_packaged_entry.py`.

FORBIDDEN: Требование реального дисплея. Сетевые вызовы. Реальная LLM. Прямое изменение статусов.

IMPLEMENTATION DETAILS:

- `packaged_entry.main()` определяет, запущено ли приложение из упакованного бандла через `sys.frozen`.
- Корректирует пути к `assets`, `settings` и `workspace` относительно директории исполняемого файла.
- Поддерживает флаги `--headless`, `--workspace`, `--smoke`, `--diagnostic-token`.
- Интеграция с `local_entry.run_headless(workspace)` из EPIC-10 v1.1 (TASK-10-27).
- Все файловые операции в тестах изолированы в `tmp_path`.

TESTS:

- `test_frozen_mode_detected`
- `test_asset_paths_resolved_correctly`
- `test_headless_flag_disables_gui`
- `test_workspace_defaults_to_local_dir`
- `test_integration_with_epic10_local_entry`
- `test_diagnostic_token_flag_supported`

ACCEPTANCE: Точка входа корректно работает в packaged-режиме. Интеграция с EPIC-10 обеспечена.

STOP_CONDITIONS: Если `local_entry` из EPIC-10 не доступен — остановить задачу. Если интерфейс `run_headless` отличается от ожидаемого — остановить задачу и передать архитектору.

---

## G2 — Бандлинг ассетов и контроль целостности

### TASK-11-04: Стратегия бандлинга локальных LLM-ассетов

GOAL: Реализовать механизм верификации и подключения локальных LLM-бинарников и весов без их загрузки в тестах.

CONTEXT: Дистрибутив должен содержать или уметь локально проверять наличие LLM-компонентов.

ALLOWED_FILES: `src/packaging/llm_assets.py`, `tests/packaging/test_llm_assets.py`.

FORBIDDEN: Скачивание моделей из сети. Загрузка реальных весов в память. Использование GPU.

IMPLEMENTATION DETAILS:

- `LlmAssetManager` проверяет наличие файлов `llm_binary` и `llm_weights` в директории `assets/llm`.
- Вычисляет `sha256` файлов и сверяет с `asset_manifest.json`.
- Возвращает `AssetStatus` с признаками `present`, `missing`, `corrupted`.
- Тесты используют пустые файлы-заглушки в `tmp_path`.
- Проверка отсутствия обязательной зависимости от GPU в ассетах.

TESTS:

- `test_present_assets_verified`
- `test_missing_files_reported`
- `test_corrupted_checksum_flagged`
- `test_no_network_or_real_loading`
- `test_no_gpu_dependency_in_assets`

ACCEPTANCE: Менеджер ассетов надёжно определяет состояние. Нет попыток загрузить реальные веса.

STOP_CONDITIONS: Если требуется автоматическая загрузка моделей — остановить задачу.

---

### TASK-11-05: MCP транспорт в packaged-окружении

GOAL: Реализовать проверку корректности работы MCP транспорта `stdio` в packaged-окружении.

CONTEXT: ТЗ Раздел 5, Секция 3 определяет `stdio` как базовый транспортный слой. В EPIC-07 MCP-сервер реализован как часть основного приложения (`src/mcp/server.py`). В packaged-окружении транспорт должен работать через `stdio` между процессами основного приложения и клиентом. Конкретное имя класса/модуля транспорта определяется реализацией EPIC-07 v1.1. Если имя отличается от ожидаемого — задача останавливается до верификации.

Замечание: Если `MCP-сервер` является частью основного приложения (как реализовано в EPIC-07), отдельный бинарник не требуется. Задача проверяет корректность работы транспорта в упакованном окружении.

ALLOWED_FILES: `src/packaging/mcp_assets.py`, `tests/packaging/test_mcp_assets.py`.

FORBIDDEN: Запуск реальных внешних процессов в тестах. Сетевые транспорты. Прямое изменение FSM.

IMPLEMENTATION DETAILS:

- `McpTransportChecker` проверяет корректность работы MCP-транспорта из EPIC-07 в packaged-окружении.
- Конкретное имя класса/модуля транспорта верифицируется по реализации EPIC-07 v1.1 до начала реализации. При несовпадении — остановка задачи.
- Проверка путей к модулям `src/mcp/` внутри упакованного бандла.
- Проверка, что `stdout` зарезервирован только для JSON-RPC (интеграция с `StdoutGuard` из EPIC-07).
- Формирует `McpTransportSpec` с абсолютными путями для `stdio`-транспорта.
- Если архитектура требует отдельного процесса для MCP — формирует спецификацию запуска.
- Тесты создают фейковые модули в `tmp_path`.

TESTS:

- `test_mcp_transport_module_found`
- `test_mcp_transport_spec_contains_paths`
- `test_stdout_guard_is_configured`
- `test_missing_mcp_module_reported`
- `test_no_separate_binary_required_if_embedded`

ACCEPTANCE: MCP транспорт корректно работает в packaged-режиме. Защита `stdout` обеспечена.

STOP_CONDITIONS: Если архитектура требует отдельного бинарника для MCP — передать решение архитектору. Если фактическое имя класса транспорта в EPIC-07 отличается от ожидаемого — остановить задачу до верификации.

---

### TASK-11-06: Упаковка промптов, шаблонов и конфигураций по умолчанию

GOAL: Реализовать бандлинг текстовых ассетов и их безопасное извлечение в рабочую директорию.

CONTEXT: Приложение должно стартовать с набором дефолтных промптов и шаблонов, не требуя сети.

ALLOWED_FILES: `src/packaging/text_assets.py`, `tests/packaging/test_text_assets.py`.

FORBIDDEN: Перезапись пользовательских промптов без подтверждения. Сетевые запросы. Хранение секретов в шаблонах.

IMPLEMENTATION DETAILS:

- `TextAssetBundler` читает файлы из `assets/prompts` и `assets/templates`.
- При первом запуске копирует отсутствующие файлы в `workspace`.
- Использует атомарную запись через временные файлы.
- Поддерживает версионирование шаблонов через `schema_version`.
- Совместимость с `ResearchConfig` из ТЗ Раздел 2, Секция 8.

TESTS:

- `test_default_prompts_extracted`
- `test_existing_user_files_not_overwritten`
- `test_atomic_write_used`
- `test_schema_version_checked`
- `test_compatible_with_research_config`

ACCEPTANCE: Текстовые ассеты доступны локально. Пользовательские данные защищены. Извлечение идемпотентно.

STOP_CONDITIONS: Если требуется автоматическое обновление промптов из сети — остановить задачу.

---

### TASK-11-07: Манифест ассетов и проверка целостности

GOAL: Реализовать единый манифест всех упакованных ассетов и механизм проверки их целостности.

CONTEXT: Релизный бандл должен гарантировать, что ни один файл не был повреждён или подменён.

ALLOWED_FILES: `src/packaging/asset_manifest.py`, `tests/packaging/test_asset_manifest.py`.

FORBIDDEN: Доверие файлам без проверки хэшей. Сетевые источники хэшей.

IMPLEMENTATION DETAILS:

- `AssetManifest` содержит список путей, размеров и `sha256` для всех ассетов.
- `verify_integrity()` читает манифест и сверяет хэши локальных файлов.
- Возвращает `IntegrityReport` с `ok`, `missing`, `mismatched`.
- Манифест подписывается локальным ключом сборки (заглушка для тестов).

TESTS:

- `test_manifest_contains_all_assets`
- `test_integrity_check_passes_for_valid_files`
- `test_mismatched_hash_reported`
- `test_missing_file_reported`

ACCEPTANCE: Целостность бандла подтверждается локально. Отчёт детерминирован.

STOP_CONDITIONS: Если требуется криптографическая подпись с внешним CA — остановить задачу.

---

## G3 — First-run опыт и локальная инициализация

### TASK-11-08: Детектор первого запуска и инициализация рабочей директории

GOAL: Реализовать определение первого запуска, автоматическое создание рабочей директории и проектной структуры БД.

CONTEXT: Packaged-приложение должно само настраивать локальное окружение. ТЗ Раздел 3, Секция 25 определяет структуру: `data/projects/{project_id}.db`, `registry.db`. Зависимость от `bootstrap_workspace()` из EPIC-09 v1.1 (TASK-09-02). Если функция недоступна или имеет иной интерфейс — задача останавливается.

ALLOWED_FILES: `src/packaging/first_run.py`, `tests/packaging/test_first_run.py`.

FORBIDDEN: Требование реального дисплея. Сетевые вызовы. Удаление существующих данных. Прямое изменение статусов.

IMPLEMENTATION DETAILS:

- `FirstRunDetector` проверяет наличие `.initialized` маркера в `workspace`.
- При отсутствии маркера вызывает `bootstrap_workspace()` из EPIC-09 v1.1 (TASK-09-02).
- Создаёт дефолтные настройки и извлекает текстовые ассеты.
- Вызывает `DbBootstrap` (TASK-11-18) для создания проектной структуры БД.
- Пишет `first_run_report.json` в `tmp_path` для тестов.

TESTS:

- `test_first_run_detected`
- `test_workspace_bootstrapped`
- `test_marker_created_after_init`
- `test_subsequent_runs_skip_init`
- `test_db_bootstrap_called`

ACCEPTANCE: Первый запуск проходит автономно. Рабочая директория и БД готовы. Повторные запуски не выполняют инициализацию.

STOP_CONDITIONS: Если `bootstrap_workspace()` из EPIC-09 не доступен — остановить задачу. Если интерфейс `bootstrap_workspace()` отличается от ожидаемого — остановить задачу и передать архитектору.

---

### TASK-11-09: Проверка оборудования и диагностика отсутствующих компонентов

GOAL: Реализовать диагностику оборудования и отсутствующих компонентов с понятным отчётом для пользователя.

CONTEXT: Gate G-11 требует: «приложение... выдаёт понятную диагностику отсутствующих компонентов». ТЗ Раздел 6, Секция 10 определяет метрики `System Health Monitor`.

ALLOWED_FILES: `src/packaging/hardware_check.py`, `src/packaging/missing_components.py`, `tests/packaging/test_hardware_check.py`.

FORBIDDEN: GPU-метрики. Стресс-тесты. Прямое изменение статусов. Внешние API.

IMPLEMENTATION DETAILS:

- `HardwareChecker` собирает `cpu_count`, `available_ram_mb`, `free_disk_mb`.
- Сравнивает с минимальными требованиями из `build_env.spec`.
- `MissingComponentsDiagnostic` проверяет наличие всех критических компонентов:
    - Проектная БД (`data/projects/`)
    - Реестр (`registry.db`)
    - Конфигурация (`settings/`)
    - Ассеты (`assets/`)
    - Шаблоны и промпты
    - Модули `src/mcp/`, `src/core/`
- Формирует понятный отчёт для пользователя с рекомендациями по исправлению.
- Возвращает `HardwareReport` с `meets_requirements`, `warnings`, `missing_components`.
- Тесты используют инжектируемые фейковые значения ресурсов.

TESTS:

- `test_sufficient_resources_pass`
- `test_low_ram_flagged`
- `test_low_disk_space_flagged`
- `test_fake_resources_used_in_tests`
- `test_missing_components_reported_clearly`
- `test_recommendations_for_missing_components`

ACCEPTANCE: Диагностика выполняется быстро. Отчёт понятен для пользователя. Требования Gate G-11 по диагностике выполнены.

STOP_CONDITIONS: Если требуется проверка сетевой пропускной способности — остановить задачу.

---

### TASK-11-10: Извлечение и верификация упакованных ассетов

GOAL: Реализовать безопасное извлечение ассетов из packaged-бандла в рабочую директорию.

CONTEXT: Ассеты могут быть упакованы внутри исполняемого файла или архива и требуют распаковки.

ALLOWED_FILES: `src/packaging/asset_extractor.py`, `tests/packaging/test_asset_extractor.py`.

FORBIDDEN: Извлечение файлов вне `workspace`. Перезапись файлов без проверки версий. Сетевые источники.

IMPLEMENTATION DETAILS:

- `AssetExtractor` читает ресурсы через `importlib.resources` или `sys._MEIPASS`.
- Сверяет версии ассетов с `asset_manifest.json`.
- Извлекает только отсутствующие или устаревшие файлы.
- Использует атомарную запись и проверяет `sha256` после извлечения.

TESTS:

- `test_assets_extracted_to_workspace`
- `test_outdated_assets_updated`
- `test_extraction_outside_workspace_blocked`
- `test_post_extraction_checksum_verified`

ACCEPTANCE: Ассеты доступны в `workspace`. Извлечение безопасно и идемпотентно.

STOP_CONDITIONS: Если требуется распаковка больших архивов в фоне — остановить задачу.

---

### TASK-11-11: Процедуры очистки и локального удаления

GOAL: Реализовать безопасное удаление рабочей директории и кэша packaged-приложения.

CONTEXT: Пользователь должен иметь возможность полностью удалить локальные данные приложения.

ALLOWED_FILES: `src/packaging/cleanup.py`, `tests/packaging/test_cleanup.py`.

FORBIDDEN: Удаление файлов вне `workspace` и кэша. Сетевые вызовы. Требование прав администратора.

IMPLEMENTATION DETAILS:

- `CleanupManager.remove_workspace()` удаляет директорию `workspace` с проверкой пути.
- `CleanupManager.clear_cache()` удаляет временные файлы и логи.
- Запрещает удаление, если путь совпадает с системными директориями.
- Возвращает `CleanupReport` с `deleted_bytes` и `errors`.

TESTS:

- `test_workspace_removed`
- `test_cache_cleared`
- `test_system_paths_protected`
- `test_report_contains_deleted_bytes`

ACCEPTANCE: Удаление безопасно и ограничено разрешёнными путями. Отчёт детерминирован.

STOP_CONDITIONS: Если требуется удаление записей реестра — остановить задачу.

---

## G4 — Оффлайн-валидация, изоляция и целевая среда

### TASK-11-12: Изолированный smoke-тест packaged-бандла

GOAL: Выполнить сквозной сценарий на упакованном бандле в изолированной временной директории.

CONTEXT: Packaged-приложение должно работать идентично исходному коду, но в автономном режиме. Зависимость от `run_happy_smoke()` из EPIC-09 v1.1 (TASK-09-17). Если функция недоступна — задача останавливается.

ALLOWED_FILES: `src/packaging/smoke_test.py`, `tests/packaging/test_packaged_smoke.py`.

FORBIDDEN: Реальная LLM. Сетевые запросы. Прямое изменение статусов. Реальный дисплей.

IMPLEMENTATION DETAILS:

- `run_packaged_smoke()` имитирует запуск исполняемого файла в `tmp_path`.
- Выполняет `first_run`, `config_load`, `start_research`, `finish_smoke`.
- Проверяет наличие всех артефактов и логов.
- Проверяет доступность модуля `sqlite3` в packaged-окружении.
- Проверяет доступность `customtkinter` в packaged-окружении.
- Формирует `packaged_smoke_report.json`.
- Интеграция с `run_happy_smoke()` из EPIC-09 v1.1 (TASK-09-17).

TESTS:

- `test_smoke_reaches_done_state`
- `test_artifacts_created_in_workspace`
- `test_no_external_dependencies_used`
- `test_report_written_to_tmp_path`
- `test_integration_with_epic09_smoke`
- `test_sqlite3_module_available_in_packaged_mode`
- `test_customtkinter_module_available_in_packaged_mode`

ACCEPTANCE: Packaged-бандл проходит базовый сценарий. Все компоненты связаны. Нет обращений к внешним ресурсам. `sqlite3` и `customtkinter` доступны.

STOP_CONDITIONS: Если требуется запуск реального GUI — остановить задачу. Если `run_happy_smoke()` из EPIC-09 не доступен — остановить задачу.

---

### TASK-11-13: Строгая проверка сетевой изоляции

GOAL: Верифицировать, что packaged-приложение не инициирует исходящие сетевые соединения.

CONTEXT: MVP обязан работать полностью оффлайн. ТЗ Раздел 2, Секция 1: «без передачи конфиденциальных данных на внешние сервера».

ALLOWED_FILES: `src/packaging/network_isolation.py`, `tests/packaging/test_network_isolation.py`.

FORBIDDEN: Реальные сетевые вызовы. Отключение сетевых интерфейсов ОС. Прямое изменение статусов.

IMPLEMENTATION DETAILS:

- `NetworkIsolationChecker` патчит `socket.socket` и `urllib.request` в тестовом окружении.
- Запускает smoke-сценарий и фиксирует любые попытки сетевых вызовов.
- Возвращает `IsolationReport` с `violations` и `attempted_hosts`.
- Тесты используют `tmp_path` и фейковые сокеты.

TESTS:

- `test_no_outbound_connections_attempted`
- `test_socket_creation_blocked`
- `test_urllib_requests_blocked`
- `test_report_written_to_tmp_path`

ACCEPTANCE: Сетевая изоляция подтверждена. Нет скрытых телеметрий или обновлений.

STOP_CONDITIONS: Если требуется проверка на уровне ОС — остановить задачу.

---

### TASK-11-14: Тест исполнения LLM-заглушки внутри packaged-бандла

GOAL: Проверить, что локальная LLM-заглушка корректно работает в packaged-окружении.

CONTEXT: Packaged-приложение должно использовать встроенные ассеты без сбоев путей. Интеграция с `LLMBackend` из исправленного EPIC-06 v1.1 (TASK-06-01). Если интерфейс `LLMBackend` недоступен или отличается — задача останавливается.

ALLOWED_FILES: `src/packaging/llm_smoke.py`, `tests/packaging/test_packaged_llm.py`.

FORBIDDEN: Загрузка реальных моделей. Сетевые вызовы. GPU. Прямое изменение статусов.

IMPLEMENTATION DETAILS:

- `run_llm_packaged_smoke()` инициализирует `LocalStubLLM` из packaged-ассетов.
- Заглушка реализует интерфейс `LLMBackend` из исправленного EPIC-06 v1.1 (TASK-06-01).
- Выполняет серию детерминированных запросов.
- Проверяет, что ответы совпадают с ожидаемыми хэшами.
- Формирует `llm_smoke_report.json` в `tmp_path`.

TESTS:

- `test_stub_initializes_from_assets`
- `test_responses_are_deterministic`
- `test_no_network_or_real_model_used`
- `test_report_written_to_tmp_path`
- `test_stub_implements_llm_backend_interface`

ACCEPTANCE: LLM-заглушка работает в packaged-режиме. Пути к ассетам резолвятся. Интерфейс `LLMBackend` соблюдён.

STOP_CONDITIONS: Если `LLMBackend` из исправленного EPIC-06 не доступен — остановить задачу. Если интерфейс `LLMBackend` отличается от ожидаемого — остановить задачу и передать архитектору.

---

### TASK-11-15: Тест stdio-коммуникации в packaged-окружении

GOAL: Проверить, что транспорт `stdio` корректно работает в packaged-окружении.

CONTEXT: MCP транспорт из исправленного EPIC-07 v1.1 должен быть доступен для оркестратора из packaged-бандла. В исправленном EPIC-07 v1.1 MCP является частью основного приложения. Зависимость от `StdoutGuard` из EPIC-07 v1.1 (TASK-07-02). Если компонент недоступен — задача останавливается.

Замечание: Если архитектура не требует отдельного процесса для MCP, задача проверяет корректность работы встроенного транспорта через `subprocess` или прямые вызовы.

ALLOWED_FILES: `src/packaging/mcp_smoke.py`, `tests/packaging/test_packaged_mcp.py`.

FORBIDDEN: Запуск реальных внешних серверов. Сетевые транспорты. Прямое изменение FSM.

IMPLEMENTATION DETAILS:

- `run_mcp_packaged_smoke()` запускает транспорт `stdio` через `subprocess.Popen` или прямые вызовы.
- Отправляет детерминированные JSON-RPC запросы.
- Проверяет корректность ответов и таймауты.
- Проверяет защиту `stdout` (интеграция с `StdoutGuard` из EPIC-07).
- Формирует `mcp_smoke_report.json` в `tmp_path`.

TESTS:

- `test_stdio_communication_works`
- `test_responses_are_valid_json`
- `test_timeouts_are_handled`
- `test_report_written_to_tmp_path`
- `test_stdout_protection_maintained`

ACCEPTANCE: Транспорт `stdio` работает стабильно. Защита `stdout` обеспечена. Нет зависаний.

STOP_CONDITIONS: Если требуется тестирование реальных внешних серверов — остановить задачу. Если `StdoutGuard` из EPIC-07 не доступен — остановить задачу.

---

### TASK-11-16: Проверка запуска на целевой Windows-среде без IDE

GOAL: Реализовать сценарий проверки запуска на целевой Windows-среде без IDE и формировать понятный отчёт.

CONTEXT: Gate G-11 требует: «приложение запускается на целевой Windows-среде без IDE». Это ключевое требование приёмки.

ALLOWED_FILES: `src/packaging/target_env_test.py`, `tests/packaging/test_target_environment.py`.

FORBIDDEN: Требование IDE. Сетевые вызовы. Реальная LLM. GPU.

IMPLEMENTATION DETAILS:

- `TargetEnvironmentTest` описывает сценарий запуска на целевой среде:
    - Распаковка портативной папки.
    - Запуск исполняемого файла без IDE.
    - Проверка инициализации рабочей директории.
    - Проверка наличия всех компонентов.
    - Выполнение базового сценария (`smoke`).
    - Формирование отчёта.
- Отчёт содержит:
    - `launched_without_ide: bool`
    - `all_components_present: bool`
    - `smoke_passed: bool`
    - `missing_components: list[str]`
    - `diagnostics: str`
- Если компонент отсутствует — формировать понятную диагностику (см. TASK-11-09).
- Тесты описывают сценарий, но не выполняют реальный запуск (это делается вручную при приёмке).

TESTS:

- `test_target_env_scenario_is_complete`
- `test_report_structure_is_valid`
- `test_missing_components_generate_diagnostics`
- `test_no_ide_requirement`

ACCEPTANCE: Сценарий проверки целевой среды определён. Отчёт структурирован. Диагностика понятна.

STOP_CONDITIONS: Если целевая среда отличается от спецификации — передать решение архитектору.

---

### TASK-11-17: Проверка отсутствия скрытых зависимостей от GPU, embeddings, vector DB

GOAL: Реализовать автоматическую проверку отсутствия скрытых обязательных зависимостей от `embeddings`, `vector search`, `vector DB` или `GPU`.

CONTEXT: Roadmap Раздел 14: «В MVP не допускаются скрытые обязательные зависимости от `embeddings`, `vector search`, `vector DB` или `GPU`».

ALLOWED_FILES: `src/packaging/hidden_deps_check.py`, `tests/packaging/test_hidden_deps.py`.

FORBIDDEN: Реальная загрузка библиотек. Сетевые вызовы.

IMPLEMENTATION DETAILS:

- `HiddenDependenciesChecker` сканирует `requirements.lock` на наличие запрещённых зависимостей.
- Список запрещённых:
    - GPU: `torch`, `tensorflow`, `jax`, `cuda`, `cudnn`
    - Vector DB: `faiss`, `chromadb`, `qdrant`, `milvus`, `pinecone`
    - Embeddings: `sentence-transformers`, `openai`, `cohere`
    - Любые библиотеки, требующие GPU по умолчанию
- Сканирует импорты в `src/` на наличие запрещённых модулей.
- Формирует `HiddenDepsReport` с `found`, `clean`.
- Блокировка сборки при обнаружении запрещённых зависимостей.

TESTS:

- `test_clean_dependencies_pass`
- `test_gpu_dependency_detected`
- `test_vector_db_dependency_detected`
- `test_embeddings_dependency_detected`
- `test_build_blocked_on_hidden_dependency`

ACCEPTANCE: Скрытые зависимости обнаруживаются. Сборка блокируется при нарушении.

STOP_CONDITIONS: Если обнаружена скрытая зависимость в коде — остановить задачу и передать архитектору.

---

## G5 — Релизные артефакты и эксплуатация

### TASK-11-18: Обработка локальной БД при первом запуске

GOAL: Реализовать создание проектной БД, применение миграций и проверку целостности при первом запуске.

CONTEXT: ТЗ Раздел 3, Секция 25 определяет проектную структуру. ТЗ Раздел 3, Секция 24 определяет правила работы с SQLite. ТЗ Раздел 3, Секция 26 определяет `PRAGMA` настройки. Зависимость от миграций из исправленного EPIC-02 v1.1. Если миграции недоступны — задача останавливается.

ALLOWED_FILES: `src/packaging/db_bootstrap.py`, `tests/packaging/test_db_bootstrap.py`.

FORBIDDEN: Прямая запись в обход `DB-write layer`. Изменение доменной схемы. Сетевые вызовы.

IMPLEMENTATION DETAILS:

- `DbBootstrap` выполняет:
    - Создание `registry.db` с таблицами `ProjectRegistry`, `GlobalDocumentIndex`, `GlobalSourceIndex` (ТЗ Раздел 3, Секция 25).
    - Создание каталога `data/projects/`.
    - Создание дефолтной проектной БД `data/projects/{project_id}.db`.
    - Применение миграций из исправленного EPIC-02 v1.1.
    - Применение `PRAGMA` настроек через фабрику подключений (ТЗ Раздел 3, Секция 26):
        - `journal_mode=WAL`
        - `synchronous=NORMAL`
        - `foreign_keys=ON`
        - `busy_timeout=5000`
        - `journal_size_limit=67108864`
        - `wal_autocheckpoint=1000`
    - Проверка целостности (`PRAGMA integrity_check`).
    - Создание контрольной точки (`PRAGMA wal_checkpoint(PASSIVE)`).
- Все операции атомарны и идемпотентны.
- При повторном запуске: проверка существующей БД, применение недостающих миграций.

TESTS:

- `test_registry_db_created_with_tables`
- `test_project_db_created`
- `test_pragma_settings_applied`
- `test_integrity_check_passes`
- `test_migrations_applied`
- `test_bootstrap_is_idempotent`
- `test_wal_checkpoint_created`

ACCEPTANCE: Проектная БД создаётся корректно. `PRAGMA` настройки применены. Миграции применены. Целостность подтверждена.

STOP_CONDITIONS: Если миграции из исправленного EPIC-02 не доступны — остановить задачу. Если интерфейс миграций отличается от ожидаемого — остановить задачу и передать архитектору.

---

### TASK-11-19: Диагностика зависимостей

GOAL: Реализовать проверку наличия всех обязательных библиотек, их версий и отсутствие конфликтов.

CONTEXT: Roadmap Раздел 14 включает «dependency diagnostics». Приложение должно выдавать понятную диагностику при отсутствии компонентов. Интеграция с `MissingComponentsDiagnostic` из TASK-11-09.

ALLOWED_FILES: `src/packaging/dependency_diagnostic.py`, `tests/packaging/test_dependency_diagnostic.py`.

FORBIDDEN: Скачивание библиотек. Сетевые вызовы. Реальная загрузка модулей.

IMPLEMENTATION DETAILS:

- `DependencyDiagnostic` проверяет:
    - Наличие всех модулей из `requirements.lock`.
    - Версии установленных модулей.
    - Совместимость версий.
    - Отсутствие конфликтов.
    - Доступность `sqlite3` как встроенного модуля.
- Формирует `DependencyReport`:
    - `available: list[str]` — найденные модули
    - `missing: list[str]` — отсутствующие модули
    - `version_mismatch: list[dict]` — несовпадения версий
    - `recommendations: list[str]` — рекомендации по исправлению
- Понятная диагностика для пользователя.
- Интеграция с `MissingComponentsDiagnostic` из TASK-11-09.
- Тесты используют фейковые результаты импортов.

TESTS:

- `test_all_dependencies_found`
- `test_missing_dependency_reported`
- `test_version_mismatch_reported`
- `test_recommendations_generated`
- `test_fake_imports_used_in_tests`
- `test_sqlite3_availability_checked`

ACCEPTANCE: Диагностика зависимостей работает. Отчёт понятен для пользователя. `sqlite3` проверен.

STOP_CONDITIONS: Если требуется проверка системных библиотек ОС — остановить задачу.

---

### TASK-11-20: Администраторский диагностический токен

GOAL: Реализовать механизм администраторского диагностического токена для доступа к расширенной диагностике.

CONTEXT: Roadmap Раздел 14 включает «administrator diagnostic token». Механизм позволяет получить расширенную диагностику без риска для обычных пользователей.

ALLOWED_FILES: `src/packaging/diagnostic_token.py`, `tests/packaging/test_diagnostic_token.py`.

FORBIDDEN: Сетевые вызовы. Хранение токена в открытом виде. Передача токена в сеть.

IMPLEMENTATION DETAILS:

- `DiagnosticTokenManager` генерирует локальный диагностический токен.
- Токен хранится локально в файле с ограниченными правами доступа.
- Использование токена для доступа к расширенной диагностике:
    - Детальные логи
    - Внутреннее состояние компонентов
    - Расширенные метрики производительности
- Токен не передаётся в сеть.
- Токен не логируется в открытом виде.
- Срок действия токена ограничен (по умолчанию 24 часа).
- Тесты используют фейковые токены в `tmp_path`.

TESTS:

- `test_token_generated_locally`
- `test_token_not_logged`
- `test_token_not_sent_to_network`
- `test_token_expires_after_24_hours`
- `test_extended_diagnostics_requires_valid_token`

ACCEPTANCE: Токен генерируется локально. Безопасность обеспечена. Расширенная диагностика доступна.

STOP_CONDITIONS: Если требуется интеграция с внешней системой аутентификации — остановить задачу.

---

### TASK-11-21: Настройка логирования в packaged-приложении

GOAL: Реализовать настройку логирования для packaged-приложения с защитой `stdout` для MCP.

CONTEXT: ТЗ Раздел 5, Секция 3.1 определяет защиту `stdout`. Логи должны идти в файл, а не в `stdout`. Интеграция с `StdoutGuard` из исправленного EPIC-07 v1.1 (TASK-07-02) и `LogGuard` из исправленного EPIC-10 v1.1. Если хотя бы один из компонентов недоступен — задача останавливается.

ALLOWED_FILES: `src/packaging/logging_config.py`, `tests/packaging/test_logging_config.py`.

FORBIDDEN: Вывод логов в `stdout`. Сетевые вызовы. Хранение секретов в логах.

IMPLEMENTATION DETAILS:

- `LoggingConfigurator` настраивает все логгеры:
    - Все пишут в файл `logs/app.log`.
    - Ни один логгер не выводит в `stdout`.
- Ротация логов: максимальный размер 10 MiB, 5 файлов ротации.
- Интеграция с `StdoutGuard` из исправленного EPIC-07 v1.1 (TASK-07-02).
- Уровни логирования конфигурируются через `ResearchConfig`.
- Маскировка чувствительных данных (интеграция с `LogGuard` из исправленного EPIC-10 v1.1).
- Ранний редирект логгеров: настройка до инициализации любых модулей.

TESTS:

- `test_all_loggers_write_to_file`
- `test_no_logger_writes_to_stdout`
- `test_log_rotation_configured`
- `test_stdout_guard_integration`
- `test_sensitive_data_masked`
- `test_early_redirect_before_modules`

ACCEPTANCE: Все логи идут в файл. `stdout` защищён. Ротация работает. Маскировка обеспечена.

STOP_CONDITIONS: Если `StdoutGuard` из исправленного EPIC-07 не доступен — остановить задачу. Если `LogGuard` из исправленного EPIC-10 не доступен — остановить задачу. Если интерфейс хотя бы одного из компонентов отличается от ожидаемого — остановить задачу и передать архитектору.

---

### TASK-11-22: Инструкции резервного копирования и восстановления

GOAL: Создать инструкции по резервному копированию и восстановлению данных приложения.

CONTEXT: Roadmap Раздел 14 включает «backup/recovery instructions». ТЗ Раздел 3, Секция 24 определяет WAL-safe snapshot. Зависимость от `SettingsGuard` из исправленного EPIC-10 v1.1 (TASK-10-07). Если компонент недоступен — задача останавливается.

ALLOWED_FILES: `src/packaging/backup_instructions.py`, `docs/backup_recovery.md`, `tests/packaging/test_backup_instructions.py`.

FORBIDDEN: Прямое копирование `.db` во время активной WAL-операции. Сетевые вызовы.

IMPLEMENTATION DETAILS:

- Создание документа `docs/backup_recovery.md` с инструкциями:
    - Что копировать: проектные БД, реестр, настройки, ассеты.
    - Как копировать: через `PRAGMA wal_checkpoint(PASSIVE)` перед копированием.
    - Как восстановить: замена файлов, проверка целостности.
    - Периодичность: рекомендации по регулярному резервному копированию.
- `BackupInstructionsValidator` проверяет наличие обязательных разделов.
- Интеграция с `SettingsGuard` из исправленного EPIC-10 v1.1 (TASK-10-07).
- Проверка, что инструкции покрывают все критические данные.

TESTS:

- `test_backup_instructions_contain_required_sections`
- `test_wal_checkpoint_mentioned`
- `test_recovery_steps_present`
- `test_all_critical_data_covered`

ACCEPTANCE: Инструкции полны и покрывают все критические данные. `PRAGMA wal_checkpoint` упомянут.

STOP_CONDITIONS: Если требуется автоматическое резервное копирование — остановить задачу (это отдельная функциональность). Если `SettingsGuard` из исправленного EPIC-10 не доступен — остановить задачу.

---

### TASK-11-23: Релизный архив и структура дистрибутива

GOAL: Реализовать упаковку всех компонентов в единый релизный архив с портативной структурой.

CONTEXT: Дистрибутив должен быть готов к распространению через локальные носители.

ALLOWED_FILES: `src/packaging/release_archive.py`, `tests/packaging/test_release_archive.py`.

FORBIDDEN: Отладочные файлы. Сетевые хранилища. Права администратора.

IMPLEMENTATION DETAILS:

- `ReleaseArchiver.create()` формирует архив с портативной структурой из TASK-11-02.
- Исключаются `.git`, `tests`, `__pycache__`, `.pyc`.
- Тесты проверяют содержимое архива в `tmp_path`.

TESTS:

- `test_archive_created`
- `test_structure_is_correct`
- `test_debug_files_excluded`
- `test_archive_extractable`

ACCEPTANCE: Архив содержит все компоненты. Структура портативна. Распаковка корректна.

STOP_CONDITIONS: Если требуется создание инсталлятора — остановить задачу.

---

### TASK-11-24: Контрольные суммы и релизный манифест

GOAL: Реализовать создание контрольных сумм и манифеста релиза для верификации.

CONTEXT: Пользователь должен иметь возможность проверить целостность дистрибутива.

ALLOWED_FILES: `src/packaging/release_manifest.py`, `tests/packaging/test_release_manifest.py`.

FORBIDDEN: Сетевые источники хэшей. Невыпущенные компоненты.

IMPLEMENTATION DETAILS:

- `ReleaseManifestGenerator` вычисляет `sha256` для архива и ключевых файлов.
- Формирует `release_manifest.json` с `version`, `build_date`, `checksums`.
- Атомарная запись манифеста.
- Тесты используют `tmp_path`.

TESTS:

- `test_manifest_created`
- `test_checksums_are_correct`
- `test_version_matches_spec`
- `test_manifest_written_to_tmp_path`

ACCEPTANCE: Манифест релиза готов. Контрольные суммы верны. Файл пригоден для локальной верификации.

STOP_CONDITIONS: Если требуется криптографическая подпись — остановить задачу.

---

## Gate G-11 Acceptance Criteria

- Запуск без IDE: Приложение запускается на целевой Windows-среде без IDE.
- Диагностика отсутствующих компонентов: Приложение выдаёт понятную диагностику при отсутствии компонентов.
- Портативная структура: Приложение работает как портативная папка без установки в реестр.
- Обработка локальной БД: Проектная БД создаётся, миграции применяются, целостность проверяется.
- Диагностика зависимостей: Все обязательные библиотеки проверены, конфликты выявлены.
- Администраторский диагностический токен: Расширенная диагностика доступна через токен.
- Проверки при запуске: `first_run`, проверка оборудования, проверка компонентов.
- Логирование: Логи идут в файл, `stdout` защищён для MCP.
- Инструкции резервного копирования: Полные инструкции по backup/recovery.
- Сетевая изоляция: Приложение не инициирует исходящие сетевые соединения.
- Нет скрытых зависимостей: Нет обязательных зависимостей от `embeddings`, `vector search`, `vector DB` или `GPU`.
- CPU-only: Все проверки работают на CPU без обязательной зависимости от GPU.
- Нет реальных сетевых вызовов в тестах.
- Нет реальной LLM в тестах.
- Нет прямого изменения `.status` в тестах.

Статус EPIC-11: Готов к передаче в разработку.