## RAG Backend with FastAPI + Cohere

### Setup

1. Clone repo and `cd` into it.

2. Create a `.env` file:
```
COHERE_API_KEY=your_cohere_key
PINECONE_API_KEY=your_pinecone_key
PINECONE_ENV=your_env
PINECONE_INDEX=your_index_name
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run server:
```bash
uvicorn app.main:app --reload
```

### Endpoints
- `POST /rag/upload` - Upload PDF
- `POST /rag/query` - Ask question (form field: `query`)