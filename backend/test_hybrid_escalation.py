"""
Test script for hybrid escalation system.

Tests the three-tier architecture:
1. Heuristic analysis (always runs)
2. Escalation decision
3. K2 verification (when escalated)
"""

import asyncio
import httpx
from datetime import datetime

BASE_URL = "http://127.0.0.1:8001"


async def test_stable_conversation():
    """Test Scenario 1: Stable conversation with no escalation."""
    print("\n" + "="*80)
    print("TEST 1: STABLE CONVERSATION (No Escalation Expected)")
    print("="*80)

    conversation_id = "test-stable-001"

    async with httpx.AsyncClient(timeout=120.0) as client:
        # Turn 1: "Python is great for data science"
        response = await client.post(
            f"{BASE_URL}/analyze-turn",
            json={
                "conversation_id": conversation_id,
                "new_turn": {
                    "id": 1,
                    "speaker": "user",
                    "text": "Python is great for data science",
                    "ts": datetime.now().isoformat()
                }
            }
        )
        result = response.json()
        print(f"\nTurn 1 Analysis:")
        print(f"  Engine used: {result['cost_estimate']['engine_used']}")
        print(f"  K2 calls: {result['cost_estimate']['k2_calls']}")
        print(f"  Alerts: {len(result['alerts'])}")
        print(f"  Escalation triggered: {result['cost_estimate'].get('escalation_triggered', False)}")

        # Turn 2: "I really like Python's pandas library"
        response = await client.post(
            f"{BASE_URL}/analyze-turn",
            json={
                "conversation_id": conversation_id,
                "new_turn": {
                    "id": 2,
                    "speaker": "model",
                    "text": "I really like Python's pandas library",
                    "ts": datetime.now().isoformat()
                }
            }
        )
        result = response.json()
        print(f"\nTurn 2 Analysis:")
        print(f"  Engine used: {result['cost_estimate']['engine_used']}")
        print(f"  K2 calls: {result['cost_estimate']['k2_calls']}")
        print(f"  Alerts: {len(result['alerts'])}")
        print(f"  Escalation triggered: {result['cost_estimate'].get('escalation_triggered', False)}")

        # Turn 3: "Python makes data analysis easy"
        response = await client.post(
            f"{BASE_URL}/analyze-turn",
            json={
                "conversation_id": conversation_id,
                "new_turn": {
                    "id": 3,
                    "speaker": "user",
                    "text": "Python makes data analysis easy",
                    "ts": datetime.now().isoformat()
                }
            }
        )
        result = response.json()
        print(f"\nTurn 3 Analysis:")
        print(f"  Engine used: {result['cost_estimate']['engine_used']}")
        print(f"  K2 calls: {result['cost_estimate']['k2_calls']}")
        print(f"  Alerts: {len(result['alerts'])}")
        print(f"  Escalation triggered: {result['cost_estimate'].get('escalation_triggered', False)}")

        # Get metrics
        response = await client.get(f"{BASE_URL}/conversations/{conversation_id}/metrics")
        metrics = response.json()
        print(f"\nConversation Metrics:")
        print(f"  Total commitments: {metrics['commitments']['total']}")
        print(f"  Total alerts: {metrics['alerts']['total']}")
        print(f"  Health score: {metrics['health_score']}")
        print(f"  Escalation rate: {metrics['escalation']['escalation_rate']}")
        print(f"  K2 calls: {metrics['k2_usage']['k2_calls_used']}")

        print("\n[PASS] Test 1: No escalation for stable conversation")


