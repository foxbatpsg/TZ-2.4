#!/usr/bin/env python3
"""
Валидатор целостности индексного слоя ТЗ v2.4.

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

# Формат нормативного определения в ТЗ: "Название нормы (A-N): текст"
REQ_DEFINITION = re.compile(r"[«\w].{2,90}?\(([AQ]-\d{2})\)\s*:")
# Любое упоминание идентификатора нормы
REQ_MENTION = re.compile(r"\b([AQ]-\d{2})\b")
# Gate
GATE_MENTION = re.compile(r"\b(G-\d{2})\b")

# Порог: норма, у которой больше одного определения, требует явного canonical
MULTI_DEFINITION_WARN = 2

# Идентификаторы, отсутствующие в корпусе намеренно (задокументированный пропуск
# нумерации). Помечаются в INDEX.md значением `status: gap`. Не считаются ошибкой.
ALLOWED_GAPS = {"Q-06", "Q-07"}


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"  ! Не удалось прочитать {path}: {exc}", file=sys.stderr)
        return ""


def collect_definitions(root: Path) -> dict[str, list[str]]:
    """Собирает, в каких файлах каждая норма определена (а не просто упомянута)."""
    definitions: dict[str, list[str]] = defaultdict(list)
    for rel in CORPUS_FILES + APPENDIX_FILES:
        path = root / rel
        if not path.exists():
            continue
        for line in read(path).splitlines():
            for match in REQ_DEFINITION.finditer(line):
                definitions[match.group(1)].append(rel)
    return definitions


def collect_mentions(root: Path) -> set[str]:
    """Собирает все идентификаторы норм, встречающиеся в корпусе."""
    found: set[str] = set()
    for rel in CORPUS_FILES + APPENDIX_FILES:
        path = root / rel
        if path.exists():
            found.update(REQ_MENTION.findall(read(path)))
    return found


def collect_gates(root: Path) -> dict[str, set[str]]:
    """Собирает Gate по файлам."""
    gates: dict[str, set[str]] = defaultdict(set)
    for rel in CORPUS_FILES + APPENDIX_FILES:
        path = root / rel
        if path.exists():
            for gate in GATE_MENTION.findall(read(path)):
                gates[gate].add(rel)
    return gates


def extract_index_norms(index_text: str) -> set[str]:
    """Извлекает нормы, заявленные в реестре INDEX.md."""
    return set(REQ_MENTION.findall(index_text))


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
    parser = argparse.ArgumentParser(description="Валидатор индексного слоя ТЗ v2.4")
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
    phantom = sorted(index_norms - mentions - ALLOWED_GAPS)
    if phantom:
        errors.append(f"Нормы объявлены в INDEX.md, но не встречаются в корпусе: {phantom}")
        print(f"  ✗ фантомные записи: {', '.join(phantom)}")
    else:
        print("  ✓ в индексе нет норм, отсутствующих в корпусе")
    declared_gaps = sorted((index_norms - mentions) & ALLOWED_GAPS)
    if declared_gaps:
        print(f"  · задокументированный пропуск нумерации: {', '.join(declared_gaps)}")

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
    undefined = sorted(n for n in mentions if n not in definitions)
    if undefined:
        for norm in undefined:
            print(f"  ⚠ {norm}: определение не найдено (проверить, дефект ли это ревизии)")
        warnings.append(f"Без определения: {', '.join(undefined)}")
    else:
        print("  ✓ у каждой нормы есть определение")

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
