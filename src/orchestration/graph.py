"""
LangGraph Orchestration - Deterministic control flow for agents.

This is the core of the multi-agent system. The graph defines:
- Which agents are invoked
- In what order
- Under what conditions
- How state flows between them

Key insight: The LLM components are non-deterministic, but the
orchestration is deterministic. This gives us predictable behavior
while leveraging LLM capabilities.
"""

import time
from typing import Annotated, Literal, TypedDict
from dataclasses import dataclass, field

from ..models.schemas import (
    UserQuery,
    IntentClassification,
    QueryIntent,
    RetrievalResult,
    PolicyAnswer,
    ConfidenceScore,
    RiskAssessment,
    EngineResponse,
    PolicyChunk,
)


# =============================================================================
# Graph State Definition
# =============================================================================

class GraphState(TypedDict):
    """
    State that flows through the LangGraph workflow.
    
    This is the "memory" of the orchestration - each node
    reads from and writes to this state.
    """
    # Input
    query: UserQuery
    
    # Router output
    intent: IntentClassification | None
    
    # Retrieval results
    policy_chunks: list[PolicyChunk]
    
    # Agent outputs
    answer: PolicyAnswer | None
    confidence: ConfidenceScore | None
    risk: RiskAssessment | None
    
    # Metadata
    agents_invoked: list[str]
    start_time: float
    errors: list[str]


def create_initial_state(query: UserQuery) -> GraphState:
    """Create the initial state for a new query."""
    return GraphState(
        query=query,
        intent=None,
        policy_chunks=[],
        answer=None,
        confidence=None,
        risk=None,
        agents_invoked=[],
        start_time=time.time(),
        errors=[]
    )


# =============================================================================
# Node Functions (Agent Invocations)
# =============================================================================

async def router_node(state: GraphState) -> GraphState:
    """
    Router node - classifies intent and determines routing.
    
    This is the entry point for all queries. It decides
    which downstream agents to invoke.
    """
    from ..agents.router import RouterAgent
    
    agent = RouterAgent()
    
    try:
        intent = await agent.run(state["query"])
        state["intent"] = intent
        state["agents_invoked"].append("router")
    except Exception as e:
        state["errors"].append(f"Router error: {str(e)}")
        # Fallback: assume policy lookup
        state["intent"] = IntentClassification(
            intent=QueryIntent.POLICY_LOOKUP,
            confidence=0.3,
            reasoning="Fallback due to router error",
            requires_policy_search=True,
            requires_decision_search=False,
            requires_risk_analysis=False,
        )
    
    return state


async def policy_rag_node(state: GraphState) -> GraphState:
    """
    Policy RAG node - retrieves relevant policy chunks.
    """
    from ..agents.policy_rag import PolicyRAGAgent
    
    agent = PolicyRAGAgent()
    
    try:
        # Use reformulated query if available
        query = state["query"]
        if state["intent"] and state["intent"].reformulated_query:
            query = UserQuery(
                text=state["intent"].reformulated_query,
                context=state["query"].context
            )
        
        result = await agent.run(query)
        state["policy_chunks"] = result.policy_chunks
        state["agents_invoked"].append("policy_rag")
    except Exception as e:
        state["errors"].append(f"Policy RAG error: {str(e)}")
    
    return state


async def synthesis_node(state: GraphState) -> GraphState:
    """
    Synthesis node - generates answer from retrieved content.
    """
    from ..agents.synthesis import SynthesisAgent
    
    agent = SynthesisAgent()
    
    try:
        retrieval_result = RetrievalResult(
            policy_chunks=state["policy_chunks"],
            total_sources=len(set(c.source for c in state["policy_chunks"]))
        )
        
        answer = await agent.run(state["query"], retrieval_result)
        state["answer"] = answer
        state["agents_invoked"].append("synthesis")
    except Exception as e:
        state["errors"].append(f"Synthesis error: {str(e)}")
    
    return state


