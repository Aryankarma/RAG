from pinecone import Pinecone
import cohere
from app.config import COHERE_API_KEY, PINECONE_API_KEY, PINECONE_INDEX

co = cohere.Client(COHERE_API_KEY)

# Initialize Pinecone with the new API
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX)

async def embed_and_store(chunks):
    responses = co.embed(texts=chunks, model="embed-english-v3.0", input_type="search_document")
    for i, (chunk, vector) in enumerate(zip(chunks, responses.embeddings)):
        index.upsert([(f"chunk-{i}", vector, {"text": chunk})])