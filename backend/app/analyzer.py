"""
Phase 3: Hybrid Escalation Analyzer.

This module orchestrates epistemic analysis using intelligent escalation:
- Layer 1: Fast heuristics (always runs)
- Layer 2: Escalation decision (intelligent gatekeeper)
- Layer 3: K2 Think V2 (strategic authority, called selectively)
"""

import logging
from typing import List, Tuple
from datetime import datetime

from app.models import (
    CommitmentGraph,
    Commitment,
    Turn,
    Alert,
    Edge,
    K2Override
)
from app.k2_client import K2Client
from app.heuristics import (
    analyze_turn_heuristics,
    extract_commitments_simple,
    detect_polarity_flip
)
from app.escalation import EscalationPolicy
from app.escalation_config import EscalationConfig
from app.topic_clustering import update_topic_stance_history
from app.dependency_graph import update_dependency_graph
from app.drift_accumulation import (
    calculate_drift_velocity,
    apply_drift_decay,
    migrate_graph_to_drift_system
)

logger = logging.getLogger(__name__)

# Initialize K2 client
k2_client = K2Client()

# Initialize escalation policy
escalation_config = EscalationConfig.from_env()
escalation_policy = EscalationPolicy(escalation_config)


async def analyze_turn_hybrid_escalation(
    graph: CommitmentGraph,
    new_turn: Turn
) -> Tuple[List[Alert], List[Commitment], List[Edge], dict]:
    """
    Phase 3 Hybrid: Heuristics first, K2 as strategic escalation.

    Flow:
    1. Run heuristic analysis (fast, <50ms)
    2. Escalation decision (intelligent gatekeeper)
    3. If escalated → K2 verification (authoritative)
    4. Return results

    Returns:
        (alerts, commitments, edges, metadata)
        metadata includes: engine_used, escalation_triggered, k2_calls
    """

    # Phase 4 (Drift Accumulator): Migrate graph if needed
    migrate_graph_to_drift_system(graph)

    metadata = {
        "engine_used": "heuristic",
        "k2_calls": 0,
        "escalation_triggered": False,
        "escalation_reason": None,
        "k2_verification_used": False,
        "k2_overrides": 0
    }

    # STEP 1: Heuristic Analysis (always runs)
    logger.info(f"[Hybrid] Running heuristic analysis for turn {new_turn.id}")
    heuristic_alerts, heuristic_commitments, heuristic_edges = analyze_turn_heuristics(
        graph, new_turn
    )

    # Phase 4 (Drift Accumulator): STEP 1.5: Topic Clustering & Stance Tracking
    logger.info(f"[Hybrid] Updating topic stance history")
    update_topic_stance_history(graph, heuristic_commitments)

    # Phase 4 (Drift Accumulator): STEP 1.6: Dependency Graph Updates
    logger.info(f"[Hybrid] Updating dependency graph")
    for commitment in heuristic_commitments:
        dependency_edges = update_dependency_graph(graph, commitment)
        heuristic_edges.extend(dependency_edges)

    # Phase 4 (Drift Accumulator): STEP 1.7: Update Drift Velocity
    graph.drift_velocity = calculate_drift_velocity(graph)
    logger.info(f"[Hybrid] Drift velocity: {graph.drift_velocity:.3f}")

    # Phase 4 (Drift Accumulator): STEP 1.8: Increment stability counter
    if not heuristic_alerts:
        graph.turns_since_last_drift += 1
        logger.info(f"[Hybrid] Stable turn (consecutive: {graph.turns_since_last_drift})")
    else:
        logger.info(f"[Hybrid] Alert detected (drift_score: {graph.epistemic_drift_score:.3f})")

    # Phase 4 (Drift Accumulator): STEP 1.9: Apply Drift Decay
    apply_drift_decay(
        graph,
        decay_factor=escalation_config.drift_decay_factor,
        stability_threshold_turns=escalation_config.stability_threshold_turns
    )
    logger.info(f"[Hybrid] Post-decay drift score: {graph.epistemic_drift_score:.3f}")

    # STEP 2: Escalation Decision
    escalation_decision = escalation_policy.should_escalate(
        graph, heuristic_commitments, heuristic_alerts
    )

    logger.info(
        f"[Hybrid] Escalation decision: {escalation_decision.should_escalate}, "
        f"reason: {escalation_decision.escalation_reason}, "
        f"urgency: {escalation_decision.urgency}"
    )

    if escalation_decision.should_escalate:
        # Store escalation event in metadata (only when actually escalating)
        graph.metadata.setdefault("escalation_events", []).append({
            "turn_id": new_turn.id,
            "escalation_reason": escalation_decision.escalation_reason,
            "urgency": escalation_decision.urgency,
            "confidence": escalation_decision.confidence,
            "triggering_factors": escalation_decision.triggering_factors,
            "timestamp": escalation_decision.timestamp.isoformat()
        })
        metadata["escalation_triggered"] = True
        metadata["escalation_reason"] = escalation_decision.escalation_reason

        # STEP 3: K2 Verification (for escalated cases)
        if escalation_decision.urgency == "immediate":
            # BLOCKING K2 verification for critical issues
            logger.info(f"[Hybrid] IMMEDIATE escalation - blocking for K2")
            metadata["engine_used"] = "k2_immediate"

            # Run K2 verification on alerts
            k2_verified_alerts = await _verify_alerts_with_k2(
                graph, heuristic_alerts, heuristic_commitments, metadata
            )

            return k2_verified_alerts, heuristic_commitments, heuristic_edges, metadata

        elif escalation_decision.urgency in ["high", "medium"]:
            # ASYNC K2 verification for high/medium priority
            logger.info(f"[Hybrid] {escalation_decision.urgency} escalation - async K2")
            metadata["engine_used"] = "heuristic_with_pending_k2"

            # Mark alerts as pending K2 verification
            for alert in heuristic_alerts:
                alert.metadata["pending_k2"] = True

            # Return heuristic results immediately
            # K2 will be triggered in background by main.py
            return heuristic_alerts, heuristic_commitments, heuristic_edges, metadata

        else:
            # Low urgency escalation - heuristics sufficient
            logger.info(f"[Hybrid] Low urgency escalation - heuristics sufficient")
            return heuristic_alerts, heuristic_commitments, heuristic_edges, metadata

    else:
        # STEP 4: No escalation - use heuristics
        logger.info(f"[Hybrid] No escalation - using heuristic results")
        return heuristic_alerts, heuristic_commitments, heuristic_edges, metadata


