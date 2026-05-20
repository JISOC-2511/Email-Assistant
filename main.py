from fastapi import FastAPI, HTTPException, UploadFile
from ingest import parse_email, ingest_doc, parse_pdf, parse_csv

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