"""
Local heuristics for epistemic drift detection.

These cheap, deterministic rules detect common patterns without API calls:
- Polarity flips (claim contradictions)
- Assumption drops (missing prerequisites)
- Agreement bias (rapid stance alignment)
- Confidence drift (suspicious confidence changes)
"""

import re
from datetime import datetime
from typing import List, Tuple, Optional
from app.models import (
    CommitmentGraph,
    Turn,
    Commitment,
    Alert,
    Edge,
    HeuristicScore
)
from app.structural_analysis import infer_polarity_structural
from app.drift_accumulation import accumulate_drift


def analyze_turn_heuristics(
    graph: CommitmentGraph,
    new_turn: Turn
) -> Tuple[List[Alert], List[Commitment], List[Edge]]:
    """
    Analyze a new turn using local heuristics.

    Returns:
        (new_alerts, new_commitments, new_edges)
    """
    new_alerts = []
    new_commitments = []
    new_edges = []

    # Extract commitments from new turn (simple regex-based)
    extracted = extract_commitments_simple(new_turn, graph)
    new_commitments.extend(extracted)

    # Run drift detection heuristics
    for commitment in extracted:
        print(f"[DEBUG] Analyzing commitment {commitment.id}: topic={commitment.topic_anchor}, polarity={commitment.polarity}, text={commitment.normalized[:50]}")
        # Check for polarity flips
        polarity_alert, polarity_edge = detect_polarity_flip(graph, commitment)
        if polarity_alert:
            new_alerts.append(polarity_alert)
        if polarity_edge:
            new_edges.append(polarity_edge)
            print(f"[DEBUG] Added edge to new_edges list: {polarity_edge.source} -> {polarity_edge.target}")

        # Check for assumption drops
        assumption_alert = detect_assumption_drop(graph, commitment)
        if assumption_alert:
            new_alerts.append(assumption_alert)

        # Check for agreement bias
        if len(graph.turns) >= 2:
            agreement_alert = detect_agreement_bias(graph, commitment)
            if agreement_alert:
                new_alerts.append(agreement_alert)

        # Check for confidence drift
        confidence_alert = detect_confidence_drift(graph, commitment)
        if confidence_alert:
            new_alerts.append(confidence_alert)

    return new_alerts, new_commitments, new_edges


def extract_commitments_simple(turn: Turn, graph: CommitmentGraph) -> List[Commitment]:
    """
    Extract commitments using simple pattern matching.

    Phase 1: Regex and keyword-based extraction.
    Phase 2: Replace with K2-powered structured extraction.
    """
    commitments = []
    text = turn.text.strip()

    # Skip trivial messages
    trivial_patterns = [
        r"^(ok|okay|yes|no|thanks|sure|got it)\.?$",
        r"^[👍👎😊🙂]+$"  # emoji-only
    ]
    if any(re.match(p, text, re.IGNORECASE) for p in trivial_patterns):
        return []

    # Detect claim patterns
    claim_patterns = [
        (r"(?:I think|I believe|It seems|It appears) (.+)", "claim"),
        (r"(?:The fact is|Actually|In reality) (.+)", "claim"),
        (r"(?:We should|We must|Let's) (.+)", "goal"),
        (r"(?:Assuming|Given that|If) (.+)", "assumption"),
    ]

    for pattern, kind in claim_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            normalized_text = match.strip()
            commitment = Commitment(
                id=f"c{len(graph.commitments) + len(commitments) + 1}",
                turn_id=turn.id,
                kind=kind,
                normalized=normalized_text,
                polarity=_infer_polarity(match),
                confidence=_infer_confidence(text),
                topic_anchor=extract_topic_anchor(normalized_text),  # Extract topic anchor
                timestamp=turn.ts
            )
            commitments.append(commitment)

    # If no patterns matched, create a generic claim
    if not commitments and len(text) > 20:
        normalized_text = text[:200]  # First 200 chars
        commitments.append(Commitment(
            id=f"c{len(graph.commitments) + 1}",
            turn_id=turn.id,
            kind="claim",
            normalized=normalized_text,
            polarity=_infer_polarity(text),  # Infer from text, don't hardcode!
            confidence=_infer_confidence(text),
            topic_anchor=extract_topic_anchor(normalized_text),  # Extract topic anchor
            timestamp=turn.ts
        ))

    return commitments


