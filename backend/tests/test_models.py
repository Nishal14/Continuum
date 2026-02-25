"""Tests for Pydantic models."""

import pytest
from datetime import datetime
from app.models import (
    Turn,
    Commitment,
    CommitmentGraph,
    Alert,
    Edge
)


def test_turn_creation():
    """Test Turn model creation."""
    turn = Turn(
        id=1,
        speaker="user",
        text="Hello world",
        ts=datetime.now()
    )

    assert turn.id == 1
    assert turn.speaker == "user"
    assert turn.text == "Hello world"


def test_commitment_creation():
    """Test Commitment model creation."""
    commitment = Commitment(
        id="c1",
        turn_id=1,
        kind="claim",
        normalized="Python is great",
        polarity="positive",
        confidence=0.9,
        timestamp=datetime.now()
    )

    assert commitment.id == "c1"
    assert commitment.kind == "claim"
    assert commitment.confidence == 0.9


def test_commitment_graph_hash():
    """Test graph hash computation."""
    graph = CommitmentGraph(
        conversation_id="test123",
        turns=[
            Turn(id=1, speaker="user", text="Hi", ts=datetime.now())
        ]
    )

    hash1 = graph.compute_hash()
    assert isinstance(hash1, str)
    assert len(hash1) == 64  # SHA256 hex length

    # Same graph should produce same hash
    hash2 = graph.compute_hash()
    assert hash1 == hash2

    # Different graph should produce different hash
    graph.turns.append(Turn(id=2, speaker="model", text="Hello", ts=datetime.now()))
    hash3 = graph.compute_hash()
    assert hash1 != hash3


def test_commitment_graph_get_methods():
    """Test graph lookup methods."""
    now = datetime.now()
    commitment = Commitment(
        id="c1",
        turn_id=1,
        kind="claim",
        normalized="test",
        timestamp=now
    )

    turn = Turn(id=1, speaker="user", text="test", ts=now)

    graph = CommitmentGraph(
        conversation_id="test",
        turns=[turn],
        commitments=[commitment]
    )

    assert graph.get_commitment("c1") == commitment
    assert graph.get_commitment("c2") is None

    assert graph.get_turn(1) == turn
    assert graph.get_turn(999) is None


def test_alert_creation():
    """Test Alert model creation."""
    alert = Alert(
        id="a1",
        severity="high",
        alert_type="polarity_flip",
        message="Contradiction detected",
        related_commitments=["c1", "c2"],
        related_turns=[1, 2],
        detected_at_turn=2,
        timestamp=datetime.now()
    )

    assert alert.severity == "high"
    assert alert.alert_type == "polarity_flip"
    assert len(alert.related_commitments) == 2
