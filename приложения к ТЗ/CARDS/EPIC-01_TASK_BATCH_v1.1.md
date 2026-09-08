# EPIC-01 FOUNDATION — TASK BATCH v1.1 CORRECTED

Проект: Research Prompt Suite
Статус: Corrected for CODE Agent Execution
Основание: ТЗ v2.4, MASTER ROADMAP v1.2, EPIC SPECIFICATIONS v1.0, EPIC → TASK DECOMPOSITION v1.0, STATE MACHINE SPECIFICATION v1.1, MCP TOOL CONTRACTS v1.1

## 0. Глобальные правила

- Одна задача даёт один проверяемый результат.
- Каждая задача содержит 8 обязательных секций: `GOAL`, `CONTEXT`, `ALLOWED_FILES`, `FORBIDDEN`, `IMPLEMENTATION DETAILS`, `TESTS`, `ACCEPTANCE`, `STOP_CONDITIONS`.
- Python 3.11+.
- Production-код EPIC-01 не использует внешние зависимости.
- Тесты используют только `stdlib` и `pytest`.
- Изоляция тестов выполняется через `tmp_path`.
- Запрещены: бизнес-логика, SQLite, сетевые запросы, LLM, MCP, GUI, прямое изменение статусов, обход будущих FSM.
- Запрещено расширять `ALLOWED_FILES`.
- При любой неясности, конфликте документов или выходе за рамки задачи: `STOP → REPORT → WAIT`.

## 1. Принятые исправления

- Удалён `pydantic`, чтобы тесты соответствовали правилу `stdlib + pytest`.
- Конфигурация приложения переименована в `AppConfig`, чтобы не конфликтовать с сущностью `ResearchConfig` уровня Study из ТЗ.
- Удалён преждевременный `db_path = "data/research.db"`.
- Ошибка `EnvironmentError` переименована в `EnvironmentSetupError`, чтобы не конфликтовать со встроенным именем.
- Убрана глобальная небезопасная подмена `sys.stdout` без восстановления.
- Добавлена фикстура `mcp_safe_stdio` с восстановлением состояния.
- Добавлена автоматическая проверка `print()` и `sys.stdout.write` в `src/`.
- Добавлена трассировка к `EPIC → TASK DECOMPOSITION v1.0`.
- Добавлены явные тесты границ пакетов, изоляции окружения и независимости от среды.
- Все задачи получили секцию `STOP_CONDITIONS`.

## 2. Трассировка относительно `EPIC → TASK DECOMPOSITION v1.0`

| Исходный атомарный результат | Фактическая задача батча | Комментарий |
|---|---|---|
| `E01-T01` | `E01-T01-PACKAGE-SKELETON` | Создание базовой структуры пакетов |
| `E01-T02` | `E01-T02-PACKAGE-BOUNDARIES` | Определение границ пакетов и тест запретов |
| `E01-T03` | `E01-T03-ENTRYPOINT` | Минимальный входной точки |
| `E01-T04` | `E01-T04-CONFIG-MODEL-AND-LOADER` | Модель и загрузчик конфигурации |
| `E01-T05` | `E01-T05-UNIFIED-IDENTIFIERS` | Унифицированные идентификаторы |
| `E01-T06` | `E01-T06-TIME-UTILITIES` | Утилиты времени |
| `E01-T07` | `E01-T07-ERROR-MODEL` | Унифицированные ошибки |
| `E01-T08` | `E01-T08-LOGGING-SUBSYSTEM` | Логгирование в файл и `stderr` |
| `E01-T09` | `E01-T09-ENV-ABSTRACTION` | Абстракция временного окружения |
| `E01-T10` | `E01-T10-PYTEST-CONFIGURATION` | Конфигурация `pytest` |
| `E01-T11` | `E01-T11-ISOLATED-ENV-FIXTURE` | Изолированное временное окружение |
| `E01-T12` | `E01-T12-ENV-INDEPENDENCE-TESTS` | Независимость от среды разработчика |
| `E01-T13` | `E01-T13-STDIO-ISOLATION-FIXTURE` | Фикстура защиты `stdout` |
| `E01-T14` | `E01-T14-FOUNDATION-INTEGRATION` | Интеграционный тест Foundation |
| Дополнительный TEST | `E01-T15-STDOUT-POLICY-ENFORCEMENT` | Добавлен по разделу 16 декомпозиции для автоматической проверки `stdout` policy |

## 3. Рекомендуемый порядок выполнения

