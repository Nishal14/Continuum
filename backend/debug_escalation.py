"""
Debug script to understand escalation behavior.
"""

import asyncio
import httpx
from datetime import datetime
import json


async def main():
    BASE_URL = "http://127.0.0.1:8001"
    conversation_id = "debug-test"

    async with httpx.AsyncClient(timeout=120.0) as client:
        # Turn 1: Normal statement
        print("\n=== Turn 1: Normal statement ===")
        response = await client.post(
            f"{BASE_URL}/analyze-turn",
            json={
                "conversation_id": conversation_id,
                "new_turn": {
                    "id": 1,
                    "speaker": "model",
                    "text": "TypeScript is safer than JavaScript",
                    "ts": datetime.now().isoformat()
                }
            }
        )
        result = response.json()
        print(f"Engine used: {result['cost_estimate']['engine_used']}")
        print(f"Escalation triggered: {result['cost_estimate'].get('escalation_triggered', False)}")
        print(f"Alerts: {len(result['alerts'])}")

        # Get full graph
        response = await client.get(f"{BASE_URL}/conversations/{conversation_id}")
        graph = response.json()
        escalation_events = graph['metadata'].get('escalation_events', [])
        print(f"Escalation events in metadata: {len(escalation_events)}")
        if escalation_events:
            print("Events:")
            for event in escalation_events:
                print(f"  - Turn {event['turn_id']}: {event['escalation_reason']} (urgency: {event['urgency']})")

        # Turn 2: Contradictory statement
        print("\n=== Turn 2: Contradictory statement ===")
        response = await client.post(
            f"{BASE_URL}/analyze-turn",
            json={
                "conversation_id": conversation_id,
                "new_turn": {
                    "id": 2,
                    "speaker": "model",
                    "text": "JavaScript is safer than TypeScript",
                    "ts": datetime.now().isoformat()
                }
            }
        )
        result = response.json()
        print(f"Engine used: {result['cost_estimate']['engine_used']}")
        print(f"Escalation triggered: {result['cost_estimate'].get('escalation_triggered', False)}")
        print(f"Pending K2: {result['cost_estimate'].get('pending_k2', False)}")
        print(f"Alerts: {len(result['alerts'])}")
        if result['alerts']:
            alert = result['alerts'][0]
            print(f"Alert type: {alert['alert_type']}, severity: {alert['severity']}")

        # Get full graph
        response = await client.get(f"{BASE_URL}/conversations/{conversation_id}")
        graph = response.json()
        escalation_events = graph['metadata'].get('escalation_events', [])
        print(f"\nEscalation events in metadata: {len(escalation_events)}")
        if escalation_events:
            print("Events:")
            for event in escalation_events:
                print(f"  - Turn {event['turn_id']}: {event['escalation_reason']} (urgency: {event['urgency']})")

        # Get metrics
        response = await client.get(f"{BASE_URL}/conversations/{conversation_id}/metrics")
        metrics = response.json()
        print(f"\nMetrics:")
        print(f"  Total escalations: {metrics['escalation']['total_escalations']}")
        print(f"  Escalation rate: {metrics['escalation']['escalation_rate']}")
        print(f"  Escalation reasons: {metrics['escalation']['escalation_reasons']}")
        print(f"  Urgency distribution: {metrics['escalation']['urgency_distribution']}")


if __name__ == "__main__":
    asyncio.run(main())
