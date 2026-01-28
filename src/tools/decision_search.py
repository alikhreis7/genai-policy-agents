"""
Decision Search Tool - Search architectural decision records.

This tool searches ADRs, RFCs, and historical design decisions.
Currently a stub - demonstrates the interface for future implementation.
"""

from typing import Optional
from pydantic import BaseModel, Field

from ..models.schemas import DecisionRecord


class DecisionSearchInput(BaseModel):
    """Input schema for decision search tool."""
    
    query: str = Field(
        ...,
        description="Search query for decision records"
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of results to return"
    )
    status_filter: Optional[str] = Field(
        default=None,
        description="Filter by status: proposed, accepted, deprecated, superseded"
    )


class DecisionSearchOutput(BaseModel):
    """Output schema for decision search tool."""
    
    records: list[DecisionRecord] = Field(
        default_factory=list,
        description="Retrieved decision records"
    )
    total_found: int = Field(
        default=0,
        description="Total number of matching records"
    )
    query_used: str = Field(
        ...,
        description="The query that was executed"
    )


class DecisionSearchTool:
    """
    Tool for searching architectural decision records.
    
    NOTE: This is currently a stub implementation that returns
    mock data. The full implementation would:
    
    1. Index ADRs from repositories (GitHub API)
    2. Parse RFC documents
    3. Extract decision and rationale
    4. Build a separate vector index
    
    The interface is complete to demonstrate the design pattern.
    """
    
    name: str = "search_decisions"
    description: str = """Search architectural decision records (ADRs) and RFCs.
    
Use this tool when you need to find:
- Past architectural decisions and their rationale
- Design patterns that have been approved or rejected
- Historical context for current architecture

The tool returns decision records with status and reasoning."""
    
    def get_schema(self) -> dict:
        """Return the JSON schema for this tool."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": DecisionSearchInput.model_json_schema()
            }
        }
    
    async def execute(self, input_data: DecisionSearchInput) -> DecisionSearchOutput:
        """
        Execute the decision search.
        
        Currently returns mock data for demonstration.
        """
        # Mock implementation - would be real vector search
        mock_records = self._get_mock_records(input_data.query)
        
        # Apply status filter
        records = mock_records
        if input_data.status_filter:
            records = [
                r for r in records
                if r.status.lower() == input_data.status_filter.lower()
            ]
        
        return DecisionSearchOutput(
            records=records[:input_data.top_k],
            total_found=len(records),
            query_used=input_data.query
        )
    
    def _get_mock_records(self, query: str) -> list[DecisionRecord]:
        """Generate mock ADRs based on query."""
        query_lower = query.lower()
        
        records = []
        
        if any(term in query_lower for term in ["cache", "redis", "performance"]):
            records.append(DecisionRecord(
                title="ADR-023: Caching Strategy",
                content="Decision to use Redis for session caching with specific security controls.",
                decision="Use Redis Cluster for session and application caching, with encryption enabled and no PII storage.",
                rationale="Redis provides sub-millisecond latency needed for session management. Cluster mode ensures high availability. PII restriction aligns with data security policy.",
                status="accepted",
                date="2024-03-15",
                source="architecture-decisions/ADR-023.md",
                relevance_score=0.88
            ))
        
        if any(term in query_lower for term in ["api", "gateway", "service"]):
            records.append(DecisionRecord(
                title="ADR-015: API Gateway Pattern",
                content="Decision to implement centralized API gateway for external traffic.",
                decision="All external API traffic must route through Kong API Gateway. Internal service mesh traffic may use direct communication with mTLS.",
                rationale="Centralizes security controls, rate limiting, and observability. Internal traffic exemption allows for performance-critical paths.",
                status="accepted",
                date="2023-11-20",
                source="architecture-decisions/ADR-015.md",
                relevance_score=0.92
            ))
        
        if any(term in query_lower for term in ["database", "postgres", "data"]):
            records.append(DecisionRecord(
                title="ADR-031: Database Selection Criteria",
                content="Criteria for selecting databases for new services.",
                decision="PostgreSQL as default for relational data. DynamoDB for high-scale key-value. MongoDB only with explicit approval for document stores.",
                rationale="Reduces operational complexity by standardizing. PostgreSQL covers 80% of use cases. NoSQL options available for specific needs.",
                status="accepted",
                date="2024-01-10",
                source="architecture-decisions/ADR-031.md",
                relevance_score=0.85
            ))
        
        # Always include a general record
        if not records:
            records.append(DecisionRecord(
                title="ADR-001: Decision Record Template",
                content="Standard template for architectural decision records.",
                decision="All significant architectural decisions must be documented using the ADR template.",
                rationale="Ensures consistency, traceability, and knowledge sharing across teams.",
                status="accepted",
                date="2023-01-01",
                source="architecture-decisions/ADR-001.md",
                relevance_score=0.50
            ))
        
        return records


# Convenience function
async def search_decisions(
    query: str,
    top_k: int = 5,
    status_filter: Optional[str] = None
) -> DecisionSearchOutput:
    """Search decision records."""
    tool = DecisionSearchTool()
    input_data = DecisionSearchInput(
        query=query,
        top_k=top_k,
        status_filter=status_filter
    )
    return await tool.execute(input_data)