- `E01-T01-PACKAGE-SKELETON`
- `E01-T02-PACKAGE-BOUNDARIES`
- `E01-T03-ENTRYPOINT`
- `E01-T07-ERROR-MODEL`
- `E01-T04-CONFIG-MODEL-AND-LOADER`
- `E01-T05-UNIFIED-IDENTIFIERS`
- `E01-T06-TIME-UTILITIES`
- `E01-T09-ENV-ABSTRACTION`
- `E01-T08-LOGGING-SUBSYSTEM`
- `E01-T10-PYTEST-CONFIGURATION`
- `E01-T11-ISOLATED-ENV-FIXTURE`
- `E01-T13-STDIO-ISOLATION-FIXTURE`
- `E01-T15-STDOUT-POLICY-ENFORCEMENT`
- `E01-T12-ENV-INDEPENDENCE-TESTS`
- `E01-T14-FOUNDATION-INTEGRATION`

---

## TASK: E01-T01-PACKAGE-SKELETON

- GOAL: Создать базовую структуру пакетов проекта и минимальный `pyproject.toml` без внешних зависимостей.
- CONTEXT: Это чистый каркас проекта. Никакой бизнес-логики, конфигурации, логгирования или точек входа в этой задаче не создаётся. Создаются только пакеты и метаданные проекта.
- ALLOWED_FILES:
  - `src/__init__.py`
  - `src/core/__init__.py`
  - `src/data/__init__.py`
  - `src/search/__init__.py`
  - `src/llm/__init__.py`
  - `src/mcp/__init__.py`
  - `src/gui/__init__.py`
  - `pyproject.toml`
  - `tests/test_package_skeleton.py`
- FORBIDDEN:
  - Любая бизнес-логика.
  - Создание `main.py`.
  - Создание конфигурационных модулей.
  - Добавление внешних зависимостей.
  - Создание файлов БД.
  - Изменение других пакетов сверх списка.
- IMPLEMENTATION DETAILS:

    Создай пустые файлы `__init__.py` во всех указанных пакетах.

    Содержимое `pyproject.toml`:

    [project]
    name = "research-prompt-suite"
    version = "0.1.0"
    requires-python = ">=3.11"
    dependencies = []

- TESTS:

    Файл `tests/test_package_skeleton.py`:

    import importlib
    from pathlib import Path

    PACKAGES = (
        "src",
        "src.core",
        "src.data",
        "src.search",
        "src.llm",
        "src.mcp",
        "src.gui",
    )

    ROOT = Path(__file__).resolve().parents[1]

    def test_packages_importable():
        for name in PACKAGES:
            importlib.import_module(name)

    def test_init_files_exist():
        expected = [
            ROOT / "src" / "__init__.py",
            ROOT / "src" / "core" / "__init__.py",
            ROOT / "src" / "data" / "__init__.py",
            ROOT / "src" / "search" / "__init__.py",
            ROOT / "src" / "llm" / "__init__.py",
            ROOT / "src" / "mcp" / "__init__.py",
            ROOT / "src" / "gui" / "__init__.py",
        ]
        for path in expected:
            assert path.exists()

- ACCEPTANCE: Команда `pytest tests/test_package_skeleton.py` проходит. Все пакеты импортируются. Внешние зависимости не добавлены.
- STOP_CONDITIONS:
  - Если уже существует конфликтующий `pyproject.toml`, который нельзя безопасно дополнить.
  - Если требуется добавить внешнюю зависимость.
  - Если структура репозитория не позволяет создать `src/`.

---

## TASK: E01-T02-PACKAGE-BOUNDARIES

- GOAL: Зафиксировать границы пакетов и добавить автоматический тест, запрещающий недопустимые импорты между пакетами.
- CONTEXT: Для прохождения Gate G-01 недостаточно создать пустые пакеты. Нужно определить минимальные архитектурные границы и проверять их тестом.
- ALLOWED_FILES:
  - `src/ARCHITECTURE_BOUNDARIES.md`
  - `tests/test_package_boundaries.py`
- FORBIDDEN:
  - Изменение кода внутри пакетов.
  - Создание новой бизнес-логики.
  - Изменение `pyproject.toml`.
  - Введение внешних зависимостей.
