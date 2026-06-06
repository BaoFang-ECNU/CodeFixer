from buggy_code import count_words

def test_hidden():
    assert count_words(['a', 'b', 'a']) == {'a': 2, 'b': 1}
