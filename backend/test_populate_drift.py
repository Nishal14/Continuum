"""
Quick test script to populate backend with drift data.

Run this to create a conversation with drift events so you can test the visualization.
"""

import requests
import json
from datetime import datetime

API_BASE = "http://localhost:8000"

def create_conversation_with_drift():
    """Create a test conversation with gradual drift."""

    conversation_id = "test-drift-demo"

    # Test turns showing gradual drift
    turns = [
        ("user", "I think Python is the best language for data science."),
        ("model", "Yes, Python has excellent libraries like pandas and numpy."),
        ("user", "Although Python is good, I'm noticing some performance issues."),
        ("model", "Performance can be a concern, but usually it's manageable."),
        ("user", "Actually, the performance issues are becoming more problematic."),
        ("model", "Have you considered using PyPy or Cython for optimization?"),
        ("user", "I've tried those, but they don't really solve the core problems."),
        ("model", "What specific problems are you encountering?"),
        ("user", "Python's GIL makes it terrible for concurrent programming."),
        ("model", "The GIL is a known limitation for CPU-bound multithreading."),
    ]

    print(f"Creating conversation: {conversation_id}")
    print("=" * 60)

    for turn_id, (speaker, text) in enumerate(turns, start=1):
        print(f"\nTurn {turn_id} ({speaker}): {text[:50]}...")

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
            response = requests.post(
                f"{API_BASE}/analyze-turn",
                json=payload,
                timeout=10
            )

            if response.ok:
                data = response.json()
                alerts = data.get("alerts", [])
                print(f"  [OK] Analyzed - {len(alerts)} alerts")

                if alerts:
                    for alert in alerts:
                        print(f"    - {alert['severity'].upper()}: {alert['alert_type']}")
            else:
                print(f"  [ERROR] Status: {response.status_code}")
                print(f"    {response.text}")

        except Exception as e:
            print(f"  [ERROR] Failed: {e}")

    # Get final metrics
    print("\n" + "=" * 60)
    print("FINAL METRICS")
    print("=" * 60)

    try:
        response = requests.get(f"{API_BASE}/conversations/{conversation_id}/metrics")
        if response.ok:
            metrics = response.json()

            print(f"\n[DRIFT] Metrics:")
            drift = metrics.get('drift', {})
            print(f"  Cumulative Score: {drift.get('cumulative_drift_score', 0):.3f}")
            print(f"  Drift Velocity: {drift.get('drift_velocity', 0):.3f}")
            print(f"  Total Events: {drift.get('total_drift_events', 0)}")
            print(f"  Recovering: {drift.get('is_recovering', False)}")

            print(f"\n[COMMITMENTS]:")
            commitments = metrics.get('commitments', {})
            print(f"  Total: {commitments.get('total', 0)}")
            print(f"  Active: {commitments.get('active', 0)}")

            print(f"\n[CONTRADICTIONS]:")
            contradictions = metrics.get('contradictions', {})
            print(f"  Count: {contradictions.get('count', 0)}")

            print(f"\n[ESCALATION]:")
            escalation = metrics.get('escalation', {})
            print(f"  Total: {escalation.get('total_escalations', 0)}")
            print(f"  Rate: {escalation.get('escalation_rate', 0):.2%}")

            print(f"\n[SUCCESS] Conversation ready for visualization!")
            print(f"   ID: {conversation_id}")

        else:
            print(f"Failed to get metrics: {response.status_code}")

    except Exception as e:
        print(f"Failed to get metrics: {e}")


if __name__ == "__main__":
    print("\n[START] Populating backend with drift data...\n")
    create_conversation_with_drift()
    print("\n[DONE] Reload extension to see the visualization.\n")
