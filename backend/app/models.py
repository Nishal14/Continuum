"""
Pydantic models for Continuum's Commitment Graph.

This module defines the core data structures for representing
conversations, commitments, assumptions, and epistemic drift alerts.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal, Any
from datetime import datetime
import hashlib
import json


class Turn(BaseModel):
    """A single conversation turn (user or model message)."""
    id: int
    speaker: Literal["user", "model"]
    text: str
    ts: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Assumption(BaseModel):
    """An implicit or explicit assumption underlying a commitment."""
    id: str  # e.g., "A1", "A2"
    text: str
    introduced_by_turn: int
    confidence: float = Field(0.5, ge=0.0, le=1.0)


class Commitment(BaseModel):
    """
    A claim, position, goal, or assumption extracted from a turn.

    Represents a statement that can be tracked for consistency over time.
    """
    id: str  # e.g., "c1", "c2"
    turn_id: int
    kind: Literal["claim", "position", "goal", "assumption"]
    normalized: str  # Canonical text for matching/comparison
    polarity: Optional[Literal["positive", "negative", "neutral"]] = "neutral"
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    assumptions: List[str] = []  # List of assumption IDs
    sources: List[str] = []  # Source turn IDs or external refs
    timestamp: datetime

    # Phase 2: Epistemic state tracking
    active: bool = True
    overridden_by: Optional[str] = None
    contradicted_by: List[str] = []
    stability_score: float = 1.0

    # Phase 4 (Drift Accumulator): Dependency tracking
    depended_on_by: List[str] = []  # Which commitments depend on this one

    # Topic-Anchor Based Detection: Primary topic for contradiction matching
    topic_anchor: Optional[str] = None  # e.g., "python", "microservices", "typescript"

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Edge(BaseModel):
    """
    A relationship between two commitments in the graph.

    Represents logical dependencies, support, or contradictions.
    """
    source: str  # Commitment ID
    target: str  # Commitment ID
    relation: Literal["supports", "contradicts", "depends_on", "refines", "questions"]
    weight: float = Field(0.5, ge=0.0, le=1.0)
    detected_at_turn: Optional[int] = None


class DriftEvent(BaseModel):
    """Individual drift measurement contributing to cumulative drift."""
    id: str
    commitment_a: str  # Earlier commitment ID
    commitment_b: str  # Later commitment ID
    similarity: float
    confidence_delta: float
    recency_weight: float
    dependency_depth: int
    drift_magnitude: float
    detected_at_turn: int
    timestamp: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class StancePoint(BaseModel):
    """Stance measurement at a point in time."""
    topic: str
    stance: float = Field(ge=-1.0, le=1.0)  # -1.0 (strongly negative) to +1.0 (strongly positive)
    turn_id: int
    confidence: float = Field(ge=0.0, le=1.0)
    timestamp: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TopicCluster(BaseModel):
    """Group of semantically related commitments."""
    topic_id: str
    topic_label: str
    commitment_ids: List[str]
    centroid_text: Optional[str] = None
    first_seen_turn: int
    last_updated_turn: int


class Alert(BaseModel):
    """A detected instance of epistemic drift or inconsistency."""
    id: str
    severity: Literal["low", "medium", "high", "critical"]
    alert_type: Literal[
        "polarity_flip",
        "assumption_drop",
        "agreement_bias",
        "confidence_drift",
        "circular_reasoning",
        "incomplete_reconciliation"
    ]
    message: str
    related_commitments: List[str]  # Commitment IDs involved
    related_turns: List[int]
    detected_at_turn: int
    suggested_action: Optional[str] = None  # Human-readable suggestion
    timestamp: datetime

    # Phase 3: Track K2 verification status
    metadata: Dict[str, Any] = {}  # Can store "pending_k2", "k2_verified", etc.

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class EscalationDecision(BaseModel):
    """Decision from escalation policy."""
    should_escalate: bool
    escalation_reason: str
    urgency: Literal["immediate", "high", "medium", "low"]
    confidence: float
    triggering_factors: List[str]
    timestamp: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class K2Override(BaseModel):
    """Detailed K2 override event."""
    id: str
    alert_id: str
    override_type: Literal["false_positive", "severity_downgrade", "severity_upgrade"]
    original_severity: str
    k2_severity: str
    reason: str
    confidence: float
    timestamp: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class K2VerificationResult(BaseModel):
    """Expanded K2 verification result."""
    is_contradiction: bool
    contradiction_type: Literal[
        "direct_contradiction",
        "refinement",
        "contextual_shift",
        "scope_change",
        "temporal_update"
    ]
    confidence: float
    explanation: str
    severity_adjustment: Optional[Literal["upgrade", "downgrade", "maintain"]] = None
    recommended_severity: Optional[str] = None
    override_reason: Optional[str] = None
    reconciliation_needed: bool = True
    suggested_reconciliation: Optional[str] = None


class CommitmentGraph(BaseModel):
    """
    The complete state of a conversation's commitment graph.

    Tracks all turns, extracted commitments, assumptions, relationships,
    and detected alerts.
    """
    conversation_id: str
    turns: List[Turn] = []
    commitments: List[Commitment] = []
    assumptions: List[Assumption] = []
    edges: List[Edge] = []
    alerts: List[Alert] = []
    metadata: Dict = {}

    # Phase 3: K2 authority tracking
    k2_overrides: List[K2Override] = []

    # Phase 3: Versioning for race condition handling
    version: int = 0
    k2_processing_version: Optional[int] = None

    # Phase 4 (Drift Accumulator): Drift accumulation fields
    epistemic_drift_score: float = 0.0
    last_stable_version: int = 0
    drift_events: List[DriftEvent] = []
    drift_velocity: float = 0.0
    last_drift_update_turn: int = 0
    turns_since_last_drift: int = 0

    # Phase 4 (Drift Accumulator): Topic tracking
    topic_stance_history: Dict[str, List[StancePoint]] = {}
    topic_clusters: List[TopicCluster] = []

    def compute_hash(self) -> str:
        """
        Compute a stable hash of the graph for caching.

        Returns a SHA256 hash based on turn IDs and commitment IDs.
        Useful for detecting when re-analysis is needed.
        """
        fingerprint = {
            "conversation_id": self.conversation_id,
            "turn_ids": [t.id for t in self.turns],
            "commitment_ids": [c.id for c in self.commitments],
            "alert_ids": [a.id for a in self.alerts]
        }
        hash_input = json.dumps(fingerprint, sort_keys=True)
        return hashlib.sha256(hash_input.encode()).hexdigest()

    def get_commitment(self, commitment_id: str) -> Optional[Commitment]:
        """Retrieve a commitment by ID."""
        for c in self.commitments:
            if c.id == commitment_id:
                return c
        return None

    def get_turn(self, turn_id: int) -> Optional[Turn]:
        """Retrieve a turn by ID."""
        for t in self.turns:
            if t.id == turn_id:
                return t
        return None

    def latest_turn_id(self) -> int:
        """Get the ID of the most recent turn."""
        return max([t.id for t in self.turns]) if self.turns else 0

    def deactivate_commitment(self, commitment_id: str, by_id: str) -> None:
        """
        Deactivate a commitment and mark it as overridden.

        Args:
            commitment_id: ID of commitment to deactivate
            by_id: ID of commitment that overrides this one
        """
        commitment = self.get_commitment(commitment_id)
        if commitment:
            commitment.active = False
            commitment.overridden_by = by_id

    def get_active_commitments(self) -> List[Commitment]:
        """Get all currently active commitments."""
        return [c for c in self.commitments if c.active]

    def count_contradictions(self) -> int:
        """Count total number of contradiction relationships in graph."""
        return sum(1 for e in self.edges if e.relation == "contradicts")


# API Request/Response Models

class AnalyzeTurnRequest(BaseModel):
    """Request to analyze a new conversation turn."""
    conversation_id: str
    new_turn: Turn
    last_graph_hash: Optional[str] = None  # For cache validation


class AnalyzeTurnResponse(BaseModel):
    """Response with updated graph and any new alerts."""
    updated_graph: CommitmentGraph
    alerts: List[Alert]
    suggested_message: Optional[str] = None
    cost_estimate: Dict[str, Any] = {"k2_calls": 0, "tokens_used": 0}  # Phase 3: Allow mixed types
    cache_hit: bool = False


class ReconcileRequest(BaseModel):
    """Request to generate a reconciliation message."""
    conversation_id: str
    alert_id: str
    mode: Literal["suggest", "auto"] = "suggest"
    user_api_key: Optional[str] = None  # For auto-send mode


class ReconcileResponse(BaseModel):
    """Response with reconciliation message and updated graph."""
    reconciliation_response: str
    updated_graph: CommitmentGraph
    resolved: bool = False
    cost_estimate: Dict[str, int] = {"k2_calls": 0}


# Heuristic Detection Models

class HeuristicScore(BaseModel):
    """Score from local heuristic analysis (before K2 call)."""
    alert_type: str
    score: float = Field(0.0, ge=0.0, le=1.0)
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    reason: str
    should_escalate_to_k2: bool = False
    related_commitments: List[str] = []
