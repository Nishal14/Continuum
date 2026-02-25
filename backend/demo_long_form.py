"""
Long-form drift accumulation demo.

Demonstrates:
- Gradual epistemic drift over 8-12 turns
- Cumulative drift score increasing
- Escalation at turn 8 (not turn 2)
- Drift velocity tracking
- Recovery detection
"""

import asyncio
from datetime import datetime
from app.models import CommitmentGraph, Turn
from app.analyzer import analyze_turn_hybrid_escalation
from app.drift_accumulation import get_drift_summary
from app.metrics import compute_epistemic_metrics


# Demo conversation: Gradual shift from "Python is best" to "Python is worst"
DEMO_TURNS = [
    # Turn 1-2: Strong positive
    ("user", "I think Python is the best programming language for data science."),
    ("model", "Yes, Python has excellent libraries like pandas and numpy."),

    # Turn 3-4: Weakening positive
    ("user", "Although Python is good, I'm noticing some performance issues."),
    ("model", "Performance can be a concern, but usually it's manageable."),

    # Turn 5-6: Neutral/Mixed
    ("user", "Actually, the performance issues are becoming more problematic."),
    ("model", "Have you considered using PyPy or Cython for optimization?"),

    # Turn 7-8: Turning negative
    ("user", "I've tried those, but they don't really solve the core problems."),
    ("model", "What specific problems are you encountering?"),

    # Turn 9-10: Strong negative
    ("user", "Python's GIL makes it terrible for concurrent programming."),
    ("model", "The GIL is a known limitation for CPU-bound multithreading."),

    # Turn 11-12: Very negative
    ("user", "Honestly, Python is probably the worst choice for my use case."),
    ("model", "It sounds like you might benefit from exploring alternatives."),
]


async def run_demo():
    """Run the long-form drift accumulation demo."""
    print("=" * 80)
    print("DRIFT ACCUMULATION DEMO: Long-Form Epistemic Shift")
    print("=" * 80)
    print("\nScenario: Gradual shift from 'Python is best' to 'Python is worst'")
    print("Expected: Drift accumulates over time, escalation at turn ~8\n")

    # Initialize graph
    graph = CommitmentGraph(conversation_id="demo_longform")

    # Process each turn
    for turn_id, (speaker, text) in enumerate(DEMO_TURNS, start=1):
        print(f"\n{'─' * 80}")
        print(f"TURN {turn_id} ({speaker}):")
        print(f"  \"{text}\"")
        print(f"{'─' * 80}")

        # Create turn
        turn = Turn(
            id=turn_id,
            speaker=speaker,
            text=text,
            ts=datetime.now()
        )

        # Add to graph
        graph.turns.append(turn)

        # Analyze turn
        alerts, commitments, edges, metadata = await analyze_turn_hybrid_escalation(
            graph, turn
        )

        # Add results to graph
        graph.commitments.extend(commitments)
        graph.edges.extend(edges)
        graph.alerts.extend(alerts)

        # Get drift summary
        drift_summary = get_drift_summary(graph)

        # Print results
        print(f"\n📊 Analysis Results:")
        print(f"  • Commitments extracted: {len(commitments)}")
        print(f"  • Alerts generated: {len(alerts)}")
        print(f"  • Drift score: {drift_summary['cumulative_drift_score']:.3f}")
        print(f"  • Drift velocity: {drift_summary['drift_velocity']:.3f}")
        print(f"  • Stable turns: {drift_summary['turns_since_last_drift']}")
        print(f"  • Total drift events: {drift_summary['total_drift_events']}")
        print(f"  • Recovering: {drift_summary['is_recovering']}")

        # Show alerts
        if alerts:
            print(f"\n⚠️  Alerts:")
            for alert in alerts:
                print(f"    [{alert.severity.upper()}] {alert.alert_type}: {alert.message[:80]}")

        # Show escalation decision
        if metadata.get("escalation_triggered"):
            print(f"\n🚨 ESCALATION TRIGGERED!")
            print(f"  • Reason: {metadata['escalation_reason']}")
            print(f"  • Engine: {metadata['engine_used']}")
            print(f"  • K2 calls: {metadata['k2_calls']}")

        # Show commitments
        if commitments:
            print(f"\n📝 New Commitments:")
            for c in commitments:
                print(f"    [{c.polarity}] {c.normalized[:80]}")

    # Final metrics
    print(f"\n{'=' * 80}")
    print("FINAL METRICS")
    print(f"{'=' * 80}")

    metrics = compute_epistemic_metrics(graph)

    print(f"\n📈 Epistemic Health:")
    print(f"  • Health score: {metrics['health_score']}")
    print(f"  • Total commitments: {metrics['commitments']['total']}")
    print(f"  • Active commitments: {metrics['commitments']['active']}")
    print(f"  • Stability average: {metrics['stability']['average']}")

    print(f"\n📉 Drift Metrics:")
    drift = metrics['drift']
    print(f"  • Cumulative drift: {drift['cumulative_drift_score']}")
    print(f"  • Drift velocity: {drift['drift_velocity']}")
    print(f"  • Total events: {drift['total_drift_events']}")
    print(f"  • Is recovering: {drift['is_recovering']}")

    print(f"\n🔗 Dependency Metrics:")
    deps = metrics['dependencies']
    print(f"  • Total dependencies: {deps['total_dependencies']}")
    print(f"  • Max depth: {deps['max_dependency_depth']}")
    print(f"  • Structural breaks: {deps['structural_breaks']}")

    print(f"\n🎯 Stance Tracking:")
    stance = metrics['stance_tracking']
    print(f"  • Topics tracked: {stance['topics_tracked']}")
    print(f"  • Stance points: {stance['total_stance_points']}")

    print(f"\n🎫 Escalation History:")
    escalation = metrics['escalation']
    print(f"  • Total escalations: {escalation['total_escalations']}")
    print(f"  • Escalation rate: {escalation['escalation_rate']:.2%}")
    print(f"  • Reasons: {escalation['escalation_reasons']}")
    print(f"  • Urgency: {escalation['urgency_distribution']}")

    print(f"\n{'=' * 80}")
    print("✅ Demo Complete!")
    print(f"{'=' * 80}\n")

    # Verification
    print("Verification:")
    if drift['total_drift_events'] >= 3:
        print("  ✓ Multiple drift events accumulated (not single-turn trigger)")
    else:
        print("  ✗ Expected multiple drift events")

    if drift['cumulative_drift_score'] > 1.0:
        print("  ✓ Cumulative drift exceeded threshold")
    else:
        print("  ✗ Expected cumulative drift > 1.0")

    if escalation['total_escalations'] > 0:
        escalation_turns = [
            e['turn_id'] for e in graph.metadata.get('escalation_events', [])
        ]
        print(f"  ✓ Escalation occurred at turns: {escalation_turns}")
        if escalation_turns and max(escalation_turns) >= 8:
            print("  ✓ Escalation delayed until turn 8+ (not turn 2)")
        else:
            print("  ⚠ Escalation may have been premature")
    else:
        print("  ⚠ No escalation triggered (may need to adjust thresholds)")

    print()


if __name__ == "__main__":
    print("\n🚀 Starting long-form drift accumulation demo...\n")
    asyncio.run(run_demo())
