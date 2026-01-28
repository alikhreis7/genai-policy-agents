"""
Policy RAG Agent - Retrieves relevant policy sections.

This agent is responsible for:
1. Searching the policy vector store
2. Returning relevant chunks with citations
3. Providing context for downstream synthesis

Key design decisions:
- Section-level chunking (not arbitrary token splits)
- Multiple retrieval strategies (semantic + keyword)
- Rich metadata for citation generation
"""

from typing import Optional
import hashlib

from .base import LLMAgent
from ..models.schemas import (
    UserQuery,
    PolicyChunk,
    RetrievalResult,
)
from ..config import get_settings


class PolicyRAGAgent(LLMAgent[RetrievalResult]):
    """
    Policy Retrieval Agent using RAG over policy documents.
    
    This agent:
    1. Takes a user query (possibly reformulated by the router)
    2. Searches the policy vector index
    3. Returns relevant chunks with metadata for citations
    
    The agent does NOT interpret the policies - that's the Synthesis Agent's job.
    This separation of concerns keeps retrieval focused and testable.
    """
    
    def __init__(self):
        super().__init__("policy_rag", use_openai=True)
        self._index = None
        self._chunks = None
        self._embeddings = None
        
    @property
    def description(self) -> str:
        return "Retrieves relevant policy sections using semantic search"
    
    def initialize_index(self, chunks: list[PolicyChunk]) -> None:
        """
        Initialize the FAISS index with policy chunks.
        
        Args:
            chunks: Pre-processed policy chunks with embeddings
        """
        try:
            import faiss
            import numpy as np
            from langchain_openai import OpenAIEmbeddings
            
            self._chunks = chunks
            
            # Create embeddings
            embeddings_model = OpenAIEmbeddings(
                model=self.settings.embedding_model,
                api_key=self.settings.openai_api_key
            )
            
            # Get embeddings for all chunks
            texts = [chunk.content for chunk in chunks]
            self._embeddings = embeddings_model.embed_documents(texts)
            
            # Build FAISS index
            dimension = len(self._embeddings[0])
            self._index = faiss.IndexFlatIP(dimension)  # Inner product for cosine sim
            
            # Normalize and add to index
            embeddings_array = np.array(self._embeddings).astype('float32')
            faiss.normalize_L2(embeddings_array)
            self._index.add(embeddings_array)
            
            self.logger.info(f"Initialized index with {len(chunks)} chunks")
            
        except ImportError as e:
            self.logger.warning(f"FAISS not available: {e}. Using mock index.")
            self._chunks = chunks
    
    async def run(
        self, 
        query: UserQuery,
        top_k: Optional[int] = None
    ) -> RetrievalResult:
        """
        Retrieve relevant policy chunks for a query.
        
        Args:
            query: User query (or reformulated query)
            top_k: Number of chunks to retrieve (default from settings)
            
        Returns:
            RetrievalResult with policy chunks
        """
        self._log_start(f"Query: {query.text[:50]}...")
        
        top_k = top_k or self.settings.retrieval_top_k
        
        if self._index is None or self._chunks is None:
            # Return mock results if index not initialized
            self.logger.warning("Index not initialized, returning mock results")
            return self._get_mock_results(query, top_k)
        
        try:
            import numpy as np
            from langchain_openai import OpenAIEmbeddings
            
            # Embed the query
            embeddings_model = OpenAIEmbeddings(
                model=self.settings.embedding_model,
                api_key=self.settings.openai_api_key
            )
            query_embedding = embeddings_model.embed_query(query.text)
            query_array = np.array([query_embedding]).astype('float32')
            
            import faiss
            faiss.normalize_L2(query_array)
            
            # Search
            scores, indices = self._index.search(query_array, top_k)
            
            # Build results
            retrieved_chunks = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx < len(self._chunks):
                    chunk = self._chunks[idx]
                    # Update relevance score
                    retrieved_chunk = PolicyChunk(
                        content=chunk.content,
                        source=chunk.source,
                        section=chunk.section,
                        relevance_score=float(score),
                        chunk_id=chunk.chunk_id,
                        metadata=chunk.metadata
                    )
                    retrieved_chunks.append(retrieved_chunk)
            
            result = RetrievalResult(
                policy_chunks=retrieved_chunks,
                total_sources=len(set(c.source for c in retrieved_chunks)),
                retrieval_metadata={
                    "top_k": top_k,
                    "query": query.text,
                    "method": "faiss_semantic"
                }
            )
            
            self._log_complete(f"Retrieved {len(retrieved_chunks)} chunks")
            return result
            
        except Exception as e:
            self._log_error(e)
            return self._get_mock_results(query, top_k)
    
    def _get_mock_results(self, query: UserQuery, top_k: int) -> RetrievalResult:
        """
        Return mock results for demo/testing.
        
        These mock results are based on realistic policy content
        to demonstrate the system's behavior.
        """
        # Mock policy chunks based on common query patterns
        mock_chunks = self._generate_mock_chunks(query.text)
        
        return RetrievalResult(
            policy_chunks=mock_chunks[:top_k],
            total_sources=len(set(c.source for c in mock_chunks[:top_k])),
            retrieval_metadata={
                "top_k": top_k,
                "query": query.text,
                "method": "mock"
            }
        )
    
    def _generate_mock_chunks(self, query: str) -> list[PolicyChunk]:
        """Generate mock chunks based on query content."""
        query_lower = query.lower()
        
        chunks = []
        
        # PII-related queries
        if any(term in query_lower for term in ["pii", "personal", "data", "privacy"]):
            chunks.extend([
                PolicyChunk(
                    content="""## Data Classification and Handling

Personal Identifiable Information (PII) must be classified as CONFIDENTIAL and handled according to the following requirements:

1. **Storage**: PII must be stored in approved data stores with encryption at rest (AES-256 minimum)
2. **Transmission**: All PII must be encrypted in transit using TLS 1.2 or higher
3. **Access Control**: Access to PII requires explicit authorization and must be logged
4. **Retention**: PII must not be retained longer than necessary for business purposes
5. **Caching**: PII MUST NOT be stored in general-purpose caches (Redis, Memcached) unless:
   - The cache is dedicated to PII handling
   - Encryption at rest is enabled
   - Access controls are enforced
   - TTL is set appropriately""",
                    source="data-security-policy.md",
                    section="Data Classification and Handling",
                    relevance_score=0.95,
                    chunk_id="dsp-001",
                    metadata={"page": 12, "last_updated": "2024-01-15"}
                ),
                PolicyChunk(
                    content="""## Approved Data Stores for Sensitive Data

The following data stores are approved for PII storage:

| Store Type | Approved Products | Notes |
|------------|-------------------|-------|
| Relational DB | PostgreSQL, MySQL (with encryption) | Preferred for structured PII |
| Document DB | MongoDB Enterprise | Must enable field-level encryption |
| Key-Value | AWS DynamoDB, Azure CosmosDB | Cloud-managed encryption required |

**NOT APPROVED for PII:**
- Redis (general purpose)
- Elasticsearch (unless configured for compliance)
- Local file systems
- Spreadsheets or shared drives""",
                    source="approved-technologies.md",
                    section="Approved Data Stores",
                    relevance_score=0.88,
                    chunk_id="at-003",
                    metadata={"page": 5}
                ),
            ])
        
        # Database/storage queries
        if any(term in query_lower for term in ["database", "store", "storage", "redis", "cache"]):
            chunks.extend([
                PolicyChunk(
                    content="""## Caching Guidelines

Caching should be used to improve performance but must follow these guidelines:

1. **Cache Sensitivity**: Never cache sensitive data (PII, credentials, tokens) in shared caches
2. **TTL Requirements**: All cached items must have explicit TTL (max 24 hours for user data)
3. **Invalidation**: Implement cache invalidation for data consistency
4. **Encryption**: Enable encryption for caches containing business-sensitive data

**Redis Specific:**
- Use Redis Cluster for high availability
- Enable AUTH for all connections
- Do not expose Redis to public networks""",
                    source="performance-guidelines.md",
                    section="Caching Guidelines",
                    relevance_score=0.85,
                    chunk_id="pg-007",
                    metadata={"page": 23}
                ),
            ])
        
        # Security queries
        if any(term in query_lower for term in ["security", "authentication", "auth", "password"]):
            chunks.extend([
                PolicyChunk(
                    content="""## Authentication Requirements

All services must implement authentication according to these requirements:

1. **No Hardcoded Credentials**: Credentials must never be stored in code or config files
2. **Secret Management**: Use approved secret management (HashiCorp Vault, AWS Secrets Manager)
3. **Token Lifetime**: Access tokens max 1 hour, refresh tokens max 30 days
4. **MFA**: Required for all admin access and sensitive operations
5. **Password Policy**: 
   - Minimum 12 characters
   - Complexity requirements enforced
   - No password reuse (last 12 passwords)""",
                    source="security-policy.md",
                    section="Authentication Requirements",
                    relevance_score=0.90,
                    chunk_id="sp-002",
                    metadata={"page": 8}
                ),
            ])
        
        # API/service queries
        if any(term in query_lower for term in ["api", "gateway", "service", "bypass"]):
            chunks.extend([
                PolicyChunk(
                    content="""## API Gateway Requirements

All external-facing APIs must route through the API Gateway. Internal service-to-service 
communication may bypass the gateway under specific conditions:

**Gateway Required:**
- All public APIs
- Partner integrations
- Mobile app backends

**Gateway Optional (with approval):**
- Internal service mesh traffic (with mTLS)
- High-frequency internal data pipelines
- Real-time streaming between approved services

**Never Bypass:**
- Any traffic involving PII
- Authentication/authorization flows
- External partner communications""",
                    source="api-standards.md",
                    section="API Gateway Requirements",
                    relevance_score=0.92,
                    chunk_id="as-001",
                    metadata={"page": 3}
                ),
            ])
        
        # Default fallback
        if not chunks:
            chunks.append(
                PolicyChunk(
                    content="""## General Development Guidelines

When implementing new features or making architectural decisions, developers should:

1. Follow the principle of least privilege
2. Document all significant decisions in ADRs
3. Conduct security reviews for sensitive changes
4. Ensure observability (logging, metrics, tracing)
5. Consider failure modes and implement appropriate fallbacks

For specific policy questions, consult the relevant policy documents or 
reach out to the Architecture Review Board.""",
                    source="development-guidelines.md",
                    section="General Guidelines",
                    relevance_score=0.60,
                    chunk_id="dg-001",
                    metadata={"page": 1}
                )
            )
        
        return chunks


# Standalone function for LangGraph
async def retrieve_policies(query: UserQuery, top_k: int = 5) -> RetrievalResult:
    """Retrieve policy chunks - designed for LangGraph node."""
    agent = PolicyRAGAgent()
    return await agent.run(query, top_k=top_k)
