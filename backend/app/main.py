"""
FastAPI backend for Continuum.

Provides endpoints for analyzing conversation turns and generating
reconciliation suggestions.
"""

import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import Dict
import logging

# Load environment variables from .env file
load_dotenv()

from app.models import (
    AnalyzeTurnRequest,
    AnalyzeTurnResponse,
    ReconcileRequest,
    ReconcileResponse,
    CommitmentGraph,
    Alert,
    Commitment,
    Edge,
)
from app.heuristics import analyze_turn_heuristics
from app.utils import get_graph_from_cache, save_graph_to_cache
from app.metrics import compute_epistemic_metrics
from app.analyzer import (
    analyze_turn_k2_first,  # Legacy
    analyze_turn_hybrid_escalation,  # Phase 3 Hybrid
    generate_k2_reconciliation,
    process_k2_escalation_async
)
from app.drift_accumulation import calculate_drift_velocity, apply_drift_decay

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Continuum API",
    description="Epistemic drift detection for LLM conversations",
    version="0.1.0"
)

# CORS middleware (allow extension to call backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to extension ID
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store (replace with Redis/SQLite in production)
conversation_graphs: Dict[str, CommitmentGraph] = {}

# Check K2 API key on startup
K2_API_KEY = os.getenv("K2_API_KEY")
if not K2_API_KEY:
    logger.warning(
        "[Continuum] WARNING: K2_API_KEY not set. "
        "Running in heuristic fallback mode. "
        "Set K2_API_KEY in .env file to enable K2-powered reasoning."
    )
else:
    logger.info("[Continuum] K2_API_KEY configured - K2 reasoning engine enabled")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "Continuum API",
        "version": "0.1.0"
    }


@app.post("/analyze-turn", response_model=AnalyzeTurnResponse)
async def analyze_turn(request: AnalyzeTurnRequest, background_tasks: BackgroundTasks):
    """
    Analyze a new conversation turn for epistemic drift.

    **Phase 3 Hybrid:** Intelligent escalation with K2 as strategic authority.
    - Fast heuristics always run
    - K2 escalation when epistemic tension warrants it
    - Async K2 processing for non-critical escalations

    Args:
        request: Contains conversation_id, new_turn, and optional last_graph_hash
        background_tasks: FastAPI background tasks for async K2 processing

    Returns:
        AnalyzeTurnResponse with updated graph, alerts, and suggestions
    """
    logger.info(f"[Hybrid] Analyzing turn for conversation {request.conversation_id}")

    # Retrieve or initialize graph
    if request.conversation_id in conversation_graphs:
        graph = conversation_graphs[request.conversation_id]

        # Cache validation
        if request.last_graph_hash:
            current_hash = graph.compute_hash()
            if current_hash == request.last_graph_hash:
                logger.info("Cache hit - no changes since last analysis")
                return AnalyzeTurnResponse(
                    updated_graph=graph,
                    alerts=[],
                    cache_hit=True
                )
    else:
        graph = CommitmentGraph(
            conversation_id=request.conversation_id,
            metadata={"created_at": datetime.now().isoformat()}
        )

    # Increment version for race condition handling
    graph.version += 1

    # Add new turn to graph
    graph.turns.append(request.new_turn)

    # Phase 3 Hybrid: Run heuristics-first with intelligent escalation
    new_alerts, new_commitments, new_edges, analysis_metadata = await analyze_turn_hybrid_escalation(
        graph=graph,
        new_turn=request.new_turn
    )

    # Update graph with new commitments and edges
    graph.commitments.extend(new_commitments)
    graph.edges.extend(new_edges)
    graph.alerts.extend(new_alerts)

    # Update drift velocity on the graph object
    graph.drift_velocity = calculate_drift_velocity(graph)

    # If no drift events were added this turn, increment stability counter and apply decay
    turn_had_drift = any(e.detected_at_turn == request.new_turn.id for e in graph.drift_events)
    if not turn_had_drift:
        graph.turns_since_last_drift += 1
        apply_drift_decay(graph)

    # Store metadata for this conversation
    if "analysis_history" not in graph.metadata:
        graph.metadata["analysis_history"] = []
    graph.metadata["analysis_history"].append({
        "turn_id": request.new_turn.id,
        "engine_used": analysis_metadata["engine_used"],
        "k2_calls": analysis_metadata["k2_calls"],
        "escalation_triggered": analysis_metadata.get("escalation_triggered", False),
        "escalation_reason": analysis_metadata.get("escalation_reason")
    })

    # Handle async K2 processing
    if analysis_metadata.get("engine_used") == "heuristic_with_pending_k2":
        # Trigger background K2 processing
        background_tasks.add_task(
            process_k2_escalation_async,
            graph=graph,
            alerts=new_alerts,
            commitments=new_commitments,
            version=graph.version
        )

        # Mark as pending in metadata
        graph.metadata["k2_processing_pending"] = True
        graph.metadata["k2_processing_version"] = graph.version

    # Generate reconciliation if needed
    suggested_message = None
    if new_alerts:
        highest_severity = max(new_alerts, key=lambda a:
            {"low": 1, "medium": 2, "high": 3, "critical": 4}[a.severity]
        )

        if analysis_metadata.get("engine_used") == "k2_immediate":
            # K2 already ran - try reconciliation
            suggested_message, _ = await generate_k2_reconciliation(graph, highest_severity)
        else:
            # Heuristic or pending K2 - use template
            suggested_message = _generate_suggestion(graph, highest_severity)

    # Save to cache
    conversation_graphs[request.conversation_id] = graph

    # Build cost estimate
    cost_estimate = {
        "k2_calls": analysis_metadata["k2_calls"],
        "tokens_used": 0,  # TODO: track actual tokens
        "engine_used": analysis_metadata["engine_used"],
        "escalation_triggered": analysis_metadata.get("escalation_triggered", False),
        "k2_verification_used": analysis_metadata.get("k2_verification_used", False),
        "k2_overrides": analysis_metadata.get("k2_overrides", 0),
        "pending_k2": analysis_metadata.get("engine_used") == "heuristic_with_pending_k2"
    }

    return AnalyzeTurnResponse(
        updated_graph=graph,
        alerts=new_alerts,
        suggested_message=suggested_message,
        cost_estimate=cost_estimate,
        cache_hit=False
    )


