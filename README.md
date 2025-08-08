
# Problem Statement - LLM Document Processing System

Build a system that uses Large Language Models (LLMs) to process natural language queries and retrieve relevant information from large unstructured documents such as policy documents, contracts, and emails.


## Objective

The system should take an input query like:

"46-year-old male, knee surgery in Pune, 3-month-old insurance policy"


It must then:

- Parse and structure the query to identify key details such as age, procedure, location, and policy duration.

- Search and retrieve relevant clauses or rules from the provided documents using semantic understanding rather than simple keyword matching.

- Evaluate the retrieved information to determine the correct decision, such as approval status or payout amount, based on the logic defined in the clauses.

- Return a structured JSON response containing: Decision (e.g., approved or rejected), Amount (if applicable), and Justification, including mapping of each decision to the specific clause(s) it was based on.


## Requirements

- Input documents may include PDFs, Word files, or emails.

- The query processing and retrieval must work even if the query is vague, incomplete, or written in plain English.

- The system must be able to explain its decision by referencing the exact clauses used from the source documents.

- The output should be consistent, interpretable, and usable for downstream applications such as claim processing or audit tracking.


## Applications

This system can be applied in domains such as insurance, legal compliance, human resources, and contract management.


## Sample Query

"46M, knee surgery, Pune, 3-month policy"


## Sample Response

"Yes, knee surgery is covered under the policy."


# Backend ENV

COHERE_API_KEY=O8XzMdRVSKka3zuce02Aq0ExL8I3QTnQyf5tqIl8

PINECONE_API_KEY=pcsk_6sPcNf_9jvVLY8ZHS8fUSnw2ddqXNt6o3dbAbyjRtEn1jkarshbiz8Hm1K4W1iyBbrmEB2

PINECONE_ENV=us-east-1

PINECONE_INDEX=rag-index-type1

FRONTEND_PRODUCTION_URL=https://rag-chi-two.vercel.app

# Frontend ENV

NEXT_PUBLIC_BACKEND_URL=https://rag-t2v5.onrender.com

NODE_ENV=dev
