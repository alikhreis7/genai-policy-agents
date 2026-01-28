"""
Pydantic models for structured inputs and outputs.

All agent communication uses typed schemas for validation and clarity.
"""

from .schemas import (
    # Query types
    UserQuery,
    QueryIntent,
    IntentClassification,
    
    # Retrieved content
    PolicyChunk,
    DecisionRecord,
    RetrievalResult,
    
    # Agent outputs
    PolicyAnswer,
    Citation,
    RiskAssessment,
    ConfidenceScore,
    
    # Final output
    EngineResponse,
)

__all__ = [
    "UserQuery",
    "QueryIntent",
    "IntentClassification",
    "PolicyChunk",
    "DecisionRecord",
    "RetrievalResult",
    "PolicyAnswer",
    "Citation",
    "RiskAssessment",
    "ConfidenceScore",
    "EngineResponse",
]
