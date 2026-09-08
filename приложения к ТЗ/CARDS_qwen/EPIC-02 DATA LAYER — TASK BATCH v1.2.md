## EPIC-02 DATA LAYER — TASK BATCH v1.2 FINAL
Проект: Research Prompt Suite
Статус: Утвержден для исполнения (Финальная монолитная редакция)
База: ТЗ v2.4 Раздел 03, MASTER ROADMAP v1.2, Спецификация подключений (с учетом ответов Архитектора)
Зависимость: EPIC-01 Foundation обязан быть полностью завершён.
------------------------------
## 0. Глобальные правила для CODE-агента

* Одна задача даёт один проверяемый результат.
* Каждая задача содержит 8 обязательных секций: GOAL, CONTEXT, ALLOWED_FILES, FORBIDDEN, IMPLEMENTATION DETAILS, TESTS, ACCEPTANCE, STOP_CONDITIONS.
* Python 3.11+. Только стандартная библиотека Python и pytest.
* Запрещены: ORM, SQLAlchemy, Alembic, внешние миграционные фреймворки, сетевые запросы, ЛЛМ, MCP, GUI, бизнес-логика исследования.
* Все тесты используют только tmp_path и работают в CPU-only режиме.
* Все пути к файлам проекта в тестах вычисляются абсолютно относительно файла теста (например, через Path(__file__).resolve().parents). Зависимость от текущей рабочей директории процесса (os.getcwd()) запрещена.
* Прямое создание SQLite-подключений запрещено вне src/data/connection.py. Все подключения создаются через create_connection.
* Транзакционная политика репозиториев: Все репозиторные функции не вызывают conn.commit() и conn.rollback(). Транзакция полностью управляется внешним контуром: transaction(conn) или DbWriter.
* Прямое изменение статусов в EPIC-02 запрещено. Допускается только первичное создание сущности с начальным статусом "DRAFT". Любые переходы статусов относятся к EPIC-03.

------------------------------
## 1. Рекомендуемый порядок выполнения задач

   1. E02-T01-DB-CONFIG
   2. E02-T02-CONNECTION-FACTORY
   3. E02-T03-TRANSACTION-HELPERS
   4. E02-T04-MIGRATION-FRAMEWORK
   5. E02-T05-SCHEMA-CORE
   6. E02-T06-SCHEMA-SEARCH
   7. E02-T07-SCHEMA-DOCUMENTS
   8. E02-T08-SCHEMA-EVIDENCE
   9. E02-T09-CONSTRAINT-AND-FK-TESTS
   10. E02-T10-REPO-BASE
   11. E02-T11-PROJECT-STUDY-REPO
   12. E02-T12-SOURCE-DOCUMENT-REPO
   13. E02-T13-CHUNK-EVIDENCE-REPO
   14. E02-T14-OPERATION-IDEMPOTENCY
   15. E02-T15-DB-WRITE-LAYER
   16. E02-T16-GLOBAL-REGISTRY
   17. E02-T17-COORDINATED-REGISTRY-SYNC
   18. E02-T18-WAL-SAFE-BACKUP
   19. E02-T19-CHECKPOINT-RESTORE
   20. E02-T20-ISOLATION-TESTS
   21. E02-T21-CONCURRENT-READ-WRITE-TEST
   22. E02-T22-DETERMINISTIC-FIXTURES
   23. E02-T23-FTS5-READINESS-TEST
   24. E02-T24-DATA-INTEGRATION-TEST

------------------------------
## 2. Спецификации задач## TASK: E02-T01-DB-CONFIG

* GOAL: Создать неизменяемую конфигурацию подключения к SQLite.
* CONTEXT: Конфигурация не создаёт подключения и не проверяет существование файла БД. Разрешен строго режим NORMAL для обеспечения баланса безопасности и производительности на CPU.
* ALLOWED_FILES:
* src/data/config.py
   * tests/data/__init__.py
   * tests/data/test_config.py
* FORBIDDEN: Создание подключений, миграции, репозитории, бизнес-логика. Любые значения synchronous, кроме NORMAL.
* IMPLEMENTATION DETAILS:
* Создай пустой tests/data/__init__.py.
   * Создай замороженный dataclass DatabaseConfig.
   * Поля: db_path: Path, busy_timeout_ms: int = 5000, journal_size_limit: int = 67108864, wal_autocheckpoint: int = 1000, synchronous: str = "NORMAL".
   * В __post_init__ проверяй положительный busy_timeout_ms, неотрицательный journal_size_limit, положительный wal_autocheckpoint.
   * Разрешай только synchronous == "NORMAL". Не проверяй существование db_path.
