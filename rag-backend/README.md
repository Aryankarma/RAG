## RAG Backend with FastAPI + Cohere

### Setup

1. Clone repo and `cd` into it.

2. Create a `.env` file (see `.env.example`). Minimum for RAG:

```
COHERE_API_KEY=your_cohere_key
PINECONE_API_KEY=your_pinecone_key
PINECONE_ENV=your_env
PINECONE_INDEX=your_index_name
```

Optional: set `PINECONE_NAMESPACE_CHUNKS` / `PINECONE_NAMESPACE_DOCS`, `FRONTEND_PRODUCTION_URL`, and SMTP variables if you use the **send email** tool (`POST /rag/chat`).

**Logging**

Set `LOG_LEVEL` (default `INFO`) to control terminal output. Application logs use the `app.*` loggers and show API requests, RAG retrieval, LLM calls, and tool execution (`[api]`, `[rag]`, `[agent]`, `[tools]` prefixes).

**Email tool behavior**

- `send_email` prepares a draft unless `confirm` is `true` **or** `EMAIL_SEND_ENABLED=true`.
- Set `EMAIL_ALLOWLIST_DOMAINS` (comma-separated) to restrict recipient domains during testing (empty means no restriction).

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the server from the `rag-backend` directory (so imports resolve; `.env` is also loaded from this folder regardless of your current directory):

```bash
cd rag-backend
uvicorn app.main:app --reload
```

If SMTP variables look “missing” at runtime, confirm `.env` is saved under `rag-backend/.env` and restart the process after editing. The app loads that file explicitly, not only from the shell’s working directory.

**SMTP: `getaddrinfo failed` / Errno 11001**

That means the **server name** in `SMTP_HOST` could not be resolved (not a bad “To” address). Use your mail provider’s real hostname, for example:

- Gmail / Google Workspace: `smtp.gmail.com`, port `587` (use an [App Password](https://support.google.com/accounts/answer/185833) if 2FA is on)
- Microsoft 365 / Outlook: `smtp.office365.com`, port `587`

Do not leave `SMTP_HOST` as a placeholder like `smtp.example.com`.

### Endpoints
- `POST /rag/upload` - Upload PDF
- `POST /rag/query` - Ask question (form field: `query`; legacy path, may use insurance heuristics)
- `POST /rag/chat` - Founder chat with tool calling (JSON body: `message`, optional `history`); uses `search_company_kb` and `send_email` tools