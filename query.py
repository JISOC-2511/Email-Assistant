from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
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
    
    """
    Full RAG pipeline: retrieve relevant chunks, build context, call the
    LLM, and return the answer with source citations.

    Steps:
    1. Call retrieve_chunks(question) to get the top chunks
    2. If chunks is empty, return early:
         {"answer": "No relevant documents found.", "sources": []}
       Don't call the LLM if there's nothing to ground it with
    3. Call build_context(chunks) to get (context, sources)
    4. Call the OpenAI chat completions API with model="gpt-4.1":
         - System message: instruct the model to answer ONLY from the
           provided context, and to cite sources using [Source N] notation.
           Be explicit — tell it not to use outside knowledge.
         - User message: include both the context string and the question,
           clearly labelled e.g. "Context:\n{context}\n\nQuestion: {question}"
    5. Extract the answer text from:
         response.choices[0].message.content
    6. Return:
         {
           "answer": <answer string>,
           "sources": <deduplicated list of filenames from build_context>
         }

    This dict shape is what your FastAPI /query endpoint will return
    directly to the frontend.
    """
    pass