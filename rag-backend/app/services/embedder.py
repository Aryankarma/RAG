from pinecone import Pinecone
import cohere
import re
from typing import List, Dict, Any
from app.config import COHERE_API_KEY, PINECONE_API_KEY, PINECONE_INDEX

co = cohere.Client(COHERE_API_KEY)

# Initialize Pinecone with the new API
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX)

class PolicyDocumentProcessor:
    """Enhanced document processor for insurance policy documents"""
    
    def __init__(self):
        self.section_patterns = {
            'coverage': [
                r'coverage\s+(?:terms|conditions|details)',
                r'what\s+is\s+covered',
                r'covered\s+(?:procedures|treatments|services)',
                r'benefits\s+covered'
            ],
            'exclusions': [
                r'exclusions?',
                r'not\s+covered',
                r'what\s+is\s+not\s+covered',
                r'exceptions?'
            ],
            'waiting_period': [
                r'waiting\s+period',
                r'waiting\s+time',
                r'pre-existing\s+conditions?',
                r'moratorium\s+period'
            ],
            'age_limits': [
                r'age\s+(?:limit|eligibility|criteria)',
                r'minimum\s+age',
                r'maximum\s+age',
                r'age\s+(?:requirements?|restrictions?)'
            ],
            'claim_procedures': [
                r'claim\s+(?:process|procedure)',
                r'how\s+to\s+claim',
                r'claim\s+settlement',
                r'reimbursement'
            ],
            'premium': [
                r'premium',
                r'cost',
                r'price',
                r'payment'
            ]
        }
    
    def identify_section_type(self, text: str) -> List[str]:
        """Identify what type of policy section this text belongs to"""
        text_lower = text.lower()
        sections = []
        
        for section_type, patterns in self.section_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    sections.append(section_type)
                    break
        
        return sections if sections else ['general']
    
    def extract_structured_info(self, text: str) -> Dict[str, Any]:
        """Extract structured information from policy text"""
        info = {}
        
        # Extract amounts
        amount_patterns = [
            r'(?:₹|Rs\.?\s*|INR\s*)(\d+(?:,\d+)*(?:\.\d+)?)',
            r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:rupees?|lakhs?|crores?)'
        ]
        
        amounts = []
        for pattern in amount_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    amount = float(match.replace(',', ''))
                    amounts.append(amount)
                except ValueError:
                    continue
        
        if amounts:
            info['amounts'] = amounts
            info['max_amount'] = max(amounts)
            info['min_amount'] = min(amounts)
        
        # Extract age information
        age_patterns = [
            r'(\d+)\s*(?:to|-)?\s*(\d+)?\s*years?\s*(?:of\s+age)?',
            r'minimum\s+age[:\s]*(\d+)',
            r'maximum\s+age[:\s]*(\d+)',
            r'age\s+(?:limit|range)[:\s]*(\d+)(?:\s*(?:to|-)?\s*(\d+))?'
        ]
        
        ages = []
        for pattern in age_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    ages.extend([int(x) for x in match if x.isdigit()])
                else:
                    ages.append(int(match))
        
        if ages:
            info['ages'] = list(set(ages))
            info['min_age'] = min(ages)
            info['max_age'] = max(ages)
        
        # Extract time periods
        period_patterns = [
            r'(\d+)\s*(month|year|day)s?',
            r'waiting\s+period[:\s]*(\d+)\s*(month|year|day)s?'
        ]
        
        periods = []
        for pattern in period_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                value, unit = match
                periods.append({'value': int(value), 'unit': unit.lower()})
        
        if periods:
            info['time_periods'] = periods
        
        # Extract procedures/treatments
        procedure_keywords = [
            'surgery', 'operation', 'treatment', 'procedure', 'therapy',
            'knee', 'heart', 'dental', 'eye', 'cardiac', 'orthopedic',
            'bypass', 'transplant', 'replacement', 'repair'
        ]
        
        found_procedures = []
        text_lower = text.lower()
        for keyword in procedure_keywords:
            if keyword in text_lower:
                # Extract context around the keyword
                pattern = rf'\b[\w\s]*{keyword}[\w\s]*\b'
                matches = re.findall(pattern, text_lower)
                found_procedures.extend(matches)
        
        if found_procedures:
            info['procedures'] = list(set(found_procedures))
        
        return info

