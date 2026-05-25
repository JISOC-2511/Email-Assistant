# tests/test_summary.py

import pytest
from unittest.mock import MagicMock
from summary import get_all_chunks, build_summary_prompt, generate_summary


# ── helpers ───────────────────────────────────────────────────────────────────

def make_chunk(content="sample content", filename="test.eml"):
    return {"content": content, "filename": filename, "score": 0.2}


def make_openai_response(text: str):
    mock = MagicMock()
    mock.choices[0].message.content = text
    return mock


# ── get_all_chunks ────────────────────────────────────────────────────────────

def test_get_all_chunks_returns_list(monkeypatch):
    """Should always return a list."""
    monkeypatch.setattr("summary.retrieve_chunks", lambda q, k: [])
    result = get_all_chunks()
    assert isinstance(result, list)

def test_get_all_chunks_deduplicates(monkeypatch):
    """Same chunk content returned by multiple queries should only appear once."""
    monkeypatch.setattr("summary.retrieve_chunks", lambda q, k: [
        make_chunk("duplicate content", "a.eml")
    ])
    result = get_all_chunks()
    contents = [c["content"] for c in result]
    assert contents.count("duplicate content") == 1

def test_get_all_chunks_uses_default_queries(monkeypatch):
    """Should work with no arguments — default queries should be used."""
    called_with = []
    def mock_retrieve(q, k):
        called_with.append(q)
        return []
    monkeypatch.setattr("summary.retrieve_chunks", mock_retrieve)
    get_all_chunks()
    assert len(called_with) > 0

def test_get_all_chunks_accepts_custom_queries(monkeypatch):
    """Should use provided queries instead of defaults when given."""
    called_with = []
    def mock_retrieve(q, k):
        called_with.append(q)
        return []
    monkeypatch.setattr("summary.retrieve_chunks", mock_retrieve)
    get_all_chunks(sample_queries=["custom query one", "custom query two"])
    assert called_with == ["custom query one", "custom query two"]

def test_get_all_chunks_multiple_files(monkeypatch):
    """Chunks from different files should all be included."""
    calls = {"n": 0}
    def mock_retrieve(q, k):
        calls["n"] += 1
        return [make_chunk(f"content {calls['n']}", f"file{calls['n']}.eml")]
    monkeypatch.setattr("summary.retrieve_chunks", mock_retrieve)
    result = get_all_chunks(sample_queries=["q1", "q2"])
    filenames = [c["filename"] for c in result]
    assert "file1.eml" in filenames
    assert "file2.eml" in filenames

def test_get_all_chunks_empty_db(monkeypatch):
    """Should return empty list when ChromaDB has no documents."""
    monkeypatch.setattr("summary.retrieve_chunks", lambda q, k: [])
    result = get_all_chunks()
    assert result == []


# ── build_summary_prompt ──────────────────────────────────────────────────────

def test_build_summary_prompt_returns_string():
    """Should always return a string."""
    result = build_summary_prompt([make_chunk()])
    assert isinstance(result, string := str)

def test_build_summary_prompt_includes_content():
    """Chunk content should appear in the prompt."""
    chunk = make_chunk(content="invoice overdue by 30 days")
    result = build_summary_prompt([chunk])
    assert "invoice overdue by 30 days" in result

def test_build_summary_prompt_includes_filename():
    """Source filename should appear in the prompt for context."""
    chunk = make_chunk(filename="finance_report.pdf")
    result = build_summary_prompt([chunk])
    assert "finance_report.pdf" in result

def test_build_summary_prompt_multiple_chunks():
    """All chunks should appear in the prompt."""
    chunks = [
        make_chunk("first chunk content", "a.eml"),
        make_chunk("second chunk content", "b.pdf"),
    ]
    result = build_summary_prompt(chunks)
    assert "first chunk content" in result
    assert "second chunk content" in result

# ── generate_summary ──────────────────────────────────────────────────────────

def test_generate_summary_empty_db(monkeypatch):
    """Should return a helpful message when no documents are uploaded."""
    monkeypatch.setattr("summary.get_all_chunks", lambda: [])
    result = generate_summary()
    assert result["summary"] == "No documents have been uploaded yet."
    assert result["sources"] == []

def test_build_summary_prompt_mentions_none_identified(monkeypatch):
    captured = {}
    monkeypatch.setattr("summary.get_all_chunks", lambda: [make_chunk()])
    def mock_create(**kwargs):
        captured["messages"] = kwargs["messages"]
        return make_openai_response("summary")
    monkeypatch.setattr("summary.client.chat.completions.create", mock_create)
    generate_summary()
    assert "None identified" in captured["messages"][0]["content"]

def test_generate_summary_returns_correct_keys(monkeypatch):
    """Result must always have summary and sources keys."""
    monkeypatch.setattr("summary.get_all_chunks", lambda: [
        make_chunk("some content", "report.pdf")
    ])
    monkeypatch.setattr(
        "summary.client.chat.completions.create",
        lambda **kwargs: make_openai_response("Executive summary here.")
    )
    result = generate_summary()
    assert "summary" in result
    assert "sources" in result

def test_generate_summary_includes_llm_response(monkeypatch):
    """Summary field should contain the text returned by GPT."""
    monkeypatch.setattr("summary.get_all_chunks", lambda: [make_chunk()])
    monkeypatch.setattr(
        "summary.client.chat.completions.create",
        lambda **kwargs: make_openai_response("Key deadlines: March 3rd invoice due.")
    )
    result = generate_summary()
    assert "March 3rd" in result["summary"]

def test_generate_summary_deduplicates_sources(monkeypatch):
    """Same filename across multiple chunks should appear once in sources."""
    monkeypatch.setattr("summary.get_all_chunks", lambda: [
        make_chunk("chunk one", "emails.eml"),
        make_chunk("chunk two", "emails.eml"),
        make_chunk("chunk three", "report.pdf"),
    ])
    monkeypatch.setattr(
        "summary.client.chat.completions.create",
        lambda **kwargs: make_openai_response("Summary text.")
    )
    result = generate_summary()
    assert result["sources"].count("emails.eml") == 1
    assert len(result["sources"]) == 2

def test_generate_summary_system_message_first(monkeypatch):
    """System message must be the first message sent to the LLM."""
    captured = {}
    monkeypatch.setattr("summary.get_all_chunks", lambda: [make_chunk()])
    def mock_create(**kwargs):
        captured["messages"] = kwargs["messages"]
        return make_openai_response("summary")
    monkeypatch.setattr("summary.client.chat.completions.create", mock_create)
    generate_summary()
    assert captured["messages"][0]["role"] == "system"

def test_generate_summary_sources_match_chunks(monkeypatch):
    """Sources list should only contain filenames from retrieved chunks."""
    monkeypatch.setattr("summary.get_all_chunks", lambda: [
        make_chunk("content", "only_this_file.eml")
    ])
    monkeypatch.setattr(
        "summary.client.chat.completions.create",
        lambda **kwargs: make_openai_response("Summary.")
    )
    result = generate_summary()
    assert result["sources"] == ["only_this_file.eml"]