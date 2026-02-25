"""
Create ONE conversation with MANY contradictions to build up drift score.
"""

import requests
from datetime import datetime

API_BASE = "http://localhost:8000"

def create_accumulating_drift():
    """Create one conversation with escalating contradictions."""

    conversation_id = "visual-test-drift"

    # Progressive contradictions on different topics
    turns = [
        # Topic 1: Python (3 flips)
        ("user", "Python is the best language ever created."),
        ("model", "Python is indeed very popular."),
        ("user", "Actually, I disagree completely. Python is terrible."),
        ("model", "That's quite a change of opinion."),
        ("user", "Yes, Python is absolutely the worst language."),
        ("model", "Can you explain what changed?"),

        # Topic 2: JavaScript (3 flips)
        ("user", "JavaScript is excellent for modern web development."),
        ("model", "JavaScript has evolved significantly."),
        ("user", "No wait, JavaScript is completely broken and unusable."),
        ("model", "That seems contradictory to what you just said."),
        ("user", "JavaScript is the worst thing that ever happened to the web."),
        ("model", "You seem to have very strong shifting opinions."),

        # Topic 3: Databases (2 flips)
        ("user", "SQL databases are clearly superior to NoSQL."),
        ("model", "SQL has its strengths."),
        ("user", "Actually SQL is outdated garbage. NoSQL is far better."),
        ("model", "Your stance keeps changing."),
    ]

    print(f"Creating conversation: {conversation_id}")
    print("=" * 60)

    for turn_id, (speaker, text) in enumerate(turns, start=1):
        print(f"\nTurn {turn_id}: {text[:50]}")

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
                    print(f"  -> {len(alerts)} alerts: {alerts[0]['severity'].upper()}")
                else:
                    print(f"  -> OK")
            else:
                print(f"  -> ERROR {response.status_code}")

        except Exception as e:
            print(f"  -> ERROR: {e}")

    # Get final metrics
    print("\n" + "=" * 60)
    print("FINAL METRICS")
    print("=" * 60)

    try:
        response = requests.get(f"{API_BASE}/conversations/{conversation_id}/metrics")
        if response.ok:
            metrics = response.json()
            drift = metrics.get('drift', {})

            print(f"\n*** DRIFT METRICS ***")
            print(f"Cumulative Score: {drift.get('cumulative_drift_score', 0):.3f}")
            print(f"Drift Velocity: {drift.get('drift_velocity', 0):.3f}")
            print(f"Total Events: {drift.get('total_drift_events', 0)}")
            print(f"Contradictions: {metrics.get('contradictions', {}).get('count', 0)}")
            print(f"Active Commitments: {metrics.get('commitments', {}).get('active', 0)}")

            score = drift.get('cumulative_drift_score', 0)
            if score > 2.0:
                print(f"\n*** ESCALATION TRIGGERED! *** (score > 2.0)")
                print("Open extension to see RED GLOW + PULSE + CARD!")
            elif score > 1.0:
                print(f"\n*** Building tension *** (score > 1.0)")
                print("Open extension to see YELLOW bar")
            else:
                print(f"\n*** Stable/Low drift *** (score < 1.0)")
                print("Open extension to see GREEN bar")

            print(f"\n[SUCCESS] Conversation ID: {conversation_id}")
        else:
            print(f"[ERROR] {response.status_code}")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    print("\n[START] Creating conversation with multiple contradictions...\n")
    create_accumulating_drift()
    print("\n[DONE]\n")
