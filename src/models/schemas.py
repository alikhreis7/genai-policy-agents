"""
Pydantic schemas for structured inputs and outputs.

These schemas define the contracts between agents and ensure
type safety throughout the system. Every agent returns validated
structured data, not raw strings.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# =============================================================================
# Query Types
# =============================================================================

class QueryIntent(str, Enum):
    """Classification of user query intent."""
    
    POLICY_LOOKUP = "policy_lookup"
    """User wants to know if something is allowed by policy."""
    
    DECISION_SUPPORT = "decision_support"
    """User wants guidance on a design/architecture decision."""
    
    RISK_CHECK = "risk_check"
    """User wants to check for potential violations or risks."""
    
    CLARIFICATION = "clarification"
    """Query is unclear and needs clarification."""
    
    OUT_OF_SCOPE = "out_of_scope"
    """Query is outside the system's domain."""


class UserQuery(BaseModel):
    """Incoming user query with metadata."""
    
    text: str = Field(..., description="The raw query text from the user")
    context: Optional[str] = Field(
        default=None, 
        description="Optional additional context provided by the user"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session identifier for conversation tracking"
    )


class IntentClassification(BaseModel):
    """Result of intent classification by the Router Agent."""
    
    intent: QueryIntent = Field(..., description="Classified intent type")
    confidence: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Confidence in the classification (0-1)"
    )
    reasoning: str = Field(
        ..., 
        description="Explanation for the classification decision"
    )
    requires_policy_search: bool = Field(
        default=False,
        description="Whether to invoke the Policy RAG agent"
    )
    requires_decision_search: bool = Field(
        default=False,
        description="Whether to invoke the Decision History agent"
    )
    requires_risk_analysis: bool = Field(
        default=False,
        description="Whether to invoke the Risk agent"
    )
    reformulated_query: Optional[str] = Field(
        default=None,
        description="Optimized query for retrieval (if different from original)"
    )


# =============================================================================
# Retrieved Content Types
# =============================================================================

class PolicyChunk(BaseModel):
    """A retrieved chunk from a policy document."""
    
    content: str = Field(..., description="The text content of the chunk")
    source: str = Field(..., description="Source document name/path")
    section: Optional[str] = Field(
        default=None,
        description="Section or heading this chunk belongs to"
    )
    relevance_score: float = Field(
        ..., 
        ge=0.0, 
        le=1.0,
        description="Similarity score from retrieval"
    )
    chunk_id: str = Field(..., description="Unique identifier for this chunk")
    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata (page, line numbers, etc.)"
    )


class DecisionRecord(BaseModel):
    """A retrieved architectural decision record (ADR) or similar."""
    
    title: str = Field(..., description="Title of the decision record")
    content: str = Field(..., description="Full content or summary")
    decision: str = Field(..., description="The actual decision made")
    rationale: Optional[str] = Field(
        default=None,
        description="Reasoning behind the decision"
    )
    status: str = Field(
        default="accepted",
        description="Status: proposed, accepted, deprecated, superseded"
    )
    date: Optional[str] = Field(default=None, description="Date of the decision")
    source: str = Field(..., description="Source repository or document")
    relevance_score: float = Field(..., ge=0.0, le=1.0)


class RetrievalResult(BaseModel):
    """Combined retrieval results from all sources."""
    
    policy_chunks: list[PolicyChunk] = Field(
        default_factory=list,
        description="Retrieved policy document chunks"
    )
    decision_records: list[DecisionRecord] = Field(
        default_factory=list,
        description="Retrieved ADRs and decision records"
    )
    total_sources: int = Field(
        default=0,
        description="Total number of unique sources consulted"
    )
    retrieval_metadata: dict = Field(
        default_factory=dict,
        description="Timing, query expansions, and other metadata"
    )


# =============================================================================
# Agent Output Types
# =============================================================================

