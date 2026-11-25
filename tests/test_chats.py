from amigo import chats


def test_chats_save_folders_delete(tmp_path, monkeypatch):
    monkeypatch.setattr(chats, "DIR", tmp_path)
    chats.save("c1", "lake_a", "r1", "first?", [{"type": "run"}])
    chats.save("c1", "lake_a", "r1", "first?", [{"type": "run"}, {"type": "done"}])  # same run again
    chats.save("c1", "lake_a", "r2", "more?", [{"type": "run"}])
    chats.save("c2", "lake_b", "r3", "other?", [])
    one = chats.load("c1")
    assert [r["uid"] for r in one["runs"]] == ["r1", "r2"] and len(one["runs"][0]["events"]) == 2
    assert one["title"] == "first?" and one["lake"] == "lake_a"

    chats.edit_folder("add", "work")
    chats.move("c1", "work")
    chats.edit_folder("rename", "work", "papers")
    assert chats.load("c1")["folder"] == "papers"
    chats.edit_folder("delete", "papers")
    assert chats.load("c1")["folder"] is None and chats.folders() == []

    chats.delete("c2")
    assert [c["id"] for c in chats.listing()] == ["c1"]
    chats.delete(None)
    assert chats.listing() == []
