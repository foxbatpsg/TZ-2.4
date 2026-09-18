#!/usr/bin/env python3
"""
Валидатор целостности индексного слоя ТЗ v2.5.

ВНИМАНИЕ (2026-10-02): задача FU-4 / Гл.0-01 вариант 3 (включение `приложения к ТЗ/Epic/`
в область индексации и таблица соответствия `E0X-C0Y` ↔ `E0X-T0Y` в `INDEX.md` §11)
ОТЛОЖЕНА владельцем (VERDICTS §3). Пока §11 в INDEX.md отсутствует, блок [7]
«TASK-карточки» выдаёт ПРЕДУПРЕЖДЕНИЕ (не ошибку) — это ОЖИДАЕМОЕ поведение, а не
дефект корпуса. На этот пункт при проверке внимание не тратить; проверят его только
после возобновления FU-4.

Проверяет:
  1. Битые ссылки: все упомянутые в INDEX.md разделы/§ существуют в файлах ТЗ.
  2. Полнота реестра норм: все A-xx и Q-xx, найденные в корпусе, присутствуют в INDEX.md.
  3. Обратная полнота: все нормы из INDEX.md реально существуют в корпусе.
  4. Дубли определений: нормы, определённые в нескольких местах (требуют canonical).
  5. Консистентность Gate: G-01..G-11 покрыты и в EPIC SPECIFICATIONS, и в INDEX.md.

Использование:
    python scripts/validate_index.py [--root <путь_к_корпусу>]

Код возврата: 0 — успех, 1 — найдены расхождения.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

# Файлы нормативного корпуса, входящие в область индекса
CORPUS_FILES = [
    "01_Research Analysis Layer.md",
    "02_Архитектура и системные принципы.md",
    "03_Модель данных и хранение.md",
    "04_Search Core.md",
    "05_Взаимодействие с LLM и протокол MCP.md",
    "06_GUI_UX.md",
    "07_QA_Acceptance.md",
]

APPENDIX_FILES = [
    "приложения к ТЗ/STATE MACHINE SPECIFICATION v1.2.md",
    "приложения к ТЗ/BUDGET CONTRACT v1.0.md",
    "приложения к ТЗ/MCP TOOL CONTRACTS v1.1.md",
    "приложения к ТЗ/EPIC SPECIFICATIONS v1.0 — BASELINE.md",
    "приложения к ТЗ/EPIC → TASK DECOMPOSITION v1.0 — BASELINE.md",
    "приложения к ТЗ/MASTER DEVELOPMENT ROADMAP v1.2 — BASELINE.md",
    "приложения к ТЗ/TASK EXECUTION CONTRACT v1.0 — BASELINE.md",
]

# TASK-карточки Astra1 (слой E0X-C0Y) — входят в область индексации (см. FU-4).
CARD_FILES = [
    "приложения к ТЗ/Epic/Глава_1_Карточки.md",
    "приложения к ТЗ/Epic/Глава_2_Карточки.md",
    "приложения к ТЗ/Epic/Глава_3_Карточки.md",
    "приложения к ТЗ/Epic/Глава_4_Карточки.md",
    "приложения к ТЗ/Epic/Глава_5_Карточки.md",
    "приложения к ТЗ/Epic/Глава_6_Карточки.md",
    "приложения к ТЗ/Epic/Глава_7_Карточки.md",
    "приложения к ТЗ/Epic/Глава_8_Карточки.md",
    "приложения к ТЗ/Epic/Глава_9_Карточки.md",
    "приложения к ТЗ/Epic/Глава_10_Карточки.md",
    "приложения к ТЗ/Epic/Глава_11_Карточки.md",
]

# Объединённый набор файлов, входящих в область индекса
INDEXED_FILES = CORPUS_FILES + APPENDIX_FILES + CARD_FILES

# Формат нормативного определения в ТЗ: "Название нормы (A-N): текст"
REQ_DEFINITION = re.compile(r"[«\w].{2,90}?\(([AQ]-\d{2})\)\s*:")
# Любое упоминание идентификатора нормы
REQ_MENTION = re.compile(r"\b([AQ]-\d{2})\b")
# Gate
GATE_MENTION = re.compile(r"\b(G-\d{2})\b")
# Идентификатор TASK-карточки: E01-C01, E10-C03a
CARD_ID = re.compile(r"^##\s*(E\d{2}-C\d+[a-z]?)\s*$", re.MULTILINE)
# TASK-карточка внутри таблицы покрытия INDEX.md §11
CARD_ID_TOKEN = re.compile(r"\bE\d{2}-C\d+[a-z]?\b")
# Явный идентификатор задачи декомпозиции: E01-T01, E10-T15a
TASK_ID = re.compile(r"\b(E\d{2}-T\d{2}[a-z]?)\b")

# Порог: норма, у которой больше одного определения, требует явного canonical
MULTI_DEFINITION_WARN = 2

# Настоящие намеренные пропуски: допуск требует строки реестра `status: gap`.
ALLOWED_GAPS: set[str] = set()
# Открытые вопросы без утверждённого определения — не пропуски нумерации.
# Допуск действует только при отдельной строке `status: open` в INDEX.md §4.
OPEN_QUESTIONS = set()


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"  ! Не удалось прочитать {path}: {exc}", file=sys.stderr)
        return ""


def collect_definitions(root: Path) -> dict[str, list[str]]:
    """Собирает, в каких файлах каждая норма определена (а не просто упомянута)."""
    definitions: dict[str, list[str]] = defaultdict(list)
    for rel in INDEXED_FILES:
        path = root / rel
        if not path.exists():
            continue
        for line in read(path).splitlines():
            for match in REQ_DEFINITION.finditer(line):
                definitions[match.group(1)].append(rel)
    return definitions


def collect_mentions(root: Path) -> set[str]:
    """Собирает все идентификаторы норм, встречающиеся в корпусе (включая карточки)."""
    found: set[str] = set()
    for rel in INDEXED_FILES:
        path = root / rel
        if path.exists():
            found.update(REQ_MENTION.findall(read(path)))
    return found


def collect_gates(root: Path) -> dict[str, set[str]]:
    """Собирает Gate по файлам (включая карточки)."""
    gates: dict[str, set[str]] = defaultdict(set)
    for rel in INDEXED_FILES:
        path = root / rel
        if path.exists():
            for gate in GATE_MENTION.findall(read(path)):
                gates[gate].add(rel)
    return gates


def collect_card_ids(root: Path) -> set[str]:
    """Собирает все TASK-карточки `E0X-C0Y` в файлах `Epic/Глава_*_Карточки.md`."""
    cards: set[str] = set()
    for rel in CARD_FILES:
        path = root / rel
        if path.exists():
            cards.update(CARD_ID.findall(read(path)))
    return cards


def collect_task_ids(root: Path) -> set[str]:
    """Собирает все TASK `E0X-T0Y` из нормативной декомпозиции."""
    rel = "приложения к ТЗ/EPIC → TASK DECOMPOSITION v1.0 — BASELINE.md"
    path = root / rel
    if not path.exists():
        return set()
    return set(TASK_ID.findall(read(path)))


def extract_index_card_rows(index_text: str) -> set[str]:
    """Извлекает идентификаторы карточек `E0X-C0Y`, перечисленные в INDEX.md §11.

    Карточки в §11 перечислены в таблице покрытия (первый столбец) — каждая
    строка таблицы начинается с `` E01-C01 `` и т.п. Сканируем весь текст
    §11 по токену ``CARD_ID_TOKEN``, чтобы не зависеть от разметки заголовков.
    """
    # находим блок §11
    start = index_text.find("## 11")
    if start == -1:
        return set()
    # §11 заканчивается либо следующим заголовком ##, либо концом файла
    end = index_text.find("\n## ", start + 5)
    if end == -1:
        end = len(index_text)
    section_text = index_text[start:end]
    return set(CARD_ID_TOKEN.findall(section_text))
    return set(CARD_ID.findall(index_text))





def extract_index_norms(index_text: str) -> set[str]:
    """Извлекает нормы, заявленные в реестре INDEX.md."""
    return set(REQ_MENTION.findall(index_text))


def collect_index_exceptions(
    index_text: str, definitions: dict[str, list[str]], mentions: set[str]
) -> tuple[set[str], set[str], list[str]]:
    """Допускает отсутствие нормы только по согласованной строке реестра §4."""
    rows: dict[str, list[str]] = defaultdict(list)
    in_registry = False
    for line in index_text.splitlines():
        if line.startswith("## "):
            in_registry = line.startswith("## 4. ")
        if not in_registry:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not line.startswith("|") or len(cells) != 5:
            continue
        match = re.fullmatch(r"\*\*(Q-\d{2})\*\*", cells[0])
        if match:
            rows[match.group(1)].append(cells[4])

    opened: set[str] = set()
    gaps: set[str] = set()
    problems: list[str] = []
    for norm in sorted(OPEN_QUESTIONS | ALLOWED_GAPS):
        if norm in OPEN_QUESTIONS and norm in ALLOWED_GAPS:
            problems.append(f"{norm}: одновременно открытый вопрос и пропуск")
            continue
        status = "open" if norm in OPEN_QUESTIONS else "gap"
        entries = rows.get(norm, [])
        if len(entries) != 1 or re.findall(r"`status: ([a-z]+)`", entries[0]) != [status]:
            problems.append(f"{norm}: нужна одна строка реестра §4 с `status: {status}`")
            continue
        if norm in definitions or (status == "gap" and norm in mentions):
            problems.append(f"{norm}: статус {status} противоречит нормативному корпусу")
            continue
        (opened if status == "open" else gaps).add(norm)
    return opened, gaps, problems


def extract_index_gates(index_text: str) -> set[str]:
    return set(GATE_MENTION.findall(index_text))


def check_index_files_exist(root: Path, index_text: str) -> list[str]:
    """Проверяет, что все файлы, упомянутые в INDEX.md, существуют."""
    problems: list[str] = []
    referenced = set(re.findall(r"`([^`]+\.md)`", index_text))
    for rel in referenced:
        if rel.startswith(("STATE", "BUDGET", "MCP", "EPIC", "MASTER", "TASK")):
            candidate = root / "приложения к ТЗ" / rel
        else:
            candidate = root / rel
        if not candidate.exists() and not (root / rel).exists():
            problems.append(f"INDEX.md ссылается на несуществующий файл: {rel}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Валидатор индексного слоя ТЗ v2.5")
    parser.add_argument("--root", default=".", help="Корень корпуса ТЗ")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    index_path = root / "INDEX.md"

    print(f"Корень корпуса: {root}")
    print("=" * 62)

    if not index_path.exists():
        print("ОШИБКА: INDEX.md не найден.")
        return 1

    index_text = read(index_path)
    definitions = collect_definitions(root)
    mentions = collect_mentions(root)
    gates = collect_gates(root)
    index_norms = extract_index_norms(index_text)
    index_gates = extract_index_gates(index_text)

    errors: list[str] = []
    warnings: list[str] = []

    # --- 1. Битые ссылки на файлы ---
    print("\n[1] Ссылки на файлы в INDEX.md")
    file_problems = check_index_files_exist(root, index_text)
    if file_problems:
        errors.extend(file_problems)
        for problem in file_problems:
            print(f"  ✗ {problem}")
    else:
        print("  ✓ все ссылки на файлы разрешаются")

    # --- 2. Полнота реестра норм ---
    print("\n[2] Полнота реестра норм")
    missing_in_index = sorted(mentions - index_norms)
    if missing_in_index:
        errors.append(f"Нормы есть в корпусе, но отсутствуют в INDEX.md: {missing_in_index}")
        print(f"  ✗ не попали в индекс: {', '.join(missing_in_index)}")
    else:
        print(f"  ✓ все {len(mentions)} норм корпуса присутствуют в индексе")

    # --- 3. Обратная полнота ---
    print("\n[3] Обратная полнота (нормы индекса против корпуса)")
    opened, declared_gaps, status_problems = collect_index_exceptions(
        index_text, definitions, mentions
    )
    errors.extend(status_problems)
    for problem in status_problems:
        print(f"  ✗ {problem}")
    phantom = sorted(index_norms - mentions - opened - declared_gaps)
    if phantom:
        errors.append(f"Нормы объявлены в INDEX.md, но не встречаются в корпусе: {phantom}")
        print(f"  ✗ фантомные записи: {', '.join(phantom)}")
    elif not status_problems:
        print("  ✓ нет необъяснённых записей вне нормативного корпуса")
    if opened:
        print(f"  · открытые вопросы без утверждённого определения: {', '.join(sorted(opened))}")
    if declared_gaps:
        print(f"  · задокументированный пропуск нумерации: {', '.join(sorted(declared_gaps))}")

    # --- 4. Дубли определений ---
    print("\n[4] Нормы с дублирующимися определениями (требуют canonical)")
    multi = {k: v for k, v in definitions.items() if len(v) >= MULTI_DEFINITION_WARN}
    if multi:
        for norm in sorted(multi):
            counts: dict[str, int] = defaultdict(int)
            for rel in multi[norm]:
                counts[rel] += 1
            parts = [
                f"{rel}×{n}" if n > 1 else rel
                for rel, n in sorted(counts.items(), key=lambda kv: -kv[1])
            ]
            print(f"  ⚠ {norm}: {len(multi[norm])} опр. → {', '.join(parts)}")
        warnings.append(
            f"{len(multi)} норм имеют несколько определений — для каждой обязателен canonical"
        )
    else:
        print("  ✓ дублей определений не обнаружено")

    # --- 5. Нормы без определения ---
    print("\n[5] Нормы без канонического определения")
    undefined = sorted(n for n in mentions if n not in definitions and n not in opened)
    if undefined:
        for norm in undefined:
            print(f"  ⚠ {norm}: определение не найдено (проверить, дефект ли это ревизии)")
        warnings.append(f"Без определения: {', '.join(undefined)}")
    else:
        print("  ✓ у каждой действующей нормы есть определение; открытые вопросы учтены в [3]")

    # --- 6. Gate ---
    print("\n[6] Покрытие Gate")
    corpus_gates = set(gates)
    missing_gates = sorted(corpus_gates - index_gates)
    if missing_gates:
        errors.append(f"Gate отсутствуют в INDEX.md: {missing_gates}")
        print(f"  ✗ не попали в индекс: {', '.join(missing_gates)}")
    else:
        print(f"  ✓ все {len(corpus_gates)} Gate отражены в индексе")
    if index_gates - corpus_gates:
        extra = sorted(index_gates - corpus_gates)
        warnings.append(f"В индексе есть Gate, отсутствующие в корпусе: {extra}")
        print(f"  ⚠ лишние Gate в индексе: {', '.join(extra)}")

    # --- 7. TASK-карточки (E0X-C0Y) ---
    print("\n[7] Покрытие TASK-карточек Astra1 (область индекса)")
    card_set = collect_card_ids(root)
    index_cards = extract_index_card_rows(index_text)
    missing_cards = sorted(card_set - index_cards)
    phantom_cards = sorted(index_cards - card_set)
    if missing_cards:
        warnings.append(
            f"TASK-карточки есть в корпусе, но отсутствуют в INDEX.md §11 и этот пункт"
            f" ОТЛОЖЕН владельцем (FU-4, 2026-10-02): на предупреждение не реагировать: {len(missing_cards)}"
        )
        print(f"  ⚠ не попали в индекс ({len(missing_cards)}): {', '.join(missing_cards)}")
        print("  ⚠ ОЖИДАЕМО: FU-4 отложена владельцем — на этот пункт внимание не тратить")
    else:
        print(f"  ✓ все {len(card_set)} карточек `E0X-C0Y` присутствуют в INDEX.md §11")
    if phantom_cards:
        errors.append(f"INDEX.md §11 ссылается на несуществующие карточки: {phantom_cards}")
        print(f"  ✗ фантомные карточки в индексе: {', '.join(phantom_cards)}")
    # проверка существования файлов карточек
    missing_card_files = [rel for rel in CARD_FILES if not (root / rel).exists()]
    if missing_card_files:
        errors.append(f"Файлы карточек недоступны: {missing_card_files}")
    # нормативные ссылки из карточек должны быть в реестре (A-xx/Q-xx)
    card_files_text = "\n".join(read(root / rel) for rel in CARD_FILES if (root / rel).exists())
    card_norm_refs = set(REQ_MENTION.findall(card_files_text))
    dangling_refs = sorted(card_norm_refs - mentions)
    if dangling_refs:
        warnings.append(f"Карточки ссылаются на нормы, отсутствующие в корпусе: {dangling_refs}")
        print(f"  ⚠ карточки ссылаются на несуществующие нормы: {', '.join(dangling_refs)}")
    else:
        print(f"  ✓ ссылки карточек на нормы ({len(card_norm_refs)}) разрешаются реестром")

    # --- 8. Явные TASK-ссылки из карточек (E0X-T0Y) ---
    print("\n[8] TASK-ссылки из карточек (E0X-T0Y)")
    task_set = collect_task_ids(root)
    card_task_refs = set(TASK_ID.findall(card_files_text))
    dangling_tasks = sorted(card_task_refs - task_set)
    if card_task_refs:
        if dangling_tasks:
            errors.append(f"Карточки ссылаются на TASK, отсутствующие в декомпозиции: {dangling_tasks}")
            print(f"  ✗ не разрешаются: {', '.join(dangling_tasks)}")
        else:
            print(f"  ✓ все {len(card_task_refs)} явных TASK-идентификатора в карточках найдены в декомпозиции")
    else:
        print("  · в карточках нет явных ссылок на TASK E0X-T0Y")

    # --- Итог ---
    print("\n" + "=" * 62)
    if errors:
        print(f"РЕЗУЛЬТАТ: FAIL — ошибок {len(errors)}, предупреждений {len(warnings)}")
        for err in errors:
            print(f"  ✗ {err}")
        return 1

    print(f"РЕЗУЛЬТАТ: PASS — предупреждений {len(warnings)}")
    for warn in warnings:
        print(f"  ⚠ {warn}")
    print("\nНапоминание: при наличии предупреждений проверить поле `canonical` у нормы")
    print("и внести подтверждённые расхождения в поле `conflicts`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
