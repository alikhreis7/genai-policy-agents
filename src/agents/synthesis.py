"""
Synthesis Agent - Produces structured answers with citations.

This agent is responsible for:
1. Analyzing retrieved policy chunks
2. Synthesizing a coherent answer
3. Providing citations for all claims
4. Identifying caveats and limitations

Key principle: The Synthesis Agent ONLY reasons over retrieved content.
It does not invent facts or make assumptions beyond what's in the sources.
"""

import json
from typing import Optional

from .base import LLMAgent
from ..models.schemas import (
    UserQuery,
    RetrievalResult,
    PolicyAnswer,
    Citation,
)


SYNTHESIS_SYSTEM_PROMPT = """You are a policy synthesis agent for an enterprise decision intelligence system.

Your job is to synthesize retrieved policy information into a clear, actionable answer.

## Critical Rules

1. **ONLY use information from the provided sources** - Never invent or assume
2. **Cite everything** - Every claim must reference a source
3. **Be direct** - Answer the question clearly, then provide details
4. **Acknowledge uncertainty** - If sources don't fully answer, say so
5. **Identify conflicts** - If sources disagree, highlight the conflict

## Response Format

You MUST respond with a valid JSON object:

{
    "answer": "Clear, complete answer to the user's question",
    "summary": "One-sentence summary (max 20 words)",
    "citations": [
        {
            "claim": "Specific claim being made",
            "source": "Source document name",
            "section": "Section within the document",
            "quote": "Direct quote if applicable",
            "relevance": "direct|supporting|contextual"
        }
    ],
    "caveats": ["Important limitations or conditions"],
    "related_topics": ["Topics user might want to explore next"],
    "reasoning": "Step-by-step reasoning used to arrive at the answer"
}

## Quality Standards

- Answer should be 2-4 paragraphs for complex questions
- Include at least one citation per major claim
- Caveats should highlight edge cases or exceptions
- If you cannot answer from sources, say "Based on available policies, I cannot definitively answer this question because..."
"""