- IMPLEMENTATION DETAILS:

    В `src/ARCHITECTURE_BOUNDARIES.md` зафиксируй правила:

    - `src/core` не импортирует `src/gui`, `src/mcp`, `src/search`, `src/llm`, `src/data`.
    - `src/data` не импортирует `src/gui`, `src/mcp`, `src/search`, `src/llm`.
    - `src/search` не импортирует `src/gui`, `src/mcp`.
    - `src/llm` не импортирует `src/gui`, `src/search`, `src/data`.
    - `src/mcp` не импортирует `src/gui`, `src/search`, `src/llm`, `src/data`.
    - `src/gui` не импортирует `src/search`, `src/llm`, `src/data`, `src/mcp`.

    Тест сканирует `.py` файлы внутри `src/` через `ast` и падает при нарушении правил.

    Минимальная структура правил в тесте:

    RULES = {
        "src.core": {"src.gui", "src.mcp", "src.search", "src.llm", "src.data"},
        "src.data": {"src.gui", "src.mcp", "src.search", "src.llm"},
        "src.search": {"src.gui", "src.mcp"},
        "src.llm": {"src.gui", "src.search", "src.data"},
        "src.mcp": {"src.gui", "src.search", "src.llm", "src.data"},
        "src.gui": {"src.search", "src.llm", "src.data", "src.mcp"},
    }

- TESTS:

    Файл `tests/test_package_boundaries.py` должен:

    - Определять корень проекта через `Path(__file__).resolve().parents[1]`.
    - Сканировать все `.py` файлы внутри `src/`.
    - Определять текущий модуль по пути файла.
    - Проверять `import` и `from ... import` конструкции.
    - Падать при запрещённом импорте.

    Обязательное требование: путь к `src/` не должен зависеть от текущей рабочей директории.

- ACCEPTANCE: Тест проходит на текущем пустом каркасе. Правила границ задокументированы.
- STOP_CONDITIONS:
  - Если требуется разрешить импорт, который противоречит архитектурным правилам.
  - Если обнаружен существующий код, нарушающий границы, но не входящий в задачу.
  - Если нужен импорт между пакетами, не описанный в правилах.

---

## TASK: E01-T03-ENTRYPOINT

- GOAL: Создать минимальный `main.py`, который запускается без ошибок и не пишет ничего в `stdout`.
- CONTEXT: Входная точка нужна для проверки запуска приложения. Вывод должен идти в `stderr`, чтобы не загрязнять `stdout`, который в будущем резервируется для MCP.
- ALLOWED_FILES:
  - `main.py`
  - `tests/test_entrypoint.py`
- FORBIDDEN:
  - Бизнес-логика.
  - Импорт внешних библиотек.
  - Вывод в `stdout`.
  - Создание файлов данных.
  - Логгирование через корневой логгер в этой задаче.
- IMPLEMENTATION DETAILS:

    Содержимое `main.py`:

    import sys

    def main() -> int:
        sys.stderr.write("Research Prompt Suite MVP Skeleton OK\n")
        return 0

    if __name__ == "__main__":
        raise SystemExit(main())

- TESTS:

    Файл `tests/test_entrypoint.py`:

    import subprocess
    import sys
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[1]

    def test_main_runs_without_stdout():
        result = subprocess.run(
            [sys.executable, str(ROOT / "main.py")],
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=20,
        )
        assert result.returncode == 0
        assert result.stdout == ""
        assert "Skeleton OK" in result.stderr

- ACCEPTANCE: `main.py` запускается через `sys.executable`, возвращает код 0, пишет сообщение только в `stderr`.
- STOP_CONDITIONS:
  - Если для запуска требуется внешняя зависимость.
  - Если тест требует сетевой доступ.
  - Если нужно изменить поведение `stdout`, отличное от запрета записи.

---

## TASK: E01-T07-ERROR-MODEL

- GOAL: Создать базовую иерархию унифицированных ошибок без обработки и логгирования.
- CONTEXT: Ошибки нужны до конфигурации, чтобы загрузчик конфигурации мог использовать унифицированные типы. Запрещено использовать имена, конфликтующие со стандартной библиотекой.
- ALLOWED_FILES:
  - `src/core/errors.py`
  - `tests/test_errors.py`
- FORBIDDEN:
  - Обработка ошибок.
  - Логгирование.
  - Сетевые коды ошибок.
  - Использование имени `EnvironmentError`.
  - Создание интерфейсов или фабрик ошибок.
- IMPLEMENTATION DETAILS:

    Содержимое `src/core/errors.py`:

    class ResearchSuiteError(Exception):
        """Базовая ошибка приложения."""

    class ConfigError(ResearchSuiteError):
        """Ошибки конфигурации."""

    class ConfigNotFoundError(ConfigError):
        """Файл конфигурации не найден."""

    class ConfigParseError(ConfigError):
        """Ошибка разбора или валидации конфигурации."""

    class EnvironmentSetupError(ResearchSuiteError):
        """Ошибка подготовки окружения."""

