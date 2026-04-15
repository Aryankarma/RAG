import logging
from typing import Any, Dict, List

from app.services.retriever import RetrievedChunk, retrieve_chunks

logger = logging.getLogger(__name__)


def run_search_company_kb(query: str, top_k: int = 5) -> Dict[str, Any]:
    logger.info(
        "[tools] search_company_kb | phase=start | top_k=%s | query=%s",
        top_k,
        query.replace("\n", " ").strip()[:120],
    )
    chunks: List[RetrievedChunk] = retrieve_chunks(query.strip(), top_k=top_k)
    citations: List[Dict[str, Any]] = []
    for c in chunks:
        citations.append(
            {
                "chunk_id": c.id,
                "score": round(c.score, 4),
                "filename": c.filename,
                "doc_id": c.doc_id,
            }
        )
    context = "\n\n".join(c.text for c in chunks)
    if not chunks:
        logger.info("[tools] search_company_kb | phase=done | status=no chunks above threshold")
        return {
            "ok": False,
            "message": "No relevant chunks found above the similarity threshold. Try a different query or upload more documents.",
            "context": "",
            "citations": [],
        }
    logger.info(
        "[tools] search_company_kb | phase=done | status=ok | chunks=%s | citations=%s",
        len(chunks),
        len(citations),
    )
    return {
        "ok": True,
        "message": f"Retrieved {len(chunks)} chunk(s).",
        "context": context,
        "citations": citations,
    }
