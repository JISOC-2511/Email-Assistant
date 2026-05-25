from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from compliance import analyse_text
import os, json

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

def ai_risk_check(chunk_content: str) -> dict:
    prompt = f"""You are a compliance analyst. Read the following text and determine 
        whether it represents a genuine compliance risk or concern.

        Consider:
        - Negations ("no breach", "not urgent") are NOT risks
        - Historical or resolved issues are LOW risk
        - Active, ongoing, or threatened issues are HIGH risk
        - Speculative or hypothetical mentions are MEDIUM risk

        Respond in JSON only, no markdown:
        {{"risky": true or false, "risk_score": "High Risk" or "Medium Risk" or "Low Risk", "reason": "one sentence explanation"}}

        Text: {chunk_content}"""

    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=256,
    )

    try:
        return json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        # if GPT doesn't return clean JSON, default to not flagging
        return {"risky": False, "risk_score": "Low Risk", "reason": "Could not parse response"}
    
def retrieve_risk_chunks(k: int = 10) -> list[dict]:
    RISK_CONCEPTS = [
        "legal dispute or lawsuit between parties",
        "data breach or unauthorised access to sensitive information",
        "overdue payment or outstanding invoice",
        "fraud or financial misconduct",
        "urgent compliance or regulatory violation",
        "confidential information shared externally",
        "criminal investigation or arbitration proceedings",
    ]

    seen_contents = set()
    flagged = []

    for concept in RISK_CONCEPTS:
        chunks = retrieve_chunks(concept, k=k)
        for chunk in chunks:
            if chunk["content"] in seen_contents:
                continue
            seen_contents.add(chunk["content"])

            # Stage 1 — fast keyword/PII check to filter obvious non-risks
            compliance = analyse_text(chunk["content"])
            if compliance["risk_score"] == "Low Risk":
                continue

            # Stage 2 — LLM makes the final call on ambiguous cases
            llm_judgement = ai_risk_check(chunk["content"])

            if llm_judgement["risky"]:
                flagged.append({
                    "content":       chunk["content"],
                    "filename":      chunk["filename"],
                    "risk_score":    llm_judgement["risk_score"],
                    "risk_keywords": compliance["risk_keywords"],
                    "personal_info": compliance["personal_info"],
                    "reason":        llm_judgement["reason"],
                })

    return flagged