def create_enhanced_chunks(text: str, chunk_size: int = 800, overlap: int = 100) -> List[Dict[str, Any]]:
    """Create enhanced chunks with metadata (compatible with existing splitter)"""
    processor = PolicyDocumentProcessor()
    
    # Use similar chunking logic as the original splitter
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap)
    basic_chunks = splitter.split_text(text)
    
    # Enhance chunks with metadata
    enhanced_chunks = []
    for i, chunk_text in enumerate(basic_chunks):
        if chunk_text.strip():
            # Extract metadata for this chunk
            section_types = processor.identify_section_type(chunk_text)
            structured_info = processor.extract_structured_info(chunk_text)
            
            chunk_data = {
                'id': f'chunk-{i}',
                'text': chunk_text,
                'section_types': section_types,
                'structured_info': structured_info,
                'length': len(chunk_text)
            }
            
            enhanced_chunks.append(chunk_data)
    
    return enhanced_chunks

async def enhanced_embed_and_store(chunks):
    """Enhanced embedding with structured metadata"""
    
    # If chunks is a list of strings (from original splitter), enhance them
    if chunks and isinstance(chunks[0], str):
        full_text = "\n".join(chunks)
        chunks_data = create_enhanced_chunks(full_text)
    else:
        # Already enhanced chunks
        chunks_data = chunks
    
    # Prepare texts for embedding
    chunk_texts = [chunk['text'] if isinstance(chunk, dict) else chunk for chunk in chunks_data]
    
    # Generate embeddings
    responses = co.embed(
        texts=chunk_texts, 
        model="embed-english-v3.0", 
        input_type="search_document"
    )
    
    # Prepare vectors for upsert
    vectors_to_upsert = []
    
    for i, (chunk_data, vector) in enumerate(zip(chunks_data, responses.embeddings)):
        if isinstance(chunk_data, dict):
            # Enhanced chunk with metadata
            metadata = {
                'text': chunk_data['text'],
                'section_types': chunk_data['section_types'],
                'length': chunk_data['length']
            }
            
            # Add structured info to metadata
            structured_info = chunk_data['structured_info']
            if 'amounts' in structured_info:
                metadata['has_amounts'] = True
                metadata['max_amount'] = structured_info['max_amount']
                metadata['min_amount'] = structured_info['min_amount']
            
            if 'ages' in structured_info:
                metadata['has_ages'] = True
                metadata['min_age'] = structured_info['min_age']
                metadata['max_age'] = structured_info['max_age']
            
            if 'procedures' in structured_info:
                metadata['has_procedures'] = True
                metadata['procedures'] = structured_info['procedures'][:5]  # Limit to first 5
            
            if 'time_periods' in structured_info:
                metadata['has_time_periods'] = True
            
            vectors_to_upsert.append((
                chunk_data['id'],
                vector,
                metadata
            ))
        else:
            # Original chunk format (backward compatibility)
            vectors_to_upsert.append((
                f"chunk-{i}",
                vector,
                {"text": chunk_data}
            ))
    
    # Upsert to Pinecone in batches
    batch_size = 100
    for i in range(0, len(vectors_to_upsert), batch_size):
        batch = vectors_to_upsert[i:i + batch_size]
        index.upsert(batch)
    
    print(f"Successfully embedded and stored {len(vectors_to_upsert)} chunks")
    return len(vectors_to_upsert)

# Backward compatibility function - this is what your existing code calls
async def embed_and_store(chunks):
    """Main embed function - enhanced but backward compatible"""
    return await enhanced_embed_and_store(chunks)