"""
Phase 3 tests for K2 integration.

Tests K2 as primary reasoning engine with heuristic fallback.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from app.models import CommitmentGraph, Turn
from app.analyzer import analyze_turn_k2_first, generate_k2_reconciliation
from app.k2_client import K2Client


@pytest.mark.asyncio
async def test_k2_extraction_success():
    """Test successful K2 claim extraction."""
    graph = CommitmentGraph(conversation_id="test_k2")
    turn = Turn(
        id=1,
        speaker="user",
        text="Python is the best programming language",
        ts=datetime.now()
    )
    graph.turns.append(turn)

    # Mock K2 response
    mock_k2_claims = [
        {
            "claim": "Python is the best programming language",
            "polarity": "positive",
            "confidence": 0.9,
            "assumptions": ["for general purpose programming"]
        }
    ]

    with patch.object(K2Client, 'extract_structured_commitments', new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = mock_k2_claims

        alerts, commitments, edges, metadata = await analyze_turn_k2_first(graph, turn)

        # Verify K2 was used
        assert metadata["engine_used"] == "k2"
        assert metadata["k2_extraction_success"] is True
        assert metadata["k2_calls"] == 1

        # Verify commitment created
        assert len(commitments) == 1
        assert commitments[0].normalized == "Python is the best programming language"
        assert commitments[0].polarity == "positive"
        assert commitments[0].confidence == 0.9


@pytest.mark.asyncio
async def test_k2_extraction_failure_fallback():
    """Test fallback to heuristics when K2 fails."""
    graph = CommitmentGraph(conversation_id="test_fallback")
    turn = Turn(
        id=1,
        speaker="user",
        text="I think TypeScript is better than JavaScript",
        ts=datetime.now()
    )
    graph.turns.append(turn)

    # Mock K2 failure
    with patch.object(K2Client, 'extract_structured_commitments', new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = None  # K2 failed

        alerts, commitments, edges, metadata = await analyze_turn_k2_first(graph, turn)

        # Verify fallback to heuristics
        assert metadata["engine_used"] == "heuristic_fallback"
        assert metadata["k2_extraction_success"] is False

        # Heuristics should still extract something
        assert len(commitments) >= 1


@pytest.mark.asyncio
async def test_k2_verification_override():
    """Test K2 overriding heuristic contradiction detection."""
    graph = CommitmentGraph(conversation_id="test_override")

    # Add first turn with commitment
    turn1 = Turn(id=1, speaker="user", text="Python is great for data science", ts=datetime.now())
    graph.turns.append(turn1)

    # Mock K2 extraction for first turn
    mock_k2_claims_1 = [
        {
            "claim": "Python is great for data science",
            "polarity": "positive",
            "confidence": 0.9,
            "assumptions": []
        }
    ]

    with patch.object(K2Client, 'extract_structured_commitments', new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = mock_k2_claims_1
        alerts1, commitments1, edges1, metadata1 = await analyze_turn_k2_first(graph, turn1)
        graph.commitments.extend(commitments1)

    # Add second turn that SEEMS contradictory
    turn2 = Turn(id=2, speaker="user", text="Python has some limitations for data science", ts=datetime.now())
    graph.turns.append(turn2)

    mock_k2_claims_2 = [
        {
            "claim": "Python has some limitations for data science",
            "polarity": "neutral",  # Not directly opposite
            "confidence": 0.8,
            "assumptions": []
        }
    ]

    # Mock K2 verification saying it's a refinement, not contradiction
    mock_verification = {
        "is_contradiction": False,
        "type": "contextual_refinement",
        "confidence": 0.85,
        "explanation": "This is a nuanced refinement, not a direct contradiction"
    }

    with patch.object(K2Client, 'extract_structured_commitments', new_callable=AsyncMock) as mock_extract, \
         patch.object(K2Client, 'verify_contradiction', new_callable=AsyncMock) as mock_verify:

        mock_extract.return_value = mock_k2_claims_2
        mock_verify.return_value = mock_verification

        alerts2, commitments2, edges2, metadata2 = await analyze_turn_k2_first(graph, turn2)

        # K2 should have overridden the heuristic
        assert metadata2["k2_verification_used"] is True
        # Should have 1 override event if heuristic detected contradiction
        # Alert might be downgraded or removed entirely


@pytest.mark.asyncio
async def test_k2_verification_confirms():
    """Test K2 confirming heuristic contradiction detection."""
    graph = CommitmentGraph(conversation_id="test_confirm")

    # Add first commitment manually
    from app.models import Commitment
    c1 = Commitment(
        id="c1",
        turn_id=1,
        kind="claim",
        normalized="Python is slow",
        polarity="negative",
        confidence=0.8,
        timestamp=datetime.now(),
        active=True
    )
    graph.commitments.append(c1)

    turn1 = Turn(id=1, speaker="user", text="Python is slow", ts=datetime.now())
    graph.turns.append(turn1)

    # Add contradictory turn
    turn2 = Turn(id=2, speaker="user", text="Actually Python is very fast", ts=datetime.now())
    graph.turns.append(turn2)

    mock_k2_claims_2 = [
        {
            "claim": "Python is very fast",
            "polarity": "positive",
            "confidence": 0.9,
            "assumptions": []
        }
    ]

    # Mock K2 verification confirming contradiction
    mock_verification = {
        "is_contradiction": True,
        "type": "direct_contradiction",
        "confidence": 0.95,
        "explanation": "Direct contradiction of performance claim"
    }

    with patch.object(K2Client, 'extract_structured_commitments', new_callable=AsyncMock) as mock_extract, \
         patch.object(K2Client, 'verify_contradiction', new_callable=AsyncMock) as mock_verify:

        mock_extract.return_value = mock_k2_claims_2
        mock_verify.return_value = mock_verification

        alerts, commitments, edges, metadata = await analyze_turn_k2_first(graph, turn2)

        # K2 should confirm contradiction
        assert metadata["k2_verification_used"] is True

        # Should have alert with K2 verification
        assert len(alerts) > 0
        assert "K2 verified" in alerts[0].message or "direct_contradiction" in alerts[0].message


@pytest.mark.asyncio
async def test_k2_reconciliation_generation():
    """Test K2 generating reconciliation."""
    graph = CommitmentGraph(conversation_id="test_reconcile")

    # Create alert with commitments
    from app.models import Commitment, Alert

    c1 = Commitment(
        id="c1",
        turn_id=1,
        kind="claim",
        normalized="Machine learning requires large datasets",
        polarity="positive",
        confidence=0.8,
        timestamp=datetime.now()
    )

    c2 = Commitment(
        id="c2",
        turn_id=2,
        kind="claim",
        normalized="Machine learning works with small datasets now",
        polarity="positive",
        confidence=0.9,
        timestamp=datetime.now()
    )

    graph.commitments.extend([c1, c2])

    alert = Alert(
        id="a1",
        severity="medium",
        alert_type="polarity_flip",
        message="Contradiction detected",
        related_commitments=["c1", "c2"],
        related_turns=[1, 2],
        detected_at_turn=2,
        timestamp=datetime.now()
    )

    graph.alerts.append(alert)

    turn1 = Turn(id=1, speaker="user", text="ML needs big data", ts=datetime.now())
    turn2 = Turn(id=2, speaker="user", text="ML works with small data now", ts=datetime.now())
    graph.turns.extend([turn1, turn2])

    # Mock K2 reconciliation
    mock_reconciliation = {
        "reconciliation": "Earlier you noted that machine learning requires large datasets. "
                         "Recent advances in few-shot learning and transfer learning have indeed "
                         "made it possible to achieve good results with smaller datasets.",
        "confidence": 0.9
    }

    with patch.object(K2Client, 'generate_reconciliation', new_callable=AsyncMock) as mock_reconcile:
        mock_reconcile.return_value = mock_reconciliation

        reconciliation_text, k2_used = await generate_k2_reconciliation(graph, alert)

        # K2 should be used
        assert k2_used is True
        assert "Earlier you noted" in reconciliation_text
        assert "few-shot learning" in reconciliation_text


@pytest.mark.asyncio
async def test_fallback_when_k2_fails():
    """Test system continues working when K2 is unavailable."""
    graph = CommitmentGraph(conversation_id="test_resilience")
    turn = Turn(
        id=1,
        speaker="user",
        text="Rust is better than C++ for systems programming",
        ts=datetime.now()
    )
    graph.turns.append(turn)

    # Mock K2 complete failure (None responses)
    with patch.object(K2Client, 'extract_structured_commitments', new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = None  # Total failure

        alerts, commitments, edges, metadata = await analyze_turn_k2_first(graph, turn)

        # Should fallback to heuristics
        assert metadata["engine_used"] == "heuristic_fallback"

        # Should still extract commitments
        assert len(commitments) > 0


@pytest.mark.asyncio
async def test_k2_client_timeout():
    """Test K2 client timeout handling."""
    import asyncio

    # Create client with mock API key
    client = K2Client(api_key="test_key")

    # Mock timeout - need to mock the entire async context manager
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client_instance = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client_instance
        mock_client_class.return_value.__aexit__.return_value = None

        # Make the post call timeout
        mock_post = AsyncMock()
        mock_post.side_effect = asyncio.TimeoutError()
        mock_client_instance.post = mock_post

        result = await client.extract_structured_commitments("Test text")

        # Should return None on timeout
        assert result is None

        # Should increment failure count
        assert client.failure_count > 0


def test_k2_client_stats():
    """Test K2 client statistics tracking."""
    client = K2Client()

    # Simulate some calls
    client.call_count = 10
    client.failure_count = 2

    stats = client.get_stats()

    assert stats["total_calls"] == 10
    assert stats["failures"] == 2
    assert stats["success_rate"] == 0.8