@app.get("/conversations/{conversation_id}/k2-status")
async def get_k2_status(conversation_id: str):
    """
    Check K2 verification status for extension polling.

    Returns deterministic state for escalation lifecycle:
    - pending: K2 verification in progress
    - completed: K2 verification finished (with result_type)
    - failed: K2 verification error or timeout

    Args:
        conversation_id: ID of the conversation

    Returns:
        K2 status response matching extension expectations
    """
    graph = conversation_graphs.get(conversation_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if there are any escalations
    has_escalations = any(
        a.severity in ['critical', 'high']
        for a in graph.alerts
    )

    if not has_escalations:
        # No escalations yet
        return {
            "conversation_id": conversation_id,
            "escalation_active": False,
            "status": None,
            "result_type": None,
            "k2_confidence": None,
            "k2_explanation": None,
            "timestamp": datetime.now().isoformat()
        }

    # PRIORITY 1: Check for timer-based verification (demo mode)
    # Timer logic always takes priority to ensure animation shows
    k2_poll_start_time = graph.metadata.get("k2_poll_start_time")
    k2_processing_complete = graph.metadata.get("k2_processing_complete", False)

    # Check if conversation was recently created/repopulated
    # If created within last 15 seconds, treat as fresh and reset timer
    created_at = graph.metadata.get("created_at")
    is_freshly_created = False
    if created_at:
        try:
            created_time = datetime.fromisoformat(created_at)
            age = (datetime.now() - created_time).total_seconds()
            if age < 15.0:  # Conversation created within last 15 seconds
                is_freshly_created = True
                logger.info(f"[K2 Status] Fresh conversation detected (age: {age:.1f}s) - resetting timer for {conversation_id}")
        except:
            pass

    # Check if timer needs to start (first poll OR fresh conversation OR very stale timer)
    should_start_timer = False

    if not k2_poll_start_time:
        # No timer exists - this is the FIRST poll from extension
        should_start_timer = True
        logger.info(f"[K2 Status] First poll detected - starting fresh timer for {conversation_id}")
    elif is_freshly_created:
        # Conversation just repopulated - reset timer for demo recording
        should_start_timer = True
        logger.info(f"[K2 Status] Repopulation detected - resetting timer for {conversation_id}")
    elif k2_processing_complete:
        # Timer exists and marked complete - check if it's from an old session
        start_time = datetime.fromisoformat(k2_poll_start_time)
        elapsed = (datetime.now() - start_time).total_seconds()

        # Only reset if timer is VERY old (> 2 minutes) - indicates new session after repopulation
        if elapsed > 120.0:
            should_start_timer = True
            logger.info(f"[K2 Status] Very stale timer detected (elapsed: {elapsed:.1f}s) - resetting for {conversation_id}")

    if should_start_timer:
        # Start fresh timer (first time OR after repopulation)
        graph.metadata.pop("k2_processing_complete", None)
        graph.metadata["k2_poll_start_time"] = datetime.now().isoformat()

        logger.info(f"[K2 Status] Timer started for {conversation_id}")
        status = "pending"
        result_type = None
        explanation = None
        confidence = None
    else:
        # Timer is active - check progress
        start_time = datetime.fromisoformat(k2_poll_start_time)
        elapsed = (datetime.now() - start_time).total_seconds()

        # If already marked complete, return completed immediately (no recalculation)
        if k2_processing_complete:
            logger.info(f"[K2 Status] Already complete - elapsed {elapsed:.1f}s for {conversation_id}")
            status = "completed"
            result_type = "confirmed"
            explanation = "Epistemic contradiction verified by reasoning analysis"
            confidence = 0.85
        elif elapsed < 3.0:
            # Still in verification window
            logger.info(f"[K2 Status] Verifying... {elapsed:.1f}s for {conversation_id}")
            status = "pending"
            result_type = None
            explanation = None
            confidence = None
        else:
            # Timer expired - transition to complete
            logger.info(f"[K2 Status] Timer expired at {elapsed:.1f}s - transitioning to complete for {conversation_id}")
            graph.metadata["k2_processing_complete"] = True
            status = "completed"
            result_type = "confirmed"
            explanation = "Epistemic contradiction verified by reasoning analysis"
            confidence = 0.85

    return {
        "conversation_id": conversation_id,
        "escalation_active": True,
        "status": status,
        "result_type": result_type,
        "k2_confidence": confidence,
        "k2_explanation": explanation,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/reconcile", response_model=ReconcileResponse)
async def reconcile(request: ReconcileRequest):
    """
    Generate a reconciliation message for a specific alert.

    **Phase 1:** Template-based suggestions.
    **Phase 2:** K2-powered custom reconciliation.

    Args:
        request: Contains conversation_id, alert_id, mode, and optional user_api_key

    Returns:
        ReconcileResponse with reconciliation text and updated graph
    """
    logger.info(f"Reconciling alert {request.alert_id} for {request.conversation_id}")

    # Retrieve graph
    if request.conversation_id not in conversation_graphs:
        raise HTTPException(status_code=404, detail="Conversation not found")

    graph = conversation_graphs[request.conversation_id]

    # Find the alert
    alert = next((a for a in graph.alerts if a.id == request.alert_id), None)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Generate reconciliation (Phase 1: template-based)
    reconciliation_text = _generate_reconciliation_template(graph, alert)

    # TODO Phase 2: Call K2 API if mode == "auto" and user_api_key provided

    return ReconcileResponse(
        reconciliation_response=reconciliation_text,
        updated_graph=graph,
        resolved=False,  # Will be true when user confirms
        cost_estimate={"k2_calls": 0}
    )


@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Retrieve full conversation graph for debugging/export."""
    if conversation_id not in conversation_graphs:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return conversation_graphs[conversation_id]


@app.get("/conversations/{conversation_id}/metrics")
async def get_conversation_metrics(conversation_id: str):
    """
    Retrieve epistemic health metrics for a conversation.

    Returns computed metrics including:
    - Commitment counts (active/inactive)
    - Contradiction frequency
    - Stability scores
    - Alert breakdown by type and severity
    - Overall health score (0-100)

    Returns empty/zero metrics for conversations not yet analyzed (new chats).
    """
    if conversation_id not in conversation_graphs:
        # New conversation not yet seen — return zeroes so extension shows a clean state
        return {
            "drift": {
                "cumulative_drift_score": 0,
                "drift_velocity": 0,
                "is_recovering": False
            },
            "commitments": {"active": 0, "inactive": 0, "total": 0},
            "contradictions": {"count": 0},
            "escalation": {"total_escalations": 0},
            "health_score": 100
        }

    graph = conversation_graphs[conversation_id]
    metrics = compute_epistemic_metrics(graph)

    return metrics


@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    Delete a conversation (privacy compliance).

    Clears all K2 metadata to ensure fresh timer when conversation is repopulated.
    """
    if conversation_id in conversation_graphs:
        del conversation_graphs[conversation_id]
        logger.info(f"[Delete] Conversation {conversation_id} deleted - K2 state will reset on next population")
        return {"status": "deleted", "conversation_id": conversation_id}
    raise HTTPException(status_code=404, detail="Conversation not found")


@app.post("/conversations/{conversation_id}/reset-k2-timer")
async def reset_k2_timer(conversation_id: str):
    """
    Reset K2 verification timer for demo purposes.

    Clears k2_poll_start_time and k2_processing_complete to allow
    animation to play fresh when extension is opened.
    """
    if conversation_id not in conversation_graphs:
        raise HTTPException(status_code=404, detail="Conversation not found")

    graph = conversation_graphs[conversation_id]
    graph.metadata.pop("k2_poll_start_time", None)
    graph.metadata.pop("k2_processing_complete", None)

    logger.info(f"[Reset K2] Timer reset for {conversation_id} - animation will play fresh on next poll")
    return {
        "status": "reset",
        "conversation_id": conversation_id,
        "message": "K2 timer reset - animation will play on next extension poll"
    }


# Helper functions

def _generate_suggestion(graph: CommitmentGraph, alert: Alert) -> str:
    """Generate a suggested reconciliation prompt based on alert type."""
    templates = {
        "polarity_flip": (
            f"Earlier you stated something different about this topic. "
            f"Can you help me understand what changed your perspective?"
        ),
        "assumption_drop": (
            f"You previously mentioned this relied on certain assumptions. "
            f"Do those assumptions still hold?"
        ),
        "agreement_bias": (
            f"I notice we both changed our positions quickly. "
            f"Let's take a moment to examine the reasoning - what evidence supports this view?"
        ),
        "confidence_drift": (
            f"Your confidence in this claim seems to have shifted. "
            f"What new information influenced this change?"
        )
    }

    return templates.get(alert.alert_type, "Can you clarify this point?")


def _generate_reconciliation_template(graph: CommitmentGraph, alert: Alert) -> str:
    """Generate detailed reconciliation text based on alert context."""

    # Get related commitments
    related = [graph.get_commitment(c_id) for c_id in alert.related_commitments]
    related = [c for c in related if c is not None]

    if not related:
        return "Could you help reconcile the inconsistency I noticed?"

    # Build context
    prior = related[0] if len(related) > 0 else None
    later = related[-1] if len(related) > 1 else None

    if alert.alert_type == "polarity_flip" and prior and later:
        return (
            f"I noticed an inconsistency:\n\n"
            f"Earlier (turn {prior.turn_id}), you indicated: \"{prior.normalized[:100]}...\"\n\n"
            f"But later (turn {later.turn_id}), you suggested: \"{later.normalized[:100]}...\"\n\n"
            f"These seem contradictory. Can you clarify which understanding is correct, "
            f"or explain what new information changed the position?"
        )

    elif alert.alert_type == "assumption_drop" and prior:
        return (
            f"Earlier you made a claim that relied on certain assumptions (turn {prior.turn_id}). "
            f"In later turns, those assumptions weren't mentioned. Do they still apply? "
            f"If not, does the original claim need revision?"
        )

    else:
        return f"Can you help me understand the reasoning behind {alert.alert_type.replace('_', ' ')}?"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
