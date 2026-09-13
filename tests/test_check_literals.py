"""Behavior tests for the optional, read-only literal comparison CLI."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills" / "human-ton" / "scripts" / "check_literals.py"
)
CATEGORIES = {"numbers", "urls", "quotes", "code", "protected"}


class CheckLiteralsTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="human ton literals ")
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.before = self.root / "before text.txt"
        self.after = self.root / "after text.txt"

    def invoke(self, *arguments, expected=0):
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), *map(str, arguments)],
            cwd=self.root, capture_output=True, text=True, encoding="utf-8",
            timeout=10,
        )
        self.assertEqual(result.returncode, expected, result.stderr + result.stdout)
        self.assertTrue(result.stdout.strip(), result.stderr)
        self.assertEqual(result.stderr, "")
        report = json.loads(result.stdout)
        self.assertEqual(report["semantic_equivalence"], "not_checked")
        self.assertTrue(report["limitations"])
        return report

    def compare(self, before, after, *protected, expected=0):
        self.before.write_text(before, encoding="utf-8")
        self.after.write_text(after, encoding="utf-8")
        options = [arg for value in protected for arg in ("--protect", value)]
        report = self.invoke(self.before, self.after, *options, expected=expected)
        self.assertEqual(
            report["status"],
            "no_literal_changes" if expected == 0 else "needs_review",
        )
        self.assertEqual(set(report["categories"]), CATEGORIES)
        return report

    def delta(self, report, category, missing=None, added=None):
        self.assertEqual(
            report["categories"][category],
            {"missing": missing or {}, "added": added or {}},
        )

    def test_paraphrase_retains_literals(self):
        report = self.compare(
            '김민수는 2026-09-13에 1,200명에게 "준비 완료"라고 말했다. '
            '대기는 20ms, 비율은 3.5%p다. `run()`과 https://example.org/v1 참고.',
            'https://example.org/v1 및 `run()` 참고: 2026-09-13, '
            '김민수가 전한 말은 "준비 완료". 1,200명 기준 3.5%p이며 대기는 20ms다.',
            "김민수",
        )
        for category in CATEGORIES:
            self.delta(report, category)

    def test_changed_number(self):
        report = self.compare("참여 12명", "참여 13명", expected=1)
        self.delta(report, "numbers", {"12명": 1}, {"13명": 1})

    def test_changed_common_units(self):
        pairs = [
            ("10ms", "10s"), ("3.5%", "3.5%p"), ("1 KB", "1 MB"),
            ("1MB", "1GB"), ("5명", "5건"), ("5개", "5원"),
            ("2년", "2월"), ("2월", "2일"), ("2시간", "2분"),
        ]
        for before, after in pairs:
            with self.subTest(before=before, after=after):
                report = self.compare(before, after, expected=1)
                self.delta(report, "numbers", {before: 1}, {after: 1})

    def test_decimals_grouping_dates_and_signed_numbers(self):
        literals = [
            "-1,234.50원", "−0.25", "+.5%", "±2 ms", "$-3.50",
            "₩1,000", "2026-09-13", "2026/9/13", "2026.09.13",
            "2026년", "9월", "13일",
        ]
        report = self.compare(" / ".join(literals), "모두 삭제", expected=1)
        self.delta(report, "numbers", dict.fromkeys(literals, 1))

    def test_number_unit_does_not_consume_start_of_english_prose(self):
        report = self.compare("10 seconds elapsed", "We waited 10 seconds")
        self.delta(report, "numbers")
        report = self.compare("10 samples", "10 samples; 20 sessions", expected=1)
        self.delta(report, "numbers", added={"20": 1})

    def test_changes_inside_dates_are_detected_as_whole_dates(self):
        report = self.compare("2026-09-13", "2026-09-14", expected=1)
        self.delta(report, "numbers", {"2026-09-13": 1}, {"2026-09-14": 1})

    def test_changed_straight_and_curly_quotes(self):
        for opening, closing in [('"', '"'), ("“", "”"), ("‘", "’")]:
            with self.subTest(opening=opening):
                report = self.compare(
                    opening + "ready" + closing,
                    opening + "waiting" + closing, expected=1,
                )
                self.delta(report, "quotes", {"ready": 1}, {"waiting": 1})

    def test_quote_delimiter_style_can_change(self):
        self.compare('He said "ready".', "“ready” was his answer.")

    def test_escaped_quote_inside_direct_quotation(self):
        report = self.compare(
            r'He said "call \"alpha\" now".',
            r'He said "call \"beta\" now".', expected=1,
        )
        self.delta(
            report, "quotes",
            {r'call \"alpha\" now': 1}, {r'call \"beta\" now': 1},
        )

    def test_prose_apostrophes_are_not_quoted_passages(self):
        report = self.compare(
            "I don't think it's Sam's fault; we can’t say it’s his.",
            "Sam is blameless in our view; we disagree.",
        )
        self.delta(report, "quotes")

    def test_curly_quoted_contraction_keeps_complete_content(self):
        report = self.compare("‘I can’t go’", "‘I won’t go’", expected=1)
        self.delta(report, "quotes", {"I can’t go": 1}, {"I won’t go": 1})

    def test_changed_inline_code_with_variable_tick_lengths(self):
        for before, after, old, new in [
            ("`x = 1`", "`x = 2`", "x = 1", "x = 2"),
            ("``x = `one` ``", "``x = `two` ``", "x = `one` ", "x = `two` "),
            ("```x``y```", "```x``z```", "x``y", "x``z"),
        ]:
            with self.subTest(before=before):
                report = self.compare(before, after, expected=1)
                self.delta(report, "code", {old: 1}, {new: 1})
                self.delta(report, "numbers")
                self.delta(report, "quotes")

    def test_both_fence_markers_and_longer_closing_fences(self):
        for opening, closing in [("```", "```"), ("~~~", "~~~~"), ("````", "`````")]:
            with self.subTest(opening=opening):
                before = opening + 'python\nprint("one")\n' + closing + "\n"
                after = opening + 'python\nprint("two")\n' + closing + "\n"
                report = self.compare(before, after, expected=1)
                self.delta(
                    report, "code", {'print("one")\n': 1}, {'print("two")\n': 1},
                )
                self.delta(report, "quotes")

    def test_shorter_fence_cannot_close_long_fence(self):
        report = self.compare(
            "````text\n```\nold\n```\n````\n",
            "````text\n```\nnew\n```\n````\n", expected=1,
        )
        self.delta(
            report, "code", {"```\nold\n```\n": 1}, {"```\nnew\n```\n": 1},
        )

    def test_fence_with_small_indent_and_different_marker(self):
        self.compare(
            "  ```python\nvalue = 1\n  ```\n",
            "   ~~~~python\nvalue = 1\n   ~~~~\n",
        )

    def test_code_quotes_do_not_swallow_neighboring_prose_quotes(self):
        code = '```text\n"unclosed quote 99\n```\n'
        report = self.compare(
            code + '`x = "` then "keep"', code + '`x = "` then "change"',
            expected=1,
        )
        self.delta(report, "quotes", {"keep": 1}, {"change": 1})
        self.delta(report, "code")
        self.delta(report, "numbers")

    def test_unclosed_fence_extends_to_eof(self):
        report = self.compare("~~~\nold", "~~~\nnew", expected=1)
        self.delta(report, "code", {"old": 1}, {"new": 1})

    def test_changed_url(self):
        report = self.compare(
            "Visit https://example.org/a?x=1&y=2.",
            "Visit https://example.org/b?x=1&y=2.", expected=1,
        )
        self.delta(
            report, "urls",
            {"https://example.org/a?x=1&y=2": 1},
            {"https://example.org/b?x=1&y=2": 1},
        )
        self.delta(report, "numbers")

    def test_terminal_url_punctuation_and_balanced_parentheses(self):
        self.compare(
            "See (https://example.org/wiki/Thing_(detail)). Also www.example.org!",
            "At https://example.org/wiki/Thing_(detail), see www.example.org.",
        )
        report = self.compare(
            "<https://example.org/wiki/Thing_(detail)>", "", expected=1,
        )
        self.delta(report, "urls", {"https://example.org/wiki/Thing_(detail)": 1})

    def test_protected_names_and_terms_are_exact_repeatable_strings(self):
        report = self.compare(
            "김민수 uses C++ and a.b", "김민서 uses C+ and axb",
            "김민수", "김민서", "C++", "a.b", expected=1,
        )
        self.delta(
            report, "protected",
            {"김민수": 1, "C++": 1, "a.b": 1}, {"김민서": 1},
        )

    def test_duplicate_deletion_in_each_category(self):
        for category, text, literal, protected in [
            ("numbers", "5명", "5명", []),
            ("quotes", '"same"', "same", []),
            ("code", "`run()`", "run()", []),
            ("urls", "https://example.org/", "https://example.org/", []),
            ("protected", "Alice", "Alice", ["Alice"]),
        ]:
            with self.subTest(category=category):
                report = self.compare(text + " " + text, text, *protected, expected=1)
                self.delta(report, category, {literal: 1})

    def test_duplicate_protect_options_do_not_multiply_counts(self):
        report = self.compare("Alice Alice", "Alice", "Alice", "Alice", expected=1)
        self.delta(report, "protected", {"Alice": 1})

    def test_protect_matches_inside_code_and_quotes(self):
        report = self.compare(
            '`Alice` and "Alice"', '`Bob` and "Bob"', "Alice", expected=1,
        )
        self.delta(report, "protected", {"Alice": 2})

    def test_multiset_number_swap_is_explicitly_not_semantic_validation(self):
        report = self.compare("Alice got 10; Bob got 20.", "Alice got 20; Bob got 10.")
        self.assertIn("multiset", " ".join(report["limitations"]).lower())
        self.assertEqual(report["semantic_equivalence"], "not_checked")

    def test_empty_files_and_unprotected_prose_pass(self):
        self.compare("", "")
        self.compare("Hello Alice, this is all new prose.", "안녕하세요, 문장을 고쳤어요.")

    def test_paths_with_spaces_are_read_without_modification_or_extra_files(self):
        before, after = "인원은 10명입니다.\r\n", "10명이 참여했습니다.\r\n"
        self.before.write_bytes(before.encode("utf-8"))
        self.after.write_bytes(after.encode("utf-8"))
        paths = set(self.root.iterdir())
        self.invoke(self.before, self.after)
        self.assertEqual(self.before.read_bytes(), before.encode("utf-8"))
        self.assertEqual(self.after.read_bytes(), after.encode("utf-8"))
        self.assertEqual(set(self.root.iterdir()), paths)

    def test_missing_file_returns_input_error(self):
        self.after.write_text("", encoding="utf-8")
        report = self.invoke(self.before, self.after, expected=2)
        self.assertTrue(report["error"])
        self.assertEqual(report["status"], "needs_review")

    def test_invalid_utf8_returns_input_error(self):
        self.before.write_bytes(b"\xff\xfe")
        self.after.write_text("", encoding="utf-8")
        report = self.invoke(self.before, self.after, expected=2)
        self.assertTrue(report["error"])

    def test_invalid_arguments_return_json_input_error(self):
        for arguments in [(), ("--unknown",), ("before", "after", "--protect", "")]:
            with self.subTest(arguments=arguments):
                report = self.invoke(*arguments, expected=2)
                self.assertTrue(report["error"])


if __name__ == "__main__":
    unittest.main()
