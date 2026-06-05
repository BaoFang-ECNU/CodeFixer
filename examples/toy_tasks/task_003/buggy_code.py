def top_scores(scores, k):
    """Return the highest k scores in descending order."""
    if k <= 0:
        return []
    return sorted(scores)[:k]

