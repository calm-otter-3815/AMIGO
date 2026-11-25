from baselines import bm25, hybrid


def test_fuse_and_query():
    assert hybrid.fuse([["a", "b", "c"], ["c", "a"]]) == ["a", "c", "b"]
    assert bm25.query('What AND "x"?') == '"what" OR "and" OR "x"'