- TESTS:

    Файл `tests/test_errors.py`:

    import pytest

    from src.core.errors import (
        ConfigNotFoundError,
        ConfigParseError,
        EnvironmentSetupError,
        ResearchSuiteError,
    )

    def test_error_hierarchy():
        assert issubclass(ConfigNotFoundError, ResearchSuiteError)
        assert issubclass(ConfigParseError, ResearchSuiteError)
        assert issubclass(EnvironmentSetupError, ResearchSuiteError)

    def test_errors_are_raiseable():
        with pytest.raises(ConfigNotFoundError):
            raise ConfigNotFoundError("missing")
        with pytest.raises(ConfigParseError):
            raise ConfigParseError("bad toml")
        with pytest.raises(EnvironmentSetupError):
            raise EnvironmentSetupError("bad env")

- ACCEPTANCE: Все ошибки являются наследниками `ResearchSuiteError`. Конфликтных имён нет.
- STOP_CONDITIONS:
  - Если требуется добавить коды ошибок уровня MCP или сети.
  - Если нужно создать обработку ошибок.
  - Если требуется изменить базовую иерархию за пределами задачи.

---

## TASK: E01-T04-CONFIG-MODEL-AND-LOADER

- GOAL: Создать базовую конфигурационную модель приложения и загрузчик TOML-конфигурации без внешних зависимостей.
- CONTEXT: Используется `tomllib` из Python 3.11. Модель называется `AppConfig`, а не `ResearchConfig`, чтобы не конфликтовать с сущностью уровня Study из ТЗ. Поле `db_path` не создаётся.
- ALLOWED_FILES:
  - `src/core/config.py`
  - `src/core/config_loader.py`
  - `tests/test_config.py`
  - `tests/test_config_loader.py`
- FORBIDDEN:
  - Использование `pydantic`.
  - Чтение переменных окружения.
  - Глобальные переменные состояния.
  - Создание или упоминание конкретной БД.
  - Сложные бизнес-правила.
- IMPLEMENTATION DETAILS:

    В `src/core/config.py` создай замороженный `dataclass`:

    from dataclasses import dataclass

    @dataclass(frozen=True)
    class AppConfig:
        app_name: str = "ResearchPromptSuite"
        log_level: str = "INFO"
        mcp_stdout_reserved: bool = True
        config_version: str = "1.0.0"

    Допустимые значения `log_level`:

    DEBUG, INFO, WARNING, ERROR, CRITICAL

    В `src/core/config_loader.py` создай загрузчик:

    import tomllib
    from pathlib import Path

    from src.core.config import AppConfig
    from src.core.errors import ConfigNotFoundError, ConfigParseError

    def load_app_config(file_path: Path) -> AppConfig:
        ...

    Требования:

    - Если файл отсутствует, поднять `ConfigNotFoundError`.
    - Если TOML повреждён, поднять `ConfigParseError`.
    - Неизвестные ключи отклонять через `ConfigParseError`.
    - Невалидные типы отклонять через `ConfigParseError`.
    - Значения по умолчанию использовать только для отсутствующих допустимых ключей.

- TESTS:

    Тесты должны использовать `tmp_path`.

    Проверить:

    - Дефолтные значения `AppConfig`.
    - Валидный TOML загружается.
    - Отсутствующий файл даёт `ConfigNotFoundError`.
    - Повреждённый TOML даёт `ConfigParseError`.
    - Неизвестный ключ даёт `ConfigParseError`.
    - Невалидный `log_level` даёт `ConfigParseError`.
    - Невалидный тип `mcp_stdout_reserved` даёт `ConfigParseError`.

- ACCEPTANCE: Конфигурация загружается из TOML, валидируется без внешних библиотек и не использует переменные окружения.
- STOP_CONDITIONS:
  - Если требуется добавить секции `search`, `llm`, `mcp` или другие секции полного `ResearchConfig`.
  - Если требуется чтение конфигурации из БД.
  - Если нужно сохранить поле `db_path`.

---

## TASK: E01-T05-UNIFIED-IDENTIFIERS

