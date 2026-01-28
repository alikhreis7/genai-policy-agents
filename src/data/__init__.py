"""
Data loading and indexing utilities.

Handles ingestion of policy documents, ADRs, and other sources.
"""

from .loader import PolicyLoader, load_policies, create_policy_index

__all__ = ["PolicyLoader", "load_policies", "create_policy_index"]
