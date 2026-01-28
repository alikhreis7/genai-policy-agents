"""
Policy Search Tool - Structured tool for policy retrieval.

This module demonstrates the tool-calling pattern that's central
to agent-based GenAI systems. Tools are:
- Typed (inputs and outputs are validated)
- Documented (LLM can understand what they do)
- Composable (agents can combine multiple tools)
"""

from typing import Optional
from pydantic import BaseModel, Field

from ..models.schemas import PolicyChunk, RetrievalResult


class PolicySearchInput(BaseModel):
    """Input schema for policy search tool."""
    
    query: str = Field(
        ...,
        description="Search query for policy documents"
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of results to return"
    )
    source_filter: Optional[str] = Field(
        default=None,
        description="Optional filter by source document name"
    )


class PolicySearchOutput(BaseModel):
    """Output schema for policy search tool."""
    
    chunks: list[PolicyChunk] = Field(
        default_factory=list,
        description="Retrieved policy chunks"
    )
    total_found: int = Field(
        default=0,
        description="Total number of matching chunks"
    )
    query_used: str = Field(
        ...,
        description="The query that was executed"
    )


class PolicySearchTool:
    """
    Tool for searching policy documents.
    
    This class represents a tool that can be used by agents through
    function calling. It demonstrates several important patterns:
    
    1. **Typed I/O**: Input and output are Pydantic models
    2. **Documentation**: Description helps LLM understand usage
    3. **Validation**: Inputs are validated before execution
    4. **Idempotency**: Same input always produces same search
    """
    
    name: str = "search_policies"
    description: str = """Search enterprise policy documents for relevant sections.
    
Use this tool when you need to find policy information about:
- Data handling and security requirements
- API and service standards
- Authentication and authorization rules
- Compliance requirements

The tool returns relevant policy chunks with source attribution."""
    
    def __init__(self):
        self._rag_agent = None
    
    @property
    def rag_agent(self):
        """Lazy load the RAG agent."""
        if self._rag_agent is None:
            from ..agents.policy_rag import PolicyRAGAgent
            self._rag_agent = PolicyRAGAgent()
        return self._rag_agent
    
    def get_schema(self) -> dict:
        """
        Return the JSON schema for this tool.
        
        This format is compatible with OpenAI's function calling API.
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": PolicySearchInput.model_json_schema()
            }
        }
    
    async def execute(self, input_data: PolicySearchInput) -> PolicySearchOutput:
        """
        Execute the policy search.
        
        Args:
            input_data: Validated search input
            
        Returns:
            Search results with policy chunks
        """
        from ..models.schemas import UserQuery
        
        # Create query object
        query = UserQuery(text=input_data.query)
        
        # Execute search
        result = await self.rag_agent.run(query, top_k=input_data.top_k)
        
        # Apply source filter if specified
        chunks = result.policy_chunks
        if input_data.source_filter:
            chunks = [
                c for c in chunks 
                if input_data.source_filter.lower() in c.source.lower()
            ]
        
        return PolicySearchOutput(
            chunks=chunks,
            total_found=len(chunks),
            query_used=input_data.query
        )
    
    def execute_sync(self, input_data: PolicySearchInput) -> PolicySearchOutput:
        """Synchronous version."""
        import asyncio
        return asyncio.run(self.execute(input_data))


# Convenience function for direct use
async def search_policies(
    query: str, 
    top_k: int = 5,
    source_filter: Optional[str] = None
) -> PolicySearchOutput:
    """
    Search policy documents.
    
    This is a convenience function that wraps the PolicySearchTool.
    Can be used directly or registered as a LangChain tool.
    """
    tool = PolicySearchTool()
    input_data = PolicySearchInput(
        query=query,
        top_k=top_k,
        source_filter=source_filter
    )
    return await tool.execute(input_data)