* TESTS: Проверить валидную конфигурацию. Проверить ошибку при busy_timeout_ms = 0. Проверить ошибку при journal_size_limit = -1. Проверить ошибку при wal_autocheckpoint = 0. Проверить ошибку при synchronous = "OFF".
* ACCEPTANCE: Конфигурация неизменяема и принимает только "NORMAL".
* STOP_CONDITIONS: Если требуется разрешить режимы OFF или FULL.

## TASK: E02-T02-CONNECTION-FACTORY

* GOAL: Создать единую фабрику подключений SQLite с полным набором обязательных PRAGMA.
* CONTEXT: Фабрика является единственным способом получения соединения во всей системе.
* ALLOWED_FILES:
* src/data/connection.py
   * tests/data/test_connection.py
* FORBIDDEN: Создание таблиц, миграции, бизнес-логика. Прямые вызовы sqlite3.connect в других модулях.
* IMPLEMENTATION DETAILS:
* Реализуй функцию create_connection(config: DatabaseConfig) -> sqlite3.Connection.
   * Используй sqlite3.connect(config.db_path, check_same_thread=False).
   * Установи conn.row_factory = sqlite3.Row.
   * Применяй на каждое открываемое соединение:
   
   PRAGMA journal_mode=WAL;
   PRAGMA synchronous=NORMAL;
   PRAGMA foreign_keys=ON;
   
   А также busy_timeout, journal_size_limit и wal_autocheckpoint из объекта конфигурации.
* TESTS: Проверить journal_mode = wal, synchronous = 1, foreign_keys = 1, busy_timeout = 5000, journal_size_limit = 67108864, wal_autocheckpoint = 1000. Проверить, что повторное подключение снова принудительно включает foreign_keys (так как это свойство сессии подключения, а не файла).
* ACCEPTANCE: Все подключения проходят через фабрику и получают обязательные PRAGMA. Без foreign_keys=ON внешние ключи в SQLite не работают.
* STOP_CONDITIONS: Если SQLite не поддерживает режим WAL на целевой платформе.

## TASK: E02-T03-TRANSACTION-HELPERS

* GOAL: Создать контекстный менеджер транзакций.
* CONTEXT: Все атомарные операции записи обязаны использовать единый контролируемый механизм фиксации/отката.
* ALLOWED_FILES:
* src/data/transactions.py
   * tests/data/test_transactions.py
* FORBIDDEN: Потоки, DbWriter, миграции предметной области, вложенные транзакции.
* IMPLEMENTATION DETAILS:
* Реализуй контекстный менеджер transaction(conn).
   * При успешном выходе выполняй conn.commit().
   * При исключении выполняй conn.rollback() и пробрасывай исключение наружу.
   * Не меняй isolation_level у соединения. Не поддерживай вложенные транзакции или savepoints на этом этапе.
* TESTS: Проверить успешный commit для тестовой вставки. Проверить автоматический rollback при искусственном исключении внутри блока. Проверить, что исключение пробрасывается наружу. Убедиться, что после отката данные отсутствуют в базе.
* ACCEPTANCE: Транзакции надежно изолируют изменения и выполняют автоматический откат при сбоях.
* STOP_CONDITIONS: Если требуется реализовать механизм savepoint для вложенных транзакций.

## TASK: E02-T04-MIGRATION-FRAMEWORK

* GOAL: Создать легковесный миграционный механизм с версионированием схемы.
* CONTEXT: Позволяет накатывать структуру таблиц из SQL-файлов последовательно и идемпотентно.
* ALLOWED_FILES:
* src/data/migrations.py
   * src/data/migrations/__init__.py
   * tests/data/test_migrations.py
* FORBIDDEN: Реальные таблицы предметной области, репозитории, бизнес-логика. Использование CREATE TRIGGER запрещено.
* IMPLEMENTATION DETAILS:
* Создай пустой файл src/data/migrations/__init__.py.
   * Создай таблицу schema_version (version INTEGER PRIMARY KEY, name TEXT, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP).
   * Формат имени файла миграции: строго {три цифры}_{название}.sql, например 001_core.sql. Если формат нарушен или номера версий дублируются — бросать ошибку.
   * Применяй миграции строго по возрастанию версий. Каждая миграция — в одной транзакции. Пропускай уже примененные версии.
   * Очищай строки от SQL-комментариев (--), разделяй операторы по точке с запятой (;).
* TESTS: Проверить накат одной миграции. Проверить повторный (идемпотентный) запуск. Проверить накат двух файлов по порядку. Проверить вызов исключений при некорректном имени файла или дублировании номеров версий.
* ACCEPTANCE: Миграции применяются последовательно, фиксируют версию схемы в базе и защищены от синтаксического брака в именах файлов.
* STOP_CONDITIONS: Если в SQL-файле обнаружен оператор создания триггера.

## TASK: E02-T05-SCHEMA-CORE

