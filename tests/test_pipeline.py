"""Offline tests for the parts of the pipeline that don't need network/API.

Run with: ``python tests/test_pipeline.py``
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from scrape_essays import extract_essay_text, slugify  # noqa: E402
from tts import chunk_text  # noqa: E402


def test_slugify():
    assert slugify("How to Do Great Work") == "how-to-do-great-work"
    assert slugify("essay123") == "essay123"
    assert slugify("  spaced  out  ") == "spaced-out"
    assert slugify("!!!") == "essay"


def test_extract_essay_text():
    html = (
        "<html><body><table><tr><td>"
        "<font size=2>" + ("This is the essay body. " * 50) + "</font>"
        "</td></tr></table></body></html>"
    )
    text = extract_essay_text(html)
    assert "This is the essay body." in text
    assert len(text) > 200


def test_chunk_text_short():
    assert chunk_text("Hello world.", 100) == ["Hello world."]
    assert chunk_text("", 100) == []


def test_chunk_text_respects_limit():
    text = " ".join(f"Sentence number {i}." for i in range(200))
    chunks = chunk_text(text, 120)
    assert len(chunks) > 1
    assert all(len(c) <= 120 for c in chunks)
    # No content is lost (modulo whitespace normalisation).
    assert "Sentence number 0." in chunks[0]
    assert "Sentence number 199." in chunks[-1]


def test_chunk_text_hard_wraps_long_unit():
    long_word_run = "word " * 1000  # one "sentence" far longer than the limit
    chunks = chunk_text(long_word_run.strip(), 100)
    assert all(len(c) <= 100 for c in chunks)


def _run_all():
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {name}: {exc}")
    if failures:
        raise SystemExit(f"{failures} test(s) failed")
    print("All tests passed.")


if __name__ == "__main__":
    _run_all()
