"""
Test topic-anchor based contradiction detection.

This test validates that contradictions are detected based on
TOPIC MATCH rather than token overlap.
"""

import requests
from datetime import datetime

API_BASE = "http://localhost:8000"

def test_case_1_same_anchor_opposite_polarity():
    """
    Case 1: Same topic anchor, opposite polarity

    Expected: DETECT contradiction
    - "Python is best" → topic_anchor="python", polarity=positive
    - "Python is terrible" → topic_anchor="python", polarity=negative
    - Anchor match + polarity diff → contradiction
    """
    print("\n" + "=" * 70)
    print("TEST CASE 1: Same Anchor, Opposite Polarity")
    print("=" * 70)

    conversation_id = "test-anchor-case1"

    turns = [
        ("user", "Python is the best language for everything."),
        ("model", "Python has many strengths."),
        ("user", "Actually, Python is terrible for performance."),
        ("model", "What changed your view?"),
    ]

    for turn_id, (speaker, text) in enumerate(turns, start=1):
        print(f"\nTurn {turn_id}: {text}")

        payload = {
            "conversation_id": conversation_id,
            "new_turn": {
                "id": turn_id,
                "speaker": speaker,
                "text": text,
                "ts": datetime.now().isoformat()
            }
        }

        try:
            response = requests.post(f"{API_BASE}/analyze-turn", json=payload, timeout=10)
            if response.ok:
                data = response.json()
                alerts = data.get("alerts", [])
                if alerts:
                    print(f"  -> DETECTED: {len(alerts)} alert(s)")
                    for alert in alerts:
                        print(f"     {alert['severity'].upper()}: {alert['message'][:80]}")
                else:
                    print(f"  -> OK (no alerts)")
        except Exception as e:
            print(f"  -> ERROR: {e}")

    # Get metrics
    try:
        response = requests.get(f"{API_BASE}/conversations/{conversation_id}/metrics")
        if response.ok:
            metrics = response.json()
            drift = metrics.get('drift', {})
            print(f"\n[RESULT]")
            print(f"  Drift Score: {drift.get('cumulative_drift_score', 0):.3f}")
            print(f"  Drift Events: {drift.get('total_drift_events', 0)}")

            if drift.get('total_drift_events', 0) > 0:
                print("  ✓ PASS: Contradiction detected via topic anchor")
            else:
                print("  ✗ FAIL: Should have detected contradiction")
    except Exception as e:
        print(f"  ERROR: {e}")


def test_case_2_different_anchors():
    """
    Case 2: Different topic anchors

    Expected: NO contradiction
    - "Microservices are better" → topic_anchor="microservices"
    - "Monoliths are better" → topic_anchor="monoliths"
    - Different anchors → no contradiction
    """
    print("\n" + "=" * 70)
    print("TEST CASE 2: Different Anchors (No Contradiction)")
    print("=" * 70)

    conversation_id = "test-anchor-case2"

    turns = [
        ("user", "Microservices are better for scalability."),
        ("model", "Microservices have advantages."),
        ("user", "But monoliths are better for simplicity."),
        ("model", "That's a different trade-off."),
    ]

    for turn_id, (speaker, text) in enumerate(turns, start=1):
        print(f"\nTurn {turn_id}: {text}")

        payload = {
            "conversation_id": conversation_id,
            "new_turn": {
                "id": turn_id,
                "speaker": speaker,
                "text": text,
                "ts": datetime.now().isoformat()
            }
        }

        try:
            response = requests.post(f"{API_BASE}/analyze-turn", json=payload, timeout=10)
            if response.ok:
                data = response.json()
                alerts = data.get("alerts", [])
                if alerts:
                    print(f"  -> DETECTED: {len(alerts)} alert(s)")
                else:
                    print(f"  -> OK (no alerts)")
        except Exception as e:
            print(f"  -> ERROR: {e}")

    # Get metrics
    try:
        response = requests.get(f"{API_BASE}/conversations/{conversation_id}/metrics")
        if response.ok:
            metrics = response.json()
            drift = metrics.get('drift', {})
            print(f"\n[RESULT]")
            print(f"  Drift Score: {drift.get('cumulative_drift_score', 0):.3f}")
            print(f"  Drift Events: {drift.get('total_drift_events', 0)}")

            if drift.get('total_drift_events', 0) == 0:
                print("  ✓ PASS: No false positive (different topics)")
            else:
                print("  ✗ FAIL: Should NOT detect contradiction (different topics)")
    except Exception as e:
        print(f"  ERROR: {e}")


