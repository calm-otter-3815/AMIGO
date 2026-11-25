import pytest

from amigo import chats, config

# a test must never read a reply an earlier run kept, nor leave one behind
config.CACHE = False


@pytest.fixture(autouse=True, scope="session")
def _chats_dir(tmp_path_factory):
    # nor may a test's run land among the person's saved chats
    chats.DIR = tmp_path_factory.mktemp("chats")
