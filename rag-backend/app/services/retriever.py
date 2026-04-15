from pinecone import Pinecone
import cohere
import json
import logging
import re
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from app.config import COHERE_API_KEY, PINECONE_API_KEY, PINECONE_INDEX, PINECONE_NAMESPACE_CHUNKS
from app.utils.cohere_llm import cohere_generate_text

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    id: str
    score: float
    text: str
    filename: Optional[str] = None
    doc_id: Optional[str] = None


SIMILARITY_THRESHOLD = 0.4


def _pinecone_vector_search(query: str, top_k: int = 5):
    """Raw Pinecone query result (single embed + query)."""
    embed_resp = co.embed(texts=[query], model="embed-english-v3.0", input_type="search_query")
    query_vector = embed_resp.embeddings[0]
    return pinecone_index.query(
        vector=query_vector,
        top_k=top_k,
        include_metadata=True,
        namespace=PINECONE_NAMESPACE_CHUNKS,
    )


# Initialize clients
co = cohere.Client(COHERE_API_KEY)
pc = Pinecone(api_key=PINECONE_API_KEY)
pinecone_index = pc.Index(PINECONE_INDEX)

class QueryParser:
    """Parses natural language queries into structured data"""
    
    def __init__(self):
        # Define patterns for extracting information
        self.patterns = {
            'age': [
                r'(\d+)\s*(?:year|yr|y)?\s*(?:old|m|male|f|female)?',
                r'(\d+)M',
                r'(\d+)F',
                r'age\s*(\d+)'
            ],
            'gender': [
                r'(\d+)([MF])',
                r'(male|female|man|woman)',
                r'(M|F)(?!\w)'
            ],
            'procedure': [
                r'(knee surgery|heart surgery|dental|eye surgery|surgery)',
                r'(operation|treatment|procedure)',
                r'(bypass|transplant|replacement)'
            ],
            'location': [
                r'in\s+([A-Za-z]+)',
                r'at\s+([A-Za-z]+)',
                r'(Mumbai|Delhi|Pune|Bangalore|Chennai|Kolkata|Hyderabad)',
                r'([A-Z][a-z]+)(?=\s*,|\s*$)'
            ],
            'policy_duration': [
                r'(\d+)\s*-?\s*(month|year|day)s?\s*(?:old\s*)?policy',
                r'(\d+)\s*-?\s*(month|year|day)s?\s*policy',
                r'policy\s*.*?(\d+)\s*(month|year|day)'
            ]
        }
    
    def extract_info(self, query: str) -> Dict[str, Any]:
        """Extract structured information from query"""
        query = query.lower().strip()
        extracted = {}
        
        # Extract age
        for pattern in self.patterns['age']:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                extracted['age'] = int(match.group(1))
                break
        
        # Extract gender
        for pattern in self.patterns['gender']:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                if match.group(1).upper() in ['M', 'MALE', 'MAN']:
                    extracted['gender'] = 'Male'
                elif match.group(1).upper() in ['F', 'FEMALE', 'WOMAN']:
                    extracted['gender'] = 'Female'
                break
        
        # Extract procedure
        for pattern in self.patterns['procedure']:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                extracted['procedure'] = match.group(1)
                break
        
        # Extract location
        for pattern in self.patterns['location']:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                extracted['location'] = match.group(1).title()
                break
        
        # Extract policy duration
        for pattern in self.patterns['policy_duration']:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                duration = int(match.group(1))
                unit = match.group(2)
                extracted['policy_duration'] = f"{duration} {unit}s"
                extracted['policy_duration_value'] = duration
                extracted['policy_duration_unit'] = unit
                break
        
        return extracted

