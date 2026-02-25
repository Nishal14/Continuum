"""
Structural polarity analysis for epistemic drift detection.

This module replaces keyword-based polarity detection with structural analysis that:
- Analyzes negation scope (not X vs X is not Y)
- Detects comparative patterns (better than, worse than)
- Analyzes modal verbs in context (should vs shouldn't)
- Aggregates sentiment per clause

Phase 4 (Drift Accumulator): Structural features replace keyword lists.
"""

import re
from typing import Literal, Tuple, List


def infer_polarity_structural(text: str) -> Literal["positive", "negative", "neutral"]:
    """
    Infer polarity from text using structural analysis.

    Analyzes:
    1. Negation scope and patterns
    2. Comparative constructions
    3. Modal verbs in context
    4. Sentiment-bearing phrases

    Args:
        text: Input text to analyze

    Returns:
        Polarity: "positive", "negative", or "neutral"
    """
    text_lower = text.lower().strip()

    # Initialize scores
    positive_score = 0.0
    negative_score = 0.0

    # 1. NEGATION SCOPE ANALYSIS
    negation_score = _analyze_negation_scope(text_lower)
    if negation_score < 0:
        negative_score += abs(negation_score)
    elif negation_score > 0:
        positive_score += negation_score

    # 2. COMPARATIVE PATTERN DETECTION
    comparative_score = _analyze_comparatives(text_lower)
    if comparative_score < 0:
        negative_score += abs(comparative_score)
    elif comparative_score > 0:
        positive_score += comparative_score

    # 3. MODAL VERB ANALYSIS
    modal_score = _analyze_modals(text_lower)
    if modal_score < 0:
        negative_score += abs(modal_score)
    elif modal_score > 0:
        positive_score += modal_score

    # 4. SENTIMENT AGGREGATION
    sentiment_score = _aggregate_sentiment(text_lower)
    if sentiment_score < 0:
        negative_score += abs(sentiment_score)
    elif sentiment_score > 0:
        positive_score += sentiment_score

    # Final decision (lowered threshold from 0.5 to 0.25)
    if negative_score > positive_score and negative_score > 0.25:
        return "negative"
    elif positive_score > negative_score and positive_score > 0.25:
        return "positive"
    else:
        return "neutral"


def _analyze_negation_scope(text: str) -> float:
    """
    Analyze negation patterns and their scope.

    Returns:
        Score: negative for negated positive, positive for negated negative, 0 for neutral
    """
    score = 0.0

    # Negation patterns with scope
    # Pattern: "not [article?] [positive word]" -> negative
    # Allow optional articles (a, an, the) between negation and positive word
    negated_positive_patterns = [
        (r'\b(?:not|no|never|n\'t)\s+(?:a|an|the)?\s*(?:good|great|excellent|better|best|essential|important|valuable|beneficial|should|must|can|recommend|prefer|ideal)\b', -1.5),
        (r'\b(?:shouldn\'t|can\'t|won\'t|don\'t|isn\'t|aren\'t)\b', -0.8),
        (r'\bdisagree\b', -0.7),
    ]

    # Pattern: "not [negative word]" -> could be positive
    negated_negative_patterns = [
        (r'\b(?:not|no|never)\s+(?:bad|wrong|terrible|worse|worst|avoid|poor)\b', 0.8),
    ]

    for pattern, weight in negated_positive_patterns:
        if re.search(pattern, text):
            score += weight

    for pattern, weight in negated_negative_patterns:
        if re.search(pattern, text):
            score += weight

    return score


def _analyze_comparatives(text: str) -> float:
    """
    Detect comparative constructions.

    Returns:
        Score: positive for favorable comparisons, negative for unfavorable
    """
    score = 0.0

    # Positive comparatives
    positive_comparatives = [
        (r'\b(?:better|superior|improved|enhanced|preferable|more\s+effective)\b', 1.0),
        (r'\b(?:best|optimal|ideal|perfect)\b', 1.2),
    ]

    # Negative comparatives
    negative_comparatives = [
        (r'\b(?:worse|inferior|degraded|less\s+effective|problematic)\b', -1.0),
        (r'\b(?:worst|terrible|awful)\b', -1.2),
    ]

    for pattern, weight in positive_comparatives:
        if re.search(pattern, text):
            score += weight

    for pattern, weight in negative_comparatives:
        if re.search(pattern, text):
            score += weight

    return score


def _analyze_modals(text: str) -> float:
    """
    Analyze modal verbs in context.

    Returns:
        Score: positive for affirmative modals, negative for negated modals
    """
    score = 0.0

    # Affirmative modals (in positive context)
    affirmative_modals = [
        (r'\b(?:should|must|ought\s+to|need\s+to)\s+(?!not)\w+', 0.8),
        (r'\b(?:will|can)\s+(?!not)\w+', 0.6),
    ]

    # Negated modals
    negated_modals = [
        (r'\b(?:should\s+not|shouldn\'t|must\s+not|mustn\'t|cannot|can\'t)\b', -0.8),
        (r'\b(?:won\'t|will\s+not)\b', -0.6),
    ]

    # Uncertainty markers (reduce scores)
    uncertainty = [
        (r'\b(?:might|may|could|perhaps|possibly|maybe)\b', -0.2),
    ]

    for pattern, weight in affirmative_modals:
        if re.search(pattern, text):
            score += weight

    for pattern, weight in negated_modals:
        if re.search(pattern, text):
            score += weight

    for pattern, weight in uncertainty:
        if re.search(pattern, text):
            score += weight

    return score


def _aggregate_sentiment(text: str) -> float:
    """
    Aggregate sentiment from positive and negative phrases.

    Returns:
        Score: net sentiment (positive - negative)
    """
    positive_phrases = [
        r'\b(?:agree|correct|true|yes|right)\b',
        r'\b(?:good|great|excellent|wonderful|fantastic|essential|important|valuable|beneficial)\b',
        r'\b(?:recommend|endorse|support|advocate)\b',
        r'\b(?:safe|secure|reliable|stable)\b',
    ]

    negative_phrases = [
        r'\b(?:disagree|false|wrong|incorrect)\b',
        r'\b(?:bad|poor|terrible|awful|horrible|harmful|useless|pointless|unnecessary)\b',
        r'\b(?:avoid|discourage|oppose|reject)\b',
        r'\b(?:unsafe|dangerous|risky|unstable)\b',
    ]

    positive_count = sum(1 for pattern in positive_phrases if re.search(pattern, text))
    negative_count = sum(1 for pattern in negative_phrases if re.search(pattern, text))

    # Normalize to 0.0-1.0 range
    net_sentiment = (positive_count - negative_count) * 0.3
    return max(-1.0, min(1.0, net_sentiment))


def extract_polarity_features(text: str) -> dict:
    """
    Extract detailed polarity features for analysis.

    Returns:
        Dictionary with feature breakdowns for debugging and explanation
    """
    text_lower = text.lower().strip()

    return {
        "negation_score": _analyze_negation_scope(text_lower),
        "comparative_score": _analyze_comparatives(text_lower),
        "modal_score": _analyze_modals(text_lower),
        "sentiment_score": _aggregate_sentiment(text_lower),
        "final_polarity": infer_polarity_structural(text)
    }
