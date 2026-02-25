import asyncio
import httpx
from datetime import datetime
import uuid

async def main():
    BASE_URL = "http://127.0.0.1:8001"
    conversation_id = f"test-{uuid.uuid4().hex[:8]}"  # Unique ID
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Turn 1
        print("\n=== Turn 1 ===")
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
        print(f"Alerts: {len(result['alerts'])}")
        print(f"Commitments: {len(result['updated_graph']['commitments'])}")
        
        # Turn 2
        print("\n=== Turn 2 ===")
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
        print(f"Alerts: {len(result['alerts'])}")
        print(f"Escalation triggered: {result['cost_estimate'].get('escalation_triggered', False)}")
        if result['alerts']:
            for alert in result['alerts']:
                print(f"  Alert: {alert['alert_type']} ({alert['severity']})")

        # Check metadata
        response = await client.get(f"{BASE_URL}/conversations/{conversation_id}")
        graph = response.json()
        escalation_events = graph['metadata'].get('escalation_events', [])
        print(f"\nEscalation events: {len(escalation_events)}")
        for event in escalation_events:
            print(f"  - {event['escalation_reason']} (urgency: {event['urgency']})")

if __name__ == "__main__":
    asyncio.run(main())
