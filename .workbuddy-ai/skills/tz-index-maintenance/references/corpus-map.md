# Карта нормативного корпуса ТЗ v2.7

**Область индексации:** 7 разделов основного ТЗ + 7 приложений + `ARCHITECTURE.md` (производный).
**Baseline:** `TZ-2.7 @ 9a5731e` (ревизия v2.7 — после переносов решений `Q-06`/`Q-07`; 2026-09-16), ветка `master`.

## Иерархия приоритета документов

```
ТЗ v2.7 (разделы 01–07)
  ↓
State Machine Spec v1.2 / MCP Tool Contracts v1.1 / Budget Contract v1.0
  ↓
MASTER DEVELOPMENT ROADMAP v1.2
  ↓
EPIC Specifications v1.0
  ↓
ARCHITECTURE.md (производный, не нормативный)
  ↓
TASK (карточка для агента)
```

При конфликте приоритет имеет документ выше по списку.

## Основное ТЗ

| Файл | Раздел | Объём | Область ответственности |
|---|---|---|---|
| `01_Research Analysis Layer.md` | 1 | 36 КБ | Роли LLM/Core, ResearchIntent, типы задач, эпистемическая цепочка, адаптивный цикл, **Sufficiency Criteria §7**, независимость источников |
| `02_Архитектура и системные принципы.md` | 2 | 26 КБ | Архитектурный закон, слои, режимы, **CPU-only baseline §5**, TokenBudgetManager §6a, resilience §7, Configuration Contract §8 |
| `03_Модель данных и хранение.md` | 3 | 63 КБ | Все сущности (§2–19), бюджетные таблицы §17c, outbox §17d, **DB-write layer §21**, изоляция и registry.db §25 |
| `04_Search Core.md` | 4 | 73 КБ | Конвейер §2, адаптеры §3–4, дедупликация §8, ранжирование §9, **BM25 §14 + RU-морфология §14.1**, Evidence §15, fingerprint §20, условия остановки §22 |
| `05_Взаимодействие с LLM и протокол MCP.md` | 5 | 48 КБ | Local LLM §1, Router §2, **MCP §3 + 23 инструмента §4**, Structured Outputs §10, Error Contract §16, Watchdog §17 |
| `06_GUI_UX.md` | 6 | 10 КБ | Main Thread/Worker §2, все представления, **Graceful Abort §9**, кооперативная отмена |
| `07_QA_Acceptance.md` | 7 | 25 КБ | Критерии приёмки по всем подсистемам, **Acceptance Criteria §25**, **MVP/Post-MVP §26**, фикстуры §28 |

## Нормативные приложения

| Файл | Что нормирует |
|---|---|
| `STATE MACHINE SPECIFICATION v1.2.md` | 6 FSM: Study, ResearchSession, SearchTask, MCP Operation, LLM Backend, Job |
| `BUDGET CONTRACT v1.0.md` | 7 dimensions, `reserve/commit/release/extend_budget` |
| `MCP TOOL CONTRACTS v1.1.md` | 23 инструмента с полными контрактами |
| `EPIC SPECIFICATIONS v1.0 — BASELINE.md` | Границы EPIC-01…11, **Gate G-01…G-11 (стр. 26–244)** |
| `EPIC → TASK DECOMPOSITION v1.0 — BASELINE.md` | Декомпозиция EPIC в TASK |
| `MASTER DEVELOPMENT ROADMAP v1.2 — BASELINE.md` | Последовательность, правила R-01…R-09 |
| `TASK EXECUTION CONTRACT v1.0 — BASELINE.md` | Context Header, `STOP → REPORT → WAIT`, формат сдачи |

## Где живёт какая категория норм

| Категория | Место |
|---|---|
| Архитектурные инварианты | `02` §2–3; `ARCHITECTURE` §1.4 (производное) |
| Правила целостности данных | `03` §1–2, §21–22 |
| Правила конвейера поиска | `04` §2–§27 |
| Контракты LLM/MCP | `05` §3–5, §16; MCP TOOL CONTRACTS |
| Требования GUI | `06` (целиком); `07` §22 |
| Критерии приёмки | `07` (целиком); Gate в EPIC SPECIFICATIONS |
| FSM-переходы | STATE MACHINE SPECIFICATION v1.2 |
| Бюджетная модель | BUDGET CONTRACT v1.0; `03` §17c; `01` §6a |
| Границы EPIC и Gate | EPIC SPECIFICATIONS v1.0 |

## Что не входит в индекс

| Объект | Причина |
|---|---|
| `Research_Prompt_Suite_Task_Cards_Astra1/` (11 файлов) | Производные инструкции, не нормы |
| `замечания GPT6.md`, `SUGGESTIONS.md` | Ревью-артефакты, не нормы |
| `корзина/` | Архив |
| `корзина/REVIEW-REGISTRY.md` | Реестр решений по замечаниям (отдельный слой) |
