# Product Overview — RAG Document Intelligence System

## Executive Summary
This project is a **document intelligence product** that turns messy, unstructured files—like **policy documents, contracts, decks, and PDFs**—into something teams can actually *use*: a conversational assistant that can **find the right clause**, **answer questions grounded in your documents**, and (when appropriate) **take actions like drafting/sending email**.

At its core, this is a **Retrieval-Augmented Generation (RAG)** system with a clean, modern web interface. Users upload PDFs, the system indexes them into a searchable knowledge base, and then users ask questions in plain English. For structured domains like **insurance claims**, the backend can also parse key fields (age, procedure, location, policy duration) and return a **structured decision** with justification.

---

## Problem Statement

### What problem does this product solve?
Organizations store critical information inside documents—policies, contracts, SOPs, internal decks, HR handbooks, and customer emails—but **finding the right answer quickly is hard**:

- **Documents are long and inconsistent**: key details are buried across pages, formats, and versions.
- **Search is brittle**: keyword search fails when the question is phrased differently than the document.
- **Decisions require traceability**: especially in compliance-heavy domains, teams need to justify answers by pointing to specific clauses.
- **Workflows are fragmented**: even after finding the information, teams still need to act—reply to a customer, summarize findings, or escalate.

This product solves that by building a **semantic knowledge base** over uploaded documents and providing a **chat-based interface** to retrieve, reason, and respond—while staying grounded in the source material.

### Who faces this problem and why it matters
- **Operations and support teams**: need fast, accurate answers for customers and internal stakeholders.
- **Insurance / claims teams**: must interpret policy clauses consistently, reduce turnaround time, and justify decisions for audits.
- **Legal and compliance teams**: must locate governing clauses, exclusions, and obligations—quickly and defensibly.
- **Founders and product teams**: want a “single place” to query company knowledge (decks, contracts, metrics) without hunting across folders.

Why it matters:
- **Speed**: minutes become seconds.
- **Consistency**: fewer ad-hoc interpretations and fewer mistakes.
- **Auditability**: answers can be tied to retrieved text and logged steps.
- **Scalability**: knowledge scales with document volume without requiring new hires just to search and summarize.

---

## Product Introduction

### What the product is
A **web-based RAG chatbot** with:
- **PDF upload and indexing**
- **Conversational Q&A grounded in uploaded documents**
- Optional **structured decisioning** for insurance-style queries
- Optional **tool actions** such as searching the knowledge base and drafting/sending email

The system is composed of:
- A **Next.js** frontend chat experience
- A **FastAPI** backend that handles ingestion, retrieval, and agent/tool execution
- **Pinecone** as the vector database
- **Cohere** for embeddings and response generation

### The core idea and vision behind it
The vision is to make “document knowledge” behave like a **reliable product capability**—not a scavenger hunt.

Instead of asking users to:
- remember *where* information lives,
- guess the right keywords,
- manually cross-reference clauses,
- and then write follow-up communication,

the product provides a single interface where users can:
- **upload and organize documents**,
- **ask questions in natural language**, and
- receive responses that are **grounded in retrieved document text**, with the ability to **show what the system did** (retrieval/tool steps) and optionally **take an action** (e.g., draft/send an email).

In short: **Less searching. More certainty. Faster decisions.**

---

## How It Works

### A simple explanation (for non-technical users)
1. **Upload a PDF** (policy, contract, deck—anything you want the system to “know”).
2. The system **reads the document** and breaks it into smaller “chunks.”
3. Those chunks are stored in a way that makes them **searchable by meaning**, not just by exact words.
4. When you ask a question, the system finds the **most relevant passages** from your uploaded documents.
5. It then generates an answer using those passages as the source—so the response is **based on your documents**, not generic internet knowledge.

For certain structured questions (like insurance-style queries), the system can also:
- extract key details (e.g., age, procedure, location, policy duration),
- evaluate basic eligibility rules,
- and return a more structured result (decision, amount estimate, justification).

### A deeper technical breakdown (for developers/technical audience)
At a high level, this system implements a modern RAG pipeline plus an optional tool-calling agent loop.