def detect_polarity_flip(graph: CommitmentGraph, commitment: Commitment) -> Tuple[Alert | None, Edge | None]:
    """
    Detect if a commitment contradicts a prior commitment.

    Topic-Anchor Based Detection:
    - PRIMARY GATE: topic_anchor must match
    - SECONDARY CONDITION: polarity must differ
    - Similarity becomes optional severity weight

    Logic:
    1. Compare against last N active commitments
    2. Match on topic_anchor (e.g., "python", "microservices")
    3. If anchor matches AND polarity differs → contradiction
    4. Compute drift magnitude with anchor-weighted formula
    """
    if commitment.confidence < 0.3:
        return None  # Too uncertain to flag

    # Skip if no topic anchor extracted
    if not commitment.topic_anchor:
        return None

    # Get the turn for this commitment to check original text
    current_turn = graph.get_turn(commitment.turn_id)
    if not current_turn:
        return None

    # Check for explicit contradiction markers in ORIGINAL turn text
    contradiction_markers = ["actually", "but", "however", "instead", "rather", "on the other hand"]
    has_marker = any(m in current_turn.text.lower() for m in contradiction_markers)

    # Get last N active commitments (longitudinal window)
    active_prior_commitments = [
        c for c in graph.commitments
        if c.turn_id < commitment.turn_id and c.active
    ]
    # Sort by turn_id descending, take last 10 (expanded window for topic matching)
    active_prior_commitments.sort(key=lambda c: c.turn_id, reverse=True)
    recent_priors = active_prior_commitments[:10]

    best_match = None
    best_severity_score = 0.0

    for prior in recent_priors:
        # PRIMARY GATE: Topic anchor must match
        if not prior.topic_anchor:
            continue  # Skip commitments without topic anchor

        anchor_match = (prior.topic_anchor == commitment.topic_anchor)

        if not anchor_match:
            continue  # Skip - different topics

        # SECONDARY CONDITION: Check for polarity difference
        is_contradiction = False
        confidence_delta = abs(commitment.confidence - prior.confidence)

        # Only flag TRUE opposites (positive ↔ negative)
        # Neutral is not opposite to anything
        is_opposite_polarity = (
            (prior.polarity == "positive" and commitment.polarity == "negative") or
            (prior.polarity == "negative" and commitment.polarity == "positive")
        )

        if is_opposite_polarity:
            # True opposite polarity on SAME topic → contradiction
            is_contradiction = True
        elif has_marker and prior.polarity != commitment.polarity:
            # Explicit contradiction marker + polarity shift
            is_contradiction = True

        if is_contradiction:
            # Compute similarity as optional bonus weight
            similarity = _text_similarity(prior.normalized, commitment.normalized)

            # Recency weight
            turn_gap = commitment.turn_id - prior.turn_id
            max_turn_gap = len(graph.turns) if len(graph.turns) > 0 else 1
            recency = 1.0 - min(turn_gap / max_turn_gap, 1.0)

            # NEW FORMULA: Anchor match dominates
            # anchor_match_weight = 1.0 (already matched)
            severity_score = (
                0.5 * 1.0 +              # Anchor match (guaranteed 0.5)
                0.2 * confidence_delta + # Confidence shift
                0.2 * recency +          # Recency
                0.1 * similarity         # Optional similarity bonus
            )

            # Keep track of highest severity match
            if severity_score > best_severity_score:
                best_severity_score = severity_score
                best_match = (prior, similarity, confidence_delta, recency)

    if best_match:
        prior, similarity, confidence_delta, recency = best_match

        # Phase 4 (Drift Accumulator): Accumulate drift instead of immediate escalation
        drift_event = accumulate_drift(
            graph=graph,
            prior_commitment=prior,
            new_commitment=commitment,
            similarity=similarity,
            confidence_delta=confidence_delta,
            recency_weight=recency
        )

        # Map severity score to categorical severity
        if best_severity_score >= 0.7:
            severity = "critical"
        elif best_severity_score >= 0.5:
            severity = "high"
        elif best_severity_score >= 0.3:
            severity = "medium"
        else:
            severity = "low"

        # Phase 2: Update stability scores
        # Both prior and current commitments lose stability
        stability_penalty = best_severity_score * 0.3  # Max 30% penalty
        prior.stability_score = max(0.0, prior.stability_score - stability_penalty)
        commitment.stability_score = max(0.0, commitment.stability_score - stability_penalty)

        # Mark contradiction relationship
        commitment.contradicted_by.append(prior.id)

        # Build descriptive message
        if prior.polarity == "positive" and commitment.polarity == "negative":
            polarity_desc = "earlier claim was positive, now negative"
        elif prior.polarity == "negative" and commitment.polarity == "positive":
            polarity_desc = "earlier claim was negative, now positive"
        else:
            polarity_desc = "statement contradicts earlier claim"

        alert = Alert(
            id=f"a{len(graph.alerts) + 1}",
            severity=severity,
            alert_type="polarity_flip",
            message=f"Detected contradiction: {polarity_desc} (similarity: {similarity:.2f}, confidence shift: {confidence_delta:.2f}, drift_magnitude: {drift_event.drift_magnitude:.2f})",
            related_commitments=[prior.id, commitment.id],
            related_turns=[prior.turn_id, commitment.turn_id],
            detected_at_turn=commitment.turn_id,
            timestamp=datetime.now(),
            metadata={"drift_event_id": drift_event.id}
        )

        # Create contradiction edge for graph
        edge = Edge(
            source=commitment.id,
            target=prior.id,
            relation="contradicts",
            weight=best_severity_score,
            detected_at_turn=commitment.turn_id
        )

        print(f"[DEBUG] Created contradiction edge: {commitment.id} -> {prior.id}")

        return alert, edge

    return None, None