* GOAL: Создать миграцию 001_core.sql для базовых сущностей проекта, исследования и сессий.
* CONTEXT: Описывает только DDL-структуру ядра системы. Без репозиториев и логики.
* ALLOWED_FILES:
* src/data/migrations/001_core.sql
   * tests/data/test_schema_core.py
* FORBIDDEN: Код репозиториев, изменение других миграций, триггеры, логика статусных переходов (все статусы по умолчанию "DRAFT").
* IMPLEMENTATION DETAILS:
* Создай таблицы: Project, Study, ResearchIntent, ResearchConfig, ResearchSession, ResearchState, WorkingMemory, LogRecord.
   * Поля и внешние ключи строго по ТЗ Раздел 03: Study.project_id -> Project, ResearchIntent.study_id (UNIQUE) -> Study, ResearchConfig.study_id (UNIQUE) -> Study, ResearchSession.study_id -> Study.
   * ResearchState.study_id и WorkingMemory.study_id являются PRIMARY KEY (связь 1-к-1 со Study).
   * Создай индексы для внешних ключей и операционных статусов: Study(project_id), Study(status), ResearchSession(study_id), ResearchSession(status), LogRecord(entity_type, entity_id).
* TESTS: Использовать абсолютный путь к миграциям относительно файла теста. Проверить существование всех 8 таблиц после наката. Проверить работу FOREIGN KEY (вставка Study с фейковым project_id должна падать). Проверить UNIQUE на связях 1-к-1.
* ACCEPTANCE: Схема ядра успешно развернута, индексы и ограничения целостности активны.
* STOP_CONDITIONS: Попытка добавить поля-коллекции (массивы) или реализовать логику статусных машин.

## TASK: E02-T06-SCHEMA-SEARCH

* GOAL: Создать миграцию 002_search.sql для поисковых сущностей и справочников нормализации.
* ALLOWED_FILES:
* src/data/migrations/002_search.sql
   * tests/data/test_schema_search.py
* FORBIDDEN: Реализация поисковых адаптеров, алгоритмов ранжирования, виртуальных таблиц FTS5.
* IMPLEMENTATION DETAILS:
* Создай таблицы: SearchTask, Source, SourceRelation, SearchResult, Entity.
   * Ограничения уникальности согласно ТЗ и ответам Архитектора: SearchTask.query_fingerprint (UNIQUE). SearchTask.idempotency_key обязан иметь ЧАСТИЧНЫЙ уникальный индекс для защиты от дублей при восстановлении:
   
   CREATE UNIQUE INDEX idx_search_task_idempotency_key_unique ON SearchTask(idempotency_key) WHERE idempotency_key IS NOT NULL;
   
   * Source.canonical_url (UNIQUE).
   * SourceRelation имеет составной уникальный индекс на (study_id, source_source_id, target_source_id) для фиксации генеалогии заимствований.
   * Entity имеет составной уникальный индекс на (study_id, normalized_key) для слоя нормализации объектов исследования.
   * Создай необходимые индексы на внешние ключи согласно Разделу 03 (секция 22).
* TESTS: Проверить создание всех 5 таблиц. Проверить падение при дублировании query_fingerprint, canonical_url, пары (study_id, normalized_key) в Entity. Проверить работу частичного индекса idempotency_key (два NULL допускаются, два одинаковых текстовых ключа — нет).
* ACCEPTANCE: Поисковая схема развернута, уникальные бизнес-ключи заблокированы на уровне СУБД.
* STOP_CONDITIONS: Попытка внедрить нейросетевые параметры или изменить структуру query_fingerprint на уровне базы.

## TASK: E02-T07-SCHEMA-DOCUMENTS

* GOAL: Создать миграцию 003_documents.sql для документов, чанков, кэша и Job.
* CONTEXT: Схема должна быть полностью готова к будущему текстовому поиску FTS5 на CPU, но не создает сами виртуальные объекты индекса.
* ALLOWED_FILES:
* src/data/migrations/003_documents.sql
   * tests/data/test_schema_documents.py
* FORBIDDEN: Создание виртуальных таблиц USING fts5, логика чанкинга, хранение массивов study_ids внутри таблицы Document.
* IMPLEMENTATION DETAILS:
* Создай таблицы: Document, StudyDocumentLink, DocumentChunk, CacheEntry, Job.
   * Связи и ограничения: Document.content_hash (UNIQUE). StudyDocumentLink имеет составной первичный ключ (study_id, document_id) для JOIN-изоляции исследований в рамках проекта.
   * Настрой каскады жестко по ТЗ: StudyDocumentLink.study_id имеет ON DELETE CASCADE, а StudyDocumentLink.document_id — ON DELETE RESTRICT (нельзя удалить документ, если на него ссылается хотя бы одно исследование).
   * DocumentChunk.document_id имеет ON DELETE CASCADE. DocumentChunk имеет составной уникальный ключ (document_id, position_index) для детерминированной нарезки. Поля: chunk_id (PK), text, token_estimate, char_start, char_end, position_index, overlap_group_id, is_overlap.
   * Индексы: Document(source_id), DocumentChunk(document_id), DocumentChunk(overlap_group_id), StudyDocumentLink(document_id), CacheEntry(expires_at), Job(status).
