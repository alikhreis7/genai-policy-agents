"""
Decision History RAG Agent - Retrieves architectural decisions.

STUB IMPLEMENTATION

This agent would retrieve:
- Architectural Decision Records (ADRs)
- Request for Comments (RFCs)
- PR discussions and design docs
- Historical context for decisions

The interface is complete to demonstrate the design pattern.
Full implementation would:
1. Index ADRs from GitHub repositories
2. Parse decision documents
3. Extract decision, rationale, and status
4. Build a separate vector index
"""

from typing import Optional, List

from .base import LLMAgent
from ..models.schemas import (
    UserQuery,
    DecisionRecord,
    RetrievalResult,
)


class DecisionRAGAgent(LLMAgent[RetrievalResult]):
    """
    Decision History Agent - Retrieves relevant ADRs and design decisions.
    
    STUB: Returns mock data for demonstration.
    
    In production, this would:
    - Connect to GitHub API for ADR repositories
    - Parse markdown decision documents
    - Build and query a vector index
    - Extract structured decision information
    
    Why a separate agent from PolicyRAGAgent?
    
    1. Different data sources (repos vs policy docs)
    2. Different chunking strategies (full documents vs sections)
    3. Different metadata extraction (decision/rationale vs policy rules)
    4. Allows independent scaling and optimization
    """
    
    def __init__(self):
        super().__init__("decision_rag", use_openai=True)
        self._index = None
    
    @property
    def description(self) -> str:
        return "Retrieves architectural decision records and design history"
    
    async def run(
        self, 
        query: UserQuery,
        top_k: int = 5
    ) -> RetrievalResult:
        """
        Retrieve relevant decision records.
        
        STUB: Returns mock records based on query content.
        """
        self._log_start(f"Query: {query.text[:50]}...")
        
        # Generate mock records based on query
        records = self._generate_mock_records(query.text, top_k)
        
        result = RetrievalResult(
            decision_records=records,
            total_sources=len(set(r.source for r in records)),
            retrieval_metadata={
                "top_k": top_k,
                "query": query.text,
                "method": "mock",
                "note": "Stub implementation - would use vector search in production"
            }
        )
        
        self._log_complete(f"Retrieved {len(records)} decision records (mock)")
        return result
    
    def _generate_mock_records(self, query: str, top_k: int) -> List[DecisionRecord]:
        """Generate contextually relevant mock records."""
        query_lower = query.lower()
        records = []
        
        # API/Gateway decisions
        if any(term in query_lower for term in ["api", "gateway", "bypass", "service"]):
            records.append(DecisionRecord(
                title="ADR-015: API Gateway Architecture",
                content="""We decided to implement a centralized API gateway for all external traffic.

## Context
Our services were directly exposed to the internet, creating security and observability challenges.

## Decision
All external traffic must route through the API Gateway (Kong). Internal service-to-service 
communication may bypass the gateway when using mTLS within the service mesh.

## Consequences
- Positive: Centralized security, rate limiting, logging
- Positive: Consistent authentication across services
- Negative: Adds latency (~5ms p99)
- Negative: Gateway becomes a critical dependency""",
                decision="External traffic through gateway; internal traffic can use direct mTLS",
                rationale="Centralized security controls outweigh latency cost for external traffic",
                status="accepted",
                date="2023-11-20",
                source="adr/015-api-gateway.md",
                relevance_score=0.92
            ))
        
        # Caching decisions
        if any(term in query_lower for term in ["cache", "redis", "performance"]):
            records.append(DecisionRecord(
                title="ADR-023: Caching Strategy",
                content="""Decision on caching infrastructure and policies.

## Context
Multiple teams were implementing caching differently, leading to inconsistencies.

## Decision
- Use Redis Cluster for distributed caching
- Session data: 24 hour TTL
- Application cache: varies by use case
- NO PII in general-purpose caches

## Consequences
- Standardized approach across teams
- Clear security boundaries for cached data""",
                decision="Redis Cluster for caching; no PII in caches",
                rationale="Standardization reduces operational complexity; PII restriction prevents data leaks",
                status="accepted",
                date="2024-03-15",
                source="adr/023-caching-strategy.md",
                relevance_score=0.88
            ))
        
        # Database decisions
        if any(term in query_lower for term in ["database", "postgres", "storage", "data"]):
            records.append(DecisionRecord(
                title="ADR-031: Database Technology Standards",
                content="""Standardizing database technologies across the organization.

## Context
Teams were choosing databases ad-hoc, increasing operational burden.

## Decision
- PostgreSQL: Default for relational data
- DynamoDB: High-scale key-value workloads
- MongoDB: Document stores (requires approval)
- Elasticsearch: Search and analytics only

## Consequences
- Reduced number of database technologies to support
- Clear guidance for teams starting new projects""",
                decision="PostgreSQL as default; specific technologies for specific use cases",
                rationale="Operational efficiency through standardization",
                status="accepted",
                date="2024-01-10",
                source="adr/031-database-standards.md",
                relevance_score=0.85
            ))
        
        # Security decisions
        if any(term in query_lower for term in ["security", "auth", "secret"]):
            records.append(DecisionRecord(
                title="ADR-008: Secret Management",
                content="""Standardizing secret management across all services.

## Context
Secrets were stored inconsistently - environment variables, config files, and even code.

## Decision
- HashiCorp Vault as primary secret store
- AWS Secrets Manager as alternative for AWS-native services
- NO secrets in code, config files, or environment variables
- Rotation required: 90 days for DB passwords, 180 days for API keys

## Consequences
- Centralized audit trail for secret access
- Automated rotation reduces breach risk""",
                decision="Vault for secrets; mandatory rotation; no secrets in code",
                rationale="Security and auditability require centralized management",
                status="accepted",
                date="2023-06-01",
                source="adr/008-secret-management.md",
                relevance_score=0.90
            ))
        
        # Return at most top_k records, or a default if none matched
        if not records:
            records.append(DecisionRecord(
                title="ADR-001: Decision Record Format",
                content="Standard template for architectural decisions.",
                decision="Use ADR format for all significant decisions",
                rationale="Consistency and traceability",
                status="accepted",
                date="2023-01-01",
                source="adr/001-adr-template.md",
                relevance_score=0.50
            ))
        
        return records[:top_k]


# Standalone function for LangGraph
async def retrieve_decisions(query: UserQuery, top_k: int = 5) -> RetrievalResult:
    """Retrieve decision records - designed for LangGraph node."""
    agent = DecisionRAGAgent()
    return await agent.run(query, top_k=top_k)