def detect_assumption_drop(graph: CommitmentGraph, commitment: Commitment) -> Alert | None:
    """
    Detect if a commitment is made without previously stated assumptions.

    Looks for prior assumptions that are no longer referenced.
    """
    # Find prior commitments with assumptions
    for prior in graph.commitments:
        if prior.turn_id >= commitment.turn_id:
            continue

        if not prior.assumptions:
            continue

        # Check if current commitment is related but missing assumptions
        similarity = _text_similarity(prior.normalized, commitment.normalized)

        if similarity > 0.6 and commitment.kind != "assumption":
            # Check if assumptions are still present
            assumption_texts = [a.text for a in graph.assumptions if a.id in prior.assumptions]

            if assumption_texts:
                return Alert(
                    id=f"a{len(graph.alerts) + 1}",
                    severity="medium",
                    alert_type="assumption_drop",
                    message=f"Prior claim relied on assumptions that are no longer mentioned",
                    related_commitments=[prior.id, commitment.id],
                    related_turns=[prior.turn_id, commitment.turn_id],
                    detected_at_turn=commitment.turn_id,
                    suggested_action=f"Verify if assumption still holds: {assumption_texts[0][:100]}",
                    timestamp=datetime.now()
                )

    return None


def detect_agreement_bias(graph: CommitmentGraph, commitment: Commitment) -> Alert | None:
    """
    Detect rapid stance alignment without justification.

    Heuristic: user and model flip positions within 2 turns of each other.
    """
    if len(graph.turns) < 3:
        return None

    recent_turns = graph.turns[-3:]
    recent_commitments = [c for c in graph.commitments if c.turn_id in [t.id for t in recent_turns]]

    # Check for user-model flip pattern
    user_flip = False
    model_flip = False

    for i in range(len(recent_commitments) - 1):
        curr = recent_commitments[i]
        next_c = recent_commitments[i + 1]

        curr_turn = graph.get_turn(curr.turn_id)
        next_turn = graph.get_turn(next_c.turn_id)

        if not curr_turn or not next_turn:
            continue

        similarity = _text_similarity(curr.normalized, next_c.normalized)

        if similarity > 0.5 and curr.polarity != next_c.polarity:
            if curr_turn.speaker == "user" and next_turn.speaker == "model":
                model_flip = True
            elif curr_turn.speaker == "model" and next_turn.speaker == "user":
                user_flip = True

    if user_flip and model_flip:
        return Alert(
            id=f"a{len(graph.alerts) + 1}",
            severity="medium",
            alert_type="agreement_bias",
            message="Both user and model changed positions rapidly without clear justification",
            related_commitments=[c.id for c in recent_commitments[-2:]],
            related_turns=[t.id for t in recent_turns[-2:]],
            detected_at_turn=commitment.turn_id,
            timestamp=datetime.now()
        )

    return None


def detect_confidence_drift(graph: CommitmentGraph, commitment: Commitment) -> Alert | None:
    """
    Detect suspicious changes in confidence levels.

    Flags when confidence changes by >0.4 on similar claims.
    """
    for prior in graph.commitments:
        if prior.turn_id >= commitment.turn_id:
            continue

        similarity = _text_similarity(prior.normalized, commitment.normalized)

        if similarity > 0.7:
            confidence_delta = abs(commitment.confidence - prior.confidence)

            if confidence_delta > 0.4:
                return Alert(
                    id=f"a{len(graph.alerts) + 1}",
                    severity="low",
                    alert_type="confidence_drift",
                    message=f"Confidence changed significantly: {prior.confidence:.1f} → {commitment.confidence:.1f}",
                    related_commitments=[prior.id, commitment.id],
                    related_turns=[prior.turn_id, commitment.turn_id],
                    detected_at_turn=commitment.turn_id,
                    timestamp=datetime.now()
                )

    return None


