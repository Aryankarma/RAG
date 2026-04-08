# app/routes/rag.py - ENHANCED VERSION
from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.services.document_handler import parse_pdf
from app.services.embedder import embed_and_store
from app.services.retriever import query_knowledge_base, enhanced_query_knowledge_base
from app.services.pinecone_documents import list_documents, delete_document

router = APIRouter()

class QueryRequest(BaseModel):
    query: str
    return_format: Optional[str] = "text"  # "json" or "text"

class InsuranceResponse(BaseModel):
    decision: str
    amount: float
    justification: list
    clauses_used: list
    extracted_data: dict
    confidence_score: float
    llm_analysis: str

@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    text_chunks = await parse_pdf(file)
    result = await embed_and_store(text_chunks, filename=file.filename)
    print("document embedded successfully")
    return {"message": "Document embedded successfully", **result}

@router.get("/upload")
async def upload_pdf():
    return {"message": "Server running at 8000"}

@router.post("/query")
async def ask_question(query: str = Form(...)):
    result = await query_knowledge_base(query)
    print("result of query: ", result)
    return {"answer": result}

# Documents sidebar endpoints
@router.get("/documents")
async def get_documents():
    return {"documents": list_documents()}

@router.delete("/documents/{doc_id}")
async def delete_uploaded_document(doc_id: str):
    deleted = delete_document(doc_id)
    return {"doc_id": doc_id, **deleted}




# NEW ENHANCED ENDPOINTS

@router.post("/query_json")
async def ask_question_structured(request: QueryRequest):
    """
    Enhanced query endpoint that returns structured JSON responses
    Perfect for insurance queries like: "46M, knee surgery, Pune, 3-month policy"
    """
    try:
        if request.return_format == "json":
            # Return structured JSON response
            result = await enhanced_query_knowledge_base(request.query)
            return result
        else:
            # Return simple text response (backward compatibility)
            result = await query_knowledge_base(request.query)
            return {"answer": result}
    except Exception as e:
        return {"error": str(e), "query": request.query}


@router.post("/process_insurance")
async def process_insurance_query(request: QueryRequest):
    """
    Dedicated endpoint for processing insurance claims
    Returns structured response with decision, amount, and justification
    """
    try:
        result = await enhanced_query_knowledge_base(request.query)
        
        # Format as InsuranceResponse structure
        return {
            "decision": result.get("decision", "UNKNOWN"),
            "amount": result.get("amount", 0),
            "justification": result.get("justification", []),
            "clauses_used": result.get("clauses_used", []),
            "extracted_data": result.get("extracted_data", {}),
            "confidence_score": result.get("confidence_score", 0),
            "llm_analysis": result.get("llm_analysis", ""),
            "query": request.query
        }
        
    except Exception as e:
        return {
            "decision": "ERROR",
            "amount": 0,
            "justification": [str(e)],
            "clauses_used": [],
            "extracted_data": {},
            "confidence_score": 0,
            "llm_analysis": "",
            "query": request.query
        }


@router.get("/test_insurance")
async def test_insurance_queries():
    """
    Test endpoint with sample insurance queries
    """
    test_queries = [
        "46M, knee surgery, Pune, 3-month policy",
        "35 year old female, heart surgery in Mumbai, 1 year policy",
        "60F, dental treatment, Delhi, 6-month policy",
        "25 year old male, eye surgery, Bangalore, 2 year policy"
    ]
    
    results = {}
    for query in test_queries:
        try:
            result = await enhanced_query_knowledge_base(query)
            results[query] = {
                "decision": result.get("decision"),
                "amount": result.get("amount"),
                "extracted_data": result.get("extracted_data")
            }
        except Exception as e:
            results[query] = {"error": str(e)}
    
    return {"test_results": results}


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Enhanced RAG system is running",
        "features": [
            "Basic document processing",
            "Enhanced insurance query processing", 
            "Structured JSON responses",
            "Age, procedure, location extraction",
            "Decision engine with waiting periods"
        ]
    }