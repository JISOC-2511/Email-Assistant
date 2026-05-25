# tests/test_query.py

import pytest
from unittest.mock import MagicMock, patch
from query import retrieve_chunks, build_context, answer_query
from query import ai_risk_check, retrieve_risk_chunks


# ── helpers ──────────────────────────────────────────────────────────────────

def make_chunk(content="some text", filename="test.eml", score=0.25):
    """Builds a chunk dict matching the shape retrieve_chunks returns."""
    return {"content": content, "filename": filename, "score": score}


def make_mock_doc(content="some text", filename="test.eml"):
    """Builds a mock LangChain Document object."""
    doc = MagicMock()
    doc.page_content = content
    doc.metadata = {"filename": filename}
    return doc


# ── retrieve_chunks ───────────────────────────────────────────────────────────

def test_retrieve_chunks_returns_list(monkeypatch):
    """Should always return a list."""
    mock_db = MagicMock()
    mock_db.similarity_search_with_score.return_value = [
        (make_mock_doc("chunk one", "a.eml"), 0.2),
        (make_mock_doc("chunk two", "b.pdf"), 0.4),
    ]
    monkeypatch.setattr("query.Chroma", lambda **kwargs: mock_db)
    monkeypatch.setattr("query.OpenAIEmbeddings", lambda: None)

    result = retrieve_chunks("what are the deadlines?")
    assert isinstance(result, list)

def test_retrieve_chunks_correct_shape(monkeypatch):
    """Each item must have content, filename, and score keys."""
    mock_db = MagicMock()
    mock_db.similarity_search_with_score.return_value = [
        (make_mock_doc("hello", "invoice.csv"), 0.3),
    ]
    monkeypatch.setattr("query.Chroma", lambda **kwargs: mock_db)
    monkeypatch.setattr("query.OpenAIEmbeddings", lambda: None)

    result = retrieve_chunks("any question")
    assert result[0]["content"] == "hello"
    assert result[0]["filename"] == "invoice.csv"
    assert "score" in result[0]

def test_retrieve_chunks_empty_db(monkeypatch):
    """Should return empty list when ChromaDB has no results."""
    mock_db = MagicMock()
    mock_db.similarity_search_with_score.return_value = []
    monkeypatch.setattr("query.Chroma", lambda **kwargs: mock_db)
    monkeypatch.setattr("query.OpenAIEmbeddings", lambda: None)

    result = retrieve_chunks("anything")
    assert result == []

def test_retrieve_chunks_respects_k(monkeypatch):
    """Should pass k through to similarity_search_with_score."""
    mock_db = MagicMock()
    mock_db.similarity_search_with_score.return_value = []
    monkeypatch.setattr("query.Chroma", lambda **kwargs: mock_db)
    monkeypatch.setattr("query.OpenAIEmbeddings", lambda: None)

    retrieve_chunks("question", k=3)
    mock_db.similarity_search_with_score.assert_called_once_with("question", k=3)


# ── build_context ─────────────────────────────────────────────────────────────

def test_build_context_returns_tuple():
    """Should return a tuple of (str, list)."""
    chunks = [make_chunk()]
    result = build_context(chunks)
    assert isinstance(result, tuple)
    assert len(result) == 2

def test_build_context_labels_sources():
    """Context string should contain [Source 1], [Source 2] etc."""
    chunks = [
        make_chunk("first chunk", "a.eml"),
        make_chunk("second chunk", "b.pdf"),
    ]
    context, _ = build_context(chunks)
    assert "[Source 1]" in context
    assert "[Source 2]" in context

def test_build_context_includes_content():
    """Chunk content should appear in the context string."""
    chunks = [make_chunk(content="invoice overdue by 30 days")]
    context, _ = build_context(chunks)
    assert "invoice overdue by 30 days" in context

def test_build_context_deduplicates_sources():
    """Same filename appearing in multiple chunks should only appear once in sources."""
    chunks = [
        make_chunk("chunk one", "emails.eml"),
        make_chunk("chunk two", "emails.eml"),
        make_chunk("chunk three", "report.pdf"),
    ]
    _, sources = build_context(chunks)
    assert sources.count("emails.eml") == 1
    assert len(sources) == 2

def test_build_context_preserves_source_order():
    """Sources list should preserve first-seen order, not sort arbitrarily."""
    chunks = [
        make_chunk(filename="b.pdf"),
        make_chunk(filename="a.eml"),
    ]
    _, sources = build_context(chunks)
    assert sources[0] == "b.pdf"
    assert sources[1] == "a.eml"

def test_build_context_includes_filename_in_label():
    """Each source label should include the filename."""
    chunks = [make_chunk(content="text", filename="contracts.pdf")]
    context, _ = build_context(chunks)
    assert "contracts.pdf" in context


# ── answer_query ──────────────────────────────────────────────────────────────