#### 1) Ingestion and indexing (PDF → chunks → embeddings → Pinecone)
- **PDF parsing**: the backend accepts uploads via `POST /rag/upload` and extracts text from PDFs.
- **Chunking**: text is split into chunks designed for retrieval (balanced chunk size with overlap).
- **Metadata enrichment (enhanced mode)**: chunks can be tagged with useful metadata such as inferred section types (coverage/exclusions/waiting period/age limits), detected amounts, age ranges, and time periods.
- **Embeddings**: chunk texts are embedded using **Cohere embeddings** (`embed-english-v3.0`).
- **Vector storage**: vectors are upserted into **Pinecone**, typically into:
  - a **chunks namespace** (for retrieval), and
  - a **docs/manifest namespace** (for listing documents in the UI without scanning chunks).

Key outcome: uploaded documents become a **queryable semantic index** with per-chunk metadata.

#### 2) Retrieval (query → embed → Pinecone similarity search)
When a user asks a question:
- The backend embeds the query with Cohere using `input_type="search_query"`.
- Pinecone is queried for `top_k` relevant chunks.
- A similarity threshold is applied so low-quality matches can be rejected.
- The selected chunk texts are assembled into a **context window** that is fed into the generator.

#### 3) Grounded generation (context + question → answer)
The generator is prompted to answer using **only the provided context**. If the context is insufficient, it returns an “I don’t have information in my knowledge base” style response—helping reduce hallucinations in real-world usage.

#### 4) Tool-calling agent loop (chat endpoint)
The chat endpoint (`POST /rag/chat`) runs a lightweight agent loop:
- The model is instructed to output **JSON only**, either:
  - a **final answer**, or
  - a list of **tool calls** to execute.
- Tools include:
  - `search_company_kb`: retrieves relevant chunks from the vector store
  - `send_email`: drafts (and optionally sends) an email via SMTP
- Tool calls are executed server-side, logged, and summarized as steps returned to the frontend.

This architecture enables conversational Q&A **and** “founder workflows” (e.g., “Find the relevant clause and email the customer a clear response”).

#### 5) Structured domain processing (insurance-style decisioning)
For certain structured queries (detected via heuristics like presence of “policy/surgery/month/year” patterns and an age signal), the backend can:
- parse fields with regex-based extraction (age/gender/procedure/location/policy duration),
- run a basic decision engine (eligibility checks, waiting periods),
- attempt to estimate coverage amounts (default amounts or extracted currency figures),
- and optionally call an LLM for a detailed analysis narrative.

This makes the product useful not only for “search and answer,” but also for **decision support** where a system must explain how it arrived at an outcome.

---

## Key Features & Components

### 1) Web chat experience (frontend)
- **What it does**: provides the main user interface to upload PDFs, chat with the assistant, and view system steps.
- **Why it exists**: adoption depends on UX. A simple, fast interface makes the system usable by non-technical teams.
- **Notable UX elements**:
  - message history (user + assistant),
  - a “What I did” expandable section (tool/retrieval transparency),
  - theme toggle (light/dark),
  - a documents sidebar sourced from backend document listing.

### 2) Document upload & processing (backend)
- **What it does**: accepts PDF uploads, extracts text, splits it into retrieval chunks, and embeds/stores them.
- **Why it exists**: ingestion is the foundation. Without clean chunking + metadata, retrieval quality collapses.

### 3) Vector knowledge base (Pinecone)
- **What it does**: stores chunk embeddings for semantic search, plus document “manifest” records for listing.
- **Why it exists**: enables fast similarity search at scale as document volume grows.

### 4) Embeddings + generation (Cohere)
- **What it does**:
  - embeddings: convert text into vectors for semantic retrieval,
  - generation: produce answers, analyses, and repaired JSON when needed.
- **Why it exists**: strong embeddings improve retrieval relevance; strong generation improves answer quality while staying grounded.

### 5) Retrieval layer
- **What it does**: embeds the query, performs similarity search, filters by threshold, and returns context chunks.
- **Why it exists**: retrieval is the “truth supply chain” of the assistant. Better retrieval = fewer hallucinations and more confidence.