* TESTS: Проверить уникальность content_hash. Проверить падение при удалении документа, связанного через StudyDocumentLink (RESTRICT). Проверить автоматическое каскадное удаление чанков при удалении базового документа.
* ACCEPTANCE: Схема документов развернута, каскады и изоляция настроены строго по ТЗ.
* STOP_CONDITIONS: Обнаружение денормализованных полей-массивов для связи документов со Study (нарушение правила JOIN-изоляции).

## TASK: E02-T08-SCHEMA-EVIDENCE

* GOAL: Создать миграцию 004_evidence.sql для доказательств, наблюдений, утверждений, конфликтов и пробелов.
* CONTEXT: Фиксирует финальный аналитический слой эпистемической цепочки.
* ALLOWED_FILES:
* src/data/migrations/004_evidence.sql
   * tests/data/test_schema_evidence.py
* FORBIDDEN: Эвристики ИИ-моделей, логика автоматического извлечения цитат на уровне базы.
* IMPLEMENTATION DETAILS:
* Создай таблицы: Evidence, EvidenceContextChunk, Observation, Claim, ClaimEvidence, Contradiction, ResearchGap, SufficiencyEvaluation.
   * Связи и ограничения: Evidence.evidence_hash (UNIQUE). EvidenceContextChunk имеет составной первичный ключ (evidence_id, chunk_id) с каскадом ON DELETE CASCADE по evidence_id и ON DELETE RESTRICT по chunk_id (соседние контекстные чанки ±1).
   * ClaimEvidence имеет составной ПК (claim_id, evidence_id) с каскадом ON DELETE CASCADE по claim_id и ON DELETE RESTRICT по evidence_id (сквозная доказательность без JSON-массивов).
   * Индексы: На все внешние ключи и аналитические связи согласно разделу 03 (секция 22).
* TESTS: Проверить уникальность evidence_hash. Проверить составные ключи связующих таблиц EvidenceContextChunk и ClaimEvidence. Проверить запрет на удаление чанка, используемого в качестве доказательства (RESTRICT).
* ACCEPTANCE: Все аналитические таблицы созданы с соблюдением требований сквозной трассируемости.
* STOP_CONDITIONS: Использование JSON-полей как источника истины для связи Claim ↔ Evidence.

## TASK: E02-T09-CONSTRAINT-AND-FK-TESTS

* GOAL: Создать комплексный изолированный тестовый набор для валидации всех ограничений БД.
* CONTEXT: Это исключительно тестовая задача для проверки надежности DDL-схемы. Исходный код миграций менять запрещено.
* ALLOWED_FILES:
* tests/data/test_schema_constraints.py
* FORBIDDEN: Изменение продуктового кода, добавление новых таблиц в миграции.
* IMPLEMENTATION DETAILS:
* Напиши тесты, которые проверяют, что PRAGMA foreign_keys = 1 реально активно на соединении фабрики.
   * Проверить работу ограничений внешних ключей, уникальных составных ключей и каскадов, созданных в задачах T05–T08.
* ACCEPTANCE: Отдельный тестовый набор полностью покрывает негативные сценарии схемы данных.
* STOP_CONDITIONS: Если тесты проходят при отключенном свойстве foreign_keys в SQLite.

## TASK: E02-T10-REPO-BASE

* GOAL: Создать базовые низкоуровневые функции выполнения SQL-запросов.
* CONTEXT: Функции используются репозиториями, но сами транзакциями не управляют.
* ALLOWED_FILES:
* src/data/repositories/__init__.py
   * src/data/repositories/base.py
   * tests/data/test_repo_base.py
* FORBIDDEN: Вызовы conn.commit() или conn.rollback() внутри функций. Динамическая сборка SQL из сырых строк.
* IMPLEMENTATION DETAILS:
* Создай пустой src/data/repositories/__init__.py.
   * В base.py реализуй: fetch_one(conn, sql, params=None) -> dict | None, fetch_all(conn, sql, params=None) -> list[dict], execute_write(conn, sql, params=None) -> int (возвращает cursor.rowcount).
   * Приводи встроенный тип sqlite3.Row к обычному Python dict для полной изоляции вышестоящих слоев от специфики драйвера.
* TESTS: Тестировать вставку и чтение строк на примере простейшей временной таблицы. Проверить, что без внешней транзакции данные не фиксируются автоматически.
* ACCEPTANCE: Базовый слой оберток готов и возвращает чистые словари.
* STOP_CONDITIONS: Обнаружение любого вызова commit() в коде модуля base.py.

## TASK: E02-T11-PROJECT-STUDY-REPO

