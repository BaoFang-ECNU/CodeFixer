def sum_to_n(n):
    """Return 1 + 2 + ... + n."""
    if n < 0:
        raise ValueError("n must be non-negative")
    return sum(range(1, n))

