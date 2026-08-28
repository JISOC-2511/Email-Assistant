# Enterprise Email AI Assistant

A **Python/FastAPI** application utilizing **Retrieval-Augmented Generation (RAG)** to analyze business documents and identify compliance risks. Users can upload emails, PDFs, and CSVs to query data via natural language, scan for Personally Identifiable Information (PII), and generate executive summaries with direct source citations.

## Features

* **Document Ingestion**: Parses `.eml`, `.msg`/`.oml` (Outlook), `.pdf`, and `.csv` files into searchable text.
* **Semantic Search & Q&A**: Answers natural language questions using source-attributed document snippets.
* **Compliance Scanning**: Detects PII (emails, phone numbers, SSNs, TFNs, credit cards) using regex paired with an AI verification layer to eliminate false positives.
* **Database-Wide Risk Analysis**: Proactively surfaces high-risk content across all uploaded repositories.
* **Executive Summaries**: Auto-generates structured digests highlighting deadlines, action items, risks, and overall sentiment.

## Architecture & Workflow

### Tech Stack

| Layer      | Technology                            |
|------------|---------------------------------------|
| Backend    | Python, FastAPI                       |
| AI         | OpenAI API (GPT-4.1, text-embedding)  |
| Retrieval  | LangChain, ChromaDB                   |
| Frontend   | React                                 |
| Testing    | Pytest (93 tests, mocked integration) |

### System Data Flow

```
[ Upload (.eml/.pdf/.csv) ]
             ↓
      [ Parse to text ]
             ↓
[ Split into 512-token chunks ]
             ↓
[ Embed chunks via OpenAI ]
             ↓
 [ Save to ChromaDB Vector Store ]

─────────────────────────────────────────────

  [ User Natural Language Query ]
             ↓
    [ Embed user question ]
             ↓
[ Query ChromaDB for top-K chunks ]
             ↓
 [ Compile context with source labels ]
             ↓
 [ GPT-4.1 synthesizes response ]
             ↓
 [ Return response + citations ]
```

### Risk Evaluation Pipeline
Compliance scanning runs a two-stage pipeline. A fast regex and keyword pass filters out obvious non-issues. Ambiguous flags are then routed to GPT-4.1 to determine semantic intent (e.g., distinguishing between "there was a breach" and "no breach occurred").

## Getting Started

### Prerequisites
* Python 3.10+
* Node.js (v18+)
* OpenAI API Key

### Backend Installation & Setup

1. Clone the repository and navigate to the project directory:
   ```bash
   git clone <your-repo-url>
   cd EmailAssistant
   ```

2. Install the required dependencies:
   ```bash
   pip install fastapi uvicorn langchain langchain-community langchain-text-splitters openai chromadb python-multipart pypdf2 python-dotenv extract-msg
   ```

3. Create a `.env` file in the root directory and add your credentials:
   ```env
   OPENAI_API_KEY=sk-proj-...
   ```

4. Launch the FastAPI application:
   ```bash
   uvicorn main:app --reload
   ```
   *The interactive API documentation will be available at `http://localhost:8000/docs`.*

### Frontend Installation & Setup

1. Navigate to the frontend directory:
   ```bash
   cd email-assistant
   ```

2. Install dependencies and start the local development server:
   ```bash
   npm install
   npm start
   ```
   *The interface will open automatically at `http://localhost:3000`.*

### Running Tests
Execute the test suite using `pytest`:
```bash
pytest tests/ -v
```

## Usage Examples

### Natural Language Query
* **Query**: `"What deadlines are coming up?"`
* **Response**: 
    > Based on the documents, there is an invoice payment due by March 3rd, flagged as overdue in an email from Finance **[Source 1]**. There is also a contract renewal deadline mentioned for end of quarter **[Source 2]**.
    >
    > **Sources**: `finance_march.eml`, `contracts_q1.pdf`

### Compliance Scan Output

| File         | Risk Level  | Flagged Issue                         |
|--------------|-------------|---------------------------------------|
| invoices.csv | High Risk   | Credit card number detected           |
| emails.eml   | Medium Risk | "overdue" keyword, unresolved payment |

## Known Limitations & Future Roadmap

* **No `.pst` File Support**: Outlook mailbox bulk exports require the `pypff` library, which exhibits cross-platform installation issues. Current workaround requires exporting individual `.eml`/`.msg` files or processing zipped folders.
* **Authentication & Access Control**: The prototype lacks user authentication and Role-Based Access Control (RBAC). Production deployments require robust login layers and at-rest encryption for the ChromaDB vector store.