async def confidence_node(state: GraphState) -> GraphState:
    """
    Confidence node - assesses answer quality and grounding.
    
    Currently a stub - returns reasonable defaults.
    Full implementation would verify claims against sources.
    """
    from ..agents.confidence import ConfidenceAgent
    
    agent = ConfidenceAgent()
    
    try:
        confidence = await agent.run(state["query"], state["answer"], state["policy_chunks"])
        state["confidence"] = confidence
        state["agents_invoked"].append("confidence")
    except Exception as e:
        state["errors"].append(f"Confidence error: {str(e)}")
        # Provide default confidence
        state["confidence"] = ConfidenceScore(
            overall_confidence=0.7,
            grounding_score=0.7,
            coverage_score=0.7,
            consistency_score=0.8,
            requires_escalation=False,
            claims_verified=len(state["answer"].citations) if state["answer"] else 0,
            claims_unverified=0
        )
    
    return state


async def risk_node(state: GraphState) -> GraphState:
    """
    Risk node - analyzes risks and policy conflicts.
    
    Currently a stub - would analyze for conflicts.
    """
    from ..agents.risk import RiskAgent
    
    agent = RiskAgent()
    
    try:
        risk = await agent.run(state["query"], state["policy_chunks"])
        state["risk"] = risk
        state["agents_invoked"].append("risk")
    except Exception as e:
        state["errors"].append(f"Risk error: {str(e)}")
    
    return state


# =============================================================================
# Routing Functions (Conditional Edges)
# =============================================================================

def route_after_router(state: GraphState) -> Literal["policy_rag", "end"]:
    """
    Determine next node after router.
    
    This is where the "deterministic control over non-deterministic components"
    pattern is most visible. The router's output is non-deterministic, but
    our response to it is deterministic.
    """
    intent = state.get("intent")
    
    if not intent:
        return "policy_rag"  # Default to policy search
    
    # Out of scope or clarification needed - skip to end
    if intent.intent in [QueryIntent.OUT_OF_SCOPE, QueryIntent.CLARIFICATION]:
        return "end"
    
    # All other intents need policy search
    return "policy_rag"


def route_after_retrieval(state: GraphState) -> Literal["synthesis", "risk", "end"]:
    """Determine next node after retrieval."""
    intent = state.get("intent")
    
    if not state["policy_chunks"]:
        return "end"  # No content to synthesize
    
    # Risk check queries go through risk analysis
    if intent and intent.requires_risk_analysis:
        return "risk"
    
    return "synthesis"


def route_after_synthesis(state: GraphState) -> Literal["confidence", "end"]:
    """Determine if we need confidence assessment."""
    if state.get("answer"):
        return "confidence"
    return "end"


# =============================================================================
# Graph Builder
# =============================================================================