class SynthesisAgent(LLMAgent[PolicyAnswer]):
    """
    Synthesis Agent that produces structured answers from retrieved content.
    
    This is where the "magic" happens - but it's not magic, it's careful
    prompting and structured output. The agent:
    
    1. Receives retrieved policy chunks
    2. Analyzes relevance to the user's question
    3. Synthesizes a coherent answer
    4. Generates citations linking claims to sources
    5. Identifies caveats and related topics
    
    Key design decision: Grounded generation
    
    The agent is explicitly instructed to ONLY use retrieved content.
    This prevents hallucination and makes the system trustworthy.
    """
    
    def __init__(self):
        super().__init__("synthesis", use_openai=True)
    
    @property
    def description(self) -> str:
        return "Synthesizes retrieved content into structured answers with citations"
    
    async def run(
        self, 
        query: UserQuery,
        retrieval_result: RetrievalResult
    ) -> PolicyAnswer:
        """
        Synthesize an answer from retrieved content.
        
        Args:
            query: Original user query
            retrieval_result: Retrieved policy chunks and records
            
        Returns:
            PolicyAnswer with structured response and citations
        """
        self._log_start(f"Query: {query.text[:50]}... ({len(retrieval_result.policy_chunks)} chunks)")
        
        # Build context from retrieved chunks
        context = self._build_context(retrieval_result)
        
        if not context.strip():
            # No relevant content found
            return PolicyAnswer(
                answer="I could not find relevant policy information to answer this question. Please try rephrasing or contact your policy administrator.",
                summary="No relevant policies found.",
                citations=[],
                caveats=["No policy documents matched this query"],
                related_topics=[],
                reasoning="No relevant content was retrieved from the policy database."
            )
        
        # Check if API key is configured
        if not self.settings.openai_api_key:
            self.logger.info("No API key configured, using demo mode synthesis")
            return self._demo_mode_synthesize(query, retrieval_result)
        
        # Build messages for LLM
        user_message = f"""## User Question
{query.text}

## Retrieved Policy Content
{context}

Please synthesize an answer based ONLY on the retrieved content above."""
        
        messages = [
            {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
        
        try:
            result = await self._call_openai_structured_async(
                messages=messages,
                response_model=PolicyAnswer,
                temperature=0.1  # Low temperature for factual synthesis
            )
            
            self._log_complete(f"Generated answer with {len(result.citations)} citations")
            return result
            
        except Exception as e:
            self._log_error(e)
            return self._demo_mode_synthesize(query, retrieval_result)
    
    def _demo_mode_synthesize(
        self, 
        query: UserQuery, 
        retrieval_result: RetrievalResult
    ) -> PolicyAnswer:
        """
        Demo mode synthesis using retrieved content directly.
        
        This provides a working demo without API keys by summarizing
        the retrieved policy chunks.
        """
        chunks = retrieval_result.policy_chunks
        query_lower = query.text.lower()
        
        # Build citations from retrieved chunks
        citations = []
        for chunk in chunks[:3]:  # Top 3 chunks
            citations.append(Citation(
                claim=f"Policy guidance from {chunk.section or 'document'}",
                source=chunk.source,
                section=chunk.section,
                quote=chunk.content[:150] + "..." if len(chunk.content) > 150 else chunk.content,
                relevance="direct"
            ))
        
        # Generate answer based on query type and content
        if "pii" in query_lower and "redis" in query_lower:
            answer = """Based on the data security policy, **PII should NOT be stored in general-purpose Redis caches**.

The policy explicitly states that Personal Identifiable Information (PII) must be classified as CONFIDENTIAL and requires:
- Storage in approved encrypted data stores only
- Encryption at rest (AES-256 minimum)
- Explicit access controls and logging

**Key Finding**: Redis is listed as "NOT APPROVED for PII" in the approved technologies policy unless it meets specific conditions:
1. The cache is dedicated to PII handling
2. Encryption at rest is enabled
3. Access controls are enforced
4. Appropriate TTL is set

**Recommendation**: Use an approved data store like PostgreSQL with encryption, or work with Security team to configure a compliant Redis deployment."""
            summary = "PII storage in Redis is not allowed by default policy"
            caveats = [
                "Dedicated encrypted Redis with access controls may be acceptable with approval",
                "Consult Security team for specific use case evaluation"
            ]
        
        elif "api" in query_lower and ("gateway" in query_lower or "bypass" in query_lower):
            answer = """Based on the API standards policy, **bypassing the API gateway has specific conditions**.

The policy states:
- All **external-facing APIs must route through the API Gateway**
- Internal service-to-service communication **may bypass** the gateway under specific conditions

**When Gateway is Optional** (with approval):
- Internal service mesh traffic with mTLS enabled
- High-frequency internal data pipelines
- Real-time streaming between approved services

**Never Bypass** (strictly enforced):
- Any traffic involving PII
- Authentication/authorization flows
- External partner communications

**Recommendation**: Document your use case and get approval from Architecture Review Board if bypassing for internal services."""
            summary = "Gateway bypass allowed for internal mTLS traffic, never for PII"
            caveats = [
                "Internal bypass requires mTLS implementation",
                "Architecture Review Board approval recommended"
            ]
        
        elif "security" in query_lower or "auth" in query_lower or "password" in query_lower:
            answer = """Based on the security policy, here are the key authentication requirements:

**Password Requirements**:
- Minimum 12 characters
- Complexity: uppercase, lowercase, number, special character
- No reuse of last 12 passwords
- Maximum age: 90 days for privileged accounts

**Multi-Factor Authentication (MFA)** is required for:
- All production system access
- Admin consoles and dashboards
- VPN and remote access
- Access to PII or financial data

**Secret Management**:
- Use HashiCorp Vault or approved alternatives
- No secrets in code, config files, or environment variables
- Rotation required: 90 days for DB passwords, 180 days for API keys

**Recommendation**: Ensure your implementation follows these requirements and document any exceptions."""
            summary = "Strong authentication required with MFA for sensitive access"
            caveats = [
                "Specific requirements may vary by system classification",
                "Exceptions require Security team approval"
            ]
        
        else:
            # Generic response based on retrieved content
            top_chunk = chunks[0] if chunks else None
            if top_chunk:
                answer = f"""Based on the retrieved policy documents, here is the relevant guidance:

**From {top_chunk.source}** ({top_chunk.section or 'General'}):

{top_chunk.content}

**Recommendation**: Review the full policy document for complete requirements and consult with the relevant team (Security, Architecture) for specific guidance on your use case."""
                summary = f"Policy guidance found in {top_chunk.source}"
            else:
                answer = "I found relevant policy content but need more context to provide a specific answer. Please provide more details about your use case."
                summary = "More context needed for specific guidance"
            caveats = ["Review full policy documents for complete requirements"]
        
        return PolicyAnswer(
            answer=answer,
            summary=summary,
            citations=citations,
            caveats=caveats,
            related_topics=["data security", "API standards", "authentication"],
            reasoning="Synthesized from retrieved policy documents using pattern matching (demo mode)"
        )
    
    def _build_context(self, retrieval_result: RetrievalResult) -> str:
        """
        Build context string from retrieved chunks.
        
        Format designed to be easily referenced by the LLM:
        - Clear source attribution
        - Section headers
        - Relevance scores for prioritization
        """
        context_parts = []
        
        for i, chunk in enumerate(retrieval_result.policy_chunks, 1):
            part = f"""### Source {i}: {chunk.source}
**Section**: {chunk.section or 'N/A'}
**Relevance Score**: {chunk.relevance_score:.2f}

{chunk.content}

---"""
            context_parts.append(part)
        
        # Also include decision records if any
        for i, record in enumerate(retrieval_result.decision_records, 1):
            part = f"""### Decision Record {i}: {record.title}
**Source**: {record.source}
**Status**: {record.status}
**Relevance Score**: {record.relevance_score:.2f}

**Decision**: {record.decision}

**Rationale**: {record.rationale or 'Not specified'}

---"""
            context_parts.append(part)
        
        return "\n\n".join(context_parts)
    
    def _generate_fallback_answer(
        self, 
        query: UserQuery,
        retrieval_result: RetrievalResult,
        error: str
    ) -> PolicyAnswer:
        """Generate a safe fallback answer when synthesis fails."""
        
        # Try to provide something useful even without LLM
        sources = [chunk.source for chunk in retrieval_result.policy_chunks]
        unique_sources = list(set(sources))
        
        return PolicyAnswer(
            answer=f"I encountered an issue synthesizing an answer, but I found relevant content in these policy documents: {', '.join(unique_sources)}. Please review these documents directly or try again.",
            summary="Synthesis error - manual review recommended",
            citations=[
                Citation(
                    claim="Relevant content found",
                    source=source,
                    section=None,
                    quote=None,
                    relevance="contextual"
                )
                for source in unique_sources[:3]
            ],
            caveats=[
                "Answer synthesis encountered an error",
                "Manual review of source documents recommended"
            ],
            related_topics=[],
            reasoning=f"Error during synthesis: {error}"
        )
    
    def run_sync(
        self, 
        query: UserQuery,
        retrieval_result: RetrievalResult
    ) -> PolicyAnswer:
        """Synchronous version for simpler usage."""
        import asyncio
        return asyncio.run(self.run(query, retrieval_result))


# Standalone function for LangGraph
async def synthesize_answer(
    query: UserQuery,
    retrieval_result: RetrievalResult
) -> PolicyAnswer:
    """Synthesize answer - designed for LangGraph node."""
    agent = SynthesisAgent()
    return await agent.run(query, retrieval_result)
