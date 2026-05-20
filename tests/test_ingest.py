import pytest
from ingest import parse_csv, parse_email, parse_pdf, ingest_doc


# ── parse_csv ────────────────────────────────────────────────────────────────

def test_parse_csv_basic():
    """Standard CSV — should produce one labelled line per data row."""
    raw = b"name,amount,status\nAlice,5000,Overdue\nBob,1200,Paid"
    result = parse_csv(raw)
    assert "Row 1" in result
    assert "Row 2" in result
    assert "name=Alice" in result
    assert "status=Overdue" in result

def test_parse_csv_any_columns():
    """Must work with arbitrary column names, not just name/amount/status."""
    raw = b"date,sender,subject\n2024-01-01,alice@corp.com,Q1 Report"
    result = parse_csv(raw)
    assert "date=2024-01-01" in result
    assert "sender=alice@corp.com" in result

def test_parse_csv_returns_string():
    """Return type must always be str, never None."""
    result = parse_csv(b"a,b\n1,2")
    assert isinstance(result, str)

def test_parse_csv_empty_values():
    """Empty cells should appear as key= without crashing."""
    raw = b"name,amount\nAlice,"
    result = parse_csv(raw)
    assert "amount=" in result

def test_parse_csv_header_only():
    """A CSV with only a header row and no data should return empty string."""
    result = parse_csv(b"name,amount,status")
    assert result == ""

def test_parse_csv_row_count():
    """Number of 'Row N' labels should equal number of data rows."""
    raw = b"a,b\n1,2\n3,4\n5,6"
    result = parse_csv(raw)
    assert result.count("Row") == 3


# ── parse_email ───────────────────────────────────────────────────────────────

def make_eml(subject="Test", sender="alice@example.com",
             date="Mon, 1 Jan 2024 10:00:00 +0000", body="Hello world") -> bytes:
    """Builds a minimal valid .eml as bytes."""
    return (
        f"From: {sender}\n"
        f"Date: {date}\n"
        f"Subject: {subject}\n"
        f"Content-Type: text/plain\n\n"
        f"{body}"
    ).encode()

def test_parse_email_subject():
    assert "Invoice Dispute" in parse_email(make_eml(subject="Invoice Dispute"))

def test_parse_email_sender():
    assert "bob@company.com" in parse_email(make_eml(sender="bob@company.com"))

def test_parse_email_body():
    assert "Please review the attached report." in parse_email(
        make_eml(body="Please review the attached report.")
    )

def test_parse_email_returns_string():
    assert isinstance(parse_email(make_eml()), str)

def test_parse_email_missing_date():
    """Should not crash when optional headers are absent."""
    raw = b"From: alice@x.com\nSubject: No Date\nContent-Type: text/plain\n\nBody"
    result = parse_email(raw)
    assert "Body" in result

def test_parse_email_multipart():
    """Multipart emails — should extract the text/plain part."""
    raw = (
        b"From: alice@x.com\nSubject: Multi\n"
        b"Content-Type: multipart/mixed; boundary=\"boundary\"\n\n"
        b"--boundary\n"
        b"Content-Type: text/plain\n\n"
        b"This is the plain text body\n"
        b"--boundary\n"
        b"Content-Type: text/html\n\n"
        b"<p>HTML version</p>\n"
        b"--boundary--"
    )
    result = parse_email(raw)
    assert "This is the plain text body" in result


# ── parse_pdf ────────────────────────────────────────────────────────────────

def make_blank_pdf() -> bytes:
    """Creates a real minimal PDF in memory — no file needed."""
    from pypdf import PdfWriter
    from io import BytesIO
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = BytesIO()
    writer.write(buf)
    return buf.getvalue()

def test_parse_pdf_returns_string():
    """Blank PDF should return a string, not crash."""
    result = parse_pdf(make_blank_pdf())
    assert isinstance(result, str)

def test_parse_pdf_bad_bytes():
    """Garbage bytes should raise an exception, not silently return None."""
    with pytest.raises(Exception):
        parse_pdf(b"this is not a pdf")

def test_parse_pdf_concatenates_pages():
    """
    Since you do full_text += page.extract_text(), verify multi-page
    PDFs don't return only the first page.
    Note: pypdf blank pages return empty string from extract_text(),
    so this just checks it doesn't crash on multiple pages.
    """
    from pypdf import PdfWriter
    from io import BytesIO
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.add_blank_page(width=200, height=200)
    buf = BytesIO()
    writer.write(buf)
    result = parse_pdf(buf.getvalue())
    assert isinstance(result, str)


# ── ingest_doc ───────────────────────────────────────────────────────────────

def test_ingest_doc_splits_and_stores(monkeypatch):
    """Text should be split into chunks and all chunks passed to add_texts."""
    captured = {}

    class FakeDB:
        def add_texts(self, texts, metadatas):
            captured["texts"] = texts
            captured["metadatas"] = metadatas
        def persist(self):
            captured["persisted"] = True

    monkeypatch.setattr("ingest.Chroma", lambda **kwargs: FakeDB())
    monkeypatch.setattr("ingest.OpenAIEmbeddings", lambda: None)

    ingest_doc("word " * 400, metadata={"filename": "test.eml"})

    assert len(captured["texts"]) > 1
    assert captured.get("persisted") is True

def test_ingest_doc_metadata_matches_chunks(monkeypatch):
    """Each chunk must have its own copy of the metadata dict."""
    captured = {}

    class FakeDB:
        def add_texts(self, texts, metadatas):
            captured["n_texts"] = len(texts)
            captured["n_meta"] = len(metadatas)
        def persist(self): pass

    monkeypatch.setattr("ingest.Chroma", lambda **kwargs: FakeDB())
    monkeypatch.setattr("ingest.OpenAIEmbeddings", lambda: None)

    ingest_doc("word " * 400, metadata={"filename": "report.pdf"})
    assert captured["n_texts"] == captured["n_meta"]

def test_ingest_doc_returns_none(monkeypatch):
    """ingest_doc should return None — it's a side-effect function."""
    class FakeDB:
        def add_texts(self, texts, metadatas): pass
        def persist(self): pass

    monkeypatch.setattr("ingest.Chroma", lambda **kwargs: FakeDB())
    monkeypatch.setattr("ingest.OpenAIEmbeddings", lambda: None)

    result = ingest_doc("some text", metadata={"filename": "x.csv"})
    assert result is None