class PolicyEngineGraph:
    """
    The main orchestration graph for the Policy Intelligence Engine.
    
    This class encapsulates the LangGraph workflow and provides
    a clean interface for execution.
    """
    
    def __init__(self):
        self._graph = None
        self._compiled = None
    
    def build(self):
        """
        Build the LangGraph workflow.
        
        The graph structure:
        
        START -> router -> policy_rag -> synthesis -> confidence -> END
                    |           |
                    v           v
                   END        risk -> synthesis -> ...
        """
        try:
            from langgraph.graph import StateGraph, END
            
            # Create the graph
            workflow = StateGraph(GraphState)
            
            # Add nodes
            workflow.add_node("router", router_node)
            workflow.add_node("policy_rag", policy_rag_node)
            workflow.add_node("synthesis", synthesis_node)
            workflow.add_node("confidence", confidence_node)
            workflow.add_node("risk", risk_node)
            
            # Set entry point
            workflow.set_entry_point("router")
            
            # Add edges
            workflow.add_conditional_edges(
                "router",
                route_after_router,
                {
                    "policy_rag": "policy_rag",
                    "end": END
                }
            )
            
            workflow.add_conditional_edges(
                "policy_rag",
                route_after_retrieval,
                {
                    "synthesis": "synthesis",
                    "risk": "risk",
                    "end": END
                }
            )
            
            workflow.add_edge("risk", "synthesis")
            
            workflow.add_conditional_edges(
                "synthesis",
                route_after_synthesis,
                {
                    "confidence": "confidence",
                    "end": END
                }
            )
            
            workflow.add_edge("confidence", END)
            
            # Compile
            self._compiled = workflow.compile()
            self._graph = workflow
            
            return self
            
        except ImportError:
            # LangGraph not installed - use simple sequential execution
            self._compiled = None
            return self
    
    async def run(self, query: UserQuery) -> EngineResponse:
        """
        Execute the workflow for a query.
        
        Args:
            query: User query to process
            
        Returns:
            Complete engine response
        """
        state = create_initial_state(query)
        
        if self._compiled:
            # Use LangGraph execution
            final_state = await self._compiled.ainvoke(state)
        else:
            # Fallback: simple sequential execution
            final_state = await self._run_sequential(state)
        
        return self._build_response(final_state)
    
    async def _run_sequential(self, state: GraphState) -> GraphState:
        """Fallback sequential execution without LangGraph."""
        # Router
        state = await router_node(state)
        
        # Check if we should continue
        intent = state.get("intent")
        if intent and intent.intent in [QueryIntent.OUT_OF_SCOPE, QueryIntent.CLARIFICATION]:
            return state
        
        # Policy RAG
        state = await policy_rag_node(state)
        
        if not state["policy_chunks"]:
            return state
        
        # Risk analysis if needed
        if intent and intent.requires_risk_analysis:
            state = await risk_node(state)
        
        # Synthesis
        state = await synthesis_node(state)
        
        # Confidence
        if state.get("answer"):
            state = await confidence_node(state)
        
        return state
    
    def _build_response(self, state: GraphState) -> EngineResponse:
        """Build the final response from graph state."""
        processing_time = (time.time() - state["start_time"]) * 1000
        
        # Handle case where we short-circuited (clarification/out of scope)
        if not state.get("answer"):
            intent = state.get("intent")
            if intent and intent.intent == QueryIntent.CLARIFICATION:
                answer = PolicyAnswer(
                    answer="I need more information to answer your question. Could you please provide more context or be more specific about what you're asking?",
                    summary="Clarification needed",
                    citations=[],
                    caveats=["Query was too vague to answer definitively"],
                    related_topics=[],
                    reasoning=intent.reasoning
                )
            elif intent and intent.intent == QueryIntent.OUT_OF_SCOPE:
                answer = PolicyAnswer(
                    answer="This question is outside the scope of the policy intelligence system. I can help with questions about enterprise policies, architectural decisions, and compliance requirements.",
                    summary="Query out of scope",
                    citations=[],
                    caveats=[],
                    related_topics=["data security policies", "API standards", "authentication requirements"],
                    reasoning=intent.reasoning
                )
            else:
                answer = PolicyAnswer(
                    answer="I was unable to generate an answer for your query. Please try rephrasing your question.",
                    summary="Unable to answer",
                    citations=[],
                    caveats=["Processing error occurred"],
                    related_topics=[],
                    reasoning="No answer was generated during processing"
                )
        else:
            answer = state["answer"]
        
        # Default confidence if not set
        confidence = state.get("confidence") or ConfidenceScore(
            overall_confidence=0.5,
            grounding_score=0.5,
            coverage_score=0.5,
            consistency_score=0.5,
            requires_escalation=True,
            escalation_reason="Confidence assessment not completed"
        )
        
        return EngineResponse(
            query=state["query"],
            intent=state.get("intent") or IntentClassification(
                intent=QueryIntent.POLICY_LOOKUP,
                confidence=0.0,
                reasoning="Intent classification failed",
                requires_policy_search=True,
                requires_decision_search=False,
                requires_risk_analysis=False,
            ),
            answer=answer,
            confidence=confidence,
            risk=state.get("risk"),
            retrieval=RetrievalResult(
                policy_chunks=state["policy_chunks"],
                total_sources=len(set(c.source for c in state["policy_chunks"]))
            ),
            processing_time_ms=processing_time,
            agents_invoked=state["agents_invoked"],
            model_calls=len(state["agents_invoked"])  # Rough estimate
        )


def create_workflow() -> PolicyEngineGraph:
    """Create and build the orchestration workflow."""
    graph = PolicyEngineGraph()
    return graph.build()
