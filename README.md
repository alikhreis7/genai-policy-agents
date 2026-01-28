# Enterprise Policy & Decision Intelligence Engine

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/alikhreis7/genai-policy-agents/actions/workflows/ci.yml/badge.svg)](https://github.com/alikhreis7/genai-policy-agents/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-29%20passed-brightgreen.svg)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A **multi-agent GenAI decision-support system** that uses RAG over enterprise policies, architectural decision records (ADRs), and historical discussions to answer:
- "Is this allowed?"
- "Has this been done before?"
- "What are the risks?"

Built with **citations, confidence scoring, and human escalation** — demonstrating production-grade GenAI engineering practices.

![Demo Screenshot](docs/demo-screenshot.png)

## Why This Project?

This project demonstrates how enterprise GenAI teams actually build systems:

| Traditional Approach | This Project's Approach |
|---------------------|------------------------|
| Single prompt → LLM → Answer | Multi-agent orchestration with specialized roles |
| Hope the LLM is right | Confidence scoring + human escalation |
| Black box responses | Citations linking every claim to sources |
| Monolithic chain | Deterministic graph-based control flow |

**Key Principle**: LLMs are treated as **unreliable components** that must be orchestrated, validated, and constrained.

## Architecture

```
User Query
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Intent Router Agent                           │
│         Classifies query → Routes to appropriate agents          │
└─────────────────────────────────────────────────────────────────┘
    │
    ├──────────────────┬──────────────────┐
    ▼                  ▼                  ▼
┌────────────┐  ┌────────────┐  ┌────────────┐
│ Policy RAG │  │ Decision   │  │   Risk     │
│   Agent    │  │ History    │  │  Agent     │
│            │  │  Agent     │  │            │
└────────────┘  └────────────┘  └────────────┘
    │                  │                  │
    └──────────────────┼──────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Synthesis Agent                              │
│         Combines evidence → Structured answer + citations        │
└─────────────────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Confidence Agent                               │
│       Validates grounding → Assigns confidence → Escalation      │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Clone the repository
git clone https://github.com/alikhreis7/genai-policy-agents.git
cd genai-policy-agents

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run in demo mode (no API keys needed!)
python -m src.main "Can we store PII in Redis?"
```

### With API Keys (Full LLM Mode)

```bash
# Copy and configure environment
cp .env.example .env
# Edit .env with your OpenAI API key

# Run with real LLM
python -m src.main "Can we store PII in Redis?"
```

## Example Queries

```bash
# Policy lookup
python -m src.main "Can we store PII in Redis?"

# Decision support
python -m src.main "Is it acceptable to bypass the API gateway for internal services?"

# Risk assessment
python -m src.main "What are the compliance risks of using MongoDB for user data?"

# Interactive mode
python -m src.main
```

## Sample Output

```
╭─────────────────────────── Intent Classification ────────────────────────────╮
│   Intent        policy_lookup                                                │
│   Confidence    90%                                                          │
│   Reasoning     Query asks about policy compliance - routing to policy lookup│
╰──────────────────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────── Answer ───────────────────────────────────╮
│ Based on the data security policy, **PII should NOT be stored in             │
│ general-purpose Redis caches**.                                              │
│                                                                              │
│ The policy explicitly states that PII must be classified as CONFIDENTIAL...  │
╰─────────────── PII storage in Redis is not allowed by default policy ────────╯

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Claim                          ┃ Source                    ┃ Relevance ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ Policy guidance from Data...   │ data-security-policy.md   │ direct    │
│ Policy guidance from Approved..│ approved-technologies.md  │ direct    │
└────────────────────────────────┴───────────────────────────┴───────────┘

╭─────────────────────────── Confidence Assessment ────────────────────────────╮
│   Overall        93%                                                         │
│   Grounding      95%                                                         │
│   Coverage       93%                                                         │
│   Consistency    90%                                                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## Project Structure

```
policy-intelligence-engine/
├── src/
│   ├── agents/              # Agent implementations
│   │   ├── router.py        # Intent classification & routing
│   │   ├── policy_rag.py    # Policy document retrieval
│   │   ├── synthesis.py     # Answer generation with citations
│   │   ├── confidence.py    # Grounding verification
│   │   └── risk.py          # Risk assessment
│   ├── orchestration/
│   │   └── graph.py         # LangGraph workflow definition
│   ├── models/
│   │   └── schemas.py       # Pydantic models (15+ schemas)
│   ├── tools/               # Structured tool definitions
│   └── main.py              # CLI interface
├── tests/                   # 29 unit & integration tests
├── docs/
│   └── ARCHITECTURE.md      # Detailed architecture documentation
└── data/
    └── policies/            # Sample policy documents
```

## Key Design Decisions

### 1. Multi-Agent Over Single Prompt
Each agent has a single responsibility and can be tested, optimized, and replaced independently.

### 2. Structured Outputs Everywhere
All agent I/O uses Pydantic models - no raw strings. This enables validation, type safety, and clear contracts.

### 3. Section-Based Chunking
Unlike typical token-count chunking, we chunk by document structure (headings/sections) to preserve semantic coherence.

### 4. Demo Mode
Works without API keys for demonstrations - perfect for interviews and portfolio reviews.

### 5. Graceful Degradation
Every component handles failures and provides fallbacks. The system never crashes; it degrades gracefully.

## Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src
```

## Tech Stack

- **Python 3.11+** - Modern Python features
- **OpenAI API** - LLM for reasoning (optional for demo mode)
- **LangGraph** - Graph-based agent orchestration
- **Pydantic** - Data validation & structured outputs
- **FAISS** - Vector similarity search
- **Rich** - Beautiful CLI output

## Documentation

- [Architecture Deep Dive](docs/ARCHITECTURE.md) - Detailed design documentation with interview talking points
- [API Reference](docs/ARCHITECTURE.md#code-locations) - Key functions and classes

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

**Ali Khreis** - [GitHub](https://github.com/alikhreis7) | [LinkedIn](https://linkedin.com/in/alikhreis)

---

*Built to demonstrate enterprise GenAI engineering practices: agent-first design, API-driven architecture, safety-conscious systems, and orchestration-focused development.*
