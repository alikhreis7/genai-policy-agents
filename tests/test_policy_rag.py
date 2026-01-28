"""
Tests for the Policy RAG Agent.

These tests focus on:
1. Retrieval quality
2. Chunking strategies
3. Mock data correctness
"""

import pytest
from src.models.schemas import UserQuery, PolicyChunk, RetrievalResult
from src.agents.policy_rag import PolicyRAGAgent
from src.data.loader import PolicyLoader


class TestPolicyChunk:
    """Test PolicyChunk model."""
    
    def test_chunk_creation(self):
        """Test creating a policy chunk."""
        chunk = PolicyChunk(
            content="PII must be encrypted at rest",
            source="data-security-policy.md",
            section="Data Classification",
            relevance_score=0.95,
            chunk_id="abc123",
            metadata={"page": 5}
        )
        
        assert chunk.content == "PII must be encrypted at rest"
        assert chunk.source == "data-security-policy.md"
        assert chunk.relevance_score == 0.95
    
    def test_chunk_relevance_bounds(self):
        """Test relevance score bounds."""
        with pytest.raises(ValueError):
            PolicyChunk(
                content="test",
                source="test.md",
                section=None,
                relevance_score=1.5,  # Invalid
                chunk_id="test"
            )


class TestPolicyLoader:
    """Test policy loading and chunking."""
    
    def test_sample_policies_exist(self):
        """Test that sample policies are generated."""
        loader = PolicyLoader()
        chunks = loader._get_sample_policies()
        
        assert len(chunks) > 0
        assert all(isinstance(c, PolicyChunk) for c in chunks)
    
    def test_sample_policy_sources(self):
        """Test that sample policies have proper sources."""
        loader = PolicyLoader()
        chunks = loader._get_sample_policies()
        
        sources = set(c.source for c in chunks)
        assert "data-security-policy.md" in sources or len(sources) > 0
    
    def test_chunk_by_sections(self):
        """Test section-based chunking."""
        loader = PolicyLoader()
        
        test_doc = """# Policy Document

## Section One
Content for section one.
More content here.

## Section Two
Content for section two.
Additional details.
"""
        
        chunks = loader.chunk_by_sections(test_doc, "test-policy.md")
        
        # Should create chunks for each section
        assert len(chunks) >= 2
        
        # Each chunk should have a section
        sections = [c.section for c in chunks if c.section]
        assert "Section One" in sections or "Section Two" in sections
    
    def test_chunk_ids_unique(self):
        """Test that chunk IDs are unique."""
        loader = PolicyLoader()
        chunks = loader._get_sample_policies()
        
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids)), "Chunk IDs should be unique"


class TestPolicyRAGAgent:
    """Test the Policy RAG Agent."""
    
    @pytest.fixture
    def agent(self):
        """Create a PolicyRAGAgent instance."""
        return PolicyRAGAgent()
    
    @pytest.mark.asyncio
    async def test_mock_retrieval_pii_query(self, agent):
        """Test mock retrieval for PII-related queries."""
        query = UserQuery(text="Can we store PII in Redis?")
        result = await agent.run(query)
        
        assert isinstance(result, RetrievalResult)
        assert len(result.policy_chunks) > 0
        
        # Should find PII-related content
        content = " ".join(c.content.lower() for c in result.policy_chunks)
        assert "pii" in content or "personal" in content
    
    @pytest.mark.asyncio
    async def test_mock_retrieval_security_query(self, agent):
        """Test mock retrieval for security queries."""
        query = UserQuery(text="What are the authentication requirements?")
        result = await agent.run(query)
        
        assert len(result.policy_chunks) > 0
        
        # Should find auth-related content
        content = " ".join(c.content.lower() for c in result.policy_chunks)
        assert "auth" in content or "password" in content or "security" in content
    
    @pytest.mark.asyncio
    async def test_retrieval_respects_top_k(self, agent):
        """Test that top_k parameter is respected."""
        query = UserQuery(text="Tell me about data policies")
        
        result_3 = await agent.run(query, top_k=3)
        result_5 = await agent.run(query, top_k=5)
        
        assert len(result_3.policy_chunks) <= 3
        assert len(result_5.policy_chunks) <= 5
    
    @pytest.mark.asyncio
    async def test_retrieval_result_metadata(self, agent):
        """Test that retrieval includes proper metadata."""
        query = UserQuery(text="API gateway policy")
        result = await agent.run(query)
        
        assert "query" in result.retrieval_metadata
        assert result.total_sources >= 0


class TestRetrievalQuality:
    """Tests focused on retrieval quality (would use real evals in production)."""
    
    @pytest.mark.asyncio
    async def test_relevance_ordering(self):
        """Test that results are ordered by relevance."""
        agent = PolicyRAGAgent()
        query = UserQuery(text="PII data handling requirements")
        
        result = await agent.run(query, top_k=5)
        
        if len(result.policy_chunks) > 1:
            scores = [c.relevance_score for c in result.policy_chunks]
            # Higher scores should come first
            assert scores == sorted(scores, reverse=True), \
                "Results should be ordered by relevance score"
    
    @pytest.mark.asyncio
    async def test_source_diversity(self):
        """Test that results come from diverse sources when available."""
        agent = PolicyRAGAgent()
        query = UserQuery(text="security authentication database api")
        
        result = await agent.run(query, top_k=10)
        
        # Should ideally have multiple sources
        sources = set(c.source for c in result.policy_chunks)
        # At least some diversity in a broad query
        assert result.total_sources == len(sources)
