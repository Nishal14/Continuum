"""
Phase 2 tests for epistemic state modeling and metrics.

Tests the new features added in Phase 2:
- Commitment lifecycle management (active/inactive states)
- Epistemic metrics computation
- Longitudinal contradiction detection
"""

import pytest
from datetime import datetime
from app.models import (
    CommitmentGraph,
    Commitment,
    Turn,
    Edge,
    Alert
)
from app.metrics import compute_epistemic_metrics
from app.heuristics import detect_polarity_flip


def test_commitment_lifecycle():
    """Test commitment deactivation and lifecycle management."""
    # Setup graph with multiple commitments
    graph = CommitmentGraph(conversation_id="test_lifecycle")

    c1 = Commitment(
        id="c1",
        turn_id=1,
        kind="claim",
        normalized="Python is slow",
        polarity="negative",
        timestamp=datetime.now(),
        active=True
    )

    c2 = Commitment(
        id="c2",
        turn_id=2,
        kind="claim",
        normalized="Python is fast with optimization",
        polarity="positive",
        timestamp=datetime.now(),
        active=True
    )

    graph.commitments = [c1, c2]

    # Test initial state
    assert len(graph.get_active_commitments()) == 2
    assert c1.active is True
    assert c1.overridden_by is None

    # Deactivate c1, overridden by c2
    graph.deactivate_commitment("c1", "c2")

    # Verify state changes
    assert c1.active is False
    assert c1.overridden_by == "c2"
    assert len(graph.get_active_commitments()) == 1
    assert graph.get_active_commitments()[0].id == "c2"


def test_metrics_computation():
    """Test epistemic metrics computation."""
    # Setup graph with varied state
    graph = CommitmentGraph(conversation_id="test_metrics")

    # Add turns
    graph.turns = [
        Turn(id=1, speaker="user", text="I think X", ts=datetime.now()),
        Turn(id=2, speaker="model", text="I agree with X", ts=datetime.now()),
        Turn(id=3, speaker="user", text="Actually, not X", ts=datetime.now())
    ]

    # Add commitments with different states
    c1 = Commitment(
        id="c1",
        turn_id=1,
        kind="claim",
        normalized="X is true",
        polarity="positive",
        confidence=0.8,
        timestamp=datetime.now(),
        active=True,
        stability_score=1.0
    )

    c2 = Commitment(
        id="c2",
        turn_id=2,
        kind="claim",
        normalized="X is true",
        polarity="positive",
        confidence=0.9,
        timestamp=datetime.now(),
        active=True,
        stability_score=0.9
    )

    c3 = Commitment(
        id="c3",
        turn_id=3,
        kind="claim",
        normalized="X is false",
        polarity="negative",
        confidence=0.7,
        timestamp=datetime.now(),
        active=True,
        stability_score=0.6,
        contradicted_by=["c1", "c2"]
    )

    graph.commitments = [c1, c2, c3]

    # Add contradiction edge
    graph.edges = [
        Edge(source="c3", target="c1", relation="contradicts", weight=0.8)
    ]

    # Add alert
    graph.alerts = [
        Alert(
            id="a1",
            severity="high",
            alert_type="polarity_flip",
            message="Test flip",
            related_commitments=["c1", "c3"],
            related_turns=[1, 3],
            detected_at_turn=3,
            timestamp=datetime.now()
        )
    ]

    # Compute metrics
    metrics = compute_epistemic_metrics(graph)

    # Verify metrics structure
    assert metrics["conversation_id"] == "test_metrics"
    assert metrics["commitments"]["total"] == 3
    assert metrics["commitments"]["active"] == 3
    assert metrics["commitments"]["inactive"] == 0

    assert metrics["contradictions"]["count"] == 1
    assert metrics["contradictions"]["rate"] == pytest.approx(1/3, abs=0.01)

    # Average stability: (1.0 + 0.9 + 0.6) / 3 = 0.833
    assert metrics["stability"]["average"] == pytest.approx(0.833, abs=0.01)
    assert metrics["stability"]["minimum"] == 0.6

    assert metrics["alerts"]["total"] == 1
    assert metrics["alerts"]["by_type"]["polarity_flip"] == 1
    assert metrics["alerts"]["by_severity"]["high"] == 1

    assert metrics["turns_analyzed"] == 3
    assert "health_score" in metrics
    assert 0 <= metrics["health_score"] <= 100


