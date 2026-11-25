import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))

import eval_lakes  # noqa: E402


def test_ablated():
    x, y = SimpleNamespace(left_out=()), SimpleNamespace(left_out=())
    assert eval_lakes._ablated({"placed": [x, y], "found": [x]}, "nojudge2") == [x, y]
    assert eval_lakes._ablated({"placed": [x], "found": [x]}, "norelaxed") == [x]
    relaxed = SimpleNamespace(left_out=(1,))
    assert eval_lakes._ablated({"placed": [relaxed], "found": [relaxed]}, "norelaxed") == []
