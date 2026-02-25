"""
Escalation Policy Engine for Continuum.

Decides when epistemic tension warrants K2 Think V2 verification.
"""

from typing import List
from datetime import datetime
import logging

from app.models import CommitmentGraph, Commitment, Alert, EscalationDecision
from app.escalation_config import EscalationConfig
from app.drift_accumulation import calculate_drift_velocity, detect_drift_recovery
from app.dependency_graph import detect_structural_breaks
from app.topic_clustering import detect_stance_instability

logger = logging.getLogger(__name__)


class EscalationPolicy:
    """
    Intelligent escalation decision engine.

    Analyzes heuristic findings and decides if K2 verification is warranted
    based on epistemic severity, similarity scores, and conversation stability.
    """

    def __init__(self, config: EscalationConfig):
        self.config = config

    def should_escalate(
        self,
        graph: CommitmentGraph,
        new_commitments: List[Commitment],
        heuristic_alerts: List[Alert]
    ) -> EscalationDecision:
        """
        Decide if K2 escalation is warranted using cumulative drift analysis.

        Phase 4 (Drift Accumulator): Uses cumulative drift score, drift velocity,
        structural breaks, and stance instability as escalation triggers.

        Args:
            graph: Current conversation graph
            new_commitments: Newly extracted commitments
            heuristic_alerts: Alerts detected by heuristics

        Returns:
            EscalationDecision with should_escalate, reason, urgency
        """

        # Analyze triggers
        triggers = []
        max_urgency = "low"
        escalation_score = 0.0

        # TRIGGER 1: Cumulative Drift Score
        if graph.epistemic_drift_score > self.config.drift_escalation_threshold:
            triggers.append("cumulative_drift_threshold")
            escalation_score = max(escalation_score, 0.9)
            max_urgency = "high"

        # TRIGGER 2: Drift Velocity (rapid accumulation)
        drift_velocity = calculate_drift_velocity(graph)
        if drift_velocity > self.config.drift_velocity_threshold:
            triggers.append("high_drift_velocity")
            escalation_score = max(escalation_score, 0.95)
            max_urgency = "immediate"

        # TRIGGER 3: Structural Break (core assumptions collapse)
        structural_breaks = detect_structural_breaks(
            graph,
            self.config.structural_break_threshold
        )
        if structural_breaks:
            triggers.append("structural_break")
            escalation_score = max(escalation_score, 1.0)
            max_urgency = "immediate"

        # TRIGGER 4: Topic Stance Instability
        unstable_topics = detect_stance_instability(
            graph,
            self.config.stance_instability_threshold
        )
        if unstable_topics:
            triggers.append("stance_instability")
            escalation_score = max(escalation_score, 0.75)
            max_urgency = "high" if max_urgency == "low" else max_urgency

        # TRIGGER 5: Recovery Detection (drift trending down - REDUCE urgency)
        if detect_drift_recovery(graph):
            triggers.append("drift_recovery")
            # Reduce escalation score and urgency
            escalation_score *= 0.7
            if max_urgency == "immediate":
                max_urgency = "high"
            elif max_urgency == "high":
                max_urgency = "medium"

        # Legacy triggers (still supported)
        # Check each alert
        for alert in heuristic_alerts:
            # IMMEDIATE escalation triggers
            if alert.severity == "critical":
                triggers.append("critical_severity")
                max_urgency = "immediate"
                escalation_score = max(escalation_score, 1.0)

            # Get related commitments for detailed analysis
            if alert.alert_type == "polarity_flip" and len(alert.related_commitments) >= 2:
                prior_id, new_id = alert.related_commitments[0], alert.related_commitments[1]
                prior = graph.get_commitment(prior_id)

                # Find new commitment in new_commitments list
                new_comm = next((c for c in new_commitments if c.id == new_id), None)

                if prior and new_comm:
                    # Calculate similarity (from alert creation)
                    similarity = self._estimate_similarity(prior.normalized, new_comm.normalized)
                    confidence_delta = abs(prior.confidence - new_comm.confidence)

                    # High similarity → escalate
                    if similarity > self.config.high_similarity_threshold:
                        triggers.append("high_similarity")
                        escalation_score = max(escalation_score, 0.75)
                        max_urgency = "high" if max_urgency not in ["immediate"] else max_urgency

                        # Additional boost for high confidence delta
                        if confidence_delta > self.config.confidence_delta_threshold:
                            triggers.append("high_confidence_delta")
                            escalation_score = max(escalation_score, 0.9)

                    # Stability drop
                    if new_comm.stability_score < self.config.stability_threshold:
                        triggers.append("stability_drop")
                        escalation_score = max(escalation_score, 0.7)
                        max_urgency = "high" if max_urgency == "low" else max_urgency

        # Contradiction accumulation (now less important with drift tracking)
        recent_contradictions = self._count_recent_contradictions(graph, window=5)
        if recent_contradictions >= self.config.contradiction_accumulation_threshold:
            triggers.append("contradiction_accumulation")
            escalation_score = max(escalation_score, 0.6)  # Reduced from 0.8

        # Assumption drops
        assumption_drops = [a for a in heuristic_alerts if a.alert_type == "assumption_drop"]
        if assumption_drops:
            triggers.append("assumption_drop")
            escalation_score = max(escalation_score, 0.6)

        # Decision
        should_escalate = escalation_score >= self.config.escalation_threshold

        return EscalationDecision(
            should_escalate=should_escalate,
            escalation_reason=triggers[0] if triggers else "low_confidence",
            urgency=max_urgency if should_escalate else "low",
            confidence=escalation_score,
            triggering_factors=triggers,
            timestamp=datetime.now()
        )

    def _estimate_similarity(self, text1: str, text2: str) -> float:
        """
        Quick token overlap similarity (Jaccard index).

        Args:
            text1: First text to compare
            text2: Second text to compare

        Returns:
            Similarity score between 0.0 and 1.0
        """
        tokens1 = set(text1.lower().split())
        tokens2 = set(text2.lower().split())

        if not tokens1 or not tokens2:
            return 0.0

        intersection = tokens1 & tokens2
        union = tokens1 | tokens2

        return len(intersection) / len(union) if union else 0.0

    def _count_recent_contradictions(self, graph: CommitmentGraph, window: int) -> int:
        """
        Count contradictions in last N turns.

        Args:
            graph: Conversation graph
            window: Number of recent turns to check

        Returns:
            Count of polarity flip alerts in window
        """
        if len(graph.turns) < window:
            window = len(graph.turns)

        if window == 0:
            return 0

        recent_turn_ids = [t.id for t in graph.turns[-window:]]
        contradictions = [
            a for a in graph.alerts
            if a.alert_type == "polarity_flip" and a.detected_at_turn in recent_turn_ids
        ]

        return len(contradictions)