async def _verify_alerts_with_k2(
    graph: CommitmentGraph,
    alerts: List[Alert],
    commitments: List[Commitment],
    metadata: dict
) -> List[Alert]:
    """
    Run K2 verification on heuristic alerts.

    K2 acts as epistemic authority - can override, upgrade, or confirm.

    Args:
        graph: Current conversation graph
        alerts: Heuristic alerts to verify
        commitments: New commitments from this turn
        metadata: Metadata dict to update with K2 stats

    Returns:
        List of verified alerts (may be filtered if K2 overrides)
    """
    verified_alerts = []

    for alert in alerts:
        if alert.alert_type == "polarity_flip" and len(alert.related_commitments) >= 2:
            prior_id = alert.related_commitments[0]
            new_id = alert.related_commitments[1]

            prior = graph.get_commitment(prior_id)
            new_comm = next((c for c in commitments if c.id == new_id), None)

            if prior and new_comm:
                # Call K2 for verification
                k2_calls_before = k2_client.call_count
                verification = await k2_client.verify_contradiction(
                    prior_claim=prior.normalized,
                    new_claim=new_comm.normalized
                )
                metadata["k2_calls"] += (k2_client.call_count - k2_calls_before)

                if verification:
                    metadata["k2_verification_used"] = True

                    if verification.get("is_contradiction", True):
                        # K2 CONFIRMS contradiction
                        alert.message = f"K2 verified: {verification.get('explanation', alert.message)}"

                        # Severity adjustment
                        k2_confidence = verification.get("confidence", 0.5)
                        if k2_confidence >= 0.8:
                            alert.severity = "high"
                        elif k2_confidence >= 0.6:
                            alert.severity = "medium"

                        alert.metadata["k2_verified"] = True
                        alert.metadata["k2_confidence"] = k2_confidence
                        verified_alerts.append(alert)

                    else:
                        # K2 OVERRIDES heuristic
                        logger.info(f"[K2 Authority] Override: {verification.get('type')}")
                        metadata["k2_overrides"] += 1

                        # Track override
                        override = K2Override(
                            id=f"k2o{len(graph.k2_overrides) + 1}",
                            alert_id=alert.id,
                            override_type="false_positive",
                            original_severity=alert.severity,
                            k2_severity="none",
                            reason=verification.get("explanation", "K2 rejected contradiction"),
                            confidence=verification.get("confidence", 0.0),
                            timestamp=datetime.now()
                        )
                        graph.k2_overrides.append(override)

                        # Don't add alert (K2 rejected it)
                else:
                    # K2 failed - trust heuristic
                    verified_alerts.append(alert)
        else:
            # Non-polarity alerts pass through
            verified_alerts.append(alert)

    return verified_alerts


