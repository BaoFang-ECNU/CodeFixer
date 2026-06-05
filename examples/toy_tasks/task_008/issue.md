# Integer parsing should use default on invalid input

The function `parse_int_or_default(text, default)` should return `int(text)`
when parsing succeeds and return `default` when parsing raises `ValueError`.
The current implementation lets invalid input crash.

