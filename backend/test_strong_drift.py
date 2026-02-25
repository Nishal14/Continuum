"""
Create a conversation with STRONG contradictions to trigger drift detection.
"""

import requests
from datetime import datetime

API_BASE = "http://localhost:8000"

def create_strong_contradiction():
    """Create obvious contradictions."""

    conversation_id = "strong-drift-demo"

    # Much more obvious contradictions
    turns = [
        ("user", "Python is definitely the best language for everything."),
        ("model", "Python is indeed very versatile."),
        ("user", "Actually, I disagree. Python is not good at all."),
        ("model", "That's quite a shift in opinion."),
        ("user", "Yes, I now think Python is the worst language."),
        ("model", "Can you clarify what changed your mind?"),
    ]

    print(f"Creating conversation: {conversation_id}")
    print("=" * 60)

    for turn_id, (speaker, text) in enumerate(turns, start=1):
        print(f"\nTurn {turn_id} ({speaker}): {text}")

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
                print(f"  [OK] {len(alerts)} alerts")

                if alerts:
                    for alert in alerts:
                        print(f"    - {alert['severity'].upper()}: {alert['message'][:60]}")
            else:
                print(f"  [ERROR] {response.status_code}")

        except Exception as e:
            print(f"  [ERROR] {e}")

    # Get metrics
    print("\n" + "=" * 60)
    try:
        response = requests.get(f"{API_BASE}/conversations/{conversation_id}/metrics")
        if response.ok:
            metrics = response.json()
            drift = metrics.get('drift', {})
            print(f"\nDrift Score: {drift.get('cumulative_drift_score', 0):.3f}")
            print(f"Drift Events: {drift.get('total_drift_events', 0)}")
            print(f"Contradictions: {metrics.get('contradictions', {}).get('count', 0)}")
            print(f"\n[SUCCESS] ID: {conversation_id}")
        else:
            print(f"[ERROR] {response.status_code}")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    print("\n[START] Creating strong contradictions...\n")
    create_strong_contradiction()
    print("\n[DONE]\n")
