"""
Escalation configuration with environment variable loading.
"""

import os
from pydantic import BaseModel
from typing import Dict, Optional


class EscalationConfig(BaseModel):
    """
    Global escalation policy configuration.

    Thresholds determine when heuristic findings warrant K2 verification.
    """

    # Similarity threshold (Jaccard index)
    high_similarity_threshold: float = 0.7  # Polarity flip similarity > 0.7 triggers escalation

    # Stability threshold
    stability_threshold: float = 0.4  # Stability score < 0.4 indicates epistemic degradation

    # Contradiction accumulation
    contradiction_accumulation_threshold: int = 3  # 3+ contradictions in window triggers escalation

    # Confidence delta threshold
    confidence_delta_threshold: float = 0.5  # Confidence shift > 0.5 combined with similarity

    # Overall escalation threshold
    escalation_threshold: float = 0.6  # Escalation score must exceed 0.6 to escalate

    # Urgency settings
    immediate_severity_trigger: bool = True  # Critical severity always triggers immediate escalation

    # Phase 4 (Drift Accumulator): Drift escalation thresholds
    drift_escalation_threshold: float = 2.0  # Cumulative drift > 2.0 triggers escalation
    drift_velocity_threshold: float = 0.4  # Drift velocity > 0.4 (drift/turn) triggers immediate
    structural_break_threshold: int = 3  # >= 3 dependent commitments = structural break
    stance_instability_threshold: float = 0.5  # Stance variance > 0.5 = unstable

    # Phase 4 (Drift Accumulator): Drift decay settings
    drift_decay_factor: float = 0.95  # 5% decay per stable turn
    stability_threshold_turns: int = 3  # Consecutive stable turns before decay kicks in

    @classmethod
    def from_env(cls) -> "EscalationConfig":
        """
        Load configuration from environment variables.

        Environment variables:
        - ESCALATION_SIMILARITY_THRESHOLD: High similarity threshold (default: 0.7)
        - ESCALATION_STABILITY_THRESHOLD: Stability drop threshold (default: 0.4)
        - ESCALATION_CONTRADICTION_THRESHOLD: Contradiction accumulation (default: 3)
        - ESCALATION_CONFIDENCE_DELTA: Confidence delta threshold (default: 0.5)
        - ESCALATION_THRESHOLD: Overall escalation threshold (default: 0.6)
        - DRIFT_ESCALATION_THRESHOLD: Cumulative drift threshold (default: 2.0)
        - DRIFT_VELOCITY_THRESHOLD: Drift velocity threshold (default: 0.4)
        - STRUCTURAL_BREAK_THRESHOLD: Structural break threshold (default: 3)
        - STANCE_INSTABILITY_THRESHOLD: Stance instability threshold (default: 0.5)
        - DRIFT_DECAY_FACTOR: Drift decay factor (default: 0.95)
        - STABILITY_THRESHOLD_TURNS: Stability threshold turns (default: 3)

        Returns:
            EscalationConfig instance with loaded values
        """
        return cls(
            high_similarity_threshold=float(
                os.getenv("ESCALATION_SIMILARITY_THRESHOLD", "0.7")
            ),
            stability_threshold=float(
                os.getenv("ESCALATION_STABILITY_THRESHOLD", "0.4")
            ),
            contradiction_accumulation_threshold=int(
                os.getenv("ESCALATION_CONTRADICTION_THRESHOLD", "3")
            ),
            confidence_delta_threshold=float(
                os.getenv("ESCALATION_CONFIDENCE_DELTA", "0.5")
            ),
            escalation_threshold=float(
                os.getenv("ESCALATION_THRESHOLD", "0.6")
            ),
            drift_escalation_threshold=float(
                os.getenv("DRIFT_ESCALATION_THRESHOLD", "2.0")
            ),
            drift_velocity_threshold=float(
                os.getenv("DRIFT_VELOCITY_THRESHOLD", "0.4")
            ),
            structural_break_threshold=int(
                os.getenv("STRUCTURAL_BREAK_THRESHOLD", "3")
            ),
            stance_instability_threshold=float(
                os.getenv("STANCE_INSTABILITY_THRESHOLD", "0.5")
            ),
            drift_decay_factor=float(
                os.getenv("DRIFT_DECAY_FACTOR", "0.95")
            ),
            stability_threshold_turns=int(
                os.getenv("STABILITY_THRESHOLD_TURNS", "3")
            )
        )
