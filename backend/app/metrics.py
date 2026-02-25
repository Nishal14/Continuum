"""
Epistemic metrics computation for commitment graphs.

This module provides functions for calculating health metrics
about a conversation's epistemic state.
"""

from typing import Dict, Any
from app.models import CommitmentGraph
from app.drift_accumulation import get_drift_summary
from app.dependency_graph import get_dependency_metrics
from app.topic_clustering import compute_topic_stance_variance


def compute_epistemic_metrics(graph: CommitmentGraph) -> Dict[str, Any]:
    """
    Compute epistemic health metrics for a commitment graph.

    Analyzes the graph to produce metrics about:
    - Commitment lifecycle (active/inactive counts)
    - Contradiction frequency
    - Stability trends
    - Alert patterns

    Args:
        graph: The commitment graph to analyze

    Returns:
        Dictionary containing computed metrics
    """
    active_commitments = graph.get_active_commitments()
    inactive_commitments = [c for c in graph.commitments if not c.active]

    # Basic commitment counts
    total_commitments = len(graph.commitments)
    active_count = len(active_commitments)
    inactive_count = len(inactive_commitments)

    # Contradiction analysis
    contradiction_count = graph.count_contradictions()
    contradiction_edges = [e for e in graph.edges if e.relation == "contradicts"]

    # Stability analysis
    stability_scores = [c.stability_score for c in graph.commitments if c.stability_score is not None]
    avg_stability = sum(stability_scores) / len(stability_scores) if stability_scores else 1.0
    min_stability = min(stability_scores) if stability_scores else 1.0

    # Alert analysis
    polarity_flip_alerts = [a for a in graph.alerts if a.alert_type == "polarity_flip"]
    assumption_drop_alerts = [a for a in graph.alerts if a.alert_type == "assumption_drop"]
    agreement_bias_alerts = [a for a in graph.alerts if a.alert_type == "agreement_bias"]
    confidence_drift_alerts = [a for a in graph.alerts if a.alert_type == "confidence_drift"]

    # Severity breakdown
    critical_alerts = [a for a in graph.alerts if a.severity == "critical"]
    high_alerts = [a for a in graph.alerts if a.severity == "high"]
    medium_alerts = [a for a in graph.alerts if a.severity == "medium"]
    low_alerts = [a for a in graph.alerts if a.severity == "low"]

    # Compute epistemic health score (0-100)
    # Higher is better: penalize contradictions, inactive commitments, low stability
    health_score = 100.0
    if total_commitments > 0:
        # Penalize high contradiction rate
        contradiction_rate = contradiction_count / total_commitments
        health_score -= contradiction_rate * 30

        # Penalize low average stability
        health_score -= (1.0 - avg_stability) * 20

        # Penalize high inactive rate
        inactive_rate = inactive_count / total_commitments
        health_score -= inactive_rate * 15

        # Penalize critical/high severity alerts
        health_score -= len(critical_alerts) * 10
        health_score -= len(high_alerts) * 5

    health_score = max(0, min(100, health_score))

    # Phase 3: K2 usage metrics
    analysis_history = graph.metadata.get("analysis_history", [])
    k2_calls_total = sum(h.get("k2_calls", 0) for h in analysis_history)
    k2_used_count = sum(1 for h in analysis_history if h.get("engine_used") == "k2")
    heuristic_fallback_count = sum(1 for h in analysis_history if h.get("engine_used") == "heuristic_fallback")

    k2_verification_rate = k2_used_count / len(analysis_history) if len(analysis_history) > 0 else 0.0

    # Phase 3 Hybrid: Escalation metrics
    escalation_events = graph.metadata.get("escalation_events", [])
    escalation_reasons_count = {}
    urgency_distribution = {"immediate": 0, "high": 0, "medium": 0, "low": 0}

    for event in escalation_events:
        reason = event.get("escalation_reason", "unknown")
        urgency = event.get("urgency", "low")

        escalation_reasons_count[reason] = escalation_reasons_count.get(reason, 0) + 1
        urgency_distribution[urgency] += 1

    # Average stability at escalation
    escalated_turn_ids = [e["turn_id"] for e in escalation_events]
    escalated_commitments = [
        c for c in graph.commitments if c.turn_id in escalated_turn_ids
    ]
    avg_stability_at_escalation = (
        sum(c.stability_score for c in escalated_commitments) / len(escalated_commitments)
        if escalated_commitments else 1.0
    )

    # Phase 3 Hybrid: K2 authority metrics
    k2_overrides_list = graph.k2_overrides if hasattr(graph, 'k2_overrides') else []
    false_positives = [o for o in k2_overrides_list if o.override_type == "false_positive"]
    upgrades = [o for o in k2_overrides_list if o.override_type == "severity_upgrade"]
    downgrades = [o for o in k2_overrides_list if o.override_type == "severity_downgrade"]

    # K2 precision estimate
    k2_precision = (
        sum(o.confidence for o in k2_overrides_list) / len(k2_overrides_list)
        if k2_overrides_list else 1.0
    )

    # Async processing metrics
    async_k2_calls = graph.metadata.get("async_k2_calls", 0)
    blocking_k2_calls = k2_calls_total - async_k2_calls
    pending_k2_tasks = len([a for a in graph.alerts if a.metadata.get("pending_k2", False)])

    # Phase 4 (Drift Accumulator): Drift metrics
    drift_summary = get_drift_summary(graph) if hasattr(graph, 'epistemic_drift_score') else {
        "cumulative_drift_score": 0.0,
        "drift_velocity": 0.0,
        "turns_since_last_drift": 0,
        "total_drift_events": 0,
        "last_drift_update_turn": 0,
        "is_recovering": False
    }

    # Phase 4 (Drift Accumulator): Stance tracking metrics
    stance_metrics = {
        "topics_tracked": len(graph.topic_stance_history) if hasattr(graph, 'topic_stance_history') else 0,
        "total_stance_points": sum(
            len(history) for history in graph.topic_stance_history.values()
        ) if hasattr(graph, 'topic_stance_history') else 0,
        "topic_variances": {}
    }

    if hasattr(graph, 'topic_stance_history'):
        for topic_id, stance_history in graph.topic_stance_history.items():
            variance = compute_topic_stance_variance(stance_history)
            stance_metrics["topic_variances"][topic_id] = round(variance, 3)

    # Phase 4 (Drift Accumulator): Dependency metrics
    dependency_metrics = get_dependency_metrics(graph)

    return {
        "conversation_id": graph.conversation_id,
        "commitments": {
            "total": total_commitments,
            "active": active_count,
            "inactive": inactive_count,
            "inactive_rate": inactive_count / total_commitments if total_commitments > 0 else 0.0
        },
        "contradictions": {
            "count": contradiction_count,
            "rate": contradiction_count / total_commitments if total_commitments > 0 else 0.0
        },
        "stability": {
            "average": round(avg_stability, 3),
            "minimum": round(min_stability, 3)
        },
        "alerts": {
            "total": len(graph.alerts),
            "by_type": {
                "polarity_flip": len(polarity_flip_alerts),
                "assumption_drop": len(assumption_drop_alerts),
                "agreement_bias": len(agreement_bias_alerts),
                "confidence_drift": len(confidence_drift_alerts)
            },
            "by_severity": {
                "critical": len(critical_alerts),
                "high": len(high_alerts),
                "medium": len(medium_alerts),
                "low": len(low_alerts)
            }
        },
        "health_score": round(health_score, 1),
        "turns_analyzed": len(graph.turns),
        "k2_usage": {
            "k2_calls_used": k2_calls_total,
            "k2_verification_rate": round(k2_verification_rate, 3),
            "k2_used_count": k2_used_count,
            "heuristic_fallback_count": heuristic_fallback_count,
            "k2_override_events": len(k2_overrides_list)
        },
        "escalation": {
            "total_escalations": len(escalation_events),
            "escalation_rate": round(len(escalation_events) / max(len(graph.turns), 1), 3),
            "escalation_reasons": escalation_reasons_count,
            "urgency_distribution": urgency_distribution,
            "avg_stability_at_escalation": round(avg_stability_at_escalation, 3)
        },
        "k2_authority": {
            "total_verifications": len(k2_overrides_list),
            "overrides": len(false_positives),
            "severity_adjustments": {
                "upgrades": len(upgrades),
                "downgrades": len(downgrades)
            },
            "false_positive_corrections": len(false_positives),
            "precision_estimate": round(k2_precision, 3)
        },
        "async_processing": {
            "total_k2_calls": k2_calls_total,
            "async_k2_calls": async_k2_calls,
            "blocking_k2_calls": blocking_k2_calls,
            "pending_k2_tasks": pending_k2_tasks
        },
        "drift": drift_summary,
        "stance_tracking": stance_metrics,
        "dependencies": dependency_metrics
    }
