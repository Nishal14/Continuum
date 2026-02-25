"""Test contradiction edges on port 8000"""
import requests

API_BASE = "http://localhost:8000"

# Simple test with 3 turns that should create contradiction edges
conversation_id = "test-port-8000-contradictions"

turns = [
    ("user", "Python is excellent for web development"),
    ("assistant", "Python has many web frameworks"),
    ("user", "Python is not excellent for web development"),
]

print("Testing contradiction edge creation on port 8000...\n")

# Clear any existing data
try:
    requests.delete(f"{API_BASE}/conversations/{conversation_id}")
except:
    pass

for turn_id, (speaker, text) in enumerate(turns, start=1):
    payload = {
        "conversation_id": conversation_id,
        "new_turn": {
            "id": turn_id,
            "speaker": speaker,
            "text": text,
            "ts": "2024-01-01T00:00:00"
        }
    }

    print(f"Turn {turn_id}: {text[:50]}...")
    response = requests.post(f"{API_BASE}/analyze-turn", json=payload)

    if response.ok:
        data = response.json()
        alerts = data.get("alerts", [])
        if alerts:
            print(f"  -> {len(alerts)} alert(s)")
        else:
            print(f"  -> OK")
    else:
        print(f"  -> ERROR {response.status_code}: {response.text[:100]}")

# Get final metrics
print("\n" + "=" * 60)
response = requests.get(f"{API_BASE}/conversations/{conversation_id}/metrics")
if response.ok:
    metrics = response.json()
    print(f"Contradictions: {metrics['contradictions']['count']}")
    print(f"Total Alerts: {metrics['alerts']['total']}")
else:
    print(f"ERROR getting metrics: {response.status_code}")

# Get full conversation to check edges
response = requests.get(f"{API_BASE}/conversations/{conversation_id}")
if response.ok:
    data = response.json()
    edges = data.get("edges", [])
    contradiction_edges = [e for e in edges if e.get("relation") == "contradicts"]

    print(f"\nTotal Edges: {len(edges)}")
    print(f"Contradiction Edges: {len(contradiction_edges)}")

    if contradiction_edges:
        print("\nSUCCESS! Contradiction edges created:")
        for edge in contradiction_edges:
            print(f"  - {edge['source']} -> {edge['target']} (weight: {edge['weight']:.2f})")
    else:
        print("\nFAIL: No contradiction edges found")
        print("The backend on port 8000 still has the old code.")
        print("Please restart it to pick up the changes.")
else:
    print(f"ERROR getting conversation: {response.status_code}")
