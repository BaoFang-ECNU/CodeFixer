import pytest

from buggy_code import fib


def test_fibonacci_values():
    assert fib(0) == 0
    assert fib(1) == 1
    assert fib(7) == 13


def test_fibonacci_rejects_negative():
    with pytest.raises(ValueError):
        fib(-1)