class InsuranceDecisionEngine:
    """Makes decisions based on extracted query data and retrieved documents"""
    
    def __init__(self):
        self.decision_logic = {
            'age_limits': {'min': 18, 'max': 65},
            'covered_procedures': ['knee surgery', 'heart surgery', 'eye surgery'],
            'covered_locations': ['mumbai', 'delhi', 'pune', 'bangalore'],
            'waiting_periods': {
                'knee surgery': 6,  # months
                'heart surgery': 12,
                'dental': 3
            }
        }
    
    def evaluate_claim(self, extracted_data: Dict[str, Any], relevant_clauses: List[str]) -> Dict[str, Any]:
        """Evaluate claim based on extracted data and policy clauses"""
        decision = {
            'decision': 'PENDING',
            'amount': 0,
            'justification': [],
            'clauses_used': []
        }
        
        # Check age eligibility
        age = extracted_data.get('age')
        if age:
            if age < self.decision_logic['age_limits']['min']:
                decision['decision'] = 'REJECTED'
                decision['justification'].append(f"Age {age} is below minimum age limit of {self.decision_logic['age_limits']['min']}")
                return decision
            elif age > self.decision_logic['age_limits']['max']:
                decision['decision'] = 'REJECTED' 
                decision['justification'].append(f"Age {age} exceeds maximum age limit of {self.decision_logic['age_limits']['max']}")
                return decision
        
        # Check procedure coverage
        procedure = extracted_data.get('procedure', '').lower()
        if procedure and procedure in self.decision_logic['covered_procedures']:
            decision['justification'].append(f"Procedure '{procedure}' is covered under the policy")
            decision['decision'] = 'APPROVED'
        elif procedure:
            # Check if procedure is mentioned in retrieved clauses
            for clause in relevant_clauses:
                if procedure in clause.lower():
                    decision['justification'].append(f"Procedure '{procedure}' found in policy clause")
                    decision['clauses_used'].append(clause[:200] + "...")
                    decision['decision'] = 'APPROVED'
                    break
        
        # Check waiting period
        policy_duration = extracted_data.get('policy_duration_value', 0)
        policy_unit = extracted_data.get('policy_duration_unit', 'month')
        
        if procedure in self.decision_logic['waiting_periods']:
            required_months = self.decision_logic['waiting_periods'][procedure]
            if policy_unit == 'month' and policy_duration >= required_months:
                decision['justification'].append(f"Waiting period satisfied for {procedure}")
            elif policy_unit == 'year' and policy_duration * 12 >= required_months:
                decision['justification'].append(f"Waiting period satisfied for {procedure}")
            else:
                decision['decision'] = 'REJECTED'
                decision['justification'].append(f"Waiting period not satisfied. Required: {required_months} months, Policy age: {policy_duration} {policy_unit}s")
        
        # Estimate amount based on procedure and retrieved information
        if decision['decision'] == 'APPROVED':
            decision['amount'] = self.estimate_coverage_amount(procedure, relevant_clauses)
        
        return decision
    
    def estimate_coverage_amount(self, procedure: str, clauses: List[str]) -> float:
        """Estimate coverage amount based on procedure and policy clauses"""
        # Default amounts based on procedure type
        default_amounts = {
            'knee surgery': 150000,
            'heart surgery': 500000,
            'eye surgery': 75000,
            'dental': 25000
        }
        
        # Try to extract amount from clauses
        for clause in clauses:
            # Look for currency amounts in clauses
            amount_matches = re.findall(r'(?:₹|Rs\.?\s*|INR\s*)(\d+(?:,\d+)*(?:\.\d+)?)', clause)
            if amount_matches:
                # Convert string to float (remove commas)
                amount = float(amount_matches[0].replace(',', ''))
                return amount
        
        # Return default amount if not found in clauses
        return default_amounts.get(procedure.lower(), 50000)

# Initialize parser and decision engine
parser = QueryParser()
decision_engine = InsuranceDecisionEngine()

def retrieve_chunks(
    query: str,
    *,
    top_k: int = 5,
    min_score: float = SIMILARITY_THRESHOLD,
) -> List[RetrievedChunk]:
    """
    Vector search only (no LLM). Used by founder tool-calling and standard RAG.
    Returns chunks at or above min_score; empty if nothing meets the threshold.
    """
    qprev = query.replace("\n", " ").strip()
    if len(qprev) > 120:
        qprev = qprev[:119] + "…"
    logger.info(
        "[rag] retrieve | phase=embed+pinecone | top_k=%s min_score=%s | query=%s",
        top_k,
        min_score,
        qprev,
    )
    result = _pinecone_vector_search(query, top_k=top_k)

    if not result.matches:
        logger.info("[rag] retrieve | phase=done | status=no matches from index")
        return []

    out: List[RetrievedChunk] = []
    for match in result.matches:
        if match.score < min_score:
            continue
        meta = match.metadata or {}
        text = meta.get("text") or ""
        if not text:
            continue
        out.append(
            RetrievedChunk(
                id=str(match.id),
                score=float(match.score),
                text=text,
                filename=meta.get("filename"),
                doc_id=meta.get("doc_id"),
            )
        )
    best = float(result.matches[0].score) if result.matches else 0.0
    logger.info(
        "[rag] retrieve | phase=done | status=ok | chunks=%s | top_score=%.4f",
        len(out),
        best,
    )
    return out


