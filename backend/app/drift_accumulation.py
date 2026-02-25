"""
Drift accumulation core for longitudinal epistemic stability monitoring.

This module implements the cumulative drift scoring system:
- Drift magnitude calculation (4-factor formula)
- Drift accumulation over time
- Drift velocity calculation
- Drift decay for recovery detection

Phase 4 (Drift Accumulator): Core drift tracking logic.
"""

from typing import List, Optional
from datetime import datetime
from app.models import (
    CommitmentGraph,
    Commitment,
    DriftEvent
)
from app.dependency_graph import find_dependency_depth


def calculate_drift_magnitude(
    prior_commitment: Commitment,
    new_commitment: Commitment,
    graph: CommitmentGraph,
    similarity: float
) -> float:
    """
    Calculate drift magnitude using topic-anchor weighted formula.

    NEW FORMULA (Topic-Anchor Based):
    drift_magnitude = (
        anchor_match × 0.5 +        # Topic anchor match (primary signal)
        confidence_delta × 0.2 +    # Confidence shift
        recency × 0.2 +             # How recent was prior commitment
        similarity × 0.1            # Optional bonus (vocabulary overlap)
    )

    Note: This function is called AFTER anchor matching succeeds,
    so anchor_match_weight = 1.0 (guaranteed 0.5 base score).

    Args:
        prior_commitment: Earlier commitment
        new_commitment: Later commitment
        graph: Commitment graph
        similarity: Token similarity (0.0-1.0) - optional bonus

    Returns:
        Drift magnitude (0.0-1.0+)
    """
    # Factor 1: Anchor match weight (0.5 weight)
    # If this function is called, anchors already matched
    anchor_match_weight = 1.0
    anchor_component = anchor_match_weight * 0.5

    # Factor 2: Confidence delta (0.2 weight)
    confidence_delta = abs(new_commitment.confidence - prior_commitment.confidence)
    confidence_component = confidence_delta * 0.2

    # Factor 3: Recency weight (0.2 weight)
    turn_gap = new_commitment.turn_id - prior_commitment.turn_id
    max_turn_gap = len(graph.turns) if len(graph.turns) > 0 else 1
    recency = 1.0 - min(turn_gap / max_turn_gap, 1.0)
    recency_component = recency * 0.2

    # Factor 4: Similarity bonus (0.1 weight)
    # Reduced weight - no longer primary gate
    similarity_component = similarity * 0.1

    # Sum components
    drift_magnitude = (
        anchor_component +
        confidence_component +
        recency_component +
        similarity_component
    )

    return drift_magnitude


def accumulate_drift(
    graph: CommitmentGraph,
    prior_commitment: Commitment,
    new_commitment: Commitment,
    similarity: float,
    confidence_delta: float,
    recency_weight: float
) -> DriftEvent:
    """
    Accumulate drift by creating a DriftEvent and updating graph's drift score.

    Side effects:
    - Adds DriftEvent to graph.drift_events
    - Increments graph.epistemic_drift_score
    - Resets graph.turns_since_last_drift to 0
    - Updates graph.last_drift_update_turn

    Args:
        graph: Commitment graph
        prior_commitment: Earlier commitment
        new_commitment: Later commitment
        similarity: Semantic similarity
        confidence_delta: Confidence shift
        recency_weight: Recency factor

    Returns:
        Created DriftEvent
    """
    # Calculate drift magnitude
    drift_magnitude = calculate_drift_magnitude(
        prior_commitment,
        new_commitment,
        graph,
        similarity
    )

    # Get dependency depth
    dependency_depth = find_dependency_depth(prior_commitment.id, graph)

    # Create DriftEvent
    drift_event = DriftEvent(
        id=f"drift_{len(graph.drift_events) + 1}",
        commitment_a=prior_commitment.id,
        commitment_b=new_commitment.id,
        similarity=similarity,
        confidence_delta=confidence_delta,
        recency_weight=recency_weight,
        dependency_depth=dependency_depth,
        drift_magnitude=drift_magnitude,
        detected_at_turn=new_commitment.turn_id,
        timestamp=datetime.now()
    )

    # Add to graph
    graph.drift_events.append(drift_event)

    # Accumulate drift score
    graph.epistemic_drift_score += drift_magnitude

    # Reset stability counter
    graph.turns_since_last_drift = 0
    graph.last_drift_update_turn = new_commitment.turn_id

    return drift_event