- GOAL: Создать утилиты генерации UUID и детерминированного отпечатка без коллизий из-за разделителя.
- CONTEXT: Отпечатки позже будут использоваться для дедупликации. Формула через простой разделитель `|` недопустима, потому что части могут содержать этот символ.
- ALLOWED_FILES:
  - `src/core/identifiers.py`
  - `tests/test_identifiers.py`
- FORBIDDEN:
  - Использование сетевых идентификаторов.
  - Обращение к БД.
  - Недетерминированные алгоритмы.
  - Использование разделителя без защиты от коллизий.
- IMPLEMENTATION DETAILS:

    В `src/core/identifiers.py` реализуй:

    import hashlib
    import uuid

    def generate_uuid() -> str:
        return str(uuid.uuid4())

    def compute_fingerprint(*parts: str) -> str:
        hasher = hashlib.sha256()
        for part in parts:
            encoded = part.encode("utf-8")
            hasher.update(len(encoded).to_bytes(8, "big"))
            hasher.update(encoded)
        return hasher.hexdigest()

- TESTS:

    Проверить:

    - `generate_uuid()` возвращает строку длиной 36 символов.
    - `compute_fingerprint()` детерминирован.
    - Результат является SHA256 hex длиной 64 символа.
    - Разный порядок частей даёт разный отпечаток.
    - Коллизия разделителя исключена:

    `compute_fingerprint("a|b", "c")` не равен `compute_fingerprint("a", "b|c")`.

- ACCEPTANCE: Утилиты детерминированы, не используют внешние ресурсы и защищены от простых коллизий конкатенации.
- STOP_CONDITIONS:
  - Если требуется реализовать `query_fingerprint` из Search Core.
  - Если нужны альтернативные алгоритмы хэширования.
  - Если требуется хранить отпечатки в БД.

---

## TASK: E01-T06-TIME-UTILITIES

- GOAL: Создать утилиты времени, которые всегда используют UTC.
- CONTEXT: Все временные метки системы должны быть воспроизводимыми и независимыми от локального часового пояса.
- ALLOWED_FILES:
  - `src/core/time_utils.py`
  - `tests/test_time_utils.py`
- FORBIDDEN:
  - Использование `datetime.now()` без `tzinfo`.
  - Использование локальных часовых поясов.
  - Зависимость от системных переменных окружения.
- IMPLEMENTATION DETAILS:

    В `src/core/time_utils.py` реализуй:

    from datetime import datetime, timezone

    def utc_now() -> datetime:
        return datetime.now(timezone.utc)

    def format_iso(dt: datetime) -> str:
        return dt.isoformat()

- TESTS:

    Проверить:

    - `utc_now()` возвращает объект с `tzinfo`.
    - `format_iso()` содержит разделитель `T`.
    - Форматирование не теряет информацию о таймзоне.

- ACCEPTANCE: Все временные утилиты используют только UTC.
- STOP_CONDITIONS:
  - Если требуется поддержка локальных таймзон.
  - Если требуется парсинг произвольных строковых дат.
  - Если нужно хранить время в БД.

---

## TASK: E01-T09-ENV-ABSTRACTION

- GOAL: Создать абстракцию временного окружения для изолированных тестов.
- CONTEXT: Окружение должно создаваться внутри переданного базового каталога и не зависеть от рабочей директории. На этом этапе не создаются пути к БД.
- ALLOWED_FILES:
  - `src/core/env.py`
  - `tests/test_env.py`
- FORBIDDEN:
  - Использование `os.getcwd()` в production-коде.
  - Использование `Path.cwd()` в production-коде.
  - Жёсткие абсолютные пути.
  - Создание файлов БД.
  - Чтение переменных окружения.
- IMPLEMENTATION DETAILS:

    В `src/core/env.py` реализуй:

    from dataclasses import dataclass
    from pathlib import Path

    @dataclass(frozen=True)
    class EnvironmentContext:
        data_dir: Path
        logs_dir: Path

    def create_temp_env(base_dir: Path) -> EnvironmentContext:
        base = Path(base_dir).resolve()
        data_dir = base / "data"
        logs_dir = base / "logs"
        data_dir.mkdir(parents=True, exist_ok=True)
        logs_dir.mkdir(parents=True, exist_ok=True)
        return EnvironmentContext(data_dir=data_dir, logs_dir=logs_dir)

- TESTS:

    Проверить:

    - `data_dir` и `logs_dir` создаются.
    - Оба пути находятся внутри `base_dir`.
    - Повторный вызов не падает.
    - Результат не зависит от текущей рабочей директории.