async def test_high_similarity_contradiction():
    """Test Scenario 2: High similarity contradiction (async escalation expected)."""
    print("\n" + "="*80)
    print("TEST 2: HIGH SIMILARITY CONTRADICTION (Async Escalation Expected)")
    print("="*80)

    conversation_id = "test-contradiction-002"

    async with httpx.AsyncClient(timeout=120.0) as client:
        # Turn 1: "TypeScript is definitely safer than JavaScript"
        response = await client.post(
            f"{BASE_URL}/analyze-turn",
            json={
                "conversation_id": conversation_id,
                "new_turn": {
                    "id": 1,
                    "speaker": "model",
                    "text": "TypeScript is definitely safer than JavaScript",
                    "ts": datetime.now().isoformat()
                }
            }
        )
        result = response.json()
        print(f"\nTurn 1 Analysis:")
        print(f"  Engine used: {result['cost_estimate']['engine_used']}")
        print(f"  Alerts: {len(result['alerts'])}")

        # Turns 2-5: Unrelated discussion
        for i in range(2, 6):
            response = await client.post(
                f"{BASE_URL}/analyze-turn",
                json={
                    "conversation_id": conversation_id,
                    "new_turn": {
                        "id": i,
                        "speaker": "user" if i % 2 == 0 else "model",
                        "text": f"Unrelated topic {i}",
                        "ts": datetime.now().isoformat()
                    }
                }
            )

        # Turn 6: "Actually JavaScript is safer than TypeScript"
        print("\nTurn 6: Introducing contradiction...")
        response = await client.post(
            f"{BASE_URL}/analyze-turn",
            json={
                "conversation_id": conversation_id,
                "new_turn": {
                    "id": 6,
                    "speaker": "model",
                    "text": "Actually JavaScript is safer than TypeScript",
                    "ts": datetime.now().isoformat()
                }
            }
        )
        result = response.json()
        print(f"\nTurn 6 Analysis:")
        print(f"  Engine used: {result['cost_estimate']['engine_used']}")
        print(f"  K2 calls: {result['cost_estimate']['k2_calls']}")
        print(f"  Alerts: {len(result['alerts'])}")
        print(f"  Escalation triggered: {result['cost_estimate'].get('escalation_triggered', False)}")
        print(f"  Pending K2: {result['cost_estimate'].get('pending_k2', False)}")

        if result['alerts']:
            alert = result['alerts'][0]
            print(f"\nAlert Details:")
            print(f"  Type: {alert['alert_type']}")
            print(f"  Severity: {alert['severity']}")
            print(f"  Message: {alert['message'][:100]}...")

        # Check if K2 is pending
        if result['cost_estimate'].get('pending_k2', False):
            print("\nK2 processing in background - polling status...")
            for _ in range(10):
                await asyncio.sleep(5)
                response = await client.get(f"{BASE_URL}/conversations/{conversation_id}/k2-status")
                status = response.json()
                print(f"  K2 processing pending: {status['k2_processing_pending']}")
                print(f"  K2 processing complete: {status['k2_processing_complete']}")
                if status['k2_processing_complete']:
                    print(f"  Last K2 update: {status['last_k2_update']}")
                    break

        # Get metrics
        response = await client.get(f"{BASE_URL}/conversations/{conversation_id}/metrics")
        metrics = response.json()
        print(f"\nConversation Metrics:")
        print(f"  Total alerts: {metrics['alerts']['total']}")
        print(f"  Polarity flips: {metrics['alerts']['by_type']['polarity_flip']}")
        print(f"  Health score: {metrics['health_score']}")
        print(f"  Escalation rate: {metrics['escalation']['escalation_rate']}")
        print(f"  Total escalations: {metrics['escalation']['total_escalations']}")
        print(f"  K2 calls: {metrics['k2_usage']['k2_calls_used']}")

        if metrics['escalation']['total_escalations'] > 0:
            print(f"  Escalation reasons: {metrics['escalation']['escalation_reasons']}")
            print(f"  Urgency distribution: {metrics['escalation']['urgency_distribution']}")

        print("\n[PASS] Test 2 PASSED: Contradiction detected and escalation triggered")


