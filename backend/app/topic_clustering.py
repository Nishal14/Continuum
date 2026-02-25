"""
Topic clustering and stance tracking for longitudinal epistemic analysis.

This module provides:
- Hierarchical clustering of commitments into topic groups
- Stance point computation (polarity × confidence)
- Topic stance history tracking over time

Phase 4 (Drift Accumulator): Tracks multi-turn stance evolution per topic.
"""

from typing import List, Dict, Tuple
from datetime import datetime
from app.models import (
    CommitmentGraph,
    Commitment,
    TopicCluster,
    StancePoint
)


def cluster_commitment_topics(
    graph: CommitmentGraph,
    similarity_threshold: float = 0.4
) -> List[TopicCluster]:
    """
    Cluster commitments into topic groups using hierarchical clustering.

    Uses simple token overlap (Jaccard similarity) for clustering.
    Phase 5+ could upgrade to sentence embeddings.

    Args:
        graph: Commitment graph
        similarity_threshold: Minimum similarity to group commitments (default: 0.4)

    Returns:
        List of topic clusters
    """
    active_commitments = graph.get_active_commitments()

    if not active_commitments:
        return []

    # Build similarity matrix
    n = len(active_commitments)
    clusters: List[List[Commitment]] = [[c] for c in active_commitments]
    cluster_ids = list(range(n))

    # Simple agglomerative clustering
    while True:
        # Find most similar pair of clusters
        best_similarity = 0.0
        best_pair = None

        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                # Compute average similarity between all pairs in clusters
                similarities = []
                for c1 in clusters[i]:
                    for c2 in clusters[j]:
                        sim = _compute_similarity(c1.normalized, c2.normalized)
                        similarities.append(sim)

                if similarities:
                    avg_sim = sum(similarities) / len(similarities)
                    if avg_sim > best_similarity:
                        best_similarity = avg_sim
                        best_pair = (i, j)

        # If no pair exceeds threshold, stop
        if best_similarity < similarity_threshold or best_pair is None:
            break

        # Merge the best pair
        i, j = best_pair
        clusters[i].extend(clusters[j])
        del clusters[j]

    # Convert clusters to TopicCluster objects
    topic_clusters = []
    for idx, cluster_commitments in enumerate(clusters):
        # Generate topic label (most frequent words)
        topic_label = _generate_topic_label(cluster_commitments)

        # Get commitment IDs
        commitment_ids = [c.id for c in cluster_commitments]

        # Get centroid text (longest commitment)
        centroid_text = max(cluster_commitments, key=lambda c: len(c.normalized)).normalized

        # Get first and last seen turns
        turn_ids = [c.turn_id for c in cluster_commitments]
        first_seen = min(turn_ids)
        last_updated = max(turn_ids)

        topic_cluster = TopicCluster(
            topic_id=f"topic_{idx + 1}",
            topic_label=topic_label,
            commitment_ids=commitment_ids,
            centroid_text=centroid_text,
            first_seen_turn=first_seen,
            last_updated_turn=last_updated
        )
        topic_clusters.append(topic_cluster)

    return topic_clusters


def compute_stance_point(
    commitment: Commitment,
    topic_id: str
) -> StancePoint:
    """
    Compute a stance point from a commitment.

    Stance = polarity_value × confidence
    - positive polarity = +1
    - negative polarity = -1
    - neutral polarity = 0

    Args:
        commitment: Commitment to compute stance from
        topic_id: Topic this commitment belongs to

    Returns:
        StancePoint with computed stance
    """
    # Map polarity to numeric value
    polarity_map = {
        "positive": 1.0,
        "negative": -1.0,
        "neutral": 0.0
    }

    polarity_value = polarity_map.get(commitment.polarity, 0.0)
    stance = polarity_value * commitment.confidence

    return StancePoint(
        topic=topic_id,
        stance=stance,
        turn_id=commitment.turn_id,
        confidence=commitment.confidence,
        timestamp=commitment.timestamp
    )


