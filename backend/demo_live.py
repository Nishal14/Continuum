"""
Live drift demo — two-phase script for showing epistemic stability dropping in real time.

Usage:
    python demo_live.py                      # uses default conversation ID
    python demo_live.py <conversation-id>    # uses the given ID

Phase 1  — Stable (runs automatically)
    Sends consistent, non-contradicting turns.
    Drift stays at 0. Graph shows a flat line. Status = Stable.

Phase 2  — Trigger (runs on your keypress)
    Sends one message that directly contradicts Phase 1 commitments.
    Drift spikes past the 2.0 threshold. Escalation card appears.
    K2 verification begins.

The sidebar polls every 3 s — you'll see the graph update live.
"""

import sys
import requests
from datetime import datetime

API  = "http://localhost:8000"
SEP  = "─" * 60


def ts():
    return datetime.now().isoformat()


def send(conv_id: str, turn_id: int, speaker: str, text: str) -> dict:
    payload = {
        "conversation_id": conv_id,
        "new_turn": {"id": turn_id, "speaker": speaker, "text": text, "ts": ts()},
    }
    r = requests.post(f"{API}/analyze-turn", json=payload, timeout=10)
    r.raise_for_status()
    return r.json()


def metrics(conv_id: str) -> dict:
    r = requests.get(f"{API}/conversations/{conv_id}/metrics", timeout=5)
    r.raise_for_status()
    return r.json()


def print_turn(turn_id: int, speaker: str, text: str, result: dict):
    alerts = result.get("alerts", [])
    tag    = f"  [{alerts[0]['severity'].upper()}]" if alerts else ""
    label  = "USR" if speaker == "user" else "MDL"
    print(f"  [{label}] T{turn_id:02d}  {text[:58]}{tag}")


# ── Phase 1 turns — 4 topics, positive positions, no contradictions ──────────
# Kept short (8 turns) so Phase 2 contradictions land within a tight recency
# window — the drift formula rewards small turn gaps with higher magnitude.

STABLE_TURNS = [
    ("user",  "AI models are excellent tools for creative writing."),
    ("model", "AI can assist with brainstorming and drafting."),
    ("user",  "TypeScript is a good choice for large projects."),
    ("model", "TypeScript provides type safety and reduces runtime errors."),
    ("user",  "Unit testing is essential for production code."),
    ("model", "Unit tests help catch bugs early in the development cycle."),
    ("user",  "Microservices are better than monoliths for scalability."),
    ("model", "Microservices offer independent deployment and scaling."),
]

# ── Phase 2 turns — two contradictions per topic (the proven pattern) ────────
# "not X" then "X is bad" — same escalation ladder as test_demo_conversation.py
# which reliably reaches 3.6+. 8 turns → 8 drift events → well past 2.0.

TRIGGER_TURNS = [
    ("user",  "AI models are not excellent tools for creative writing."),
    ("user",  "AI models are terrible tools for creative writing."),
    ("user",  "TypeScript is not a good choice for large projects."),
    ("user",  "TypeScript is a bad choice for large projects."),
    ("user",  "Unit testing is not essential for production code."),
    ("user",  "Unit testing is harmful for production code."),
    ("user",  "Microservices are not better than monoliths for scalability."),
    ("user",  "Microservices are worse than monoliths for scalability."),
]


def run(conv_id: str):
    # Clear any existing data for a clean start
    try:
        requests.delete(f"{API}/conversations/{conv_id}", timeout=3)
        print("[Cleared previous data]\n")
    except Exception:
        pass

    # ── Phase 1: Stable ──────────────────────────────────────────────────────
    print(SEP)
    print("PHASE 1 — Stable Conversation")
    print("Sending consistent turns… drift should stay at 0.")
    print(SEP)

    for i, (speaker, text) in enumerate(STABLE_TURNS, start=1):
        result = send(conv_id, i, speaker, text)
        print_turn(i, speaker, text, result)

    m = metrics(conv_id)
    score = m["drift"]["cumulative_drift_score"]
    print(f"\n  Drift score after Phase 1: {score:.3f}  ✓ Stable")
    print(f"\n  Open the sidebar now — graph should show a flat line at 0.")
    print(f"  URL: https://chatgpt.com/c/{conv_id}\n")

    # ── Pause ────────────────────────────────────────────────────────────────
    input("  Press ENTER when ready to trigger drift ▶ ")
    print()

    # ── Phase 2: Trigger ─────────────────────────────────────────────────────
    print(SEP)
    print("PHASE 2 — Contradiction Trigger")
    print("Sending contradicting turns… watch the graph spike.")
    print(SEP)

    turn_id = len(STABLE_TURNS) + 1
    for i, (speaker, text) in enumerate(TRIGGER_TURNS):
        result = send(conv_id, turn_id + i, speaker, text)
        print_turn(turn_id + i, speaker, text, result)

        m = metrics(conv_id)
        score = m["drift"]["cumulative_drift_score"]
        label = "ESCALATED ▲" if score >= 2.0 else "building…"
        print(f"       → drift: {score:.3f}  {label}")

        if score >= 2.0 and i < len(TRIGGER_TURNS) - 1:
            print("\n  Threshold crossed. Remaining turns will compound the spike.")

    # ── Final summary ────────────────────────────────────────────────────────
    print()
    print(SEP)
    m = metrics(conv_id)
    d = m["drift"]
    print("FINAL METRICS")
    print(SEP)
    print(f"  Cumulative drift : {d['cumulative_drift_score']:.3f}")
    print(f"  Drift velocity   : {d['drift_velocity']:.3f}")
    print(f"  Total events     : {d['total_drift_events']}")
    print(f"  Commitments      : {m['commitments']['active']} active")

    if d["cumulative_drift_score"] >= 2.0:
        print("\n  [ESCALATION TRIGGERED] Sidebar shows red escalation card + K2 verification.")
    print()

    # Reset K2 timer so the animation plays from the start
    try:
        requests.post(f"{API}/conversations/{conv_id}/reset-k2-timer", timeout=3)
        print("  [K2 Timer Reset] Animation ready.\n")
    except Exception:
        pass


if __name__ == "__main__":
    DEFAULT_ID = "demo-live-001"
    conv_id    = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ID

    print(f"\n  Conversation ID : {conv_id}")
    print(f"  Backend         : {API}\n")

    run(conv_id)
