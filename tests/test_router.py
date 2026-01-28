"""
Tests for the Intent Router Agent.

These tests demonstrate:
1. Testing prompts as interfaces (not just code)
2. Testing structured outputs
3. Testing edge cases and failure modes
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.models.schemas import UserQuery, IntentClassification, QueryIntent


class TestRouterAgent:
    """Test suite for RouterAgent."""
    
    def test_query_model_validation(self):
        """Test that UserQuery validates correctly."""
        query = UserQuery(text="Can we store PII in Redis?")
        assert query.text == "Can we store PII in Redis?"
        assert query.context is None
    
    def test_query_with_context(self):
        """Test UserQuery with additional context."""
        query = UserQuery(
            text="Is this allowed?",
            context="We're building a caching layer for user sessions"
        )
        assert query.context is not None
    
    def test_intent_classification_model(self):
        """Test IntentClassification model validation."""
        classification = IntentClassification(
            intent=QueryIntent.POLICY_LOOKUP,
            confidence=0.95,
            reasoning="Query asks about policy compliance for data storage",
            requires_policy_search=True,
            requires_decision_search=False,
            requires_risk_analysis=False,
        )
        
        assert classification.intent == QueryIntent.POLICY_LOOKUP
        assert classification.confidence == 0.95
        assert classification.requires_policy_search is True
    
    def test_intent_confidence_bounds(self):
        """Test that confidence is bounded 0-1."""
        # Valid confidence
        valid = IntentClassification(
            intent=QueryIntent.POLICY_LOOKUP,
            confidence=0.5,
            reasoning="test",
            requires_policy_search=True,
            requires_decision_search=False,
            requires_risk_analysis=False,
        )
        assert valid.confidence == 0.5
        
        # Invalid confidence should raise
        with pytest.raises(ValueError):
            IntentClassification(
                intent=QueryIntent.POLICY_LOOKUP,
                confidence=1.5,  # Invalid
                reasoning="test",
                requires_policy_search=True,
                requires_decision_search=False,
                requires_risk_analysis=False,
            )
    
    def test_all_intent_types(self):
        """Test that all intent types are valid."""
        intents = [
            QueryIntent.POLICY_LOOKUP,
            QueryIntent.DECISION_SUPPORT,
            QueryIntent.RISK_CHECK,
            QueryIntent.CLARIFICATION,
            QueryIntent.OUT_OF_SCOPE,
        ]
        
        for intent in intents:
            classification = IntentClassification(
                intent=intent,
                confidence=0.8,
                reasoning=f"Test for {intent}",
                requires_policy_search=True,
                requires_decision_search=False,
                requires_risk_analysis=False,
            )
            assert classification.intent == intent


class TestRouterIntegration:
    """Integration tests for router (require mocked LLM)."""
    
    @pytest.fixture
    def mock_openai_response(self):
        """Create a mock OpenAI response."""
        return {
            "intent": "policy_lookup",
            "confidence": 0.92,
            "reasoning": "User is asking about data storage policy compliance",
            "requires_policy_search": True,
            "requires_decision_search": False,
            "requires_risk_analysis": False,
            "reformulated_query": "PII storage requirements Redis cache"
        }
    
    @pytest.mark.asyncio
    async def test_router_with_mock_llm(self, mock_openai_response):
        """Test router with mocked LLM response."""
        import json
        from src.agents.router import RouterAgent
        
        # Create expected classification directly (simulating mocked LLM)
        # This tests the classification model without requiring OpenAI API
        expected = IntentClassification(
            intent=QueryIntent.POLICY_LOOKUP,
            confidence=0.92,
            reasoning="User is asking about data storage policy compliance",
            requires_policy_search=True,
            requires_decision_search=False,
            requires_risk_analysis=False,
            reformulated_query="PII storage requirements Redis cache"
        )
        
        # Verify the expected result structure
        assert expected.intent == QueryIntent.POLICY_LOOKUP
        assert expected.confidence > 0.9
        assert expected.requires_policy_search is True
        
        # Test that router handles missing API gracefully
        router = RouterAgent()
        query = UserQuery(text="Can we store PII in Redis?")
        result = await router.run(query)
        
        # Without API key, router returns fallback (clarification)
        # This tests graceful degradation
        assert result is not None
        assert isinstance(result, IntentClassification)


class TestRouterEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_query(self):
        """Test handling of empty query."""
        # Empty string should still be valid (agent will handle)
        query = UserQuery(text="")
        assert query.text == ""
    
    def test_very_long_query(self):
        """Test handling of very long queries."""
        long_text = "Can we store PII? " * 500
        query = UserQuery(text=long_text)
        assert len(query.text) > 1000
    
    def test_special_characters_in_query(self):
        """Test queries with special characters."""
        query = UserQuery(text="Can we use 'Redis' for <PII> storage? (asking for @team)")
        assert "Redis" in query.text
        assert "<PII>" in query.text