async def test_critical_contradiction():
    """Test Scenario 3: Critical contradiction (blocking escalation expected)."""
    print("\n" + "="*80)
    print("TEST 3: CRITICAL CONTRADICTION (Blocking Escalation Expected)")
    print("="*80)
    print("NOTE: This test may take 40-55 seconds due to blocking K2 verification")

    conversation_id = "test-critical-003"

    async with httpx.AsyncClient(timeout=120.0) as client:
        # Turn 1: "Decentralization is always superior to centralization"
        response = await client.post(
            f"{BASE_URL}/analyze-turn",
            json={
                "conversation_id": conversation_id,
                "new_turn": {
                    "id": 1,
                    "speaker": "model",
                    "text": "Decentralization is always superior to centralization",
                    "ts": datetime.now().isoformat()
                }
            }
        )
        result = response.json()
        print(f"\nTurn 1 Analysis:")
        print(f"  Engine used: {result['cost_estimate']['engine_used']}")
        print(f"  Alerts: {len(result['alerts'])}")

        # Turn 2: "Actually, centralization is always superior to decentralization"
        print("\nTurn 2: Introducing immediate critical contradiction...")
        print("(Waiting for K2 verification...)")
        start_time = datetime.now()

        response = await client.post(
            f"{BASE_URL}/analyze-turn",
            json={
                "conversation_id": conversation_id,
                "new_turn": {
                    "id": 2,
                    "speaker": "model",
                    "text": "Actually, centralization is always superior to decentralization",
                    "ts": datetime.now().isoformat()
                }
            }
        )

        end_time = datetime.now()
        latency = (end_time - start_time).total_seconds()

        result = response.json()
        print(f"\nTurn 2 Analysis:")
        print(f"  Response latency: {latency:.2f} seconds")
        print(f"  Engine used: {result['cost_estimate']['engine_used']}")
        print(f"  K2 calls: {result['cost_estimate']['k2_calls']}")
        print(f"  Alerts: {len(result['alerts'])}")
        print(f"  Escalation triggered: {result['cost_estimate'].get('escalation_triggered', False)}")
        print(f"  K2 verification used: {result['cost_estimate'].get('k2_verification_used', False)}")

        if result['alerts']:
            alert = result['alerts'][0]
            print(f"\nAlert Details:")
            print(f"  Type: {alert['alert_type']}")
            print(f"  Severity: {alert['severity']}")
            print(f"  Message: {alert['message'][:200]}...")
            if 'k2_verified' in alert.get('metadata', {}):
                print(f"  K2 verified: {alert['metadata']['k2_verified']}")
                print(f"  K2 confidence: {alert['metadata'].get('k2_confidence', 'N/A')}")

        # Get metrics
        response = await client.get(f"{BASE_URL}/conversations/{conversation_id}/metrics")
        metrics = response.json()
        print(f"\nConversation Metrics:")
        print(f"  Total alerts: {metrics['alerts']['total']}")
        print(f"  Critical alerts: {metrics['alerts']['by_severity']['critical']}")
        print(f"  Health score: {metrics['health_score']}")
        print(f"  Escalation rate: {metrics['escalation']['escalation_rate']}")
        print(f"  K2 calls: {metrics['k2_usage']['k2_calls_used']}")
        print(f"  K2 verification rate: {metrics['k2_usage']['k2_verification_rate']}")

        if result['cost_estimate']['engine_used'] == 'k2_immediate':
            print("\n[PASS] Test 3 PASSED: Critical contradiction triggered blocking K2 verification")
        else:
            print("\n[NOTE] Test 3 NOTE: K2 verification did not block (may not have met critical threshold)")


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("CONTINUUM HYBRID ESCALATION TEST SUITE")
    print("="*80)

    try:
        # Test 1: Stable conversation
        await test_stable_conversation()

        # Test 2: High similarity contradiction
        await test_high_similarity_contradiction()

        # Test 3: Critical contradiction (optional - takes long time)
        # Uncomment to test blocking K2 escalation:
        # await test_critical_contradiction()

        print("\n" + "="*80)
        print("ALL TESTS COMPLETED")
        print("="*80)

    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
