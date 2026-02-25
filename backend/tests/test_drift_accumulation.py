"""
Unit tests for drift accumulation system.

Tests:
- Drift magnitude calculation
- Drift accumulation over time
- Drift velocity calculation
- Drift decay with stable turns
- Recovery detection
"""

import pytest
from datetime import datetime
from app.models import (
    CommitmentGraph,
    Commitment,
    Turn
)
from app.drift_accumulation import (
    calculate_drift_magnitude,
    accumulate_drift,
    calculate_drift_velocity,
    apply_drift_decay,
    detect_drift_recovery,
    migrate_graph_to_drift_system
)
from app.dependency_graph import update_dependency_graph


def test_calculate_drift_magnitude():
    """Test drift magnitude calculation with 4-factor formula."""
    # Create a test graph
    graph = CommitmentGraph(conversation_id="test_1")
    migrate_graph_to_drift_system(graph)

    # Add turns
    turn1 = Turn(id=1, speaker="user", text="I think Python is great", ts=datetime.now())
    turn2 = Turn(id=2, speaker="user", text="I think Python is terrible", ts=datetime.now())
    graph.turns = [turn1, turn2]

    # Create commitments
    prior = Commitment(
        id="c1",
        turn_id=1,
        kind="claim",
        normalized="Python is great",
        polarity="positive",
        confidence=0.8,
        timestamp=datetime.now()
    )

    new = Commitment(
        id="c2",
        turn_id=2,
        kind="claim",
        normalized="Python is terrible",
        polarity="negative",
        confidence=0.9,
        timestamp=datetime.now()
    )

    graph.commitments = [prior]

    # Calculate drift magnitude
    similarity = 0.6
    magnitude = calculate_drift_magnitude(prior, new, graph, similarity)

    # Should be between 0 and 1
    assert 0.0 <= magnitude <= 1.0
    # Should be non-zero for contradictions
    assert magnitude > 0.0
    print(f"✓ Drift magnitude: {magnitude:.3f}")


def test_accumulate_drift():
    """Test drift accumulation adds to cumulative score."""
    graph = CommitmentGraph(conversation_id="test_2")
    migrate_graph_to_drift_system(graph)

    # Add turns
    turn1 = Turn(id=1, speaker="user", text="Test 1", ts=datetime.now())
    turn2 = Turn(id=2, speaker="user", text="Test 2", ts=datetime.now())
    graph.turns = [turn1, turn2]

    # Create commitments
    prior = Commitment(
        id="c1",
        turn_id=1,
        kind="claim",
        normalized="Initial claim",
        polarity="positive",
        confidence=0.7,
        timestamp=datetime.now()
    )

    new = Commitment(
        id="c2",
        turn_id=2,
        kind="claim",
        normalized="Contradictory claim",
        polarity="negative",
        confidence=0.8,
        timestamp=datetime.now()
    )

    graph.commitments = [prior]

    # Initial drift score should be 0
    assert graph.epistemic_drift_score == 0.0

    # Accumulate drift
    drift_event = accumulate_drift(
        graph=graph,
        prior_commitment=prior,
        new_commitment=new,
        similarity=0.7,
        confidence_delta=0.1,
        recency_weight=0.8
    )

    # Drift score should increase
    assert graph.epistemic_drift_score > 0.0
    assert len(graph.drift_events) == 1
    assert graph.turns_since_last_drift == 0
    assert graph.last_drift_update_turn == 2

    print(f"✓ Drift accumulated: {graph.epistemic_drift_score:.3f}")


def test_drift_velocity():
    """Test drift velocity calculation over window."""
    graph = CommitmentGraph(conversation_id="test_3")
    migrate_graph_to_drift_system(graph)

    # Add 6 turns
    for i in range(1, 7):
        turn = Turn(id=i, speaker="user", text=f"Turn {i}", ts=datetime.now())
        graph.turns.append(turn)

    # Create commitments and drift events
    for i in range(1, 6):
        prior = Commitment(
            id=f"c{i}",
            turn_id=i,
            kind="claim",
            normalized=f"Claim {i}",
            polarity="positive" if i % 2 == 0 else "negative",
            confidence=0.7,
            timestamp=datetime.now()
        )
        graph.commitments.append(prior)

    # Add drift events to last 3 turns
    from app.models import DriftEvent
    for i in range(4, 7):
        drift_event = DriftEvent(
            id=f"drift_{i}",
            commitment_a=f"c{i-1}",
            commitment_b=f"c{i}",
            similarity=0.6,
            confidence_delta=0.2,
            recency_weight=0.8,
            dependency_depth=0,
            drift_magnitude=0.4,
            detected_at_turn=i,
            timestamp=datetime.now()
        )
        graph.drift_events.append(drift_event)

    # Calculate velocity
    velocity = calculate_drift_velocity(graph, window=5)

    # Velocity should be positive (3 events in last 5 turns)
    assert velocity > 0.0
    print(f"✓ Drift velocity: {velocity:.3f}")


