"""
Confidence & Hallucination Detection Agent.

STUB IMPLEMENTATION

This agent is crucial for enterprise trust. It:
1. Extracts claims from the synthesized answer
2. Verifies each claim against retrieved sources
3. Assigns confidence scores
4. Triggers escalation when confidence is low

This agent embodies the principle: "LLMs are unreliable components."
"""

from typing import List, Optional

from .base import LLMAgent
from ..models.schemas import (
    UserQuery,
    PolicyChunk,
    PolicyAnswer,
    ConfidenceScore,
)
from ..config import get_settings


class ConfidenceAgent(LLMAgent[ConfidenceScore]):
    """
    Confidence Assessment Agent - Verifies answer grounding.
    
    STUB: Uses heuristics for confidence scoring.
    
    In production, this would:
    1. Use an LLM to extract individual claims from the answer
    2. For each claim, verify it appears in retrieved sources
    3. Calculate grounding score (% of claims verified)
    4. Use a second LLM (Gemini) for cross-validation
    
    Why this agent exists (interview talking point):
    
    "LLMs hallucinate. In enterprise systems, we can't afford that.
    This agent provides a second opinion specifically focused on
    verifying that the answer is grounded in actual sources.
    When it can't verify, it triggers human escalation."
    """
    
    def __init__(self):
        super().__init__("confidence", use_openai=True, use_gemini=True)
        self.settings = get_settings()
    
    @property
    def description(self) -> str:
        return "Verifies answer grounding and assigns confidence scores"
    
    async def run(
        self,
        query: UserQuery,
        answer: Optional[PolicyAnswer],
        policy_chunks: List[PolicyChunk]
    ) -> ConfidenceScore:
        """
        Assess confidence in the generated answer.
        
        STUB: Uses heuristics to generate realistic scores.
        """
        self._log_start("Assessing answer confidence")
        
        if not answer:
            return ConfidenceScore(
                overall_confidence=0.0,
                grounding_score=0.0,
                coverage_score=0.0,
                consistency_score=0.0,
                requires_escalation=True,
                escalation_reason="No answer was generated"
            )
        
        # Calculate component scores
        grounding = self._calculate_grounding_score(answer, policy_chunks)
        coverage = self._calculate_coverage_score(query, policy_chunks)
        consistency = self._calculate_consistency_score(answer)
        
        # Overall is weighted average
        overall = (grounding * 0.4 + coverage * 0.3 + consistency * 0.3)
        
        # Determine if escalation is needed
        requires_escalation = overall < self.settings.escalation_threshold
        escalation_reason = None
        
        if requires_escalation:
            if grounding < 0.5:
                escalation_reason = "Answer may not be fully supported by sources"
            elif coverage < 0.5:
                escalation_reason = "Retrieved sources may not fully cover the query"
            else:
                escalation_reason = "Overall confidence below threshold"
        
        # Count verified claims (simplified)
        claims_verified = len([c for c in answer.citations if c.relevance == "direct"])
        claims_unverified = len(answer.citations) - claims_verified
        
        score = ConfidenceScore(
            overall_confidence=overall,
            grounding_score=grounding,
            coverage_score=coverage,
            consistency_score=consistency,
            requires_escalation=requires_escalation,
            escalation_reason=escalation_reason,
            claims_verified=claims_verified,
            claims_unverified=claims_unverified
        )
        
        self._log_complete(f"Confidence: {overall:.2f}, Escalation: {requires_escalation}")
        return score
    
    def _calculate_grounding_score(
        self,
        answer: PolicyAnswer,
        chunks: List[PolicyChunk]
    ) -> float:
        """
        Calculate how well the answer is grounded in sources.
        
        Heuristic: Based on number of citations and their relevance.
        """
        if not answer.citations:
            return 0.3  # No citations is suspicious
        
        # Score based on citation quality
        direct_citations = sum(1 for c in answer.citations if c.relevance == "direct")
        supporting_citations = sum(1 for c in answer.citations if c.relevance == "supporting")
        
        # More direct citations = higher grounding
        citation_score = min(1.0, (direct_citations * 0.3 + supporting_citations * 0.15))
        
        # Check if citations reference actual retrieved sources
        source_names = [chunk.source for chunk in chunks]
        matching_sources = sum(
            1 for c in answer.citations if c.source in source_names
        )
        source_match_score = matching_sources / max(len(answer.citations), 1)
        
        return (citation_score + source_match_score) / 2
    
    def _calculate_coverage_score(
        self,
        query: UserQuery,
        chunks: List[PolicyChunk]
    ) -> float:
        """
        Calculate how well sources cover the query.
        
        Heuristic: Based on relevance scores of retrieved chunks.
        """
        if not chunks:
            return 0.0
        
        # Average relevance of top chunks
        avg_relevance = sum(c.relevance_score for c in chunks) / len(chunks)
        
        # Number of sources (more = better coverage)
        unique_sources = len(set(c.source for c in chunks))
        source_diversity = min(1.0, unique_sources / 3)  # Cap at 3 sources
        
        return (avg_relevance * 0.7 + source_diversity * 0.3)
    
    def _calculate_consistency_score(self, answer: PolicyAnswer) -> float:
        """
        Calculate internal consistency of the answer.
        
        Heuristic: Based on answer structure and caveats.
        """
        score = 0.7  # Base score
        
        # Having caveats shows self-awareness (good)
        if answer.caveats:
            score += 0.1
        
        # Having reasoning shows transparency (good)
        if answer.reasoning and len(answer.reasoning) > 50:
            score += 0.1
        
        # Very short answers might be incomplete
        if len(answer.answer) < 100:
            score -= 0.1
        
        # Very long answers might be rambling
        if len(answer.answer) > 2000:
            score -= 0.05
        
        return min(1.0, max(0.0, score))


# Standalone function for LangGraph
async def assess_confidence(
    query: UserQuery,
    answer: Optional[PolicyAnswer],
    policy_chunks: List[PolicyChunk]
) -> ConfidenceScore:
    """Assess confidence - designed for LangGraph node."""
    agent = ConfidenceAgent()
    return await agent.run(query, answer, policy_chunks)
