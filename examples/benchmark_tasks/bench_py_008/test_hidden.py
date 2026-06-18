from buggy_code import parse_int_or_default

def test_hidden():
    assert parse_int_or_default('42', default=-1) == 42