def make_mock_openai_response(answer_text: str):
    """Builds a mock OpenAI API response matching the shape of the real one."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = answer_text
    return mock_response


def test_answer_query_empty_chunks(monkeypatch):
    """Should return early with a helpful message if no chunks are retrieved."""
    monkeypatch.setattr("query.retrieve_chunks", lambda q: [])
    result = answer_query("any question")
    assert result["answer"] == "No relevant documents found."
    assert result["sources"] == []

def test_answer_query_returns_answer_and_sources(monkeypatch):
    """Happy path — should return answer text and source filenames."""
    monkeypatch.setattr("query.retrieve_chunks", lambda q: [
        make_chunk("the deadline is March 3rd", "emails.eml")
    ])
    monkeypatch.setattr(
        "query.client.chat.completions.create",
        lambda **kwargs: make_mock_openai_response("The deadline is March 3rd [Source 1]")
    )
    result = answer_query("what are the deadlines?")
    assert "deadline" in result["answer"].lower()
    assert "emails.eml" in result["sources"]

def test_answer_query_correct_keys(monkeypatch):
    """Result dict must always have exactly 'answer' and 'sources' keys."""
    monkeypatch.setattr("query.retrieve_chunks", lambda q: [
        make_chunk("some content", "report.pdf")
    ])
    monkeypatch.setattr(
        "query.client.chat.completions.create",
        lambda **kwargs: make_mock_openai_response("Here is the answer.")
    )
    result = answer_query("a question")
    assert "answer" in result
    assert "sources" in result

def test_answer_query_passes_context_to_llm(monkeypatch):
    """The user message sent to the LLM must contain both context and question."""
    captured = {}
    monkeypatch.setattr("query.retrieve_chunks", lambda q: [
        make_chunk("relevant content", "data.csv")
    ])
    def mock_create(**kwargs):
        captured["messages"] = kwargs["messages"]
        return make_mock_openai_response("answer")
    monkeypatch.setattr("query.client.chat.completions.create", mock_create)

    answer_query("what is the risk level?")
    user_msg = captured["messages"][1]["content"]
    assert "relevant content" in user_msg
    assert "what is the risk level?" in user_msg

def test_answer_query_system_message_present(monkeypatch):
    """A system message must be sent to the LLM — it's what enforces citation behaviour."""
    captured = {}
    monkeypatch.setattr("query.retrieve_chunks", lambda q: [make_chunk()])
    def mock_create(**kwargs):
        captured["messages"] = kwargs["messages"]
        return make_mock_openai_response("answer")
    monkeypatch.setattr("query.client.chat.completions.create", mock_create)

    answer_query("question")
    assert captured["messages"][0]["role"] == "system"
    assert len(captured["messages"][0]["content"]) > 0

def make_ai_response(content: str):
    """Builds a mock OpenAI response with the given content string."""
    mock = MagicMock()
    mock.choices[0].message.content = content
    return mock

def test_ai_risk_check_high_risk(monkeypatch):
    """Should return risky=True and High Risk for genuinely risky content."""
    monkeypatch.setattr(
        "query.client.chat.completions.create",
        lambda **kwargs: make_ai_response(
            '{"risky": true, "risk_score": "High Risk", "reason": "Active fraud allegation."}'
        )
    )
    result = ai_risk_check("We have detected fraud in the accounts.")
    assert result["risky"] is True
    assert result["risk_score"] == "High Risk"
    assert "reason" in result

def test_ai_risk_check_low_risk_negation(monkeypatch):
    """Should return risky=False when negation makes content safe."""
    monkeypatch.setattr(
        "query.client.chat.completions.create",
        lambda **kwargs: make_ai_response(
            '{"risky": false, "risk_score": "Low Risk", "reason": "Negation present — no actual breach."}'
        )
    )
    result = ai_risk_check("There was no breach of contract.")
    assert result["risky"] is False
    assert result["risk_score"] == "Low Risk"

def test_ai_risk_check_medium_risk(monkeypatch):
    """Should return Medium Risk for speculative mentions."""
    monkeypatch.setattr(
        "query.client.chat.completions.create",
        lambda **kwargs: make_ai_response(
            '{"risky": true, "risk_score": "Medium Risk", "reason": "Speculative legal mention."}'
        )
    )
    result = ai_risk_check("There could potentially be legal implications.")
    assert result["risk_score"] == "Medium Risk"

def test_ai_risk_check_bad_json_fallback(monkeypatch):
    """If GPT returns malformed JSON, should fall back to safe defaults."""
    monkeypatch.setattr(
        "query.client.chat.completions.create",
        lambda **kwargs: make_ai_response("sorry I cannot answer that")
    )
    result = ai_risk_check("some text")
    assert result["risky"] is False
    assert result["risk_score"] == "Low Risk"
    assert "reason" in result