def test_drift_decay():
    """Test drift decay after stable turns."""
    graph = CommitmentGraph(conversation_id="test_4")
    migrate_graph_to_drift_system(graph)

    # Set initial drift score
    graph.epistemic_drift_score = 2.0
    graph.turns_since_last_drift = 0

    # No decay yet (need 3 stable turns)
    apply_drift_decay(graph, decay_factor=0.95, stability_threshold_turns=3)
    assert graph.epistemic_drift_score == 2.0

    # After 3 stable turns
    graph.turns_since_last_drift = 3
    apply_drift_decay(graph, decay_factor=0.95, stability_threshold_turns=3)
    assert graph.epistemic_drift_score < 2.0
    assert graph.epistemic_drift_score == pytest.approx(1.9, rel=0.01)

    print(f"✓ Drift decayed to: {graph.epistemic_drift_score:.3f}")


def test_recovery_detection():
    """Test drift recovery detection."""
    graph = CommitmentGraph(conversation_id="test_5")
    migrate_graph_to_drift_system(graph)

    # Add turns
    for i in range(1, 11):
        turn = Turn(id=i, speaker="user", text=f"Turn {i}", ts=datetime.now())
        graph.turns.append(turn)

    # Low drift score
    graph.epistemic_drift_score = 0.5

    # No recent drift events (last 5 turns are stable)
    from app.models import DriftEvent
    drift_event = DriftEvent(
        id="drift_1",
        commitment_a="c1",
        commitment_b="c2",
        similarity=0.6,
        confidence_delta=0.2,
        recency_weight=0.8,
        dependency_depth=0,
        drift_magnitude=0.5,
        detected_at_turn=3,  # Old event, not in last 5 turns
        timestamp=datetime.now()
    )
    graph.drift_events.append(drift_event)

    # Should detect recovery
    is_recovering = detect_drift_recovery(graph, lookback_window=5)
    assert is_recovering

    print(f"✓ Recovery detected: {is_recovering}")


def test_migration():
    """Test backward compatibility migration."""
    # Create legacy graph (no drift fields)
    graph = CommitmentGraph(conversation_id="test_6")

    # Migrate
    migrate_graph_to_drift_system(graph)

    # Should have drift fields
    assert hasattr(graph, 'epistemic_drift_score')
    assert graph.epistemic_drift_score == 0.0
    assert hasattr(graph, 'drift_events')
    assert hasattr(graph, 'topic_stance_history')
    assert hasattr(graph, 'topic_clusters')

    print("✓ Migration successful")


def test_gradual_accumulation():
    """Test that drift accumulates gradually over multiple turns."""
    graph = CommitmentGraph(conversation_id="test_7")
    migrate_graph_to_drift_system(graph)

    # Add 10 turns
    for i in range(1, 11):
        turn = Turn(id=i, speaker="user", text=f"Turn {i}", ts=datetime.now())
        graph.turns.append(turn)

    # Create commitments with increasing contradiction
    claims = [
        ("Python is excellent", "positive", 0.9),
        ("Python is very good", "positive", 0.8),
        ("Python is okay", "neutral", 0.6),
        ("Python has issues", "neutral", 0.5),
        ("Python is problematic", "negative", 0.6),
        ("Python is bad", "negative", 0.8),
    ]

    for i, (claim, polarity, confidence) in enumerate(claims):
        commitment = Commitment(
            id=f"c{i+1}",
            turn_id=i+1,
            kind="claim",
            normalized=claim,
            polarity=polarity,
            confidence=confidence,
            timestamp=datetime.now()
        )
        graph.commitments.append(commitment)

        # Accumulate drift if not first commitment
        if i > 0:
            prior = graph.commitments[i-1]
            similarity = 0.6  # Related topic (Python)

            accumulate_drift(
                graph=graph,
                prior_commitment=prior,
                new_commitment=commitment,
                similarity=similarity,
                confidence_delta=abs(confidence - prior.confidence),
                recency_weight=0.8
            )

    # Drift should accumulate over time
    assert graph.epistemic_drift_score > 1.0
    assert len(graph.drift_events) == 5

    print(f"✓ Gradual accumulation: {graph.epistemic_drift_score:.3f} (5 events)")


if __name__ == "__main__":
    print("Running drift accumulation tests...\n")

    test_calculate_drift_magnitude()
    test_accumulate_drift()
    test_drift_velocity()
    test_drift_decay()
    test_recovery_detection()
    test_migration()
    test_gradual_accumulation()

    print("\n✅ All tests passed!")
