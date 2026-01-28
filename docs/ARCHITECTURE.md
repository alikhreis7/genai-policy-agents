# Architecture Deep Dive

## Interview Discussion Guide

This document provides detailed architecture explanations for interview discussions. Each section includes key talking points and demonstrates understanding of enterprise GenAI systems.

---

## 1. Core Philosophy

### "LLMs Are Unreliable Components"

This is the foundational principle of the system. Unlike typical demos that treat LLMs as magic boxes, this system:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Traditional Approach                          │
│                                                                  │
│    User Query  ──────►  LLM  ──────►  Answer                    │
│                        (hope it's right)                         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    Our Approach                                  │
│                                                                  │
│    User Query ──► Router ──► RAG ──► Synthesis ──► Confidence   │
│                     │         │          │             │         │
│                     ▼         ▼          ▼             ▼         │
│               (classify)  (retrieve)  (ground)    (verify)      │
│                                                                  │
│    Every step is validated, logged, and can fail safely         │
└─────────────────────────────────────────────────────────────────┘
```

**Key talking point:**
> "We treat LLMs the way we'd treat any unreliable external service - with validation, retry logic, fallbacks, and observability. The orchestration is deterministic even though the components are non-deterministic."

---

## 2. Agent Architecture

### Why Multiple Agents?

Single-prompt approaches fail because:
1. **Responsibility diffusion** - One prompt tries to do too much
2. **Testing difficulty** - Can't unit test a monolithic prompt
3. **Failure opacity** - Hard to know where things went wrong
4. **Scalability limits** - Can't optimize individual components

Our multi-agent approach:

```
┌──────────────────────────────────────────────────────────────────┐
│                        Agent Responsibilities                     │
├────────────────┬─────────────────────────────────────────────────┤
│ Router Agent   │ Intent classification, routing decisions        │
│                │ "What kind of question is this?"                 │
├────────────────┼─────────────────────────────────────────────────┤
│ Policy RAG     │ Retrieval from policy documents                 │
│                │ "What do our policies say about this?"          │
├────────────────┼─────────────────────────────────────────────────┤
│ Decision RAG   │ Retrieval from ADRs/historical decisions        │
│                │ "Have we made similar decisions before?"        │
├────────────────┼─────────────────────────────────────────────────┤
│ Risk Agent     │ Conflict detection, risk assessment             │
│                │ "What could go wrong?"                          │
├────────────────┼─────────────────────────────────────────────────┤
│ Synthesis      │ Answer generation with citations                │
│                │ "Here's the answer, grounded in sources"        │
├────────────────┼─────────────────────────────────────────────────┤
│ Confidence     │ Hallucination detection, escalation             │
│                │ "How confident are we? Should humans review?"   │
└────────────────┴─────────────────────────────────────────────────┘
```

**Key talking point:**
> "Each agent has a single responsibility and can be tested, optimized, and replaced independently. The Router doesn't answer questions - it classifies and routes. The Synthesis agent doesn't retrieve - it reasons over retrieved content."

---

## 3. LangGraph Orchestration

### Why LangGraph?

LangChain is good for linear chains. But real systems need:
- Conditional branching
- Parallel execution
- State management
- Failure handling

LangGraph provides **graph-based orchestration**:

```python
# Deterministic control flow
workflow = StateGraph(GraphState)

# Nodes are agent invocations
workflow.add_node("router", router_node)
workflow.add_node("policy_rag", policy_rag_node)
workflow.add_node("synthesis", synthesis_node)

# Edges define flow (can be conditional)
workflow.add_conditional_edges(
    "router",
    route_by_intent,  # Function that decides next node
    {
        "policy_query": "policy_rag",
        "out_of_scope": END,
    }
)
```

### State Flow

```
┌─────────────┐
│ GraphState  │
├─────────────┤
│ query       │◄── Input
│ intent      │◄── Set by Router
│ chunks      │◄── Set by RAG agents
│ answer      │◄── Set by Synthesis
│ confidence  │◄── Set by Confidence
│ errors      │◄── Accumulated errors
│ agents_used │◄── Tracking
└─────────────┘
     │
     │ Flows through graph
     ▼
┌─────────────┐
│   Router    │──► Classifies intent
└─────────────┘
     │
     ▼ (conditional)
┌─────────────┐
│ Policy RAG  │──► Retrieves policies
└─────────────┘
     │
     ▼
┌─────────────┐
│  Synthesis  │──► Generates answer
└─────────────┘
     │
     ▼
┌─────────────┐
│ Confidence  │──► Validates & scores
└─────────────┘
```

**Key talking point:**
> "The graph structure means I can reason about the system's behavior. Given this intent, these nodes will execute in this order. It's predictable and testable, even though individual nodes use LLMs."

---

## 4. RAG Design Decisions

### Multiple Indexes

We don't use one giant vector store. Different content needs different treatment:

| Index | Content | Chunking | Why Separate |
|-------|---------|----------|--------------|
| Policy | Policies, standards | By section | Legal precision matters |
| ADR | Decision records | Full document | Context is crucial |
| Discussion | PRs, issues | By thread | Conversation context |

### Section-Based Chunking

**Bad (typical approach):**
```
Chunk 1: "...PII must be encrypted. All data"
Chunk 2: "stores must implement access..."
```
Breaks mid-sentence, loses context.

**Good (our approach):**
```
Chunk 1: "## PII Handling
          PII must be encrypted at rest..."

Chunk 2: "## Access Control  
          All data stores must implement..."
```
Preserves document structure.

```python
def chunk_by_sections(content: str, source: str) -> list[PolicyChunk]:
    """
    Key insight: Policies have structure.
    We chunk by section headers, not token count.
    """
    pattern = r"^(##|###)\s+(.+)$"  # Markdown headers
    # Split on headers, preserve structure
```

**Key talking point:**
> "Most RAG failures are retrieval failures. If you chunk a policy mid-sentence, the LLM won't get the full context. Section-based chunking preserves the semantic units the document authors intended."

---

## 5. Structured Outputs

### Why Pydantic Everywhere?

LLMs return strings. Strings are unreliable. We force structure:

```python
class PolicyAnswer(BaseModel):
    answer: str
    summary: str
    citations: list[Citation]
    caveats: list[str]
    reasoning: str

# LLM must return valid JSON matching this schema
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    response_format={"type": "json_object"},
)
```

Benefits:
1. **Validation** - Invalid responses fail fast
2. **Type safety** - IDE support, catching bugs early
3. **Documentation** - Schema IS the spec
4. **Testing** - Can test without LLM calls

**Key talking point:**
> "Every agent input and output is a Pydantic model. This isn't just nice-to-have - it's how we maintain contracts between components. If the LLM returns malformed JSON, we catch it immediately."

---

## 6. Confidence & Escalation

### The Confidence Agent

This agent embodies enterprise trust requirements:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Confidence Scoring                            │
├─────────────────┬───────────────────────────────────────────────┤
│ Grounding Score │ Are claims supported by retrieved sources?    │
│ Coverage Score  │ Do sources fully address the query?           │
│ Consistency     │ Is the answer internally consistent?          │
├─────────────────┼───────────────────────────────────────────────┤
│ Overall Score   │ Weighted combination (0.0 - 1.0)              │
├─────────────────┼───────────────────────────────────────────────┤
│ Escalation      │ If score < 0.5, flag for human review         │
└─────────────────┴───────────────────────────────────────────────┘
```

