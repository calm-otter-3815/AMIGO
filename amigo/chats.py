"""Saved chats of the page: one JSON file per chat, the events of each of its runs, and folders."""

import json
import os
import threading
import time
import uuid
from pathlib import Path

# outside the checkout, so every worktree's page sees the same history
DIR = Path(os.environ.get("AMIGO_CHATS_DIR", Path.home() / ".amigo" / "chats"))
FOLDERS = "folders.json"
_lock = threading.Lock()


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def _path(chat: str) -> Path:
    if not chat.isalnum():
        raise ValueError(f"no chat {chat!r}")
    return DIR / f"{chat}.json"


def _write(path: Path, data) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data))
    temp.replace(path)


def load(chat: str) -> dict | None:
    path = _path(chat)
    return json.loads(path.read_text()) if path.exists() else None


def save(chat: str, lake: str, uid: str, question: str, events: list[dict]) -> None:
    """Keep one run's events in its chat, in place of what was saved of that run before."""
    with _lock:
        now = time.time()
        data = load(chat) or {"id": chat, "title": question, "lake": lake, "created": now,
                              "folder": None, "runs": []}
        runs = [one for one in data["runs"] if one["uid"] != uid]
        data["runs"] = runs + [{"uid": uid, "question": question, "events": events}]
        data["updated"] = now
        _write(_path(chat), data)


def listing() -> list[dict]:
    """Every chat without its events, the latest first."""
    found = []
    for path in DIR.glob("*.json") if DIR.exists() else []:
        if path.name == FOLDERS:
            continue
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        found.append({key: data.get(key) for key in ("id", "title", "lake", "created", "updated", "folder")}
                     | {"runs": len(data.get("runs", []))})
    return sorted(found, key=lambda one: one["updated"] or 0, reverse=True)


def move(chat: str, folder: str | None) -> None:
    with _lock:
        data = load(chat)
        if data is None:
            raise ValueError(f"no chat {chat!r}")
        if folder is not None and folder not in folders():
            raise ValueError(f"no folder {folder!r}")
        data["folder"] = folder
        _write(_path(chat), data)


def delete(chat: str | None) -> None:
    """One chat, or every chat when `chat` is None. The folders stay."""
    with _lock:
        for path in [_path(chat)] if chat else DIR.glob("*.json") if DIR.exists() else []:
            if path.name != FOLDERS:
                path.unlink(missing_ok=True)


def folders() -> list[str]:
    path = DIR / FOLDERS
    return json.loads(path.read_text()) if path.exists() else []


def edit_folder(action: str, name: str, to: str | None = None) -> None:
    """Add, rename or delete a folder; a deleted folder's chats stay, in no folder."""
    name, to = name.strip(), (to or "").strip()
    with _lock:
        names = folders()
        if action == "add":
            if not name or name in names:
                raise ValueError(f"a folder needs a new name, not {name!r}")
            names.append(name)
        elif action in ("rename", "delete"):
            if name not in names:
                raise ValueError(f"no folder {name!r}")
            if action == "rename" and (not to or to in names):
                raise ValueError(f"a folder needs a new name, not {to!r}")
            names = [to if one == name else one for one in names] if action == "rename" else \
                [one for one in names if one != name]
            for one in listing():
                if one["folder"] == name:
                    data = load(one["id"])
                    data["folder"] = to if action == "rename" else None
                    _write(_path(one["id"]), data)
        else:
            raise ValueError(f"no folder action {action!r}")
        _write(DIR / FOLDERS, names)