def chunks_to_context(chunks: List[RetrievedChunk]) -> str:
    return "\n\n".join(c.text for c in chunks)


def answer_from_context(context: str, question: str) -> str:
    """Grounded answer using existing RAG prompt rules."""
    qprev = question.replace("\n", " ").strip()
    if len(qprev) > 100:
        qprev = qprev[:99] + "…"
    logger.info(
        "[rag] answer | phase=llm | status=calling Cohere | context_chars=%s | question=%s",
        len(context),
        qprev,
    )
    prompt = format_prompt(context, question)
    out = cohere_generate_text(
        co,
        prompt,
        model="command-r-plus-08-2024",
        max_tokens=300,
        temperature=0.1,
    )
    logger.info("[rag] answer | phase=llm | status=done | answer_chars=%s", len(out or ""))
    return out


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

def format_enhanced_prompt(context: str, extracted_data: Dict[str, Any], question: str) -> str:
    """Create enhanced prompt with structured data"""
    return f"""You are an insurance policy analyst. Based on the provided context and extracted query information, provide a detailed analysis.

EXTRACTED QUERY INFORMATION:
{json.dumps(extracted_data, indent=2)}

RELEVANT POLICY CONTEXT:
{context}

ORIGINAL QUESTION: {question}

INSTRUCTIONS:
1. Analyze if the extracted information matches any policy clauses
2. Determine coverage eligibility based on the context
3. Identify specific clauses that apply to this case
4. Provide clear reasoning for your decision

Focus on:
- Age eligibility
- Procedure coverage
- Waiting periods
- Location restrictions
- Policy terms and conditions

Answer:"""

async def enhanced_query_knowledge_base(query: str) -> Dict[str, Any]:
    """Enhanced query processing with structured parsing and decision making"""
    logger.info("[rag] insurance | phase=start | path=enhanced_query_knowledge_base")

    # Step 1: Parse query into structured data
    extracted_data = parser.extract_info(query)
    
    if not extracted_data:
        return {
            "decision": "ERROR",
            "message": "Could not extract meaningful information from the query. Please provide details like age, procedure, location, and policy duration.",
            "extracted_data": {}
        }
    
    # Step 2: Generate multiple search queries for better retrieval
    search_queries = []
    
    # Original query
    search_queries.append(query)
    
    # Procedure-based query
    if 'procedure' in extracted_data:
        search_queries.append(f"{extracted_data['procedure']} coverage policy terms")
        search_queries.append(f"waiting period {extracted_data['procedure']}")
    
    # Age-based query
    if 'age' in extracted_data:
        search_queries.append(f"age limit eligibility {extracted_data['age']} years")
    
    # Location-based query
    if 'location' in extracted_data:
        search_queries.append(f"treatment location {extracted_data['location']}")
    
    # Step 3: Retrieve relevant documents using multiple queries
    all_matches = []
    
    for search_query in search_queries:
        embed_resp = co.embed(texts=[search_query], model="embed-english-v3.0", input_type="search_query")
        query_vector = embed_resp.embeddings[0]
        
        result = pinecone_index.query(
            vector=query_vector,
            top_k=3,
            include_metadata=True,
            namespace=PINECONE_NAMESPACE_CHUNKS,
        )
        
        if result.matches:
            all_matches.extend(result.matches)
    
    # Remove duplicates and filter by score
    unique_matches = {}
    for match in all_matches:
        if match.id not in unique_matches and match.score > 0.3:
            unique_matches[match.id] = match
    
    relevant_matches = list(unique_matches.values())
    
    if not relevant_matches:
        return {
            "decision": "INSUFFICIENT_DATA",
            "message": "No relevant policy information found for this query.",
            "extracted_data": extracted_data
        }
    
    # Step 4: Extract context and make decision
    context = "\n\n".join([match.metadata["text"] for match in relevant_matches])
    relevant_clauses = [match.metadata["text"] for match in relevant_matches]
    
    # Step 5: Use decision engine
    decision_result = decision_engine.evaluate_claim(extracted_data, relevant_clauses)
    
    # Step 6: Generate detailed explanation using LLM
    logger.info("[rag] insurance | phase=llm | status=calling Cohere (analysis)")
    prompt = format_enhanced_prompt(context, extracted_data, query)
    llm_analysis = cohere_generate_text(
        co,
        prompt,
        model="command-r-plus-08-2024",
        max_tokens=500,
        temperature=0.1,
    )
    logger.info("[rag] insurance | phase=llm | status=done | analysis_chars=%s", len(llm_analysis or ""))

    # Step 7: Combine results
    final_response = {
        "decision": decision_result['decision'],
        "amount": decision_result['amount'],
        "justification": decision_result['justification'],
        "clauses_used": decision_result['clauses_used'],
        "llm_analysis": llm_analysis,
        "extracted_data": extracted_data,
        "confidence_score": max([match.score for match in relevant_matches]) if relevant_matches else 0
    }
    
    return final_response

