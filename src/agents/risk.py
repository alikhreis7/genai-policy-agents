"""
Risk & Ambiguity Agent - Detects conflicts and assesses risk.

STUB IMPLEMENTATION

This agent analyzes:
- Policy conflicts (when two policies seem to contradict)
- Missing context (when more information is needed)
- Compliance risks
- Edge cases that need human review

The interface demonstrates the pattern; full implementation
would use LLM reasoning over retrieved policies.
"""

from typing import List

from .base import LLMAgent
from ..models.schemas import (
    UserQuery,
    PolicyChunk,
    RiskAssessment,
)


class RiskAgent(LLMAgent[RiskAssessment]):
    """
    Risk Assessment Agent - Analyzes policies for conflicts and risks.
    
    STUB: Returns reasonable assessments based on heuristics.
    
    In production, this would:
    1. Compare retrieved policy chunks for conflicts
    2. Identify ambiguous requirements
    3. Flag missing context
    4. Assess compliance risk level
    
    Why this agent matters:
    
    This agent embodies the "LLMs are unreliable" principle. Even when
    the Synthesis Agent provides an answer, this agent provides a
    second opinion focused on what could go wrong.
    """
    
    def __init__(self):
        super().__init__("risk", use_openai=True)
    
    @property
    def description(self) -> str:
        return "Analyzes policies for conflicts, ambiguities, and risks"
    
    async def run(
        self,
        query: UserQuery,
        policy_chunks: List[PolicyChunk]
    ) -> RiskAssessment:
        """
        Assess risks in the query and retrieved content.
        
        STUB: Uses heuristics to generate realistic assessments.
        """
        self._log_start(f"Analyzing {len(policy_chunks)} chunks for risks")
        
        # Analyze for potential risks
        risks = self._identify_risks(query.text, policy_chunks)
        conflicts = self._detect_conflicts(policy_chunks)
        missing = self._identify_missing_context(query.text, policy_chunks)
        
        # Determine overall risk level
        risk_level = self._calculate_risk_level(risks, conflicts)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(risks, conflicts, missing)
        
        assessment = RiskAssessment(
            risk_level=risk_level,
            identified_risks=risks,
            policy_conflicts=conflicts,
            missing_context=missing,
            recommendations=recommendations
        )
        
        self._log_complete(f"Risk level: {risk_level}")
        return assessment
    
    def _identify_risks(
        self, 
        query: str, 
        chunks: List[PolicyChunk]
    ) -> List[str]:
        """Identify potential risks based on query and policies."""
        risks = []
        query_lower = query.lower()
        
        # PII-related risks
        if any(term in query_lower for term in ["pii", "personal", "user data"]):
            if any("cache" in query_lower for _ in [1]):
                risks.append("Storing PII in caches may violate data retention policies")
            if any("log" in query_lower for _ in [1]):
                risks.append("PII in logs creates compliance exposure")
        
        # Security-related risks
        if any(term in query_lower for term in ["bypass", "skip", "workaround"]):
            risks.append("Bypassing security controls requires explicit approval")
        
        # Performance vs security tradeoffs
        if "performance" in query_lower and any(
            term in query_lower for term in ["security", "encrypt", "auth"]
        ):
            risks.append("Performance optimizations may conflict with security requirements")
        
        # Low coverage risk
        if len(chunks) < 2:
            risks.append("Limited policy coverage for this topic - manual review recommended")
        
        return risks
    
    def _detect_conflicts(self, chunks: List[PolicyChunk]) -> List[str]:
        """Detect potential conflicts between policy chunks."""
        conflicts = []
        
        # Simple heuristic: look for contradictory language
        sources = [c.source for c in chunks]
        
        # If policies come from different sources, note potential for conflict
        unique_sources = set(sources)
        if len(unique_sources) > 2:
            conflicts.append(
                f"Multiple policy sources involved ({len(unique_sources)}) - "
                "verify consistency across documents"
            )
        
        return conflicts
    
    def _identify_missing_context(
        self, 
        query: str, 
        chunks: List[PolicyChunk]
    ) -> List[str]:
        """Identify what additional context would help."""
        missing = []
        
        # Check if query mentions specific technologies not covered
        query_lower = query.lower()
        
        # Common technologies that might need specific policies
        tech_mentions = []
        for tech in ["kubernetes", "docker", "terraform", "aws", "gcp", "azure"]:
            if tech in query_lower:
                tech_mentions.append(tech)
        
        if tech_mentions:
            missing.append(
                f"Query mentions specific technologies ({', '.join(tech_mentions)}) - "
                "technology-specific policies may apply"
            )
        
        # Check for temporal/conditional context
        if any(term in query_lower for term in ["sometimes", "occasionally", "depends"]):
            missing.append("Query context is conditional - specific conditions would help")
        
        return missing
    
    def _calculate_risk_level(
        self, 
        risks: List[str], 
        conflicts: List[str]
    ) -> str:
        """Calculate overall risk level."""
        total_issues = len(risks) + len(conflicts)
        
        if total_issues == 0:
            return "low"
        elif total_issues <= 2:
            return "medium"
        elif total_issues <= 4:
            return "high"
        else:
            return "critical"
    
    def _generate_recommendations(
        self,
        risks: List[str],
        conflicts: List[str],
        missing: List[str]
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        if conflicts:
            recommendations.append("Review with policy owner to resolve conflicts")
        
        if missing:
            recommendations.append("Gather additional context before final decision")
        
        if risks:
            recommendations.append("Document risk acceptance if proceeding")
            recommendations.append("Consider escalation to Architecture Review Board")
        
        if not recommendations:
            recommendations.append("Proceed with standard approval process")
        
        return recommendations


# Standalone function for LangGraph
async def assess_risk(
    query: UserQuery,
    policy_chunks: List[PolicyChunk]
) -> RiskAssessment:
    """Assess risk - designed for LangGraph node."""
    agent = RiskAgent()
    return await agent.run(query, policy_chunks)
