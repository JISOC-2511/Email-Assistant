from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from io import BytesIO, StringIO

import email, pypdf, csv, extract_msg

def parse_email(fileBytes) -> str:
    msg = email.message_from_bytes(fileBytes)
    body = ""
    if msg.is_multipart():
        for section in msg.walk():
            if section.get_content_type() == "text/plain":
                body += section.get_payload(decode=True).decode()
    else:
        body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
    subject = msg.get("Subject", "")
    sender = msg.get("From", "")
    date = msg.get("Date", "")
    return f"Subject: {subject}\nFrom: {sender}\nDate: {date}\n\n{body}"


def ingest_doc(text, metadata) -> None:
    splitter = RecursiveCharacterTextSplitter(chunk_size = 512, chunk_overlap = 52)
    chunks = splitter.split_text(text)
    embeddings = OpenAIEmbeddings()
    db = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    db.add_texts(chunks, metadatas=[metadata] * len(chunks))
    db.persist()


def parse_pdf(file_bytes: bytes) -> str:
    buffer = BytesIO(file_bytes)
    reader = pypdf.PdfReader(buffer)
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text()
    return full_text


def parse_csv(file_bytes: bytes) -> str:
    content = file_bytes.decode("utf-8", errors="ignore")
    reader = csv.DictReader(StringIO(content))
    lines = []
    # Can not handle CSV files without header
    if (csv.Sniffer().has_header(content)):
        for i, row in enumerate(reader):
            parts = [f"{k}={v}" for k, v in row.items()]
            lines.append(f"Row {i+1}: {', '.join(parts)}")
    return "\n".join(lines)

# Handles both .msg and .oml files, which are both Outlook email formats
def parse_msg(file_bytes: bytes) -> str:
    buffer = BytesIO(file_bytes)
    content = extract_msg.Message(buffer)
    subject = content.subject or ""
    sender = content.sender or ""
    date = content.date or ""
    body = content.body or ""
    content.close()
    return f"Subject: {subject}\nFrom: {sender}\nDate: {date}\n\n{body}"