* GOAL: Создать функции создания и чтения для Project и Study.
* ALLOWED_FILES:
* src/data/repositories/project_study.py
   * tests/data/test_project_study_repo.py
* FORBIDDEN: Логика FSM, функции обновления статусов исследований после создания (это зона EPIC-03).
* IMPLEMENTATION DETAILS:
* Реализуй: create_project(conn, project_id, name, description=None), get_project(conn, project_id), create_study(conn, study_id, project_id, title, goal, domain, research_mode, status="DRAFT"), get_study(conn, study_id), list_studies_by_project(conn, project_id).
   * Начальный статус "DRAFT" жестко зашит в коде вставки и разрешен только в момент инсерта. Функции апдейта статуса не создаются.
* TESTS: Проверить создание проекта и исследования в рамках transaction(conn). Проверить фильтрацию list_studies_by_project. Убедиться в отсутствии функций мутации статуса.
* ACCEPTANCE: Функции CRUD для проектов и исследований реализованы без возможности изменения состояний.
* STOP_CONDITIONS: Если в коде репозитория обнаружена функция update_study_status.

## TASK: E02-T12-SOURCE-DOCUMENT-REPO

* GOAL: Создать репозиторий Source/Document с жесткой защитой от скрытых обновлений (сквозное переиспользование).
* CONTEXT: Документ глобален в рамках проекта и переиспользуется без мутации полей при совпадении хэша.
* ALLOWED_FILES:
* src/data/repositories/documents.py
   * tests/data/test_documents_repo.py
* FORBIDDEN: Логика автоматического перезаписывания полей при конфликтах (конструкция INSERT OR REPLACE запрещена).
* IMPLEMENTATION DETAILS:
* Реализуй: upsert_source(conn, source_id, canonical_url, domain, source_type, quality_profile). Если canonical_url существует — не меняй запись, верни существующий source_id. Если source_id передан существующий, но с другим URL — бросай ValueError.
   * Реализуй: upsert_document(conn, document_id, source_id, content_hash, title, content, content_type, processing_status="RAW"). Логика аналогичная: при совпадении content_hash — вернуть старый document_id без обновлений полей. При конфликте самого document_id с другой сущностью — ValueError.
   * Реализуй: link_study_document(conn, study_id, document_id, relation_type="RETRIEVED") через INSERT OR IGNORE. Повторная связь не затирает relation_type.
   * Реализуй функции чтения: list_documents_by_study(conn, study_id), get_document_by_content_hash(conn, content_hash).
* TESTS: Проверить, что повторный апсерт документа с тем же хэшем, но другими заголовками/текстом, не изменяет запись в БД и возвращает первоначальный ID. Проверить изоляцию: документ, привязанный к Study А, не должен вычитываться для Study Б.
* ACCEPTANCE: Принцип переиспользования документов гарантирует неизменяемость данных (идемпотентность без мутаций).
* STOP_CONDITIONS: Использование конструкции INSERT OR REPLACE или оператора UPDATE для контента документов.

## TASK: E02-T13-CHUNK-EVIDENCE-REPO

* GOAL: Создать репозиторий для DocumentChunk, Evidence и контекстных связей.
* ALLOWED_FILES:
* src/data/repositories/evidence.py
   * tests/data/test_evidence_repo.py
* FORBIDDEN: Модификация или апдейты уже созданных доказательств (Evidence).
* IMPLEMENTATION DETAILS:
* Реализуй insert_chunk(conn, chunk_id, document_id, text, token_estimate, char_start, char_end, position_index, overlap_group_id, is_overlap=False). Операция строго идемпотентна по chunk_id + document_id.
   * Реализуй insert_evidence(conn, evidence_id, study_id, document_id, target_chunk_id, task_id, text, evidence_hash, evidence_type). Если evidence_hash существует — вернуть существующий evidence_id без создания строки. При конфликте самого evidence_id с другим хэшем — ValueError.
   * Реализуй link_evidence_context_chunk(conn, evidence_id, chunk_id, is_target). Использовать INSERT OR IGNORE.
   * Реализуй get_evidence_by_hash(conn, evidence_hash).
* TESTS: Проверить, что повторная попытка сохранить Evidence с идентичным evidence_hash отрабатывает успешно, не плодит записи в базе и возвращает старый UUID. Проверить корректность связывания контекстных чанков.
* ACCEPTANCE: Репозиторий гарантирует уникальность и стабильность доказательной базы.
* STOP_CONDITIONS: Наличие функций для редактирования текста цитат Evidence.

## TASK: E02-T14-OPERATION-IDEMPOTENCY

* GOAL: Создать утилиты генерации системных идентификаторов и детерминированных ключей идемпотентности.
* CONTEXT: Опирается на исправленный в EPIC-01 алгоритм хэширования без коллизий разделителей.
* ALLOWED_FILES:
* src/data/operations.py
   * tests/data/test_operations.py
