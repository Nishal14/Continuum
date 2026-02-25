"""End-to-end tests with demo transcripts."""

import pytest
import json
from pathlib import Path
from datetime import datetime
from app.models import CommitmentGraph, Turn
from app.heuristics import analyze_turn_heuristics


def load_transcript(name: str):
    """Load a demo transcript."""
    transcript_path = Path(__file__).parent.parent.parent / "demo-transcripts" / name
    with open(transcript_path) as f:
        return json.load(f)


def test_simple_flip_scenario():
    """Test detection of simple polarity flip (demo transcript 1)."""
    transcript = load_transcript("01_simple_flip.json")

    graph = CommitmentGraph(conversation_id="test_flip")

    all_alerts = []

    # Process each turn
    for turn_data in transcript["turns"]:
        turn = Turn(
            id=turn_data["id"],
            speaker=turn_data["speaker"],
            text=turn_data["text"],
            ts=datetime.fromisoformat(turn_data["ts"].replace("Z", "+00:00"))
        )

        graph.turns.append(turn)

        # Analyze turn
        alerts, commitments, edges = analyze_turn_heuristics(graph, turn)

        graph.commitments.extend(commitments)
        graph.edges.extend(edges)
        graph.alerts.extend(alerts)

        all_alerts.extend(alerts)

    # Should detect at least one alert
    assert len(all_alerts) > 0

    # Should have extracted commitments
    assert len(graph.commitments) >= 2

    print(f"\n[OK] Simple flip test passed: {len(all_alerts)} alerts detected")
    for alert in all_alerts:
        print(f"  - {alert.alert_type}: {alert.message}")


def test_assumption_drop_scenario():
    """Test detection of assumption drop (demo transcript 2)."""
    transcript = load_transcript("02_assumption_drop.json")

    graph = CommitmentGraph(conversation_id="test_assumption")

    all_alerts = []

    for turn_data in transcript["turns"]:
        turn = Turn(
            id=turn_data["id"],
            speaker=turn_data["speaker"],
            text=turn_data["text"],
            ts=datetime.fromisoformat(turn_data["ts"].replace("Z", "+00:00"))
        )

        graph.turns.append(turn)

        alerts, commitments, edges = analyze_turn_heuristics(graph, turn)

        graph.commitments.extend(commitments)
        graph.edges.extend(edges)
        graph.alerts.extend(alerts)

        all_alerts.extend(alerts)

    # Should have extracted some commitments
    assert len(graph.commitments) > 0

    print(f"\n[OK] Assumption drop test passed: {len(all_alerts)} alerts detected")
    for alert in all_alerts:
        print(f"  - {alert.alert_type}: {alert.message}")


def test_false_reconciliation_scenario():
    """Test detection of false reconciliation (demo transcript 3)."""
    transcript = load_transcript("03_false_reconciliation.json")

    graph = CommitmentGraph(conversation_id="test_false_recon")

    all_alerts = []

    for turn_data in transcript["turns"]:
        turn = Turn(
            id=turn_data["id"],
            speaker=turn_data["speaker"],
            text=turn_data["text"],
            ts=datetime.fromisoformat(turn_data["ts"].replace("Z", "+00:00"))
        )

        graph.turns.append(turn)

        alerts, commitments, edges = analyze_turn_heuristics(graph, turn)

        graph.commitments.extend(commitments)
        graph.edges.extend(edges)
        graph.alerts.extend(alerts)

        all_alerts.extend(alerts)

    # Should detect contradictions
    assert len(all_alerts) > 0

    print(f"\n[OK] False reconciliation test passed: {len(all_alerts)} alerts detected")
    for alert in all_alerts:
        print(f"  - {alert.alert_type}: {alert.message}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
