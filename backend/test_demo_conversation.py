"""
Populate backend with drift data for any ChatGPT conversation.

Usage:
    python test_demo_conversation.py                          # uses default hardcoded ID
    python test_demo_conversation.py <conversation-id>       # uses specified ID

The conversation ID is the UUID in the ChatGPT URL:
    https://chatgpt.com/c/<conversation-id>

Target: Generate escalation-level drift (score > 2.0)
"""

import sys
import requests
from datetime import datetime

API_BASE = "http://localhost:8000"

def create_demo_drift(conversation_id: str):
    """Create drift data for the given conversation."""

    # High-overlap contradictions for maximum drift detection
    turns = [
        # Topic 1: AI capabilities (strong contradictions)
        ("user", "AI models are excellent tools for creative writing."),
        ("model", "AI can assist with brainstorming and drafting."),
        ("user", "AI models are not excellent tools for creative writing."),
        ("model", "What changed your perspective?"),
        ("user", "AI models are terrible tools for creative writing."),
        ("model", "I see you've reconsidered."),

        # Topic 2: Code quality (escalating drift)
        ("user", "TypeScript is a good choice for large projects."),
        ("model", "TypeScript provides type safety benefits."),
        ("user", "TypeScript is not a good choice for large projects."),
        ("model", "That's quite a shift in opinion."),
        ("user", "TypeScript is a bad choice for large projects."),
        ("model", "Can you explain what led to this change?"),

        # Topic 3: Testing practices (more contradictions)
        ("user", "Unit testing is essential for production code."),
        ("model", "Unit tests help catch bugs early."),
        ("user", "Unit testing is not essential for production code."),
        ("model", "Your stance has changed."),
        ("user", "Unit testing is harmful for production code."),
        ("model", "That's a significant reversal."),

        # Topic 4: Architecture decisions (push over threshold)
        ("user", "Microservices are better than monoliths for scalability."),
        ("model", "Microservices offer independent scaling."),
        ("user", "Microservices are not better than monoliths for scalability."),
        ("model", "What made you reconsider?"),
        ("user", "Microservices are worse than monoliths for scalability."),
        ("model", "I notice you've changed your view again."),
    ]

    print(f"Creating drift data for demo conversation")
    print(f"Conversation ID: {conversation_id}")
    print("=" * 70)

    for turn_id, (speaker, text) in enumerate(turns, start=1):
        print(f"\nTurn {turn_id}: {text[:60]}...")

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
    print("\n" + "=" * 70)
    print("DEMO CONVERSATION METRICS")
    print("=" * 70)

    try:
        response = requests.get(f"{API_BASE}/conversations/{conversation_id}/metrics")
        if response.ok:
            metrics = response.json()
            drift = metrics.get('drift', {})

            print(f"\n[DRIFT METRICS]")
            print(f"Cumulative Score: {drift.get('cumulative_drift_score', 0):.3f}")
            print(f"Drift Velocity: {drift.get('drift_velocity', 0):.3f}")
            print(f"Total Events: {drift.get('total_drift_events', 0)}")
            print(f"Active Commitments: {metrics.get('commitments', {}).get('active', 0)}")

            score = drift.get('cumulative_drift_score', 0)
            if score > 2.0:
                print(f"\n[ESCALATION] Drift score > 2.0!")
                print("Extension will show RED GLOW + PULSE + ESCALATION CARD")
            elif score > 1.0:
                print(f"\n[WARNING] Building tension (score > 1.0)")
                print("Extension will show YELLOW bar")
            else:
                print(f"\n[STABLE] Low drift (score < 1.0)")
                print("Extension will show GREEN bar")

            print(f"\n[SUCCESS] Demo conversation ready!")
            print(f"Open: https://chatgpt.com/c/{conversation_id}")
            print("Then click the Continuum extension icon to see visualization.")
        else:
            print(f"[ERROR] {response.status_code}")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    # Accept conversation ID from command line, default to the original demo ID
    DEFAULT_ID = "69995ff5-64d8-8324-aa70-2da83e14c636"
    conversation_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ID

    print(f"\n[START] Populating conversation: {conversation_id}")
    print(f"Open: https://chatgpt.com/c/{conversation_id}\n")

    # Clear any existing data for fresh demo
    try:
        requests.delete(f"http://localhost:8000/conversations/{conversation_id}", timeout=2)
        print("[Cleared previous conversation data]\n")
    except:
        pass

    create_demo_drift(conversation_id)

    # Reset K2 timer so animation plays fresh when extension is opened
    try:
        response = requests.post(f"http://localhost:8000/conversations/{conversation_id}/reset-k2-timer", timeout=2)
        if response.ok:
            print("\n[K2 Timer Reset] Animation ready for demo recording")
        else:
            print(f"\n[WARNING] Could not reset K2 timer: {response.status_code}")
    except Exception as e:
        print(f"\n[WARNING] Could not reset K2 timer: {e}")

    print("\n[DONE]\n")