* FORBIDDEN: Хранение ключей в операционных таблицах (это утилитарный слой).
* IMPLEMENTATION DETAILS:
* Реализуй: new_operation_id() -> str (генерирует UUID4), new_request_id() -> str (генерирует UUID4), make_idempotency_key(*parts: str) -> str (вызывает src.core.identifiers.compute_fingerprint).
* TESTS: Проверить детерминированность вывода make_idempotency_key. Убедиться в защите от коллизий конкатенации: ключ от ("a|b", "c") обязан отличаться от ключа для ("a", "b|c").
* ACCEPTANCE: Утилитарный слой идентификаторов готов к интеграции во все будущие MCP-команды.
* STOP_CONDITIONS: Использование примитивной конкатенации строк через символ | вместо compute_fingerprint.

## TASK: E02-T15-DB-WRITE-LAYER

* GOAL: Создать единый диспетчер записи DbWriter (Single-Writer Pattern) с контролируемым жизненным циклом.
* CONTEXT: Предотвращает конкурентные блокировки файла SQLite при записи из параллельных воркеров ИИ или сети.
* ALLOWED_FILES:
* src/data/db_writer.py
   * tests/data/test_db_writer.py
* FORBIDDEN: Реализация нескольких пишущих потоков, использование асинхронных библиотек (asyncio).
* IMPLEMENTATION DETAILS:
* Реализуй класс DbWriter. Внутренний воркер запускается в отдельном threading.Thread. Взаимодействие через queue.Queue.
   * Методы: start() (строго один раз), submit(fn, *args, **kwargs) -> concurrent.futures.Future (принимает синхронную функцию, выполняемую воркером в контексте соединения), stop() (безопасен для повторного вызова, блокирует очередь, дорабатывает остаток и гасит поток).
   * Если воркеру передан registry_path: Path, он обязан при открытии соединения выполнить ATTACH DATABASE '{registry_path}' AS registry;.
   * Каждая задача из очереди воркера оборачивается в transaction(conn). Результат или исключение пробрасывается в возвращенный Future.
* TESTS: Проверить последовательное выполнение записей. Проверить генерацию ошибок при вызове submit до старта или после остановки диспетчера. Убедиться, что исключение, возникшее внутри выполняемой функции, корректно передается в Future.exception().
* ACCEPTANCE: Диспетчер обеспечивает строго однопоточную изоляцию всех операций записи в СУБД.
* STOP_CONDITIONS: Использование пула потоков вместо одного выделенного фонового потока записи.

## TASK: E02-T16-GLOBAL-REGISTRY

* GOAL: Создать схему и базовые функции для работы с глобальным реестром проектов.
* CONTEXT: Реестр хранится в отдельном файле registry.db и связывает метаданные проектов и хэши документов.
* ALLOWED_FILES:
* src/data/registry.py
   * tests/data/test_registry.py
* FORBIDDEN: Логика сквозного поиска по проектам (только управление индексами). Вызовы commit() внутри функций.
* IMPLEMENTATION DETAILS:
* Реализуй ensure_registry_schema(conn). Создай таблицы: ProjectRegistry (project_id TEXT PRIMARY KEY, name TEXT, db_path TEXT, status TEXT, created_at TIMESTAMP), GlobalDocumentIndex (content_hash TEXT PRIMARY KEY, project_id TEXT, document_id TEXT, title TEXT), GlobalSourceIndex (canonical_url TEXT PRIMARY KEY, project_id TEXT, source_id TEXT, domain TEXT).
   * Реализуй функции вставки (без коммитов): register_project(conn, project_id, name, db_path), insert_registry_document(conn, project_id, document_id, content_hash, title=None), insert_registry_source(conn, project_id, source_id, canonical_url, domain). Используй INSERT OR IGNORE.
   * Реализуй чтение: get_registry_project(conn, project_id).
* TESTS: Проверить создание схемы реестра в изолированном файле. Проверить идемпотентность вставок в индексы документов и источников.
* ACCEPTANCE: Инфраструктура глобального реестра готова к координации с проектными БД.
* STOP_CONDITIONS: Наличие операций UPDATE или затирания существующих записей в индексах реестра.

## TASK: E02-T17-COORDINATED-REGISTRY-SYNC

* GOAL: Реализовать механизм координированной атомарной записи в проектную БД и глобальный реестр.
* CONTEXT: Запись документа/источника должна быть атомарной для обеих баз в рамках одного соединения.
* ALLOWED_FILES:
* src/data/registry_sync.py
   * tests/data/test_registry_sync.py