class Citation(BaseModel):
    """A citation linking a claim to its source."""
    
    claim: str = Field(..., description="The specific claim being cited")
    source: str = Field(..., description="Source document or record")
    section: Optional[str] = Field(default=None, description="Specific section")
    quote: Optional[str] = Field(
        default=None,
        description="Direct quote from the source (if applicable)"
    )
    relevance: str = Field(
        default="direct",
        description="How the source relates: direct, supporting, contextual"
    )


class RiskAssessment(BaseModel):
    """Risk analysis output from the Risk Agent."""
    
    risk_level: str = Field(
        ...,
        description="Risk level: low, medium, high, critical"
    )
    identified_risks: list[str] = Field(
        default_factory=list,
        description="List of identified risks or concerns"
    )
    policy_conflicts: list[str] = Field(
        default_factory=list,
        description="Any conflicting policies detected"
    )
    missing_context: list[str] = Field(
        default_factory=list,
        description="Information that would help but is missing"
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Suggested actions or mitigations"
    )


class ConfidenceScore(BaseModel):
    """Confidence assessment from the Confidence Agent."""
    
    overall_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall confidence in the answer (0-1)"
    )
    grounding_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="How well the answer is grounded in retrieved sources"
    )
    coverage_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="How well the sources cover the query"
    )
    consistency_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Internal consistency of the answer"
    )
    requires_escalation: bool = Field(
        default=False,
        description="Whether this should be escalated to a human"
    )
    escalation_reason: Optional[str] = Field(
        default=None,
        description="Why escalation is recommended"
    )
    claims_verified: int = Field(default=0, description="Number of claims verified")
    claims_unverified: int = Field(default=0, description="Number of unverified claims")


class PolicyAnswer(BaseModel):
    """Synthesized answer from the Synthesis Agent."""
    
    answer: str = Field(
        ...,
        description="The main answer to the user's query"
    )
    summary: str = Field(
        ...,
        description="One-sentence summary of the answer"
    )
    citations: list[Citation] = Field(
        default_factory=list,
        description="Citations supporting the answer"
    )
    caveats: list[str] = Field(
        default_factory=list,
        description="Important caveats or limitations"
    )
    related_topics: list[str] = Field(
        default_factory=list,
        description="Related topics the user might want to explore"
    )
    reasoning: str = Field(
        ...,
        description="Chain of reasoning used to arrive at the answer"
    )


# =============================================================================
# Final Output
# =============================================================================

class EngineResponse(BaseModel):
    """Complete response from the Policy Intelligence Engine."""
    
    query: UserQuery = Field(..., description="Original user query")
    intent: IntentClassification = Field(..., description="Classified intent")
    answer: PolicyAnswer = Field(..., description="Synthesized answer")
    confidence: ConfidenceScore = Field(..., description="Confidence assessment")
    risk: Optional[RiskAssessment] = Field(
        default=None,
        description="Risk assessment (if applicable)"
    )
    retrieval: RetrievalResult = Field(
        ...,
        description="Retrieved sources used"
    )
    
    # Metadata
    processing_time_ms: float = Field(
        default=0.0,
        description="Total processing time in milliseconds"
    )
    agents_invoked: list[str] = Field(
        default_factory=list,
        description="List of agents that were invoked"
    )
    model_calls: int = Field(
        default=0,
        description="Number of LLM API calls made"
    )
    
    def should_escalate(self) -> bool:
        """Check if this response should be escalated to a human."""
        return (
            self.confidence.requires_escalation or
            self.confidence.overall_confidence < 0.5 or
            (self.risk and self.risk.risk_level in ["high", "critical"])
        )


# =============================================================================
# Agent State (for LangGraph)
# =============================================================================

class AgentState(BaseModel):
    """State passed between agents in the LangGraph workflow."""
    
    model_config = {"arbitrary_types_allowed": True}
    
    # Input
    query: UserQuery
    
    # Router output
    intent: Optional[IntentClassification] = None
    
    # Retrieval outputs
    retrieval: RetrievalResult = Field(default_factory=RetrievalResult)
    
    # Agent outputs
    answer: Optional[PolicyAnswer] = None
    confidence: Optional[ConfidenceScore] = None
    risk: Optional[RiskAssessment] = None
    
    # Tracking
    agents_invoked: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
