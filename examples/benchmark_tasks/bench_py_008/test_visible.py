from buggy_code import parse_int_or_default

def test_visible():
    assert parse_int_or_default('bad', default=-1) == -1