* FORBIDDEN: Фоновые или асинхронные компенсирующие транзакции. Прямой sqlite3.connect внутри модуля.
* IMPLEMENTATION DETAILS:
* Реализуй ensure_registry_attached(conn, registry_path: Path). Проверяет через PRAGMA database_list, прикреплен ли алиас registry. Если нет — выполняет ATTACH.
   * Реализуй sync_document_to_registry(conn, project_id, document_id, content_hash, title=None) и sync_source_to_registry(conn, project_id, source_id, canonical_url, domain). Они выполняют прямые инсерты вида INSERT OR IGNORE INTO registry.GlobalDocumentIndex .... Они не вызывают коммит. Атомарность гарантируется внешним контуром транзакции.
* TESTS: Начать транзакцию. Записать Document в проектную БД, вызвать sync_document_to_registry. Сделать искусственный сбой (поднять ошибку). Убедиться, что после отката запись отсутствует и в проектной БД, и в файле глобального реестра.
* ACCEPTANCE: Проектная запись и реестр синхронизируются строго синхронно и атомарно.
* STOP_CONDITIONS: Если запись в реестр вынесена в отдельный поток или выполняется после коммита основной базы.

## TASK: E02-T18-WAL-SAFE-BACKUP

* GOAL: Создать механизм резервного копирования, безопасный для активного режима WAL.
* CONTEXT: Прямое копирование файлов .db на диске во время активных транзакций запрещено из-за риска получить поврежденный снимок.
* ALLOWED_FILES:
* src/data/backup.py
   * tests/data/test_backup.py
* FORBIDDEN: Использование функций shutil.copy, os.system, ручное копирование .db-wal файлов.
* IMPLEMENTATION DETAILS:
* Реализуй функцию backup_database(source_config: DatabaseConfig, target_config: DatabaseConfig).
   * Открой оба соединения через фабрику create_connection. Вызови встроенный метод СУБД: source_conn.backup(target_conn). Обеспечь закрытие соединений в блоке finally.
* TESTS: Наполнить исходную БД данными. Выполнить backup_database. Открыть целевой файл бэкапа через фабрику, проверить структуру и идентичность записей.
* ACCEPTANCE: Резервное копирование реализовано через официальный детерминированный API Connection.backup.
* STOP_CONDITIONS: Наличие любого побайтового файлового копирования основного файла базы данных.

## TASK: E02-T19-CHECKPOINT-RESTORE

* GOAL: Создать функции принудительного сброса логов (checkpoint) и восстановления из резервной копии.
* ALLOWED_FILES:
* src/data/checkpoint.py
   * tests/data/test_checkpoint.py
* FORBIDDEN: Ручное удаление или обнуление файлов .db-wal и .db-shm с диска средствами ОС.
* IMPLEMENTATION DETAILS:
* Реализуй checkpoint(conn): выполняет PRAGMA wal_checkpoint(PASSIVE); и вычитывает результат для подтверждения сброса страниц из WAL-файла в основной файл БД.
   * Реализуй restore_database(backup_config: DatabaseConfig, target_config: DatabaseConfig): накатывает бэкап поверх целевой базы в обратном порядке через метод backup_conn.backup(target_conn).
* TESTS: Записать данные, вызвать checkpoint, убедиться в отсутствии ошибок. Проверить процедуру restore_database на пустую временную базу, подтвердив полное восстановление состояния.
* ACCEPTANCE: Механизмы обслуживания WAL и восстановления данных полностью детерминированы.
* STOP_CONDITIONS: Использование дисковых утилит для удаления файлов логов ломает консистентность WAL.

## TASK: E02-T20-ISOLATION-TESTS

* GOAL: Создать обособленный тестовый навигатор для проверки жесткой изоляции данных.
* CONTEXT: Это исключительно тестовая задача для верификации. Продуктовый код репозиториев менять запрещено.
* ALLOWED_FILES:
* tests/data/test_isolation.py
* FORBIDDEN: Изменение продуктовых файлов.
* IMPLEMENTATION DETAILS:
* Напиши тесты, подтверждающие:
   1. Изоляцию Study: документы изолированы через JOIN по таблице StudyDocumentLink. Поиск в рамках Study А не видит документы Study Б.
      2. Физическую изоляцию проектов: создание документа в файле project_1.db физически никак не влияет на файл project_2.db.
   * ACCEPTANCE: Тесты гарантируют стопроцентную изоляцию данных на уровне исследований и отдельных проектных файлов.
* STOP_CONDITIONS: Если тесты требуют модификации схемы данных или добавления колонок доступа в таблицу Document.

## TASK: E02-T21-CONCURRENT-READ-WRITE-TEST

* GOAL: Проверить систему на отсутствие race conditions при параллельном чтении и записи.
* CONTEXT: Тестовая задача для верификации паттерна Single-Writer / Multi-Reader в режиме WAL.
* ALLOWED_FILES:
* tests/data/test_concurrent_read_write.py
* FORBIDDEN: Изменение продуктового кода.
* IMPLEMENTATION DETAILS:
* Инициализируй базу и DbWriter. Запусти 3 параллельных потока (threading.Thread), которые массово отправляют запросы на запись Project через DbWriter.submit().
   * Одновременно запусти 2 читающих потока, которые через прямые соединения create_connection() непрерывно выполняют SELECT COUNT(*) из таблицы проектов.
