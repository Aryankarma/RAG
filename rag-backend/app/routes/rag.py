from fastapi import APIRouter, UploadFile, File, Form
from app.services.document_handler import parse_pdf
from app.services.embedder import embed_and_store
from app.services.retriever import query_knowledge_base

router = APIRouter()

@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    text_chunks = await parse_pdf(file)
    await embed_and_store(text_chunks)
    print("document embedded successfully")
    return {"message": "Document embedded successfully"}

@router.get("/upload")
async def upload_pdf():
    return {"message": "Server running at 8000"}

@router.post("/query")
async def ask_question(query: str = Form(...)):
    result = await query_knowledge_base(query)
    print("result of query: ", result)
    return {"answer": result}

