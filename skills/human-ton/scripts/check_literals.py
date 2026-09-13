#!/usr/bin/env python3
"""Optional, read-only UTF-8 literal comparison (Python 3.9+, stdlib only).

Usage: python3 check_literals.py BEFORE AFTER [--protect STRING]...
Comparisons and input/usage errors emit JSON to stdout; --help uses stderr.
Exit 0: collected literals unchanged; 1: review differences; 2: input error.
Neither exit 0 nor any other result establishes semantic equivalence.

Heuristic extraction, NOT a full Markdown parser or semantic validator:
* Numbers: ASCII digits, signs/currencies, comma grouping, decimal points,
  YYYY-MM-DD/slash/dot dates, and common units (including Korean suffixes).
  Locale-specific forms, spelled-out numbers and arbitrary units may be missed.
* URLs: http(s) and www; trim sentence punctuation and excess closing brackets.
  Literal URL-ending punctuation is ambiguous; protect the exact URL if needed.
* Quotes: straight double and paired curly quotes; ignore prose apostrophes.
* Code: backtick/tilde fences (0-3 spaces indent) and equal-length inline ticks.
  Unclosed fences extend to EOF. Nested containers, indented code, HTML,
  complex escapes and malformed markup are not fully supported.
* Compare exact contents, including whitespace; ignore quote/fence delimiters
  and fence info strings. Inline-code whitespace is not Markdown-normalized.
* --protect counts exact, case-sensitive, non-overlapping substrings everywhere.
  Repeated options are deduplicated. Names/terms are not inferred automatically.
Counts ignore context/order: swapping numbers with the same multiset is missed.
No files are written, and no rewrite or score is produced.
"""

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys


LIMITATIONS = [
    "Heuristic extraction, not a full Markdown parser: nested containers, "
    "indented code, HTML, complex escapes and malformed markup may be missed.",
    "Only common number/unit/date forms and http(s)/www URLs; "
    "literal URL-ending punctuation is ambiguous.",
    "Exact contents/whitespace are compared; quote/fence delimiters and fence "
    "info strings are ignored. Inline whitespace is not Markdown-normalized.",
    "Counts ignore context/order; swaps with the same multiset are undetected. "
    "Semantic equivalence is not checked.",
    "Unlisted names/terms need --protect; protected substrings are exact, "
    "case-sensitive, non-overlapping matches.",
]

FENCE = re.compile(r"(?m)^ {0,3}(`{3,}|~{3,})([^\r\n]*)(?:\r?\n|$)")
INLINE = re.compile(r"(?<![\\`])(`+)(?!`)([^\x00]*?)(?<!`)\1(?!`)")
QUOTES = re.compile(
    r'(?<!\\)"(?:\\.|[^"\\])*"'
    r"|“(?:\\.|[^”\\])*”"
    r"|‘(?:\\.|(?<=[A-Za-z])’(?=[A-Za-z])|[^’\\])*’",
    re.DOTALL,
)
URL = re.compile(r"""(?:https?://|www\.)[^\s<>"`“”‘’\x00]+""", re.IGNORECASE)
UNITS = (
    r"(?:%p|%|(?:[KMGT]i?B|B|ns|[µμu]s|ms|s|min|h|"
    r"GHz|MHz|kHz|Hz|mm|cm|km|m|mg|kg|g|ml|l|°[CF])(?![A-Za-z_])|"
    r"개월|시간|명|건|개|원|년|월|일|분|초|주|회|대|배|점)"
)
NUMBER = re.compile(
    r"(?<![A-Za-z0-9_])(?:"
    r"[0-9]{4}[-/.][0-9]{1,2}[-/.][0-9]{1,2}|"
    r"[+\-−±]?(?:[$€£¥₩][ \t]*[+\-−±]?)?"
    r"(?:(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?|\.[0-9]+)"
    r"(?:[ \t]*" + UNITS + r")?)",
    re.IGNORECASE,
)


def mask(text, spans):
    """Hide syntax without shifting offsets or joining neighboring tokens."""
    chars = list(text)
    for start, end in spans:
        chars[start:end] = re.sub(r"[^\r\n]", "\x00", text[start:end])
    return "".join(chars)


def extract_code(text):
    code, spans, consumed = Counter(), [], 0
    for opening in FENCE.finditer(text):
        if opening.start() < consumed:
            continue
        ticks, info = opening.group(1, 2)
        if ticks[0] == "`" and "`" in info:
            continue  # A same-line triple-tick span is not a fenced block.
        closing = re.search(
            rf"(?m)^ {{0,3}}{re.escape(ticks[0])}{{{len(ticks)},}}"
            r"[ \t]*(?:\r?\n|$)",
            text[opening.end():],
        )
        body_end = opening.end() + closing.start() if closing else len(text)
        consumed = opening.end() + closing.end() if closing else len(text)
        code[text[opening.end():body_end]] += 1
        spans.append((opening.start(), consumed))
    prose = mask(text, spans)
    for match in INLINE.finditer(prose):
        code[text[match.start(2):match.end(2)]] += 1
        spans.append(match.span())
    return code, mask(text, spans)


def trim_url(url):
    pairs = {")": "(", "]": "[", "}": "{"}
    while url:
        last = url[-1]
        if last in ".,;:!?" or (
            last in pairs and url.count(last) > url.count(pairs[last])
        ):
            url = url[:-1]
        else:
            break
    return url


def collect(text, protected):
    code, prose = extract_code(text)
    urls = list(URL.finditer(prose))
    numbers_prose = mask(prose, [match.span() for match in urls])
    return {
        "numbers": Counter(match.group() for match in NUMBER.finditer(numbers_prose)),
        "urls": Counter(trim_url(match.group()) for match in urls),
        "quotes": Counter(
            text[match.start() + 1:match.end() - 1]
            for match in QUOTES.finditer(prose)
        ),
        "code": code,
        "protected": Counter({term: text.count(term) for term in set(protected)}),
    }


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)

    def print_help(self, file=None):
        super().print_help(file=sys.stderr if file is None else file)


def main(argv=None):
    parser = JsonArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    parser.add_argument("before", metavar="BEFORE", type=Path)
    parser.add_argument("after", metavar="AFTER", type=Path)
    parser.add_argument(
        "--protect", action="append", default=[], metavar="STRING",
        help="count an exact nonempty substring; repeat for multiple literals",
    )
    report = {
        "status": "needs_review",
        "semantic_equivalence": "not_checked",
        "categories": {},
        "limitations": LIMITATIONS,
    }
    try:
        args = parser.parse_args(argv)
        if "" in args.protect:
            parser.error("--protect requires a nonempty string")
        before = collect(args.before.read_bytes().decode("utf-8"), args.protect)
        after = collect(args.after.read_bytes().decode("utf-8"), args.protect)
    except (OSError, UnicodeError, ValueError) as error:
        report["error"] = str(error)
        exit_code = 2
    else:
        report["categories"] = {
            name: {
                "missing": dict(sorted((before[name] - after[name]).items())),
                "added": dict(sorted((after[name] - before[name]).items())),
            }
            for name in before
        }
        changed = any(
            delta["missing"] or delta["added"]
            for delta in report["categories"].values()
        )
        report["status"] = "needs_review" if changed else "no_literal_changes"
        exit_code = int(changed)
    print(json.dumps(report, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