def update_topic_stance_history(
    graph: CommitmentGraph,
    new_commitments: List[Commitment]
) -> None:
    """
    Update topic stance history with new commitments.

    Side effect: Modifies graph.topic_stance_history in place.

    Args:
        graph: Commitment graph to update
        new_commitments: New commitments to add to stance history
    """
    # Re-cluster all commitments
    topic_clusters = cluster_commitment_topics(graph)

    # Update graph's topic clusters
    graph.topic_clusters = topic_clusters

    # Build commitment -> topic mapping
    commitment_to_topic = {}
    for cluster in topic_clusters:
        for commitment_id in cluster.commitment_ids:
            commitment_to_topic[commitment_id] = cluster.topic_id

    # Add stance points for new commitments
    for commitment in new_commitments:
        topic_id = commitment_to_topic.get(commitment.id)
        if topic_id:
            stance_point = compute_stance_point(commitment, topic_id)

            # Add to history
            if topic_id not in graph.topic_stance_history:
                graph.topic_stance_history[topic_id] = []

            graph.topic_stance_history[topic_id].append(stance_point)


def compute_topic_stance_variance(
    stance_history: List[StancePoint]
) -> float:
    """
    Compute variance of stance over time for a topic.

    High variance indicates instability.

    Args:
        stance_history: List of stance points for a topic

    Returns:
        Variance of stance values
    """
    if len(stance_history) < 2:
        return 0.0

    stances = [sp.stance for sp in stance_history]
    mean_stance = sum(stances) / len(stances)
    variance = sum((s - mean_stance) ** 2 for s in stances) / len(stances)

    return variance


def detect_stance_instability(
    graph: CommitmentGraph,
    instability_threshold: float = 0.5
) -> List[Tuple[str, float]]:
    """
    Detect topics with high stance instability.

    Returns:
        List of (topic_id, variance) tuples for unstable topics
    """
    unstable_topics = []

    for topic_id, stance_history in graph.topic_stance_history.items():
        variance = compute_topic_stance_variance(stance_history)

        if variance > instability_threshold:
            unstable_topics.append((topic_id, variance))

    return unstable_topics


# Helper functions

def _compute_similarity(text1: str, text2: str) -> float:
    """
    Compute Jaccard similarity between two texts.

    Args:
        text1: First text
        text2: Second text

    Returns:
        Similarity score (0.0 to 1.0)
    """
    tokens1 = set(text1.lower().split())
    tokens2 = set(text2.lower().split())

    if not tokens1 or not tokens2:
        return 0.0

    intersection = tokens1 & tokens2
    union = tokens1 | tokens2

    return len(intersection) / len(union) if union else 0.0


def _generate_topic_label(commitments: List[Commitment]) -> str:
    """
    Generate a topic label from a cluster of commitments.

    Uses most frequent non-stopword tokens.

    Args:
        commitments: List of commitments in cluster

    Returns:
        Topic label string
    """
    # Simple stopwords
    stopwords = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "was", "are", "be", "been",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "must", "can", "i", "you", "we", "they",
        "he", "she", "it", "this", "that", "these", "those"
    }

    # Collect all tokens
    all_tokens = []
    for c in commitments:
        tokens = c.normalized.lower().split()
        all_tokens.extend(tokens)

    # Filter stopwords and count frequency
    token_freq = {}
    for token in all_tokens:
        # Remove punctuation
        token = token.strip(".,!?;:'\"()[]{}").lower()
        if token and len(token) > 2 and token not in stopwords:
            token_freq[token] = token_freq.get(token, 0) + 1

    # Get top 3 most frequent tokens
    if not token_freq:
        return "unknown_topic"

    sorted_tokens = sorted(token_freq.items(), key=lambda x: x[1], reverse=True)
    top_tokens = [token for token, freq in sorted_tokens[:3]]

    return "_".join(top_tokens)
