from buggy_code import safe_average


def test_average_regular_values():
    assert safe_average([2, 4, 6]) == 4


def test_average_empty_values():
    assert safe_average([]) == 0.0

