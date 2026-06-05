def fib(n):
    """Return the nth Fibonacci number."""
    if n < 0:
        raise ValueError("n must be non-negative")
    if n < 2:
        return n
    dp = [0, 1]
    for _ in range(2, n + 1):
        dp.append(dp[-1] + dp[-1])
    return dp[-1]