def test_longitudinal_contradiction():
    """Test that polarity_flip only checks last 5 active commitments."""
    # Setup graph with many commitments
    graph = CommitmentGraph(conversation_id="test_longitudinal")

    # Add 10 turns
    for i in range(1, 11):
        graph.turns.append(
            Turn(id=i, speaker="user" if i % 2 == 1 else "model",
                 text=f"Statement {i}", ts=datetime.now())
        )

    # Add 10 commitments, all active
    # First 5 say "The sky is blue and beautiful"
    # Last 5 say "Completely different unrelated topic here"
    for i in range(1, 11):
        c = Commitment(
            id=f"c{i}",
            turn_id=i,
            kind="claim",
            normalized="The sky is blue and beautiful" if i <= 5 else "Completely different unrelated topic here",
            polarity="positive",
            confidence=0.8,
            timestamp=datetime.now(),
            active=True,
            stability_score=1.0
        )
        graph.commitments.append(c)

    # Create new commitment contradicting the OLD commitments (c1-c5)
    # But c1-c5 will be deactivated, so should NOT detect
    new_commitment = Commitment(
        id="c11",
        turn_id=11,
        kind="claim",
        normalized="The sky is blue and beautiful",  # Same as c1-c5
        polarity="negative",  # Opposite polarity
        confidence=0.9,
        timestamp=datetime.now(),
        active=True,
        stability_score=1.0
    )

    # Deactivate c1-c5 (older commitments)
    for i in range(1, 6):
        graph.commitments[i-1].active = False

    # Now the last 5 active commitments are c6-c10
    # c6-c10 have "Completely different unrelated topic", so should NOT detect contradiction
    alert = detect_polarity_flip(graph, new_commitment)

    # Should be None because c1-c5 are inactive (even though they match)
    assert alert is None, "Should not detect contradiction beyond last 5 active commitments"

    # Now test that it DOES detect within the window
    # Re-activate c5 and change its content to match new_commitment
    graph.commitments[4].active = True
    graph.commitments[4].normalized = "The sky is blue and beautiful"
    graph.commitments[4].polarity = "positive"  # Opposite from new_commitment
    graph.commitments[4].turn_id = 9  # Make it recent enough to be in last 5

    # Add turn 11 for new_commitment
    graph.turns.append(
        Turn(id=11, speaker="user", text="Statement 11", ts=datetime.now())
    )

    # Now detect with new_commitment
    alert = detect_polarity_flip(graph, new_commitment)

    # Now should detect because c5 is active and within last 5
    assert alert is not None, "Should detect contradiction within last 5 active commitments"
    assert alert.alert_type == "polarity_flip"


def test_dynamic_severity_scoring():
    """Test that severity is computed based on similarity, confidence, and recency."""
    graph = CommitmentGraph(conversation_id="test_severity")

    # Add turns (make them close together for high recency)
    graph.turns = [
        Turn(id=1, speaker="user", text="I believe Python is the best language for data science", ts=datetime.now()),
        Turn(id=2, speaker="user", text="Actually Python is not good for data science", ts=datetime.now())
    ]

    # High confidence, high similarity (same words), recent = should be critical/high severity
    c1 = Commitment(
        id="c1",
        turn_id=1,
        kind="claim",
        normalized="Python is the best language for data science projects",  # Long similar text
        polarity="positive",
        confidence=0.95,  # High confidence
        timestamp=datetime.now(),
        active=True,
        stability_score=1.0
    )

    c2 = Commitment(
        id="c2",
        turn_id=2,
        kind="claim",
        normalized="Python is not good for data science projects",  # Very similar, mostly same words
        polarity="negative",
        confidence=0.90,  # High confidence
        timestamp=datetime.now(),
        active=True,
        stability_score=1.0
    )

    graph.commitments = [c1, c2]

    alert = detect_polarity_flip(graph, c2)

    # Should produce medium or higher severity due to high similarity + confidence + recency
    assert alert is not None
    assert alert.severity in ["medium", "high", "critical"], f"Got severity: {alert.severity}, message: {alert.message}"

    # Verify stability scores were updated (reduced)
    assert c1.stability_score < 1.0, f"c1 stability should be reduced, got {c1.stability_score}"
    assert c2.stability_score < 1.0, f"c2 stability should be reduced, got {c2.stability_score}"

    # Verify contradiction was marked
    assert len(c2.contradicted_by) > 0, "c2 should have contradicted_by list populated"


def test_count_contradictions():
    """Test the count_contradictions helper method."""
    graph = CommitmentGraph(conversation_id="test_count")

    # Add edges with different relations
    graph.edges = [
        Edge(source="c1", target="c2", relation="contradicts", weight=0.8),
        Edge(source="c3", target="c4", relation="supports", weight=0.9),
        Edge(source="c5", target="c6", relation="contradicts", weight=0.7),
        Edge(source="c7", target="c8", relation="depends_on", weight=0.6),
    ]

    # Should count only "contradicts" relations
    assert graph.count_contradictions() == 2