async def analyze_turn_k2_first(
    graph: CommitmentGraph,
    new_turn: Turn
) -> Tuple[List[Alert], List[Commitment], List[Edge], dict]:
    """
    Phase 3: Analyze turn using K2 as primary engine.

    Flow:
    1. Try K2 commitment extraction
    2. If K2 fails → fallback to heuristics
    3. Check for contradictions
    4. If contradiction found → verify with K2
    5. If verified → generate K2 reconciliation
    6. Return results + metadata

    Returns:
        (new_alerts, new_commitments, new_edges, metadata)
        metadata includes: engine_used, k2_calls, k2_verification_used
    """
    metadata = {
        "engine_used": "unknown",
        "k2_calls": 0,
        "k2_extraction_success": False,
        "k2_verification_used": False,
        "k2_reconciliation_used": False,
        "k2_overrides": 0
    }

    new_commitments = []
    new_alerts = []
    new_edges = []

    # PART 1: Commitment Extraction (K2 First)
    logger.info(f"[Continuum DEBUG] Attempting K2 structured extraction for turn {new_turn.id}")
    logger.info(f"[Continuum DEBUG] K2 client has API key: {k2_client.api_key is not None}")

    # Track K2 call count BEFORE the call (to capture attempts)
    k2_calls_before = k2_client.call_count

    k2_claims = await k2_client.extract_structured_commitments(new_turn.text)

    # Track actual K2 calls made (not just attempts)
    metadata["k2_calls"] = k2_client.call_count - k2_calls_before

    logger.info(f"[Continuum DEBUG] K2 extraction result: {k2_claims}")
    logger.info(f"[Continuum DEBUG] K2 calls made this turn: {metadata['k2_calls']}")

    if k2_claims is not None and len(k2_claims) > 0:
        # K2 SUCCESS - Convert K2 claims to Commitments
        logger.info(f"[K2-First] K2 extracted {len(k2_claims)} claims - using K2")
        metadata["engine_used"] = "k2"
        metadata["k2_extraction_success"] = True

        for idx, k2_claim in enumerate(k2_claims):
            commitment = Commitment(
                id=f"c{len(graph.commitments) + idx + 1}",
                turn_id=new_turn.id,
                kind="claim",  # K2 doesn't distinguish yet
                normalized=k2_claim.get("claim", ""),
                polarity=k2_claim.get("polarity", "neutral"),
                confidence=k2_claim.get("confidence", 0.5),
                assumptions=k2_claim.get("assumptions", []),
                timestamp=new_turn.ts,
                active=True,
                stability_score=1.0
            )
            new_commitments.append(commitment)

    else:
        # K2 FAILED - Fallback to heuristics
        logger.warning(f"[Continuum DEBUG] Falling back to heuristic extraction (K2 returned: {k2_claims})")
        metadata["engine_used"] = "heuristic_fallback"

        heuristic_commitments = extract_commitments_simple(new_turn, graph)
        new_commitments.extend(heuristic_commitments)

    # PART 2: Contradiction Detection
    for commitment in new_commitments:
        # First, let heuristics suggest potential contradiction
        heuristic_alert = detect_polarity_flip(graph, commitment)

        if heuristic_alert:
            logger.info(f"[K2-First] Heuristic detected potential contradiction")

            # Get the prior commitment involved
            prior_id = heuristic_alert.related_commitments[0]
            prior_commitment = graph.get_commitment(prior_id)

            if prior_commitment and metadata["engine_used"] == "k2":
                # K2 VERIFICATION LAYER
                logger.info(f"[K2-First] Verifying contradiction with K2...")
                verification = await k2_client.verify_contradiction(
                    prior_claim=prior_commitment.normalized,
                    new_claim=commitment.normalized
                )
                metadata["k2_calls"] += 1

                if verification:
                    metadata["k2_verification_used"] = True

                    if verification.get("is_contradiction", True):
                        # K2 CONFIRMS contradiction
                        logger.info(f"[K2-First] K2 confirmed contradiction")

                        # Update alert with K2 reasoning
                        heuristic_alert.message = (
                            f"K2 verified contradiction: {verification.get('explanation', 'See details')} "
                            f"(type: {verification.get('type', 'unknown')})"
                        )

                        # Adjust severity based on K2 confidence
                        k2_confidence = verification.get("confidence", 0.5)
                        if k2_confidence >= 0.8:
                            heuristic_alert.severity = "high"
                        elif k2_confidence >= 0.6:
                            heuristic_alert.severity = "medium"
                        else:
                            heuristic_alert.severity = "low"

                        new_alerts.append(heuristic_alert)

                    else:
                        # K2 OVERRIDES - Not a real contradiction
                        logger.info(f"[K2-First] K2 overrode heuristic - not a contradiction ({verification.get('type')})")
                        metadata["k2_overrides"] += 1

                        # Downgrade to low severity or skip
                        if verification.get("type") == "contextual_refinement":
                            heuristic_alert.severity = "low"
                            heuristic_alert.message = f"Refinement detected: {verification.get('explanation')}"
                            new_alerts.append(heuristic_alert)
                        # else: skip alert entirely

                else:
                    # K2 verification failed - trust heuristic
                    logger.warning(f"[K2-First] K2 verification failed - trusting heuristic")
                    new_alerts.append(heuristic_alert)

            else:
                # No K2 verification needed (heuristic mode) or no prior commitment
                new_alerts.append(heuristic_alert)

    return new_alerts, new_commitments, new_edges, metadata