- ACCEPTANCE: Окружение создаётся изолированно и только внутри переданного каталога.
- STOP_CONDITIONS:
  - Если требуется создать путь к проектной БД.
  - Если требуется реестр проектов.
  - Если нужно читать пользовательские настройки окружения.

---

## TASK: E01-T08-LOGGING-SUBSYSTEM

- GOAL: Настроить логгирование в файл и `stderr` без глобальной небезопасной подмены `sys.stdout`.
- CONTEXT: Логи не должны попадать в `stdout`. При этом фундамент не должен ломать будущий MCP-транспорт глобальной подменой потоков. Защита `stdout` обеспечивается фикстурой и политикой, а не безусловным глобальным перенаправлением.
- ALLOWED_FILES:
  - `src/core/logging_setup.py`
  - `tests/test_logging_setup.py`
- FORBIDDEN:
  - Вывод логов в `stdout`.
  - Использование `print()` в `src/`.
  - Глобальная подмена `sys.stdout` без восстановления.
  - Использование `logging.basicConfig` как единственного механизма без очистки старых обработчиков.
- IMPLEMENTATION DETAILS:

    В `src/core/logging_setup.py` реализуй:

    import logging
    import sys
    from pathlib import Path

    LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    def configure_logging(logs_dir: Path, level: str = "INFO") -> Path:
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_file = logs_dir / "app.log"
        root = logging.getLogger()

        for handler in list(root.handlers):
            root.removeHandler(handler)
            handler.close()

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        stderr_handler = logging.StreamHandler(stream=sys.stderr)
        formatter = logging.Formatter(LOG_FORMAT)

        file_handler.setFormatter(formatter)
        stderr_handler.setFormatter(formatter)

        root.setLevel(getattr(logging, level.upper(), logging.INFO))
        root.addHandler(file_handler)
        root.addHandler(stderr_handler)

        return log_file

    def reset_logging() -> None:
        root = logging.getLogger()
        for handler in list(root.handlers):
            root.removeHandler(handler)
            handler.close()

- TESTS:

    Проверить:

    - После `configure_logging()` сообщение попадает в файл.
    - Сообщение не попадает в `stdout`.
    - Сообщение попадает в `stderr`.
    - Повторный вызов `configure_logging()` не дублирует обработчики.
    - `reset_logging()` удаляет обработчики.
    - Каждый тест обязан восстанавливать состояние корневого логгера.

- ACCEPTANCE: Логгирование идемпотентно, не использует `stdout`, не ломает глобальное состояние без очистки.
- STOP_CONDITIONS:
  - Если требуется реализовать транспортный слой MCP.
  - Если нужно писать логи в БД.
  - Если требуется глобальный перехват исключений всего процесса.

---

## TASK: E01-T10-PYTEST-CONFIGURATION

- GOAL: Настроить `pytest` для запуска тестов из корня проекта.
- CONTEXT: Тесты должны запускаться воспроизводимо и не зависеть от произвольной рабочей директории.
- ALLOWED_FILES:
  - `pyproject.toml`
  - `tests/test_pytest_configuration.py`
- FORBIDDEN:
  - Ручное изменение `sys.path` в коде.
  - Создание глобальных фикстур в этой задаче.
  - Добавление внешних зависимостей.
- IMPLEMENTATION DETAILS:

    Добавь в `pyproject.toml`:

    [tool.pytest.ini_options]
    testpaths = ["tests"]
    pythonpath = ["."]
    addopts = "-q"

- TESTS:

    Файл `tests/test_pytest_configuration.py` должен проверить содержимое `pyproject.toml` через `tomllib`.

    Проверить:

    - `testpaths` содержит `tests`.
    - `pythonpath` содержит `.`.
    - Файл читается без ошибок.

- ACCEPTANCE: Конфигурация `pytest` присутствует и проверяется автоматическим тестом.
- STOP_CONDITIONS:
  - Если текущий `pyproject.toml` содержит конфликтующую секцию `tool.pytest`.
  - Если требуется подключить плагины `pytest`.
  - Если нужно изменить стратегию поиска пакетов.

---

## TASK: E01-T11-ISOLATED-ENV-FIXTURE

- GOAL: Создать фикстуру `isolated_env` для использования изолированного окружения в тестах.
- CONTEXT: Фикстура должна использовать `tmp_path` и `create_temp_env`. Никакие пользовательские данные не должны затрагиваться.
- ALLOWED_FILES:
  - `tests/conftest.py`
  - `tests/test_isolated_env.py`