### Escalation Logic

```python
def should_escalate(self) -> bool:
    return (
        self.confidence.requires_escalation or
        self.confidence.overall_confidence < 0.5 or
        (self.risk and self.risk.risk_level in ["high", "critical"])
    )
```

**Key talking point:**
> "The system knows when to say 'I don't know.' Enterprise users need to trust the system. If we're not confident, we escalate to humans rather than guessing."

---

## 7. Tool Calling Pattern

### Tools as Interfaces

Agents don't call random functions. They use **structured tools**:

```python
class PolicySearchTool:
    name = "search_policies"
    description = """Search enterprise policy documents..."""
    
    def get_schema(self) -> dict:
        """OpenAI function calling format"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": PolicySearchInput.model_json_schema()
            }
        }
```

Why this matters:
1. **LLM understands** - Description helps it use tools correctly
2. **Validation** - Inputs are checked before execution
3. **Logging** - Every tool call can be traced
4. **Swappable** - Implementation can change, interface stays

**Key talking point:**
> "Tools are the API between agents and capabilities. The LLM decides WHAT to do, tools define HOW to do it. This separation lets us audit, rate-limit, and secure tool calls."

---

## 8. Error Handling & Failure Modes

### Graceful Degradation

```python
async def router_node(state: GraphState) -> GraphState:
    try:
        intent = await agent.run(state["query"])
        state["intent"] = intent
    except Exception as e:
        state["errors"].append(f"Router error: {str(e)}")
        # Fallback: assume policy lookup
        state["intent"] = IntentClassification(
            intent=QueryIntent.POLICY_LOOKUP,
            confidence=0.3,
            reasoning="Fallback due to router error",
            ...
        )
    return state
```

