from __future__ import annotations

from pathlib import Path

from app.voice.transcript import (
    chunk_text,
    clean_transcript,
    load_corpus,
    persona_from_filename,
)

LESSON_DIR = Path(__file__).resolve().parents[2] / "lesson"

SAMPLE = (
    "[00:00](https://youtu.be/jJAEK2QhGyE?t=0)(https://youtu.be/jJAEK2QhGyE?t=0) "
    "bahwa ketika kita berhenti\n"
    "[00:12](https://youtu.be/jJAEK2QhGyE?t=12)(https://youtu.be/jJAEK2QhGyE?t=12) [Musik]\n"
    "[00:15](https://youtu.be/jJAEK2QhGyE?t=15)(https://youtu.be/jJAEK2QhGyE?t=15) welcome back"
)


def test_clean_transcript_removes_timestamps_and_links():
    out = clean_transcript(SAMPLE)
    assert "youtu.be" not in out
    assert "[00:00]" not in out
    assert "[Musik]" not in out
    assert "bahwa ketika kita berhenti" in out
    assert "welcome back" in out


def test_persona_from_filename():
    assert persona_from_filename("nessie-ajaran-sesat-di-desa.txt") == "nessie"
    assert persona_from_filename("nadia-bunda.txt") == "nadia"


def test_chunk_text_sizes():
    text = "kata " * 1000
    chunks = chunk_text(text, chunk_chars=1500, overlap=150)
    assert chunks
    assert all(len(c) <= 1500 for c in chunks)


def test_load_real_corpus_two_personas():
    if not LESSON_DIR.exists():
        return
    corpus = load_corpus(LESSON_DIR)
    assert "nessie" in corpus
    assert "nadia" in corpus
    for _persona, files in corpus.items():
        for _fname, text in files:
            assert "youtu.be" not in text
            assert len(text) > 1000