- FORBIDDEN:
  - Создание файлов вне `tmp_path`.
  - Использование реального каталога данных.
  - Чтение переменных окружения.
- IMPLEMENTATION DETAILS:

    В `tests/conftest.py` создай:

    import pytest

    from src.core.env import create_temp_env

    @pytest.fixture
    def isolated_env(tmp_path):
        return create_temp_env(tmp_path)

- TESTS:

    В `tests/test_isolated_env.py` проверить:

    - `isolated_env.data_dir` существует.
    - `isolated_env.logs_dir` существует.
    - Оба пути находятся внутри `tmp_path`.

- ACCEPTANCE: Фикстура доступна тестам и создаёт только временные каталоги.
- STOP_CONDITIONS:
  - Если фикстура требует реального файлового пути.
  - Если нужно автоматически поднимать БД.
  - Если требуется глобальное состояние между тестами.

---

## TASK: E01-T13-STDIO-ISOLATION-FIXTURE

- GOAL: Создать фикстуру `mcp_safe_stdio`, которая безопасно контролирует `stdout` внутри теста и восстанавливает исходное состояние.
- CONTEXT: Фикстура нужна для MCP-безопасного выполнения тестов. Она не должна глобально ломать `stdout` вне теста.
- ALLOWED_FILES:
  - `tests/conftest.py`
  - `tests/test_stdio_isolation.py`
- FORBIDDEN:
  - Безусловная глобальная подмена `sys.stdout` вне фикстуры.
  - Отсутствие восстановления `sys.stdout`.
  - Изменение `src/`.
- IMPLEMENTATION DETAILS:

    Обнови `tests/conftest.py` до итогового состояния:

    import io
    import sys

    import pytest

    from src.core.env import create_temp_env
    from src.core.logging_setup import reset_logging

    @pytest.fixture
    def isolated_env(tmp_path):
        return create_temp_env(tmp_path)

    @pytest.fixture
    def mcp_safe_stdio():
        old_stdout = sys.stdout
        buffer = io.StringIO()
        sys.stdout = buffer
        yield buffer
        sys.stdout = old_stdout

    @pytest.fixture(autouse=True)
    def clean_root_logger():
        yield
        reset_logging()

- TESTS:

    В `tests/test_stdio_isolation.py` проверить:

    - Во время действия `mcp_safe_stdio` любой случайный вывод в `stdout` попадает в буфер.
    - После завершения фикстуры `sys.stdout` восстанавливается.
    - Логгирование через `configure_logging()` не пишет в буфер `stdout`.

- ACCEPTANCE: Фикстура изолирует `stdout`, восстанавливает состояние и совместима с логгированием.
- STOP_CONDITIONS:
  - Если требуется реальный вывод в транспортный `stdout` MCP.
  - Если нужно реализовать сам MCP-сервер.
  - Если восстановление потока невозможно из-за конфликта фикстур.

---

## TASK: E01-T15-STDOUT-POLICY-ENFORCEMENT

- GOAL: Автоматически запретить `print()` и `sys.stdout.write()` в `src/`.
- CONTEXT: Это прямое требование защиты транспортного слоя. Проверка должна быть детерминированной и не зависеть от рабочей директории.
- ALLOWED_FILES:
  - `tests/test_stdout_policy.py`
- FORBIDDEN:
  - Изменение файлов `src/`.
  - Использование сетевых запросов.
  - Зависимость от текущей рабочей директории.
- IMPLEMENTATION DETAILS:

    Реализуй тестовый помощник, который через `ast` ищет:

    - вызовы `print(...)`;
    - вызовы `sys.stdout.write(...)`.

    Путь к `src/` определяй относительно файла теста:

    SRC_ROOT = Path(__file__).resolve().parents[1] / "src"

    Список разрешённых файлов пуст:

    ALLOWED_STDOUT_FILES = set()

- TESTS:

    Проверить:

    - В чистом `src/` нарушений нет.
    - Детектор находит `print()` во временном файле.
    - Детектор находит `sys.stdout.write()` во временном файле.
    - Тест не зависит от `os.getcwd()`.

- ACCEPTANCE: Любая попытка добавить `print()` или `sys.stdout.write()` в `src/` приводит к падению теста.
- STOP_CONDITIONS:
  - Если обнаружено разрешённое место для записи в `stdout`, не описанное архитектором.
  - Если нужно проверять `main.py`.
  - Если требуется линтер или CI-интеграция.

---

