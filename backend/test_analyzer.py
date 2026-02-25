"""Test analyzer to see what error occurs"""
import asyncio
import sys
sys.path.insert(0, '.')

from app.models import CommitmentGraph, Turn
from app.analyzer import analyze_turn_hybrid_escalation

async def test():
    graph = CommitmentGraph(conversation_id="test")
    turn = Turn(id=1, speaker="user", text="Test message", ts="2024-01-01T00:00:00")

    try:
        result = await analyze_turn_hybrid_escalation(graph, turn)
        print("SUCCESS:", result)
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