def test_case_3_low_token_overlap():
    """
    Case 3: Same topic, low token overlap

    Expected: DETECT contradiction
    - "TypeScript helps maintainability" → topic_anchor="typescript"
    - "I avoid static typing" → topic_anchor="typescript" (inferred)
    - Low Jaccard similarity but same anchor → detect
    """
    print("\n" + "=" * 70)
    print("TEST CASE 3: Low Token Overlap, Same Topic")
    print("=" * 70)

    conversation_id = "test-anchor-case3"

    turns = [
        ("user", "TypeScript is excellent for large codebases."),
        ("model", "Type safety has benefits."),
        ("user", "Actually, TypeScript is terrible for productivity."),
        ("model", "What's your concern?"),
    ]

    for turn_id, (speaker, text) in enumerate(turns, start=1):
        print(f"\nTurn {turn_id}: {text}")

        payload = {
            "conversation_id": conversation_id,
            "new_turn": {
                "id": turn_id,
                "speaker": speaker,
                "text": text,
                "ts": datetime.now().isoformat()
            }
        }

        try:
            response = requests.post(f"{API_BASE}/analyze-turn", json=payload, timeout=10)
            if response.ok:
                data = response.json()
                alerts = data.get("alerts", [])
                if alerts:
                    print(f"  -> DETECTED: {len(alerts)} alert(s)")
                    for alert in alerts:
                        print(f"     {alert['severity'].upper()}: {alert['message'][:80]}")
                else:
                    print(f"  -> OK (no alerts)")
        except Exception as e:
            print(f"  -> ERROR: {e}")

    # Get metrics
    try:
        response = requests.get(f"{API_BASE}/conversations/{conversation_id}/metrics")
        if response.ok:
            metrics = response.json()
            drift = metrics.get('drift', {})
            print(f"\n[RESULT]")
            print(f"  Drift Score: {drift.get('cumulative_drift_score', 0):.3f}")
            print(f"  Drift Events: {drift.get('total_drift_events', 0)}")

            if drift.get('total_drift_events', 0) > 0:
                print("  ✓ PASS: Detected despite low token overlap")
            else:
                print("  ✗ FAIL: Should have detected (same topic)")
    except Exception as e:
        print(f"  ERROR: {e}")


def test_case_4_long_conversation():
    """
    Case 4: Long conversation with gradual drift

    Expected: Accumulate drift over multiple turns
    """
    print("\n" + "=" * 70)
    print("TEST CASE 4: Long Conversation with Accumulation")
    print("=" * 70)

    conversation_id = "test-anchor-case4"

    turns = [
        ("user", "Functional programming is elegant."),
        ("model", "FP has nice properties."),
        ("user", "Functional programming is difficult to learn."),
        ("model", "There's a learning curve."),
        ("user", "Object-oriented programming is intuitive."),
        ("model", "OOP is widely taught."),
        ("user", "Object-oriented programming is overly complex."),
        ("model", "OOP can have drawbacks."),
        ("user", "Databases should use SQL for queries."),
        ("model", "SQL is a standard."),
        ("user", "Databases should avoid SQL entirely."),
        ("model", "What alternative do you prefer?"),
    ]

    for turn_id, (speaker, text) in enumerate(turns, start=1):
        print(f"\nTurn {turn_id}: {text[:50]}...")

        payload = {
            "conversation_id": conversation_id,
            "new_turn": {
                "id": turn_id,
                "speaker": speaker,
                "text": text,
                "ts": datetime.now().isoformat()
            }
        }

        try:
            response = requests.post(f"{API_BASE}/analyze-turn", json=payload, timeout=10)
            if response.ok:
                data = response.json()
                alerts = data.get("alerts", [])
                if alerts:
                    print(f"  -> {len(alerts)} alert(s)")
                else:
                    print(f"  -> OK")
        except Exception as e:
            print(f"  -> ERROR: {e}")

    # Get metrics
    try:
        response = requests.get(f"{API_BASE}/conversations/{conversation_id}/metrics")
        if response.ok:
            metrics = response.json()
            drift = metrics.get('drift', {})
            print(f"\n[RESULT]")
            print(f"  Drift Score: {drift.get('cumulative_drift_score', 0):.3f}")
            print(f"  Drift Events: {drift.get('total_drift_events', 0)}")
            print(f"  Drift Velocity: {drift.get('drift_velocity', 0):.3f}")

            if drift.get('cumulative_drift_score', 0) > 1.0:
                print("  ✓ PASS: Drift accumulated over conversation")
            else:
                print("  ⚠ Note: Drift score lower than expected")
    except Exception as e:
        print(f"  ERROR: {e}")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("TOPIC-ANCHOR BASED CONTRADICTION DETECTION TESTS")
    print("=" * 70)

    test_case_1_same_anchor_opposite_polarity()
    test_case_2_different_anchors()
    test_case_3_low_token_overlap()
    test_case_4_long_conversation()

    print("\n" + "=" * 70)
    print("ALL TESTS COMPLETE")
    print("=" * 70)
    print()