### 6) Agent & tools framework
- **What it does**: supports JSON tool calling with a bounded iteration loop and returns step summaries.
- **Why it exists**: enables “answer + act” experiences (e.g., search KB → draft/send email) while keeping actions controlled and observable.

### 7) Document management endpoints
- **What it does**: lists uploaded documents and deletes them from Pinecone (both manifests and chunks).
- **Why it exists**: operational hygiene—users need to manage what the system “knows.”

### 8) Domain-specific decision support (insurance)
- **What it does**: parses structured fields from natural language and produces a decision + justification.
- **Why it exists**: many high-value use cases are not just Q&A; they are **decisions with explanations**.

---

## User Experience / Flow

### Step-by-step user journey
1. **Open the web app**
   - The user sees a chat interface and a sidebar listing uploaded documents (if any).
2. **Upload a PDF**
   - The system confirms it was processed and indexed.
   - The document appears in the sidebar with metadata like chunk count and upload time.
3. **Ask a question**
   - The user types a question in plain language (e.g., “Is knee surgery covered under this policy?”).
4. **System retrieves the best evidence**
   - The backend searches the document index for semantically relevant passages.
5. **User gets a grounded answer**
   - The assistant responds based on the retrieved content.
   - If the chat invoked tools, the UI can show a “What I did” panel containing a transparent summary of steps.
6. **Manage documents**
   - The user can refresh the document list and delete documents that should no longer be part of the knowledge base.

### What “good” feels like
- The user doesn’t need to know where information is stored.
- The assistant answers quickly and confidently when the KB contains evidence.
- When evidence is missing, the system says so—avoiding false certainty.
- For high-stakes workflows, users can review the system’s steps and maintain trust.

---

## Value Proposition

### What makes this product unique
- **Grounded responses**: answers are generated from *retrieved document context*, not generic knowledge.
- **Workflow-ready**: tool calling enables “find + act” experiences (e.g., search KB → draft/send email).
- **Transparent execution**: the product can return step summaries so users understand what happened.
- **Structured domain capability**: supports turning natural language into structured decisions (insurance-style).
- **Scales with document volume**: vector search is built for growth; document manifests make listing efficient.

### Why users should choose it over alternatives
- **Over manual search**: it finds meaning, not just keywords; it’s faster and less error-prone.
- **Over generic chatbots**: it is anchored to *your* documents, reducing irrelevant or hallucinated answers.
- **Over basic RAG demos**: it includes product-level building blocks—document lifecycle management, a real UI, logging, tool calling, and structured outputs that downstream systems can use.
- **Over single-purpose systems**: it can evolve from Q&A into decision support and operational automation.

---

## Use Cases / Scenarios

### 1) Insurance claims triage (policy coverage check)
**Scenario**: A claims agent receives: “46-year-old male, knee surgery in Pune, 3-month-old policy.”

**How it’s used**:
- The system extracts key fields (age, procedure, location, policy duration).
- It retrieves relevant policy clauses.
- It returns a structured result:
  - decision (approved/rejected),
  - amount estimate (if available),
  - justification and clause snippets used.

**Outcome**: faster triage, more consistent decisions, and audit-friendly reasoning.

### 2) Contract and compliance Q&A
**Scenario**: “What is our termination notice period?” or “Are we allowed to use subcontractors?”

**How it’s used**:
- Upload contracts and policies.
- Ask specific questions.
- Receive grounded answers from retrieved clauses.

**Outcome**: reduced legal back-and-forth and faster internal responses.

### 3) Founder/company knowledge assistant
**Scenario**: “Summarize our pricing terms from the latest deck and draft an email to a prospect.”

**How it’s used**:
- Retrieve relevant chunks from the KB.
- Produce a clean summary.
- Use the email tool to draft a professional message (send only when explicitly confirmed or enabled).

**Outcome**: less context-switching, faster external communication.

### 4) HR / internal policy guidance
**Scenario**: “What’s our leave policy for new employees?” or “What’s the expense reimbursement limit?”

