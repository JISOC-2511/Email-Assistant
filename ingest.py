from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
import email, PyPDF2

def parse_email(fileBytes) -> str:
    msg = email.message_from_bytes(fileBytes)
    body = ""
    if msg.is_multipart():
        for section in msg.walk():
            if section.get_content_type == "text/plain":
                body += section.get_payload(decode=True).decode()
    else:
        body = msg.get_payload(decode=True).decode
    subject = msg.get("Subject", "")
    sender = msg.get("From", "")
    date = msg.get("Date", "")
    return f"Subject: {subject}\nFrom: {sender}\nDate: {date}\n\n{body}"

def ingest_doc(text, metadata) -> str:
    splitter = RecursiveCharacterTextSplitter(chunk_size = 512, chunk_overlap = 52)
    chunks = splitter.split_documents(text)
    embeddings = OpenAIEmbeddings()
    db = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    db.add_texts(chunks, metadatas=[metadata] * len(chunks))
    db.persist()



