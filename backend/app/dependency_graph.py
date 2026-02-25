"""
Dependency graph tracking for structural contradiction detection.

This module provides:
- BFS traversal to find dependency depth
- Dependency edge creation based on semantic similarity
- Structural break detection (when core assumptions collapse)

Phase 4 (Drift Accumulator): Tracks how many commitments depend on a given commitment.
"""

from typing import List, Set
from collections import deque
from app.models import CommitmentGraph, Commitment, Edge


def find_dependency_depth(
    commitment_id: str,
    graph: CommitmentGraph
) -> int:
    """
    Find the dependency depth of a commitment using BFS.

    Dependency depth = number of commitments that depend on this one
    (directly or transitively).

    Args:
        commitment_id: ID of commitment to analyze
        graph: Commitment graph

    Returns:
        Number of commitments that depend on this one
    """
    commitment = graph.get_commitment(commitment_id)
    if not commitment:
        return 0

    # BFS to find all dependents
    visited: Set[str] = set()
    queue = deque([commitment_id])
    visited.add(commitment_id)

    while queue:
        current_id = queue.popleft()
        current = graph.get_commitment(current_id)

        if not current:
            continue

        # Add all direct dependents
        for dependent_id in current.depended_on_by:
            if dependent_id not in visited:
                visited.add(dependent_id)
                queue.append(dependent_id)

    # Return count (excluding the commitment itself)
    return len(visited) - 1


def update_dependency_graph(
    graph: CommitmentGraph,
    new_commitment: Commitment,
    similarity_threshold: float = 0.6
) -> List[Edge]:
    """
    Update dependency graph by finding commitments that the new commitment depends on.

    Creates "depends_on" edges when similarity exceeds threshold.

    Side effect: Updates commitment.depended_on_by fields.

    Args:
        graph: Commitment graph
        new_commitment: New commitment to analyze
        similarity_threshold: Minimum similarity to create dependency (default: 0.6)

    Returns:
        List of new dependency edges
    """
    new_edges = []

    # Compare against prior commitments
    for prior in graph.commitments:
        if prior.turn_id >= new_commitment.turn_id:
            continue

        if not prior.active:
            continue

        # Calculate similarity
        similarity = _compute_similarity(prior.normalized, new_commitment.normalized)

        if similarity > similarity_threshold:
            # Create depends_on edge
            edge = Edge(
                source=new_commitment.id,
                target=prior.id,
                relation="depends_on",
                weight=similarity,
                detected_at_turn=new_commitment.turn_id
            )
            new_edges.append(edge)

            # Update prior's depended_on_by list
            if new_commitment.id not in prior.depended_on_by:
                prior.depended_on_by.append(new_commitment.id)

    return new_edges


def detect_structural_breaks(
    graph: CommitmentGraph,
    structural_break_threshold: int = 3
) -> List[str]:
    """
    Detect structural breaks (contradictions to commitments with many dependents).

    A structural break occurs when a commitment with >= N dependents is contradicted.

    Args:
        graph: Commitment graph
        structural_break_threshold: Minimum dependents to be considered structural

    Returns:
        List of commitment IDs involved in structural breaks
    """
    structural_breaks = []

    for commitment in graph.commitments:
        # Check if commitment has many dependents
        dependency_depth = find_dependency_depth(commitment.id, graph)

        if dependency_depth >= structural_break_threshold:
            # Check if this commitment is contradicted
            if commitment.contradicted_by:
                structural_breaks.append(commitment.id)

    return structural_breaks


def get_dependency_metrics(graph: CommitmentGraph) -> dict:
    """
    Compute dependency graph metrics.

    Returns:
        Dictionary with dependency statistics
    """
    if not graph.commitments:
        return {
            "total_dependencies": 0,
            "max_dependency_depth": 0,
            "avg_dependency_depth": 0.0,
            "structural_breaks": 0
        }

    # Count dependency edges
    dependency_edges = [e for e in graph.edges if e.relation == "depends_on"]

    # Calculate dependency depths
    depths = []
    for commitment in graph.commitments:
        depth = find_dependency_depth(commitment.id, graph)
        depths.append(depth)

    max_depth = max(depths) if depths else 0
    avg_depth = sum(depths) / len(depths) if depths else 0.0

    # Count structural breaks
    structural_breaks = detect_structural_breaks(graph)

    return {
        "total_dependencies": len(dependency_edges),
        "max_dependency_depth": max_depth,
        "avg_dependency_depth": round(avg_depth, 2),
        "structural_breaks": len(structural_breaks),
        "structural_break_commitments": structural_breaks
    }


# Helper functions

def _compute_similarity(text1: str, text2: str) -> float:
    """
    Compute Jaccard similarity between two texts.

    Args:
        text1: First text
        text2: Second text

    Returns:
        Similarity score (0.0 to 1.0)
    """
    tokens1 = set(text1.lower().split())
    tokens2 = set(text2.lower().split())

    if not tokens1 or not tokens2:
        return 0.0

    intersection = tokens1 & tokens2
    union = tokens1 | tokens2

    return len(intersection) / len(union) if union else 0.0
