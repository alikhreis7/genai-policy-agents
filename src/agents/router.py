"""
Intent Router Agent - The orchestration entry point.

This agent is responsible for:
1. Classifying the intent of user queries
2. Deciding which downstream agents to invoke
3. Reformulating queries for optimal retrieval

The router demonstrates the "agent as coordinator" pattern - it doesn't
answer questions directly, but routes them to specialized agents.
"""

import json
from typing import Optional

from .base import LLMAgent
from ..models.schemas import (
    UserQuery,
    IntentClassification,
    QueryIntent,
)


# System prompt for intent classification
ROUTER_SYSTEM_PROMPT = """You are an intent classification agent for an enterprise policy and decision intelligence system.

Your job is to analyze user queries and determine:
1. What type of question is being asked
2. Which specialized agents should be invoked
3. How to reformulate the query for optimal retrieval

## Intent Types

1. **policy_lookup**: User wants to know if something is allowed/prohibited by policy
   - Examples: "Can we store PII in Redis?", "What's our password policy?"
   - Requires: Policy search

2. **decision_support**: User wants guidance on an architectural/design decision
   - Examples: "Should we use microservices?", "Is it okay to bypass the API gateway?"
   - Requires: Decision history search, possibly policy search

3. **risk_check**: User wants to verify compliance or identify risks
   - Examples: "Does this design violate any policies?", "What are the risks of X?"
   - Requires: Policy search AND risk analysis

4. **clarification**: Query is too vague or ambiguous to answer
   - Examples: "What about security?", "Is it allowed?"
   - Action: Ask for clarification

5. **out_of_scope**: Query is outside the system's domain
   - Examples: "What's the weather?", "Write me some code"
   - Action: Politely decline

## Response Format

You MUST respond with a valid JSON object containing these fields:
{
    "intent": "policy_lookup|decision_support|risk_check|clarification|out_of_scope",
    "confidence": 0.0 to 1.0,
    "reasoning": "Brief explanation of classification",
    "requires_policy_search": true/false,
    "requires_decision_search": true/false,
    "requires_risk_analysis": true/false,
    "reformulated_query": "Optimized query for retrieval (or null)"
}

Be conservative with confidence - if unsure, score lower and flag for clarification.
"""


class RouterAgent(LLMAgent[IntentClassification]):
    """
    Intent Router Agent that classifies queries and routes to appropriate agents.
    
    This is the entry point for all user queries. It determines:
    - What the user is asking about
    - Which specialized agents should handle the query
    - How to optimize the query for downstream processing
    
    Key design decisions:
    - Uses structured output (JSON) for deterministic parsing
    - Conservative confidence scoring (better to ask than assume)
    - Query reformulation for better retrieval
    """
    
    def __init__(self):
        super().__init__("router", use_openai=True)
    
    @property
    def description(self) -> str:
        return "Classifies user intent and routes to appropriate specialist agents"
    
    async def run(self, query: UserQuery) -> IntentClassification:
        """
        Classify the intent of a user query.
        
        Args:
            query: The user's query with optional context
            
        Returns:
            IntentClassification with routing decisions
        """
        self._log_start(f"Query: {query.text[:50]}...")
        
        # Check if API key is configured
        if not self.settings.openai_api_key:
            self.logger.info("No API key configured, using demo mode classification")
            return self._demo_mode_classify(query)
        
        # Build the prompt
        user_message = self._build_user_message(query)
        
        messages = [
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
        
        try:
            # Call LLM for classification
            result = await self._call_openai_structured_async(
                messages=messages,
                response_model=IntentClassification,
                temperature=0.0  # Deterministic for classification
            )
            
            self._log_complete(f"Intent: {result.intent}, Confidence: {result.confidence}")
            return result
            
        except Exception as e:
            self._log_error(e)
            # Fallback to demo mode on error
            return self._demo_mode_classify(query)
    
    def _demo_mode_classify(self, query: UserQuery) -> IntentClassification:
        """
        Demo mode classification using keyword matching.
        
        This allows the system to work without API keys for demos.
        """
        query_lower = query.text.lower()
        
        # Risk check patterns
        if any(term in query_lower for term in ["risk", "violate", "compliance", "audit"]):
            return IntentClassification(
                intent=QueryIntent.RISK_CHECK,
                confidence=0.85,
                reasoning="Query contains risk/compliance keywords - routing to risk assessment",
                requires_policy_search=True,
                requires_decision_search=False,
                requires_risk_analysis=True,
            )
        
        # Decision support patterns
        if any(term in query_lower for term in ["should we", "is it okay", "acceptable", "recommend", "best practice"]):
            return IntentClassification(
                intent=QueryIntent.DECISION_SUPPORT,
                confidence=0.82,
                reasoning="Query asks for guidance on a decision - routing to decision support",
                requires_policy_search=True,
                requires_decision_search=True,
                requires_risk_analysis=False,
            )
        
        # Policy lookup patterns (default for most questions)
        if any(term in query_lower for term in ["can we", "allowed", "policy", "must", "require", "pii", "security", "auth", "data", "store", "cache"]):
            return IntentClassification(
                intent=QueryIntent.POLICY_LOOKUP,
                confidence=0.90,
                reasoning="Query asks about policy compliance - routing to policy lookup",
                requires_policy_search=True,
                requires_decision_search=False,
                requires_risk_analysis=False,
                reformulated_query=query.text,
            )
        
        # Default to policy lookup for anything else
        return IntentClassification(
            intent=QueryIntent.POLICY_LOOKUP,
            confidence=0.70,
            reasoning="General query - defaulting to policy lookup",
            requires_policy_search=True,
            requires_decision_search=False,
            requires_risk_analysis=False,
        )
    
    def _build_user_message(self, query: UserQuery) -> str:
        """Build the user message for the LLM."""
        message = f"User Query: {query.text}"
        
        if query.context:
            message += f"\n\nAdditional Context: {query.context}"
        
        return message
    
    def run_sync(self, query: UserQuery) -> IntentClassification:
        """Synchronous version for simpler usage."""
        import asyncio
        return asyncio.run(self.run(query))


# Standalone function for use in LangGraph
async def classify_intent(query: UserQuery) -> IntentClassification:
    """
    Classify the intent of a user query.
    
    This function is designed to be used as a LangGraph node.
    """
    agent = RouterAgent()
    return await agent.run(query)