**How it’s used**:
- Upload HR policies.
- Ask policy questions conversationally.

**Outcome**: consistent guidance with fewer repetitive HR requests.

---

## System Architecture (High-Level)

### Components and how they connect
- **Frontend (Next.js)**
  - Uploads PDFs
  - Sends chat messages (with conversational history)
  - Shows assistant responses + step summaries
  - Lists/deletes uploaded documents

- **Backend (FastAPI)**
  - Ingestion pipeline: parse PDF → chunk → embed → upsert into Pinecone
  - Retrieval pipeline: embed query → Pinecone query → context assembly
  - Answering: grounded generation with the retrieved context
  - Agent loop: JSON tool calling with bounded iterations
  - Tools: KB search and SMTP email drafting/sending
  - Document lifecycle: list/delete documents via manifest records + chunk deletion

- **Vector database (Pinecone)**
  - Chunk vectors (primary retrieval)
  - Manifest vectors (document listing without scanning)

- **Model provider (Cohere)**
  - Embeddings for documents and queries
  - Text generation for answers and analyses

### Typical request paths
- **Upload**
  - `POST /rag/upload` → parse → chunk → embed → Pinecone upsert (+ manifest)
- **Chat / Q&A**
  - `POST /rag/chat` → agent loop → tool execution (optional) → final answer
- **Document management**
  - `GET /rag/documents` → list manifests
  - `DELETE /rag/documents/{doc_id}` → delete manifest + delete chunks by filter

### Design principles reflected in the architecture
- **Grounding first**: retrieval supplies evidence; generation is constrained to it.
- **Separation of concerns**: ingestion, retrieval, generation, tools, and UI are modular.
- **Operational safety**: email sending is gated (draft by default, allowlists optional).
- **Explainability**: step summaries provide a transparent trail.

---

## Future Scope / Vision

This codebase is already a strong foundation for a production-grade “document intelligence” platform. High-impact evolution paths include:

### Retrieval quality upgrades
- **Better chunking strategies**: layout-aware chunking for PDFs; preserve headings/tables.
- **Hybrid search**: combine vector similarity + keyword/BM25 for precision.
- **Reranking**: add a reranker model to improve top-k quality.
- **Citations UI**: show exact source passages with page numbers, filenames, and confidence.

### Trust, governance, and compliance
- **Role-based access control**: restrict document sets by team, role, or customer.
- **Audit logs**: store retrieval results and tool steps for compliance review.
- **PII redaction**: detect/mask sensitive information in uploaded docs and outputs.

### Workflow automation
- **Additional tools**: create tickets, update CRM, generate reports, schedule follow-ups.
- **Approval flows**: “draft → approve → send” patterns for emails and external actions.
- **Templates**: standardized responses for claims decisions, customer replies, legal summaries.

### Productization and scale
- **Multi-tenant architecture**: namespaces per organization/customer.
- **Document versioning**: track changes over time and prevent stale knowledge.
- **Usage analytics**: identify unanswered questions and content gaps.
- **Async ingestion**: background processing for large PDFs and high throughput.

### Deeper domain intelligence (insurance/legal)
- **Clause classification and policy ontology**: stronger structured understanding.
- **Deterministic decision rules + LLM explanation**: separate “decision” from “narrative.”
- **Confidence calibration**: clearer, consistent confidence scoring with thresholds.

---

## Conclusion
This project addresses a universal and expensive problem: **critical knowledge trapped inside documents**. By combining semantic retrieval, grounded generation, and tool-enabled workflows, it turns documents into an interactive capability—one that teams can trust, act on, and scale.

For non-technical users, it feels simple: **upload → ask → get an answer you can use**.  
For technical teams, it’s a clear, extensible architecture: **FastAPI + Next.js + Cohere + Pinecone**, with a retrieval layer, structured domain logic, and a controlled tool-calling loop.

In a world where organizations drown in PDFs and policy text, this product turns document chaos into **speed, clarity, and defensible decisions**—and lays the foundation for a next-generation platform where knowledge retrieval and action are seamlessly connected.