async def generate_k2_reconciliation(
    graph: CommitmentGraph,
    alert: Alert
) -> Tuple[str, bool]:
    """
    Phase 3: Generate reconciliation using K2.

    Returns:
        (reconciliation_text, k2_used)
    """
    # Get related commitments
    if len(alert.related_commitments) < 2:
        return "Unable to generate reconciliation - insufficient context", False

    prior_id = alert.related_commitments[0]
    new_id = alert.related_commitments[1]

    prior_commitment = graph.get_commitment(prior_id)
    new_commitment = graph.get_commitment(new_id)

    if not prior_commitment or not new_commitment:
        return "Unable to generate reconciliation - commitments not found", False

    # Build conversation summary
    recent_turns = graph.turns[-5:] if len(graph.turns) >= 5 else graph.turns
    conversation_summary = " | ".join([f"{t.speaker}: {t.text[:50]}..." for t in recent_turns])

    # Try K2 reconciliation
    logger.info(f"[K2-First] Generating K2 reconciliation...")
    reconciliation = await k2_client.generate_reconciliation(
        prior_claim=prior_commitment.normalized,
        new_claim=new_commitment.normalized,
        conversation_summary=conversation_summary
    )

    if reconciliation and "reconciliation" in reconciliation:
        logger.info(f"[K2-First] K2 generated reconciliation")
        return reconciliation["reconciliation"], True

    # Fallback to template
    logger.warning(f"[K2-First] K2 reconciliation failed - using template")
    return (
        f"Earlier you stated: '{prior_commitment.normalized[:100]}'. "
        f"Now you're saying: '{new_commitment.normalized[:100]}'. "
        f"Can you help clarify what changed?"
    ), False


