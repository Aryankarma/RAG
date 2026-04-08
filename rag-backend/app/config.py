import os
from dotenv import load_dotenv

load_dotenv()

COHERE_API_KEY = os.getenv("COHERE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENV")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")

# Pinecone namespaces (keep docs separate from chunks)
PINECONE_NAMESPACE_CHUNKS = os.getenv("PINECONE_NAMESPACE_CHUNKS") or "chunks"
PINECONE_NAMESPACE_DOCS = os.getenv("PINECONE_NAMESPACE_DOCS") or "docs"