# Original function with enhanced capabilities
async def query_knowledge_base(query):
    """Enhanced query function that handles both simple and structured queries"""
    qprev = query.replace("\n", " ").strip()
    if len(qprev) > 100:
        qprev = qprev[:99] + "…"
    logger.info("[rag] query | endpoint=/rag/query | phase=start | query=%s", qprev)

    # Check if this looks like a structured insurance query
    insurance_keywords = ['surgery', 'policy', 'month', 'year', 'treatment', 'procedure']
    has_insurance_pattern = any(keyword in query.lower() for keyword in insurance_keywords)
    has_age_pattern = bool(re.search(r'\d+\s*[mf]?(?:\s|,|$)', query.lower()))
    
    # If it looks like an insurance query, use enhanced processing
    if has_insurance_pattern and has_age_pattern:
        logger.info("[rag] query | route=insurance-enhanced | status=matched heuristics")
        try:
            result = await enhanced_query_knowledge_base(query)
            
            if result["decision"] == "APPROVED":
                return f"✅ APPROVED: {result['extracted_data'].get('procedure', 'The procedure')} is covered under the policy.\n\n💰 Coverage Amount: ₹{result['amount']:,.0f}\n\n📋 Justification: {'; '.join(result['justification'])}\n\n📊 Extracted Information: {json.dumps(result['extracted_data'], indent=2)}"
            elif result["decision"] == "REJECTED":
                return f"❌ REJECTED: {'; '.join(result['justification'])}\n\n📊 Extracted Information: {json.dumps(result['extracted_data'], indent=2)}"
            else:
                return result.get("message", "Unable to process the insurance query.")
        except Exception as e:
            logger.exception(
                "Enhanced insurance processing failed; falling back to standard RAG: %s",
                e,
            )
            # Fall back to standard processing if enhanced fails
    
    # Standard RAG processing for non-insurance queries
    logger.info("[rag] query | route=standard-rag | phase=pinecone+llm")
    result = _pinecone_vector_search(query, top_k=5)

    if not result.matches:
        return "No results were returned from the vector store. This likely means that the query didn't match any document embeddings closely enough. Please try rephrasing your question or ensure it's relevant to the uploaded documents."

    if result.matches[0].score < SIMILARITY_THRESHOLD:
        return (
            f"The top match has a similarity score below the acceptable threshold ({SIMILARITY_THRESHOLD}). "
            f"This indicates that even the closest document is not semantically similar enough to your query. "
            f"Try asking a more specific question based on the content of your documents. "
            f"(Score: {result.matches[0].score:.4f})"
        )

    relevant_matches = [m for m in result.matches if m.score >= SIMILARITY_THRESHOLD]
    if not relevant_matches:
        return (
            "Although matches were found, none passed the similarity threshold (> 0.4). "
            "This suggests that the query does not closely align with any document content. "
            "Consider rephrasing or using keywords present in the uploaded documents."
        )

    chunks: List[RetrievedChunk] = []
    for match in relevant_matches:
        meta = match.metadata or {}
        text = meta.get("text") or ""
        if not text:
            continue
        chunks.append(
            RetrievedChunk(
                id=str(match.id),
                score=float(match.score),
                text=text,
                filename=meta.get("filename"),
                doc_id=meta.get("doc_id"),
            )
        )

    if not chunks:
        return (
            "Although matches were found, none passed the similarity threshold (> 0.4). "
            "This suggests that the query does not closely align with any document content. "
            "Consider rephrasing or using keywords present in the uploaded documents."
        )

    context = chunks_to_context(chunks)
    return answer_from_context(context, query)