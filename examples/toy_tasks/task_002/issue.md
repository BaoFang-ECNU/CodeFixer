# Empty-list division by zero

The function `safe_average(values)` should return `0.0` when the input list is
empty. It currently divides by the list length unconditionally.

Run `python -m pytest test_buggy_code.py` to reproduce the failure.

