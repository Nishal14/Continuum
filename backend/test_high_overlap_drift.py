"""
Create conversation with HIGH TOKEN OVERLAP contradictions.

This works around the Jaccard similarity limitation by using
statements that share many common words while still contradicting.
"""

import requests
from datetime import datetime

API_BASE = "http://localhost:8000"

def create_high_overlap_drift():
    """Create contradictions with high token overlap for Jaccard similarity."""

    conversation_id = "high-overlap-drift"

    # Contradictions with MAXIMUM token overlap
    turns = [
        # Python topic - same structure, opposite meaning
        ("user", "Python is an excellent programming language for data science."),
        ("model", "Python has excellent data science libraries."),
        ("user", "Python is not an excellent programming language for data science."),
        ("model", "What changed your view?"),
        ("user", "Python is a terrible programming language for data science."),
        ("model", "Can you explain more?"),

        # JavaScript topic - repeat structure
        ("user", "JavaScript is a good language for web development."),
        ("model", "JavaScript has evolved significantly."),
        ("user", "JavaScript is not a good language for web development."),
        ("model", "That's a change in stance."),
        ("user", "JavaScript is a bad language for web development."),
        ("model", "What led to this conclusion?"),

        # Databases - high overlap
        ("user", "SQL databases are better than NoSQL databases for most applications."),
        ("model", "SQL has strong consistency guarantees."),
        ("user", "SQL databases are not better than NoSQL databases for most applications."),
        ("model", "Your position has shifted."),
        ("user", "SQL databases are worse than NoSQL databases for most applications."),
        ("model", "I see you've reconsidered."),

        # Typing - maximum overlap
        ("user", "Static typing is good for large codebases."),
        ("model", "Static typing provides compile-time safety."),
        ("user", "Static typing is not good for large codebases."),
        ("model", "Your opinion changed."),
        ("user", "Static typing is bad for large codebases."),
        ("model", "What caused this shift?"),
    ]

    print(f"Creating conversation: {conversation_id}")
    print("=" * 60)

    for turn_id, (speaker, text) in enumerate(turns, start=1):
        print(f"\nTurn {turn_id}: {text[:55]}...")

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
                    print(f"  -> {len(alerts)} alert(s): {alerts[0]['severity'].upper()}")
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

            print(f"\n[DRIFT METRICS]")
            print(f"Cumulative Score: {drift.get('cumulative_drift_score', 0):.3f}")
            print(f"Drift Velocity: {drift.get('drift_velocity', 0):.3f}")
            print(f"Total Events: {drift.get('total_drift_events', 0)}")
            print(f"Contradictions: {metrics.get('contradictions', {}).get('count', 0)}")

            score = drift.get('cumulative_drift_score', 0)
            if score > 2.0:
                print(f"\n[ESCALATION] Score > 2.0!")
                print("Open extension to see RED GLOW + PULSE + ESCALATION CARD")
            elif score > 1.0:
                print(f"\n[WARNING] Building tension (score > 1.0)")
                print("Open extension to see YELLOW bar")
            else:
                print(f"\n[STABLE] Low drift (score < 1.0)")
                print("Open extension to see GREEN bar")

            print(f"\n[SUCCESS] Conversation ID: {conversation_id}")
        else:
            print(f"[ERROR] {response.status_code}")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    print("\n[START] Creating high-overlap contradictions...\n")
    create_high_overlap_drift()
    print("\n[DONE]\n")
