from buggy_code import count_words

def test_visible():
    assert count_words(['a', 'a']) == {'a': 2}
