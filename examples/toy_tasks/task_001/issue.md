# Off-by-one in inclusive summation

The function `sum_to_n(n)` should return the sum of all integers from 1 through
`n`, inclusive. The current implementation misses the upper bound.

Run `python -m pytest test_buggy_code.py` to reproduce the failure.