def test_ai_risk_check_returns_required_keys(monkeypatch):
    """Response must always contain risky, risk_score, and reason keys."""
    monkeypatch.setattr(
        "query.client.chat.completions.create",
        lambda **kwargs: make_ai_response(
            '{"risky": true, "risk_score": "High Risk", "reason": "Fraud detected."}'
        )
    )
    result = ai_risk_check("fraud occurred")
    assert "risky" in result
    assert "risk_score" in result
    assert "reason" in result


# ── retrieve_risk_chunks ──────────────────────────────────────────────────────

def make_chunk(content="risky text", filename="emails.eml", score=0.2):
    return {"content": content, "filename": filename, "score": score}

def test_retrieve_risk_chunks_returns_list(monkeypatch):
    """Should always return a list."""
    monkeypatch.setattr("query.retrieve_chunks", lambda q, k: [])
    result = retrieve_risk_chunks()
    assert isinstance(result, list)

def test_retrieve_risk_chunks_skips_low_risk(monkeypatch):
    """Chunks that pass stage 1 as Low Risk should never reach the LLM."""
    llm_called = {"called": False}

    monkeypatch.setattr("query.retrieve_chunks", lambda q, k: [
        make_chunk("completely normal business update")
    ])
    monkeypatch.setattr("query.analyse_text", lambda t: {
        "risk_score": "Low Risk", "flagged": False,
        "risk_keywords": [], "personal_info": {}
    })
    def mock_llm(text):
        llm_called["called"] = True
        return {"risky": True, "risk_score": "High Risk", "reason": "test"}
    monkeypatch.setattr("query.ai_risk_check", mock_llm)

    retrieve_risk_chunks()
    assert llm_called["called"] is False

def test_retrieve_risk_chunks_includes_llm_flagged(monkeypatch):
    """Chunks that pass stage 1 and are flagged by LLM should be included."""
    monkeypatch.setattr("query.retrieve_chunks", lambda q, k: [
        make_chunk("fraud was committed", "report.pdf")
    ])
    monkeypatch.setattr("query.analyse_text", lambda t: {
        "risk_score": "High Risk", "flagged": True,
        "risk_keywords": ["fraud"], "personal_info": {}
    })
    monkeypatch.setattr("query.ai_risk_check", lambda t: {
        "risky": True, "risk_score": "High Risk", "reason": "Active fraud."
    })

    result = retrieve_risk_chunks()
    assert len(result) == 1
    assert result[0]["filename"] == "report.pdf"
    assert result[0]["risk_score"] == "High Risk"
    assert "reason" in result[0]

def test_retrieve_risk_chunks_excludes_llm_cleared(monkeypatch):
    """Chunks that pass stage 1 but are cleared by LLM should NOT be included."""
    monkeypatch.setattr("query.retrieve_chunks", lambda q, k: [
        make_chunk("there was no breach of contract")
    ])
    monkeypatch.setattr("query.analyse_text", lambda t: {
        "risk_score": "Medium Risk", "flagged": True,
        "risk_keywords": ["breach"], "personal_info": {}
    })
    monkeypatch.setattr("query.ai_risk_check", lambda t: {
        "risky": False, "risk_score": "Low Risk", "reason": "Negation present."
    })

    result = retrieve_risk_chunks()
    assert result == []

def test_retrieve_risk_chunks_deduplicates(monkeypatch):
    """Same chunk content appearing for multiple concepts should only be processed once."""
    call_count = {"n": 0}

    monkeypatch.setattr("query.retrieve_chunks", lambda q, k: [
        make_chunk("fraud and breach detected", "a.eml")
    ])
    monkeypatch.setattr("query.analyse_text", lambda t: {
        "risk_score": "High Risk", "flagged": True,
        "risk_keywords": ["fraud"], "personal_info": {}
    })
    def counting_llm(text):
        call_count["n"] += 1
        return {"risky": True, "risk_score": "High Risk", "reason": "Fraud."}
    monkeypatch.setattr("query.ai_risk_check", counting_llm)

    retrieve_risk_chunks()
    assert call_count["n"] == 1

def test_retrieve_risk_chunks_correct_shape(monkeypatch):
    """Each returned chunk must have all required keys."""
    monkeypatch.setattr("query.retrieve_chunks", lambda q, k: [
        make_chunk("invoice dispute unresolved", "finance.eml")
    ])
    monkeypatch.setattr("query.analyse_text", lambda t: {
        "risk_score": "High Risk", "flagged": True,
        "risk_keywords": ["invoice dispute"], "personal_info": {}
    })
    monkeypatch.setattr("query.ai_risk_check", lambda t: {
        "risky": True, "risk_score": "High Risk", "reason": "Active dispute."
    })

    result = retrieve_risk_chunks()
    assert "content" in result[0]
    assert "filename" in result[0]
    assert "risk_score" in result[0]
    assert "risk_keywords" in result[0]
    assert "personal_info" in result[0]
    assert "reason" in result[0]