# Utility functions

def _text_similarity(text1: str, text2: str) -> float:
    """
    Compute simple token overlap similarity.

    Phase 1: Basic token intersection.
    Phase 2: Replace with sentence embeddings.
    """
    tokens1 = set(text1.lower().split())
    tokens2 = set(text2.lower().split())

    if not tokens1 or not tokens2:
        return 0.0

    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)

    return len(intersection) / len(union) if union else 0.0


def extract_topic_anchor(text: str) -> Optional[str]:
    """
    Extract primary topic anchor from text using simple heuristics.

    Topic anchor = the main noun/subject being discussed.

    Rules:
    1. Look for pattern: [subject] [copula verb] [predicate]
       e.g., "Python is best" → "python"
    2. Extract first content word after copula verbs (is, are, was, were)
    3. If no copula, take first 1-2 noun-like tokens
    4. Normalize: lowercase, strip punctuation

    Examples:
    - "Microservices are better for scaling" → "microservices"
    - "Python is the best language" → "python"
    - "I prefer TypeScript" → "typescript"
    - "Unit testing is essential" → "unit testing"

    Args:
        text: Input text

    Returns:
        Topic anchor string (normalized), or None if can't extract
    """
    if not text:
        return None

    # Normalize text
    text_lower = text.lower().strip()

    # Remove common punctuation at start/end
    text_lower = text_lower.strip('.,!?;:')

    # Common discourse markers to remove from start
    discourse_markers = ['actually', 'but', 'however', 'though', 'although', 'yet', 'still',
                        'instead', 'rather', 'on the other hand', 'in fact', 'meanwhile']

    # Remove discourse markers from the beginning (handle with or without comma)
    for marker in discourse_markers:
        # Check for "marker " or "marker, "
        if text_lower.startswith(marker + ' ') or text_lower.startswith(marker + ','):
            text_lower = text_lower[len(marker):].strip()
            text_lower = text_lower.lstrip(',').strip()
            break

    # Common copula verbs that signal subject-predicate structure
    copulas = ['is', 'are', 'was', 'were', 'be', 'being', 'been']

    # Common stop words to skip
    stop_words = {'i', 'the', 'a', 'an', 'to', 'for', 'of', 'in', 'on', 'at', 'by', 'with'}

    tokens = text_lower.split()
    if not tokens:
        return None

    # Strategy 1: Look for copula verb and extract subject before it
    for i, token in enumerate(tokens):
        if token in copulas and i > 0:
            # Extract subject before copula (1-2 tokens)
            if i >= 2 and tokens[i-2] not in stop_words:
                # Multi-word anchor (e.g., "unit testing")
                anchor = f"{tokens[i-2]} {tokens[i-1]}"
            else:
                # Single-word anchor
                anchor = tokens[i-1]

            # Clean and validate
            anchor = anchor.strip('.,!?;:\'\"')
            if anchor not in stop_words and len(anchor) > 2:
                return anchor

    # Strategy 2: Look for common patterns like "I prefer X", "X helps", etc.
    preference_verbs = ['prefer', 'like', 'love', 'hate', 'avoid', 'use', 'need', 'want']
    for i, token in enumerate(tokens):
        if token in preference_verbs and i < len(tokens) - 1:
            # Extract object after preference verb
            anchor = tokens[i+1].strip('.,!?;:\'\"')
            if anchor not in stop_words and len(anchor) > 2:
                return anchor

    # Strategy 3: Take first significant content word
    for token in tokens:
        cleaned = token.strip('.,!?;:\'\"')
        if cleaned not in stop_words and len(cleaned) > 2:
            # Check if it's likely a noun (very simple heuristic: not a common verb)
            common_verbs = {'think', 'believe', 'seems', 'appears', 'actually', 'however'}
            if cleaned not in common_verbs:
                return cleaned

    return None


def _infer_polarity(text: str) -> str:
    """
    Infer polarity from text using structural analysis.

    Phase 4 (Drift Accumulator): Uses structural_analysis.infer_polarity_structural()
    instead of keyword matching.
    """
    return infer_polarity_structural(text)


def _infer_confidence(text: str) -> float:
    """Infer confidence from hedging language."""
    hedges = ["maybe", "perhaps", "possibly", "might", "could", "seems", "appears"]
    strong = ["definitely", "certainly", "absolutely", "clearly", "obviously"]

    text_lower = text.lower()

    if any(h in text_lower for h in strong):
        return 0.9
    elif any(h in text_lower for h in hedges):
        return 0.5
    return 0.7  # default moderate confidence