Every node:
1. Catches exceptions
2. Logs errors to state
3. Provides safe fallback
4. Continues execution

**Key talking point:**
> "Failure is expected. LLM APIs go down, rate limits hit, parsing fails. Each component handles its own failures and provides fallbacks. The system degrades gracefully rather than crashing."

---

## 9. Testing Strategy

### Multi-Level Testing

```
┌─────────────────────────────────────────────────────────────────┐
│ Unit Tests                                                       │
│ - Schema validation                                              │
│ - Chunking logic                                                 │
│ - State transformations                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Integration Tests (mocked LLM)                                   │
│ - Agent behavior with canned responses                          │
│ - Graph execution paths                                          │
│ - Error handling                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Evaluation Tests (real LLM)                                      │
│ - Retrieval quality                                              │
│ - Answer accuracy                                                │
│ - Hallucination detection                                        │
└─────────────────────────────────────────────────────────────────┘
```

**Key talking point:**
> "GenAI systems are systems. We test them like systems - unit tests for components, integration tests for flows, and evaluations for quality. You can't just vibe-check a production system."

---

## 10. What's Next (Future Work)

| Feature | Description | Why It Matters |
|---------|-------------|----------------|
| Real Vector DB | Pinecone/Weaviate integration | Production scale |
| GitHub ADR Ingestion | Automatic ADR discovery | Living documentation |
| Feedback Loop | User corrections improve retrieval | Continuous learning |
| Multi-Tenant | Per-org policy isolation | Enterprise deployment |
| Observability | OpenTelemetry tracing | Production debugging |

---

## Interview Cheat Sheet

**If they ask about architecture:**
> "Multi-agent with LangGraph orchestration. Each agent has single responsibility. Structured I/O everywhere."

**If they ask about reliability:**
> "LLMs are unreliable components. We validate, score confidence, and escalate when unsure."

**If they ask about RAG:**
> "Section-based chunking, multiple indexes for different content types. Retrieval failures cause most GenAI failures."

**If they ask about testing:**
> "Unit tests for schemas and logic. Integration tests with mocked LLMs. Evaluations for quality."

**If they ask why not just one prompt:**
> "Can't test it. Can't debug it. Can't optimize parts independently. Can't handle failures gracefully."

---

## Code Locations

| Component | File | Key Function |
|-----------|------|--------------|
| Router Agent | `src/agents/router.py` | `RouterAgent.run()` |
| Policy RAG | `src/agents/policy_rag.py` | `PolicyRAGAgent.run()` |
| Synthesis | `src/agents/synthesis.py` | `SynthesisAgent.run()` |
| Orchestration | `src/orchestration/graph.py` | `PolicyEngineGraph.run()` |
| Schemas | `src/models/schemas.py` | All Pydantic models |
| Tools | `src/tools/policy_search.py` | `PolicySearchTool` |
