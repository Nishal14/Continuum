"""Utility functions for caching, rate limiting, and graph operations."""

from typing import Dict, Optional
from app.models import CommitmentGraph
import hashlib
import json

# Simple in-memory cache (replace with Redis in production)
graph_cache: Dict[str, str] = {}


def get_graph_from_cache(conversation_id: str) -> Optional[str]:
    """Retrieve cached graph hash for a conversation."""
    return graph_cache.get(conversation_id)


def save_graph_to_cache(conversation_id: str, graph_hash: str):
    """Save graph hash to cache."""
    graph_cache[conversation_id] = graph_hash


def compute_stable_hash(data: dict) -> str:
    """Compute SHA256 hash of dictionary for caching."""
    json_str = json.dumps(data, sort_keys=True)
    return hashlib.sha256(json_str.encode()).hexdigest()
