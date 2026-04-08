from __future__ import annotations

from typing import Any, Dict, List

import cohere
from pinecone import Pinecone

from app.config import (
    COHERE_API_KEY,
    PINECONE_API_KEY,
    PINECONE_INDEX,
    PINECONE_NAMESPACE_CHUNKS,
    PINECONE_NAMESPACE_DOCS,
)


pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX)
co = cohere.Client(COHERE_API_KEY)


def _manifest_id(doc_id: str) -> str:
    return f"doc:{doc_id}"


def list_documents(limit: int = 100) -> List[Dict[str, Any]]:
    """
    List uploaded documents from Pinecone by scanning manifest vectors in the docs namespace.
    """
    docs: List[Dict[str, Any]] = []

    # Primary strategy: list IDs by prefix from docs namespace.
    # Some Pinecone environments / SDKs can return empty here; we fallback to a query-based strategy.
    try:
        token = None
        remaining = max(1, limit)
        while remaining > 0:
            page = index.list(
                namespace=PINECONE_NAMESPACE_DOCS,
                prefix="doc:",
                limit=min(remaining, 100),
                pagination_token=token,
            )

            ids = getattr(page, "ids", None) or []
            pagination = getattr(page, "pagination", None)
            token = getattr(pagination, "next", None) if pagination else None

            if not ids:
                break

            fetched = index.fetch(ids=ids, namespace=PINECONE_NAMESPACE_DOCS)
            vectors = getattr(fetched, "vectors", {}) or {}

            for _id, vec in vectors.items():
                md = getattr(vec, "metadata", None) or {}
                docs.append(
                    {
                        "doc_id": md.get("doc_id") or _id.replace("doc:", "", 1),
                        "filename": md.get("filename") or "uploaded.pdf",
                        "uploaded_at": md.get("uploaded_at"),
                        "chunk_count": md.get("chunk_count"),
                    }
                )

            remaining = limit - len(docs)
            if not token:
                break
    except Exception:
        # We'll fallback below
        pass

    # Fallback strategy: query the docs namespace and return manifest metadata.
    # This reliably surfaces documents even if list/prefix isn't supported.
    if not docs:
        embed = co.embed(
            texts=["list uploaded documents"],
            model="embed-english-v3.0",
            input_type="search_query",
        )
        q = index.query(
            vector=embed.embeddings[0],
            top_k=min(limit, 100),
            include_metadata=True,
            namespace=PINECONE_NAMESPACE_DOCS,
        )
        matches = getattr(q, "matches", None) or []
        for m in matches:
            md = getattr(m, "metadata", None) or {}
            doc_id = md.get("doc_id") or str(getattr(m, "id", "")).replace("doc:", "", 1)
            docs.append(
                {
                    "doc_id": doc_id,
                    "filename": md.get("filename") or "uploaded.pdf",
                    "uploaded_at": md.get("uploaded_at"),
                    "chunk_count": md.get("chunk_count"),
                }
            )

    # newest first (uploaded_at may be None for older records)
    docs.sort(key=lambda d: d.get("uploaded_at") or 0, reverse=True)
    return docs[:limit]


def delete_document(doc_id: str) -> Dict[str, Any]:
    """
    Delete a document by:
    - removing its manifest record from the docs namespace
    - deleting all chunk vectors with metadata filter doc_id in chunks namespace
    """
    # Delete manifest vector
    index.delete(ids=[_manifest_id(doc_id)], namespace=PINECONE_NAMESPACE_DOCS)

    # Delete all chunk vectors for that doc_id
    index.delete(filter={"doc_id": {"$eq": doc_id}}, namespace=PINECONE_NAMESPACE_CHUNKS)

    return {"deleted": True}

