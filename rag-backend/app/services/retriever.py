from pinecone import Pinecone
import cohere
from app.config import COHERE_API_KEY, PINECONE_API_KEY, PINECONE_INDEX

print(COHERE_API_KEY, PINECONE_API_KEY, PINECONE_INDEX)

# Initialize clients
co = cohere.Client(COHERE_API_KEY)
pc = Pinecone(api_key=PINECONE_API_KEY)
pinecone_index = pc.Index(PINECONE_INDEX)

def format_prompt(context, question):
    return f"""You are a helpful assistant that ONLY answers questions based on the provided context. 

IMPORTANT RULES:
- You MUST only use information from the context below
- If the context does not contain information to answer the question, respond with: "I don't have information about that in my knowledge base."
- Do NOT use your general knowledge or training data
- Do NOT make up information that's not in the context

Context:
{context}

Question: {question}

Answer:"""

async def query_knowledge_base(query):
    # Generate embeddings using Cohere
    embed_resp = co.embed(texts=[query], model="embed-english-v3.0", input_type="search_query")
    query_vector = embed_resp.embeddings[0]
    
    # Query Pinecone index
    result = pinecone_index.query(
        vector=query_vector, 
        top_k=5, 
        include_metadata=True
    )
    
    # Check if we have any results returned at all
    if not result.matches:
        return "No results were returned from the vector store. This likely means that the query didn't match any document embeddings closely enough. Please try rephrasing your question or ensure it's relevant to the uploaded documents."

    # Check if the top result has a low similarity score
    if result.matches[0].score < 0.4:  # Adjust threshold as needed
        return (
            f"The top match has a similarity score below the acceptable threshold (0.4). "
            f"This indicates that even the closest document is not semantically similar enough to your query. "
            f"Try asking a more specific question based on the content of your documents. "
            f"(Score: {result.matches[0].score:.4f})"
        )

    # Filter matches by similarity score to ensure relevance
    relevant_matches = [match for match in result.matches if match.score > 0.4]

    if not relevant_matches:
        return (
            "Although matches were found, none passed the similarity threshold (> 0.4). "
            "This suggests that the query does not closely align with any document content. "
            "Consider rephrasing or using keywords present in the uploaded documents."
        )

    # Extract context from relevant results only
    context = "\n\n".join([match.metadata["text"] for match in relevant_matches])
    
    # Format prompt and generate response
    prompt = format_prompt(context, query)
    completion = co.generate(
        prompt=prompt, 
        model="command-r-plus", 
        max_tokens=300,
        temperature=0.1  # Lower temperature for more focused responses
    )
    
    return completion.generations[0].text.strip()