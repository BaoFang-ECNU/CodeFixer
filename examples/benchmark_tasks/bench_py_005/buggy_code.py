def fib(n):
    if n < 2:
        return n
    dp = [0, 1]
    for _ in range(2, n + 1):
        dp.append(dp[-1] + dp[-1])
    return dp[-1]
