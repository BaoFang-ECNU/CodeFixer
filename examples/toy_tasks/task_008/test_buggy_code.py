from buggy_code import parse_int_or_default


def test_parse_valid_int():
    assert parse_int_or_default("42") == 42


def test_parse_invalid_returns_default():
    assert parse_int_or_default("not-a-number", default=-1) == -1

