from types import SimpleNamespace

import pytest

from amigo import llm
from baselines import full_schema


def test_known():
    check = full_schema.known(SimpleNamespace(table={"db.a": object()}))
    for bad in (["db.nope"], []):
        with pytest.raises(llm.ModelError):
            check(full_schema.Chosen(tables=bad))
    check(full_schema.Chosen(tables=["db.a"]))
