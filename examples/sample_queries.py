#!/usr/bin/env python3
"""
Sample Queries for Policy Intelligence Engine

This script demonstrates various query types and expected behaviors.
Run with: python examples/sample_queries.py
"""

import asyncio
import sys
sys.path.insert(0, '.')

from src.models.schemas import UserQuery
from src.orchestration.graph import create_workflow

# Sample queries organized by intent type
SAMPLE_QUERIES = {
    "policy_lookup": [
        "Can we store PII in Redis?",
        "What encryption is required for user data at rest?",
        "Are we allowed to log user email addresses?",
        "What's the password policy for admin accounts?",
        "Can we use MongoDB for storing financial records?",
    ],
    
    "decision_support": [
        "Is it acceptable to bypass the API gateway for internal services?",
        "Should we use microservices or a monolith for the new payment system?",
        "What's the recommended approach for service-to-service authentication?",
        "Is it okay to store session data in Redis?",
    ],
    
    "risk_check": [
        "What are the compliance risks of using a third-party analytics service?",
        "Does storing data in US-East region violate any data residency requirements?",
        "What security risks should we consider when exposing an internal API?",
    ],
}


async def run_query(query_text: str) -> None:
    """Run a single query and print the result."""
    print(f"\n{'='*60}")
    print(f"QUERY: {query_text}")
    print('='*60)
    
    workflow = create_workflow()
    query = UserQuery(text=query_text)
    
    response = await workflow.run(query)
    
    print(f"\nIntent: {response.intent.intent.value} ({response.intent.confidence:.0%} confidence)")
    print(f"\nAnswer: {response.answer.summary}")
    print(f"\nConfidence: {response.confidence.overall_confidence:.0%}")
    print(f"Agents used: {', '.join(response.agents_invoked)}")
    
    if response.answer.citations:
        print(f"\nCitations:")
        for citation in response.answer.citations[:3]:
            print(f"  - {citation.source}: {citation.claim[:50]}...")


async def main():
    """Run sample queries demonstrating different intents."""
    print("=" * 60)
    print("POLICY INTELLIGENCE ENGINE - SAMPLE QUERIES")
    print("=" * 60)
    
    # Run one query from each category
    for intent_type, queries in SAMPLE_QUERIES.items():
        print(f"\n\n{'#'*60}")
        print(f"# Intent Type: {intent_type.upper()}")
        print('#'*60)
        
        # Run first query from each category
        await run_query(queries[0])


if __name__ == "__main__":
    asyncio.run(main())
