# Username normalization misses whitespace

The function `normalize_username(name)` should remove leading/trailing
whitespace and return lowercase text. The current implementation lowercases but
does not strip spaces.

