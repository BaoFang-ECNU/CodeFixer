from buggy_code import largest_or_none


def test_largest_regular_values():
    assert largest_or_none([3, 1, 9, 2]) == 9


def test_largest_empty_values():
    assert largest_or_none([]) is None

