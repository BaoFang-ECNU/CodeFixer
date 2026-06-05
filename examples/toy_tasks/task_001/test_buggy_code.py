import pytest

from buggy_code import sum_to_n


def test_sum_to_n_inclusive():
    assert sum_to_n(1) == 1
    assert sum_to_n(5) == 15


def test_sum_to_n_zero():
    assert sum_to_n(0) == 0


def test_sum_to_n_rejects_negative():
    with pytest.raises(ValueError):
        sum_to_n(-1)

