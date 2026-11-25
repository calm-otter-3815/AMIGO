"""Replies kept by what was asked, so the same question gets the same outcome every run.

A model can answer one prompt two ways on two runs; the first answer is kept and given
back after. AMIGO_CACHE=off turns it off, to measure how much the answers vary.
"""

import hashlib
import json
import os
import threading
from pathlib import Path

from . import config


def _path(kind: str, asked: dict) -> Path | None:
    if not config.CACHE:
        return None
    text = json.dumps(asked, sort_keys=True, ensure_ascii=False)
    key = hashlib.sha256(text.encode()).hexdigest()
    return config.CACHE_DIR / kind / key[:2] / f"{key}.json"


def get(kind: str, asked: dict) -> object | None:
    path = _path(kind, asked)
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text())


def put(kind: str, asked: dict, reply: object, replace: bool = False) -> object:
    """Keep `reply` for what was asked, and give back the reply kept. The first one kept
    stays: two callers that ask the same thing at the same moment both go on with it.
    `replace` puts `reply` in place of a kept one the caller refused."""
    path = _path(kind, asked)
    if path is None:
        return reply
    path.parent.mkdir(parents=True, exist_ok=True)
    # written whole, then linked or renamed, so a reader in another thread never sees half a file
    part = path.with_suffix(f".{os.getpid()}.{threading.get_ident()}.part")
    part.write_text(json.dumps(reply, ensure_ascii=False))
    if replace:
        part.replace(path)
        return reply
    try:
        os.link(part, path)  # refused when another caller's reply is already there
    except FileExistsError:
        reply = json.loads(path.read_text())
    part.unlink()
    return reply
