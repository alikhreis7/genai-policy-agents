"""
Tests for the Synthesis Agent.

These tests focus on:
1. Answer structure and validation
2. Citation generation
3. Handling edge cases (no context, errors)
"""

import pytest
from src.models.schemas import (
    UserQuery, 
    PolicyChunk, 
    RetrievalResult, 
    PolicyAnswer,
    Citation
)
from src.agents.synthesis import SynthesisAgent


class TestPolicyAnswer:
    """Test PolicyAnswer model."""
    
    def test_answer_creation(self):
        """Test creating a policy answer."""
        answer = PolicyAnswer(
            answer="Based on the data security policy, PII should not be stored in Redis.",
            summary="PII not allowed in Redis",
            citations=[
                Citation(
                    claim="PII should not be stored in general-purpose caches",
                    source="data-security-policy.md",
                    section="Data Classification",
                    quote="PII MUST NOT be stored in general-purpose caches",
                    relevance="direct"
                )
            ],
            caveats=["Dedicated encrypted caches may be acceptable with approval"],
            related_topics=["data encryption", "cache security"],
            reasoning="The policy explicitly prohibits PII in general caches like Redis."
        )
        
        assert "PII" in answer.answer
        assert len(answer.citations) == 1
        assert answer.citations[0].relevance == "direct"
    
    def test_answer_without_citations(self):
        """Test answer with no citations (edge case)."""
        answer = PolicyAnswer(
            answer="Unable to find relevant policies.",
            summary="No relevant policies found",
            citations=[],
            caveats=["No matching policies in database"],
            related_topics=[],
            reasoning="Search returned no relevant results"
        )
        
        assert len(answer.citations) == 0


class TestCitation:
    """Test Citation model."""
    
    def test_citation_creation(self):
        """Test creating a citation."""
        citation = Citation(
            claim="API calls must use TLS 1.2 or higher",
            source="api-standards.md",
            section="Security Requirements",
            quote="All API communication MUST use TLS 1.2+",
            relevance="direct"
        )
        
        assert citation.relevance in ["direct", "supporting", "contextual"]
    
    def test_citation_without_quote(self):
        """Test citation without direct quote."""
        citation = Citation(
            claim="Databases should be encrypted",
            source="data-security-policy.md",
            relevance="supporting"
        )
        
        assert citation.quote is None
        assert citation.section is None


class TestSynthesisAgent:
    """Test the Synthesis Agent."""
    
    @pytest.fixture
    def agent(self):
        """Create a SynthesisAgent instance."""
        return SynthesisAgent()
    
    @pytest.fixture
    def sample_retrieval(self):
        """Create sample retrieval results."""
        return RetrievalResult(
            policy_chunks=[
                PolicyChunk(
                    content="PII must not be stored in general-purpose caches like Redis.",
                    source="data-security-policy.md",
                    section="Data Classification",
                    relevance_score=0.95,
                    chunk_id="chunk1"
                ),
                PolicyChunk(
                    content="All data stores containing PII must use encryption at rest.",
                    source="data-security-policy.md",
                    section="Encryption Requirements",
                    relevance_score=0.88,
                    chunk_id="chunk2"
                )
            ],
            total_sources=1
        )
    
    def test_context_building(self, agent, sample_retrieval):
        """Test that context is built correctly."""
        context = agent._build_context(sample_retrieval)
        
        assert "Source 1" in context
        assert "data-security-policy.md" in context
        assert "PII" in context
    
    @pytest.mark.asyncio
    async def test_empty_retrieval_handling(self, agent):
        """Test handling of empty retrieval results."""
        query = UserQuery(text="Some random query")
        empty_retrieval = RetrievalResult(policy_chunks=[], total_sources=0)
        
        result = await agent.run(query, empty_retrieval)
        
        assert isinstance(result, PolicyAnswer)
        assert "could not find" in result.answer.lower() or "no" in result.answer.lower()


class TestSynthesisQuality:
    """Tests for synthesis quality (would use LLM evals in production)."""
    
    def test_fallback_answer_structure(self):
        """Test that fallback answers have proper structure."""
        from src.agents.synthesis import SynthesisAgent
        
        agent = SynthesisAgent()
        
        query = UserQuery(text="Test query")
        retrieval = RetrievalResult(
            policy_chunks=[
                PolicyChunk(
                    content="Test content",
                    source="test.md",
                    section="Test",
                    relevance_score=0.5,
                    chunk_id="test1"
                )
            ],
            total_sources=1
        )
        
        fallback = agent._generate_fallback_answer(query, retrieval, "Test error")
        
        assert isinstance(fallback, PolicyAnswer)
        assert fallback.answer  # Non-empty
        assert fallback.summary  # Non-empty
        assert fallback.reasoning  # Non-empty
        assert len(fallback.caveats) > 0  # Should have caveats about error


class TestEndToEndSynthesis:
    """End-to-end synthesis tests."""
    
    @pytest.mark.asyncio
    async def test_full_pipeline_mock(self):
        """Test full synthesis pipeline with mock data."""
        from src.agents.policy_rag import PolicyRAGAgent
        from src.agents.synthesis import SynthesisAgent
        
        # Get retrieval results
        rag_agent = PolicyRAGAgent()
        query = UserQuery(text="Can we store PII in Redis?")
        retrieval = await rag_agent.run(query)
        
        # Run synthesis (will use mock without API key)
        synthesis_agent = SynthesisAgent()
        
        # The synthesis will fail without API key, but we can test the setup
        assert len(retrieval.policy_chunks) > 0
        
        # Context should be buildable
        context = synthesis_agent._build_context(retrieval)
        assert len(context) > 0
        assert "PII" in context.upper() or "pii" in context.lower()