def calculate_drift_velocity(
    graph: CommitmentGraph,
    window: int = 5
) -> float:
    """
    Calculate drift velocity (drift per turn over recent window).

    drift_velocity = sum(drift_magnitude in last N turns) / N

    Args:
        graph: Commitment graph
        window: Number of recent turns to consider (default: 5)

    Returns:
        Drift velocity (0.0+)
    """
    if len(graph.turns) == 0:
        return 0.0

    # Get recent turn IDs
    recent_turns = graph.turns[-window:] if len(graph.turns) >= window else graph.turns
    recent_turn_ids = [t.id for t in recent_turns]

    # Sum drift magnitude in recent window
    recent_drift = sum(
        event.drift_magnitude
        for event in graph.drift_events
        if event.detected_at_turn in recent_turn_ids
    )

    # Calculate velocity
    velocity = recent_drift / len(recent_turns) if recent_turns else 0.0

    return velocity


def apply_drift_decay(
    graph: CommitmentGraph,
    decay_factor: float = 0.95,
    stability_threshold_turns: int = 3
) -> None:
    """
    Apply drift decay when conversation stabilizes.

    Decay rule:
    - If turns_since_last_drift >= stability_threshold_turns
    - Then drift_score *= decay_factor (5% decay per stable turn)

    Side effect: Updates graph.epistemic_drift_score

    Args:
        graph: Commitment graph
        decay_factor: Decay multiplier (default: 0.95 = 5% decay)
        stability_threshold_turns: Min consecutive stable turns (default: 3)
    """
    if graph.turns_since_last_drift >= stability_threshold_turns:
        # Apply decay
        graph.epistemic_drift_score *= decay_factor

        # Floor at 0.0
        graph.epistemic_drift_score = max(0.0, graph.epistemic_drift_score)


def detect_drift_recovery(
    graph: CommitmentGraph,
    lookback_window: int = 5
) -> bool:
    """
    Detect if drift is trending downward (recovery).

    Recovery = no new drift events in last N turns AND drift_score decreasing.

    Args:
        graph: Commitment graph
        lookback_window: Number of recent turns to check (default: 5)

    Returns:
        True if drift is recovering, False otherwise
    """
    if len(graph.turns) < lookback_window:
        return False

    # Get recent turn IDs
    recent_turns = graph.turns[-lookback_window:]
    recent_turn_ids = [t.id for t in recent_turns]

    # Check for new drift events in recent window
    recent_drift_events = [
        event for event in graph.drift_events
        if event.detected_at_turn in recent_turn_ids
    ]

    # Recovery = no recent drift AND score is low
    is_recovering = (
        len(recent_drift_events) == 0 and
        graph.epistemic_drift_score < 1.0
    )

    return is_recovering


def get_drift_summary(graph: CommitmentGraph) -> dict:
    """
    Get a summary of the current drift state.

    Returns:
        Dictionary with drift metrics
    """
    return {
        "cumulative_drift_score": round(graph.epistemic_drift_score, 3),
        "drift_velocity": round(calculate_drift_velocity(graph), 3),
        "turns_since_last_drift": graph.turns_since_last_drift,
        "total_drift_events": len(graph.drift_events),
        "last_drift_update_turn": graph.last_drift_update_turn,
        "is_recovering": detect_drift_recovery(graph)
    }


def migrate_graph_to_drift_system(graph: CommitmentGraph) -> CommitmentGraph:
    """
    Migrate legacy graph to include drift tracking fields.

    For backward compatibility with existing graphs.

    Args:
        graph: Commitment graph (may be legacy)

    Returns:
        Updated graph with drift fields
    """
    # Check if already migrated
    if hasattr(graph, 'epistemic_drift_score') and graph.epistemic_drift_score is not None:
        return graph

    # Add drift fields with defaults
    graph.epistemic_drift_score = 0.0
    graph.last_stable_version = graph.version if hasattr(graph, 'version') else 0
    graph.drift_events = []
    graph.drift_velocity = 0.0
    graph.last_drift_update_turn = 0
    graph.turns_since_last_drift = 0

    # Add topic tracking fields
    if not hasattr(graph, 'topic_stance_history'):
        graph.topic_stance_history = {}
    if not hasattr(graph, 'topic_clusters'):
        graph.topic_clusters = []

    # Add depended_on_by to all commitments
    for commitment in graph.commitments:
        if not hasattr(commitment, 'depended_on_by'):
            commitment.depended_on_by = []

    return graph