async def process_k2_escalation_async(
    graph: CommitmentGraph,
    alerts: List[Alert],
    commitments: List[Commitment],
    version: int
) -> None:
    """
    Process K2 verification asynchronously in background.

    Updates graph when complete and marks K2 processing as done.

    Args:
        graph: Conversation graph to update
        alerts: Alerts to verify with K2
        commitments: New commitments from this turn
        version: Expected graph version (for race condition handling)
    """
    conversation_id = graph.conversation_id
    logger.info(f"[Async K2] Starting background processing for {conversation_id}")

    # Version check - ensure graph hasn't changed
    if graph.version != version:
        logger.warning(
            f"[Async K2] Version mismatch: expected {version}, got {graph.version}. "
            "Discarding stale K2 results."
        )
        return

    try:
        # Run K2 verification
        k2_calls_made = 0
        k2_overrides = 0

        for alert in alerts:
            if alert.metadata.get("pending_k2") and alert.alert_type == "polarity_flip":
                if len(alert.related_commitments) >= 2:
                    prior_id = alert.related_commitments[0]
                    new_id = alert.related_commitments[1]

                    prior = graph.get_commitment(prior_id)
                    new_comm = next((c for c in graph.commitments if c.id == new_id), None)

                    if prior and new_comm:
                        # K2 verification
                        k2_calls_before = k2_client.call_count
                        verification = await k2_client.verify_contradiction(
                            prior_claim=prior.normalized,
                            new_claim=new_comm.normalized
                        )
                        k2_calls_made += (k2_client.call_count - k2_calls_before)

                        if verification:
                            # Update alert in graph
                            graph_alert = next((a for a in graph.alerts if a.id == alert.id), None)
                            if graph_alert:
                                if verification.get("is_contradiction", True):
                                    # K2 confirms
                                    graph_alert.message = f"K2 verified: {verification.get('explanation')}"
                                    graph_alert.metadata["k2_verified"] = True
                                    graph_alert.metadata["k2_confidence"] = verification.get("confidence", 0.0)
                                    graph_alert.metadata.pop("pending_k2", None)
                                else:
                                    # K2 overrides
                                    override = K2Override(
                                        id=f"k2o{len(graph.k2_overrides) + 1}",
                                        alert_id=alert.id,
                                        override_type="false_positive",
                                        original_severity=alert.severity,
                                        k2_severity="none",
                                        reason=verification.get("explanation", ""),
                                        confidence=verification.get("confidence", 0.0),
                                        timestamp=datetime.now()
                                    )
                                    graph.k2_overrides.append(override)
                                    k2_overrides += 1

                                    # Remove alert from graph (K2 rejected it)
                                    graph.alerts = [a for a in graph.alerts if a.id != alert.id]

        # Update metadata
        graph.metadata["k2_processing_pending"] = False

        # Only set k2_processing_complete if NOT using timer-based demo mode
        # If k2_poll_start_time exists, timer controls the completion state
        if not graph.metadata.get("k2_poll_start_time"):
            graph.metadata["k2_processing_complete"] = True

        graph.metadata["last_k2_update"] = datetime.now().isoformat()
        graph.metadata["async_k2_calls"] = k2_calls_made
        graph.metadata["async_k2_overrides"] = k2_overrides

        logger.info(
            f"[Async K2] Completed for {conversation_id}: "
            f"{k2_calls_made} calls, {k2_overrides} overrides"
        )

    except Exception as e:
        logger.error(f"[Async K2] Processing failed for {conversation_id}: {e}")
        graph.metadata["k2_processing_pending"] = False
        graph.metadata["k2_processing_error"] = str(e)
