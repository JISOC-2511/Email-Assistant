from fastapi import FastAPI, HTTPException, UploadFile
from ingest import parse_email, ingest_doc, parse_pdf, parse_csv
from query import answer_query, retrieve_risk_chunks
from compliance import analyse_text
from summary import generate_summary

app = FastAPI()

@app.post("/upload")
async def upload_file(file: UploadFile):
    content = await file.read()
    if file.filename.endswith(".eml"):
        text = parse_email(content)
    elif file.filename.endswith(".pdf"):
        text = parse_pdf(content)
    elif file.filename.endswith(".csv"):
        text = parse_csv(content)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    ingest_doc(text, metadata={"filename": file.filename})
    return {"status": "ingested", "file": file.filename}

@app.post("/query")
async def query(body: dict):
    question = body.get("question")
    if not question:
        raise HTTPException(status_code=400, detail="Question field is required")
    result = answer_query(question)
    return result

@app.post("/compliance")
async def compliance_check(body: dict):
    text = body.get("text")
    if not text:
        raise HTTPException(status_code=422, detail="Text field is required")
    return analyse_text(text)

@app.get("/compliance/scan")
async def compliance_scan():
    flagged_chunks = retrieve_risk_chunks()
    return {
        "flagged_chunks": flagged_chunks,
        "total_flagged":  len(flagged_chunks)
    }

@app.get("/summary")
async def get_summary():
    result = generate_summary()
    return result