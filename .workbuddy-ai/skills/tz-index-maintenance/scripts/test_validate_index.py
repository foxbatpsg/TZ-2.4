"""Регрессии статусов Q-06/Q-07; только стандартная библиотека."""
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).with_name("validate_index.py")
SPEC = importlib.util.spec_from_file_location("validate_index", SCRIPT)
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)
ROOT = SCRIPT.parents[4]


def row(norm, status="open"):
    return f"| **{norm}** | Тема | — | — | `status: {status}` |\n"


class StatusTests(unittest.TestCase):
    def setUp(self):
        # Логика проверяется на паре Q-06/Q-07 независимо от текущего состояния корпуса.
        patcher = patch.object(validator, "OPEN_QUESTIONS", {"Q-06", "Q-07"})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.index = "## 4. Реестр решений\n" + row("Q-06") + row("Q-07")

    def test_open_questions_without_definitions(self):
        opened, gaps, errors = validator.collect_index_exceptions(self.index, {}, set())
        self.assertEqual(opened, {"Q-06", "Q-07"})
        self.assertEqual(gaps, set())
        self.assertEqual(errors, [])

    def test_mentions_do_not_close_an_open_question(self):
        opened, _, errors = validator.collect_index_exceptions(self.index, {}, {"Q-06"})
        self.assertIn("Q-06", opened)
        self.assertEqual(errors, [])

    def test_invalid_registry_rows(self):
        variants = [
            self.index.replace(row("Q-06"), ""),
            self.index.replace(row("Q-06"), row("Q-06", "gap")),
            self.index.replace(row("Q-06"), row("Q-06", "closed")),
            self.index.replace("`status: open`", "OPEN", 1),
            self.index + row("Q-06"),
            self.index.replace("## 4.", "## 9."),
        ]
        for text in variants:
            with self.subTest(text=text):
                opened, _, errors = validator.collect_index_exceptions(text, {}, set())
                self.assertNotIn("Q-06", opened)
                self.assertTrue(errors)

    def test_definition_requires_removing_open_exception(self):
        opened, _, errors = validator.collect_index_exceptions(
            self.index, {"Q-06": ["source.md"]}, {"Q-06"}
        )
        self.assertNotIn("Q-06", opened)
        self.assertTrue(errors)

    def test_true_gap_requires_matching_status_and_no_mentions(self):
        with patch.object(validator, "ALLOWED_GAPS", {"Q-99"}):
            text = self.index + row("Q-99", "gap")
            _, gaps, errors = validator.collect_index_exceptions(text, {}, set())
            self.assertEqual(gaps, {"Q-99"})
            self.assertEqual(errors, [])
            for candidate, mentions in [(self.index, set()), (text, {"Q-99"})]:
                _, gaps, errors = validator.collect_index_exceptions(candidate, {}, mentions)
                self.assertFalse(gaps)
                self.assertTrue(errors)

    def test_real_corpus_cli_positive_and_negative(self):
        # Реальный корпус: штатный OPEN_QUESTIONS пуст (Q-06 и Q-07 закрыты 2026-09-16).
        original = (ROOT / "INDEX.md").read_text(encoding="utf-8")
        variants = [
            (original, 0),
            ("\n".join(line for line in original.splitlines()
                       if not line.startswith("| **Q-07** |")), 0),
            (original + "\nФантом Q-99\n", 1),
        ]
        # Копируются только перечисленные нормативные файлы, не архив и не карточки.
        # Штатный OPEN_QUESTIONS пуст — переопределяем патч класса setUp().
        with patch.object(validator, "OPEN_QUESTIONS", set()), \
             tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for rel in validator.CORPUS_FILES + validator.APPENDIX_FILES:
                target = root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / rel).read_bytes())
            for text, expected in variants:
                with self.subTest(expected=expected, text=text[:30]):
                    # Остальные реальные ссылки проверяет штатный запуск на рабочем корпусе.
                    with patch.object(validator, "check_index_files_exist", return_value=[]), \
                         patch.object(validator.sys, "argv", [str(SCRIPT), "--root", directory]):
                        (root / "INDEX.md").write_text(text, encoding="utf-8")
                        output = io.StringIO()
                        with contextlib.redirect_stdout(output):
                            result = validator.main()
                        self.assertEqual(result, expected, output.getvalue())
                        if expected == 0:
                            self.assertIn("РЕЗУЛЬТАТ: PASS", output.getvalue())
        # Регрессия формата: открытый вопрос требует строки §4 с `status: open`.
        with patch.object(validator, "OPEN_QUESTIONS", {"Q-07"}), \
             tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for rel in validator.CORPUS_FILES + validator.APPENDIX_FILES:
                target = root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / rel).read_bytes())
            with patch.object(validator, "check_index_files_exist", return_value=[]), \
                 patch.object(validator.sys, "argv", [str(SCRIPT), "--root", directory]):
                (root / "INDEX.md").write_text(original, encoding="utf-8")
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    result = validator.main()
                self.assertEqual(result, 1, output.getvalue())
                self.assertIn("Q-07: нужна одна строка реестра §4", output.getvalue())


if __name__ == "__main__":
    unittest.main()
