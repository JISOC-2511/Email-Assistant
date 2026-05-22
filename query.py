from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
import os

from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI
client = OpenAI()

def retrieve_chunks(question: str, k: int = 5) -> list[dict]:
    embeddings = OpenAIEmbeddings()
    db = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
    results = db.similarity_search_with_score(question, k=k)
    chunks = []
    for doc, score in results:
        chunk_info = {
            "content": doc.page_content,
            "filename": doc.metadata.get("filename", "Unknown"),
            "score": score
        }
        chunks.append(chunk_info)
    return chunks


def build_context(chunks: list[dict]) -> tuple[str, list[str]]:
    context = ""
    for i, chunk in enumerate(chunks):
        chunk["source"] = f"[Source {i+1}] ({chunk['filename']})"
        context += f"{chunk['source']}\n{chunk['content']}\n\n"
    sources = list(dict.fromkeys([chunk["filename"] for chunk in chunks]))
    return context, sources


def answer_query(question: str) -> dict:
    chunks = retrieve_chunks(question)
    if not chunks:
        return {"answer": "No relevant documents found.", "sources": []}
    context, sources = build_context(chunks)
    system_message = (
        "You are an assistant that answers questions based ONLY on the provided context. "
        "Use the context to answer the question, and cite sources using [Source N] notation. "
        "Do NOT use any outside knowledge."
    )
    user_message = f"Context:\n{context}\n\nQuestion: {question}"
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
    )
    answer = response.choices[0].message.content
    return {"answer": answer, "sources": sources}