* ACCEPTANCE: Все транзакции на запись завершаются успешно (без ошибок SQLITE_BUSY благодаря busy_timeout и DbWriter), а читатели всегда видят консистентное состояние.
* STOP_CONDITIONS: Возникновение взаимных блокировок (Deadlocks) или падение потоков по таймауту.

## TASK: E02-T22-DETERMINISTIC-FIXTURES

* GOAL: Создать стабильные, воспроизводимые фикстуры тестовых данных.
* CONTEXT: Исключает фактор случайности. Код тестов должен быть воспроизводим на любых машинах.
* ALLOWED_FILES:
* tests/data/fixtures.py
   * tests/data/test_deterministic_fixtures.py
* FORBIDDEN: Использование модуля random, генераторов случайных UUID или текущего системного времени.
* IMPLEMENTATION DETAILS:
* В файле fixtures.py зафиксируй константные UUID для проектов, исследований, источников и документов. Напиши функции заполнения соединения conn базовым набором связанных сущностей (эпистемическая цепочка). Функции не должны сами вызывать коммит.
* TESTS: Проверить, что два последовательных вызова фикстуры генерируют абсолютно идентичные слепки данных с неизменными хэшами.
* ACCEPTANCE: База детерминированных фикстур готова к использованию во всех последующих EPIC.
* STOP_CONDITIONS: Использование динамических или случайных генераторов данных в фикстурах.

## TASK: E02-T23-FTS5-READINESS-TEST

* GOAL: Проверить архитектурную готовность реляционной схемы к интеграции текстового поиска.
* CONTEXT: Чисто проверочная задача. EPIC-02 не настраивает сам поиск FTS5, но гарантирует совместимость полей.
* ALLOWED_FILES:
* tests/data/test_fts5_readiness.py
* FORBIDDEN: Создание виртуальных таблиц USING fts5 (это задача EPIC-04).
* IMPLEMENTATION DETAILS:
* Напиши тест, проверяющий структуру таблицы DocumentChunk: она обязана иметь стабильный chunk_id (PRIMARY KEY), текст чанка (text), и точные числовые указатели позиций (char_start, char_end, position_index), которые понадобятся для синхронизации с поисковым индексом на CPU.
* ACCEPTANCE: Тест подтверждает полную совместимость полей реляционной структуры с будущим IR-слоем.
* STOP_CONDITIONS: Обнаружение реального поискового индекса FTS5 в схеме базы данных.

## TASK: E02-T24-DATA-INTEGRATION-TEST

* GOAL: Финальный сквозной интеграционный тест слоя хранения данных (Gate G-02).
* CONTEXT: Проверяет весь контур EPIC-02 в единой связке на базе детерминированных фикстур.
* ALLOWED_FILES:
* tests/data/test_data_integration.py
* FORBIDDEN: Подключение модулей MCP, интерфейсов GUI или эвристик ЛЛМ.
* IMPLEMENTATION DETAILS:
* Разверни в tmp_path файл проекта и файл реестра. Запусти DbWriter с поддержкой прикрепления реестра.
   * Через DbWriter.submit() последовательно запиши полную эпистемическую цепочку: от Project до Evidence, включая вызовы атомарной синхронизации документов в глобальный реестр.
   * Проверить идемпотентность (повторный апсерт дубликатов). Проверить изоляцию Study. Выполни checkpoint, сделай backup_database и восстанови бэкап в третью чистую базу. Проверить финальную консистентность восстановленного файла.
* TESTS: Весь интеграционный сценарий упакован в этот файл.
* ACCEPTANCE: Тест успешно проходит, подтверждая выполнение всех критериев Definition of Done для Gate G-02.
* STOP_CONDITIONS: Если для выполнения теста требуется доступ к сети Интернет или запущенная модель ИИ.

------------------------------
## 3. Критерии готовности (Definition of Done) для EPIC-02

* Миграции разделены на 4 изолированных файла, накат происходит последовательно и идемпотентно.
* Все подключения создаются строго через create_connection и получают полный набор PRAGMA (foreign_keys=ON).
* Все операции записи внутри репозиториев изолированы от вызовов commit/rollback и выполняются через транзакционный контур DbWriter.
* Глобальный реестр синхронизируется с проектными БД атомарно на уровне СУБД с помощью механизма ATTACH DATABASE.
* Резервное копирование использует только метод Connection.backup.
* Все тесты полностью изолированы, работают CPU-only и используют абсолютные пути относительно файлов тестов.

------------------------------