## TASK: E01-T12-ENV-INDEPENDENCE-TESTS

- GOAL: Проверить, что код Foundation не зависит от среды разработчика.
- CONTEXT: Тесты не должны зависеть от переменных окружения, рабочей директории, пользовательских данных или реального каталога проекта.
- ALLOWED_FILES:
  - `tests/test_env_independence.py`
- FORBIDDEN:
  - Изменение `src/`.
  - Использование реальных пользовательских данных.
  - Сетевые проверки.
- IMPLEMENTATION DETAILS:

    Реализуй два типа проверок:

    1. Поведенческая проверка:

    - `create_temp_env()` работает при смене текущей рабочей директории.
    - Все создаваемые пути остаются внутри переданного `base_dir`.

    2. Статическая проверка исходников:

    - В `src/` нет использования `os.environ`.
    - В `src/` нет использования `os.getenv`.
    - В `src/` нет использования `os.getcwd`.
    - В `src/` нет использования `Path.cwd`.
    - В `src/` нет использования `expanduser`.

- TESTS:

    Проверки должны использовать `tmp_path`, `monkeypatch` и `ast`.

    Путь к `src/` должен вычисляться относительно файла теста.

- ACCEPTANCE: Код и тесты Foundation не опираются на среду разработчика.
- STOP_CONDITIONS:
  - Если найдено использование среды, которое требуется для будущего этапа.
  - Если нужно разрешить доступ к переменным окружения.
  - Если найден конфликт с кодом вне `ALLOWED_FILES`.

---

## TASK: E01-T14-FOUNDATION-INTEGRATION

- GOAL: Проверить совместную работу конфигурации, окружения, логгирования, идентификаторов и времени.
- CONTEXT: Это финальный тест для Gate G-01. Он не должен создавать файлы вне `tmp_path`, писать в `stdout` или оставлять глобальные побочные эффекты.
- ALLOWED_FILES:
  - `tests/test_foundation_integration.py`
- FORBIDDEN:
  - Изменение `src/`.
  - Использование реальной БД.
  - Использование сети.
  - Вывод в `stdout`.
- IMPLEMENTATION DETAILS:

    Тест должен выполнить следующую последовательность:

    1. Создать временный TOML-файл в `tmp_path`.
    2. Загрузить `AppConfig`.
    3. Создать `EnvironmentContext` через `create_temp_env(tmp_path)`.
    4. Настроить логгирование в `logs_dir`.
    5. Записать тестовое сообщение в лог.
    6. Проверить, что лог-файл создан и содержит сообщение.
    7. Проверить, что буфер `mcp_safe_stdio` пуст.
    8. Проверить `generate_uuid()` и `compute_fingerprint()`.
    9. Проверить `utc_now()` и `format_iso()`.

- TESTS:

    Тест должен использовать фикстуры:

    - `tmp_path`
    - `mcp_safe_stdio`

    Пример проверяемых утверждений:

    - `cfg.app_name == "IntegrationTest"`.
    - `len(fp) == 64`.
    - `"Bootstrap complete" in log_file.read_text(encoding="utf-8")`.
    - `mcp_safe_stdio.getvalue() == ""`.
    - `utc_now().tzinfo is not None`.

- ACCEPTANCE: Все компоненты Foundation работают вместе, не загрязняют `stdout` и не оставляют файлов вне временной директории.
- STOP_CONDITIONS:
  - Если интеграционный тест требует реального файла БД.
  - Если требуется участие будущего Research Engine.
  - Если нужно подключить LLM, MCP или GUI.

---

## 4. Definition of Done для EPIC-01

- Все задачи выполнены в пределах `ALLOWED_FILES`.
- Все задачи имеют 8 обязательных секций.
- `pytest` запускается из корня проекта и проходит.
- В `src/` нет `print()`.
- В `src/` нет `sys.stdout.write()`.
- Тесты используют только `tmp_path` и не пишут в реальную файловую систему пользователя.
- Конфигурация валидируется без внешних библиотек.
- Логгирование не попадает в `stdout`.
- Фикстура `mcp_safe_stdio` восстанавливает `sys.stdout`.
- Границы пакетов зафиксированы и проверяются тестом.
- Ошибки унифицированы и не конфликтуют со стандартной библиотекой.
- Идентификаторы детерминированы и защищены от коллизий разделителя.
- Время использует только UTC.
- Нет преждевременной фиксации пути к БД.
- Нет конфликта имени `AppConfig` с сущностью `ResearchConfig` из ТЗ.