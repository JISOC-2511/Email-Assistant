from query import retrieve_chunks
from compliance import analyse_text
from openai import OpenAI

client = OpenAI()

def get_all_chunks(sample_queries: list[str] = None, k: int = 10) -> list[dict]:
    if sample_queries is None:
        sample_queries = [
            "What are the key points in this document?",
            "Summarize the main findings.",
            "What risks are mentioned?",
            "Deadlines and due dates",
            "Action items and follow ups",
            "Financial figures and transactions",
            "Legal terms and conditions"
        ]
    all_chunks = []
    seen_contents = set()
    for query in sample_queries:
        chunks = retrieve_chunks(query, k=k)
        for chunk in chunks:
            if chunk["content"] in seen_contents:
                continue
            seen_contents.add(chunk["content"])
            all_chunks.append(chunk)

    return all_chunks

def build_summary_prompt(chunks: list[dict]) -> str:
    prompt = "Please summarise the following document chunks:\n"
    for i, chunk in enumerate(chunks):
        prompt += f"\n\n[Chunk {i+1}] ({chunk['filename']}):\n{chunk['content']}"
    return prompt

def generate_summary() -> dict:
    chunks = get_all_chunks()
    if not chunks:
        return {"summary": "No documents have been uploaded yet.", "sources": []}
    prompt = build_summary_prompt(chunks)
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an executive assistant summarising internal business communications. "
                    "Be concise, factual and professional. "
                    "Structure your response with these exact sections:\n"
                    "# Key Deadlines\n"
                    "# Action Items\n"
                    "# Risks & Concerns\n"
                    "# Overall Sentiment\n"
                    "Write 'None identified' for any section where nothing was found."
                )
            },
            {"role": "user", "content": prompt}
        ]
    )
    summary = response.choices[0].message.content
    sources = list(dict.fromkeys([chunk["filename"] for chunk in chunks]))
    return {"summary": summary, "sources": sources}