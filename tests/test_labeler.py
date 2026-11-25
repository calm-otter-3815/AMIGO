import sqlite3

from labeler.gold import find, literals


def test_literals_skip_thresholds_and_formats():
    sql = ("SELECT * FROM t WHERE a = 'x' AND b IN ('p', 'q') AND strftime('%Y', d) = '2012'"
           " AND c BETWEEN '1' AND '2' AND e LIKE '%foo%' AND f > '2010-01-01' AND lower(g) = lower('Hi')")
    assert literals(sql) == ["x", "p", "q", "2012", "%foo%", "Hi"]


def test_find_tries_exact_then_nocase_then_contains():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE t (name TEXT)")
    conn.executemany("INSERT INTO t VALUES (?)", [("Alameda County",), ("Lindale ",)])
    columns = {("t", "name")}
    assert find(conn, columns, "Alameda County") == ("exact", "t.name")
    assert find(conn, columns, "lindale") == ("nocase", "t.name")
    assert find(conn, columns, "%Alameda%") == ("contains", "t.name")
    assert find(conn, columns, "Oakland") is None


def test_result_hash_ignores_row_order_and_spacing(tmp_path):
    from labeler.gold import result

    path = tmp_path / "t.db"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE t (name TEXT, n REAL)")
    conn.executemany("INSERT INTO t VALUES (?, ?)", [("a ", 1.0000001), ("b", 2.0)])
    conn.commit()
    one = result(path, "SELECT name, n FROM t ORDER BY name")
    two = result(path, "SELECT name, n FROM t ORDER BY name DESC")
    assert one["status"] == "ok" and one["hash"] == two["hash"]
    # numbers by value: 1 and 1.0 are one answer; column order and duplicates still count
    assert result(path, "SELECT name, CAST(n AS INTEGER) FROM t")["hash"] == one["hash"]
    assert result(path, "SELECT n, name FROM t")["hash"] != one["hash"]
    assert result(path, "SELECT name, n FROM t UNION ALL SELECT 'b', 2")["hash"] != one["hash"]
    assert result(path, "SELECT * FROM t WHERE 0")["status"] == "empty"
    assert result(path, "SELECT nope FROM t")["status"] == "error"


def test_verdict_is_majority_of_three():
    from labeler.judge import verdict

    assert verdict([True, True, False]) == "yes"
    assert verdict([False, None, False]) == "no"
    assert verdict([True, False, None]) == "unsure"
    assert verdict([None, None, None]) == "failed"
    assert verdict([False]) == "no" and verdict([None]) == "failed"


def test_grouped_merges_columns_tied_to_the_same_words():
    from labeler.pool import grouped

    items = [{"item": "t", "role": "table", "words": "info", "note_only": False},
             {"item": "t.a", "role": "answer", "words": "info", "note_only": False},
             {"item": "t.b", "role": "answer", "words": "info", "note_only": False},
             {"item": "t.c", "role": "filter", "words": "in 2019", "note_only": False},
             {"item": "t.id", "role": "join", "words": None, "note_only": False}]
    out = grouped(items)
    assert [i["item"] for i in out] == ["t", "t", "t.c", "t.id"]
    assert out[1]["columns"] == ["a", "b"]


def test_code_swap_renames_a_column_through_its_alias_or_a_copied_table(tmp_path):
    from types import SimpleNamespace

    from labeler.swap import code_swap

    path = tmp_path / "d.db"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE schools (id INT, City TEXT, MailCity TEXT, Closed INT)")
    conn.execute("INSERT INTO schools VALUES (1, 'Fresno', 'Fresno', 0)")
    conn.commit()
    lake = SimpleNamespace(paths={"d": path}, columns={"d.schools": [
        ("id", "INT"), ("City", "TEXT"), ("MailCity", "TEXT"), ("Closed", "INT")]}, case={"d.schools": "d.schools"})
    row = {"db_id": "d", "gold_sql": "SELECT T1.id FROM schools AS T1 WHERE T1.City = 'Fresno'"}
    column = {"item": "schools.City", "role": "filter", "kind": "column", "literal": "Fresno", "sources": []}
    assert code_swap(lake, row, column, "d.schools.MailCity") == \
        "SELECT T1.id FROM schools AS T1 WHERE T1.\"MailCity\" = 'Fresno'"
    assert code_swap(lake, row, {**column, "literal": "Oakland"}, "d.schools.MailCity") is None
    table = {"item": "schools", "kind": "table", "sources": ["copy"]}
    assert code_swap(lake, row, table, "d.schools_2023") == \
        "SELECT T1.id FROM \"schools_2023\" AS T1 WHERE T1.City = 'Fresno'"
    assert code_swap(lake, row, column, "other.schools.City") is None
    flag = {"item": "schools.Closed", "role": "filter", "kind": "column", "literal": None, "sources": []}
    flagged = {**row, "gold_sql": "SELECT id FROM schools WHERE Closed = 0"}
    assert code_swap(lake, flagged, flag, "d.schools.City") is None  # number test on a text column: LLM
    quoted = {**row, "gold_sql": 'SELECT "schools"."id" FROM "schools" WHERE "schools"."City" = \'Fresno\''}  # taco_us style
    assert code_swap(lake, quoted, column, "d.schools.MailCity") == \
        'SELECT "schools"."id" FROM "schools" WHERE "schools"."MailCity" = \'Fresno\''
    assert code_swap(lake, quoted, table, "d.schools_2023") == \
        'SELECT "schools_2023"."id" FROM "schools_2023" WHERE "schools_2023"."City" = \'Fresno\''


def test_run_drops_a_half_line_left_by_a_killed_run(tmp_path, monkeypatch):
    import json

    import labeler

    monkeypatch.setattr(labeler, "RUN", tmp_path)
    (tmp_path / "t.jsonl").write_text('{"id": "a"}\n{"id": "b", "x')
    labeler.run("t", [{"id": "a"}, {"id": "b"}], lambda i: {"id": i["id"]}, threads=1)
    lines = (tmp_path / "t.jsonl").read_text().splitlines()
    assert [json.loads(line)["id"] for line in lines] == ["a", "b"]


def test_anchor_reads_double_quoted_values_but_not_names(tmp_path):
    from labeler.gold import anchor

    path = tmp_path / "d.sqlite"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE airlines (uid INTEGER, Airline TEXT, Abbreviation TEXT)")
    conn.execute("INSERT INTO airlines VALUES (1, 'JetBlue Airways', 'JetBlue')")
    conn.execute("CREATE TABLE flights (Airline INTEGER)")
    conn.execute("INSERT INTO flights VALUES (1)")
    conn.commit()
    conn.close()
    sql = ('SELECT count(*) FROM FLIGHTS AS T1 JOIN AIRLINES AS T2 ON T1.Airline  =  T2.uid '
           'WHERE T2.Airline = "JetBlue Airways"')
    assert anchor(path, sql)["literals"] == [{"text": "JetBlue Airways", "route": "exact", "column": "airlines.Airline"}]
    assert literals('SELECT a FROM t WHERE b = "uid"', {"uid"}) == []


def test_anchor_ties_a_literal_to_the_column_it_is_compared_with(tmp_path):
    from labeler.gold import anchor, compared

    path = tmp_path / "d.sqlite"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE schools (CDSCode TEXT, City TEXT, County TEXT)")
    conn.execute("INSERT INTO schools VALUES ('1', 'Monterey', 'Monterey')")
    conn.commit()
    conn.close()
    sql = "SELECT T2.City FROM schools AS T2 WHERE T2.County = 'Monterey'"
    assert anchor(path, sql)["literals"] == [{"text": "Monterey", "route": "exact", "column": "schools.County"}]
    assert compared("SELECT 1 FROM t WHERE T1.`School Type` = 'High'", "High", {("t", "School Type")}) == [{("t", "School Type")}]
    assert compared("SELECT 1 FROM s AS T1 WHERE strftime('%Y', T1.OpenDate) = '1980'", "1980",
                    {("s", "OpenDate"), ("s", "CDSCode")}) == [{("s", "OpenDate")}]


def test_anchor_follows_aliases_and_every_comparison(tmp_path):
    from labeler.gold import anchor

    path = tmp_path / "d.sqlite"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE atom (atom_id TEXT, molecule_id TEXT, element TEXT)")
    conn.execute("INSERT INTO atom VALUES ('TR060_1', 'TR060', 'c')")
    conn.execute("CREATE TABLE molecule (molecule_id TEXT, label TEXT)")
    conn.execute("INSERT INTO molecule VALUES ('TR060', '+')")
    conn.execute("CREATE TABLE schools (AdmEmail1 TEXT, County TEXT, City TEXT)")
    conn.execute("INSERT INTO schools VALUES ('a@b', 'San Bernardino', 'San Bernardino')")
    conn.commit()
    conn.close()
    sql = ("SELECT DISTINCT T1.element, T2.label FROM atom AS T1 INNER JOIN molecule AS T2 "
           "ON T1.molecule_id = T2.molecule_id WHERE T2.molecule_id = 'TR060'")
    assert anchor(path, sql)["literals"] == [{"text": "TR060", "route": "exact", "column": "molecule.molecule_id"}]
    sql = "SELECT T2.AdmEmail1 FROM schools AS T2 WHERE T2.County = 'San Bernardino' AND T2.City = 'San Bernardino'"
    assert anchor(path, sql)["literals"] == [
        {"text": "San Bernardino", "route": "exact", "column": "schools.County"},
        {"text": "San Bernardino", "route": "exact", "column": "schools.City"},
    ]


def test_code_swap_renames_a_table_only_to_its_copy():
    from types import SimpleNamespace

    from labeler.swap import code_swap

    lake = SimpleNamespace(paths={}, columns={}, case={})
    sql = ("SELECT COUNT(T1.account_id) FROM account AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id "
           "INNER JOIN loan AS T3 ON T1.account_id = T3.account_id "
           "WHERE T1.district_id = 1 AND (T3.status = 'C' OR T3.status = 'D')")
    row = {"db_id": "financial", "gold_sql": sql}
    table = {"item": "district", "kind": "table", "role": "table", "sources": ["meaning"]}
    assert code_swap(lake, row, table, "financial.account") is None
    renamed = code_swap(lake, row, {**table, "sources": ["copy"]}, "financial.district_2")
    assert 'INNER JOIN "district_2" AS T2' in renamed and "JOIN district" not in renamed


def test_code_swap_leaves_join_keys_and_subqueries_to_the_llm():
    from types import SimpleNamespace

    from labeler.swap import code_swap

    lake = SimpleNamespace(paths={}, columns={}, case={})

    def item(name):
        return {"item": name, "role": "answer", "kind": "column", "literal": None, "sources": []}

    q16 = {"db_id": "california_schools", "gold_sql": (
        "SELECT COUNT(T1.CDSCode) FROM schools AS T1 INNER JOIN satscores AS T2 ON T1.CDSCode = T2.cds "
        "WHERE T1.StatusType = 'Merged' AND T2.NumTstTakr < 100 AND T1.County = 'Lake'")}
    assert code_swap(lake, q16, item("schools.CDSCode"), "california_schools.schools.School") is None  # join key
    cards = {"db_id": "card_games", "gold_sql": "SELECT T1.name, T1.isPromo FROM cards AS T1 WHERE T1.isPromo = 1"}
    assert code_swap(lake, cards, item("cards.isPromo"), "card_games.cards.promoTypes") is None  # also a filter
    sub = {"db_id": "card_games", "gold_sql": "SELECT T1.name FROM cards AS T1 WHERE T1.artist = (SELECT artist FROM cards LIMIT 1)"}
    assert code_swap(lake, sub, item("cards.name"), "card_games.cards.asciiName") is None  # subquery
    plain = {"db_id": "card_games", "gold_sql": "SELECT T1.name FROM cards AS T1 WHERE T1.artist = 'Aaron Boyd'"}
    assert code_swap(lake, plain, item("cards.name"), "card_games.cards.asciiName") == \
        "SELECT T1.\"asciiName\" FROM cards AS T1 WHERE T1.artist = 'Aaron Boyd'"
    q725 = {"db_id": "superhero", "gold_sql": (
        "SELECT COUNT(T1.id) FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id "
        "WHERE T2.publisher_name = 'Marvel Comics'")}
    assert code_swap(lake, q725, item("superhero.id"), "superhero.superhero.superhero_name") == (  # T2.id is another table's
        "SELECT COUNT(T1.\"superhero_name\") FROM superhero AS T1 INNER JOIN publisher AS T2 ON T1.publisher_id = T2.id "
        "WHERE T2.publisher_name = 'Marvel Comics'")


def test_swap_with_no_reply_is_failed_not_unanswerable(monkeypatch):
    from types import SimpleNamespace

    from labeler import llm, swap

    lake = SimpleNamespace(paths={}, case={}, tables=["o.t"], columns={"o.t": [("c", "TEXT")]},
                           shown={"o.t.c": "t.c (TEXT) values: x"})
    row = {"id": "x", "db_id": "d", "question": "q", "gold_sql": "SELECT c FROM t", "tables": ["t"], "gold": {"hash": "h"}}
    item = {"item": "t.c", "kind": "column", "role": "answer", "words": "w", "gold_shown": "t.c"}
    option = {"name": "o.t.c", "sources": ["meaning"]}

    def cut(*args, **kwargs):
        raise ValueError("thinking ran out of room")

    monkeypatch.setattr(llm, "ask_json", cut)
    assert swap.swap(lake, row, item, option)["answer"] == "failed"
    monkeypatch.setattr(llm, "ask_json", lambda *args, **kwargs: {"sql": None})
    assert swap.swap(lake, row, item, option)["answer"] == "not answerable"


def test_kind_labels_a_clone_by_where_it_is():
    from labeler.label import kind

    row = {"db_id": "financial"}
    clone = {"name": "financial.trans.account_id", "sources": ["meaning"], "clone_of": "financial.disp.account_id"}
    assert kind(row, "account.account_id", clone) == "other table"
    assert kind(row, "account.account_id", {**clone, "sources": ["copy"]}) == "copy"


def test_a_clone_of_a_copy_is_a_copy_in_any_order():
    from labeler.judge import judge_item

    for question in ("q0", "q1", "q2", "q3", "q4", "q5"):  # different shuffles
        item = {"item": "Student.StuID", "words": "students", "gold_shown": "Student.StuID", "decoys": [],
                "candidates": [{"name": "college_3.Enrolled_in.StuID", "sources": ["meaning"],
                                "clone_of": "activity_1.Student.StuID"},
                               {"name": "activity_1.Student.StuID", "sources": ["copy"]}]}
        verdicts = {o["name"]: o["verdict"] for o in judge_item(question, item, None, "x")["options"]}
        assert verdicts == {"college_3.Enrolled_in.StuID": "copy", "activity_1.Student.StuID": "copy"}


def test_a_cut_judge_call_is_retried_with_full_room(monkeypatch):
    from labeler import judge, label, llm

    calls = []

    def fake(prompt, seed, schema, tag="", limit=None, finished_under=None):
        calls.append((seed, limit))
        if limit is not None:
            raise ValueError("thinking ran out of room")
        return {"1": "yes"}

    monkeypatch.setattr(llm, "ask_json", fake)
    item = {"item": "t.c", "words": "w", "gold_shown": "t.c"}
    assert judge.ask("q", item, ["t.b (TEXT) values: x"], 0, [0], "x") == [True]
    assert calls == [(0, 10_000), (3, 10_000), (3, None)]

    # a full-room call reuses a reply saved under the cap only when that reply finished
    saved = {llm._key("p", 0, None, 10_000): {"reply": "done"}, llm._key("p", 1, None, 10_000): {"reply": None}}
    monkeypatch.setattr(llm, "_cache", saved)
    monkeypatch.setattr(llm, "_clients", None)  # any real call would fail
    assert llm.ask("p", 0, None, finished_under=10_000) == "done"
    try:
        llm.ask("p", 1, None, finished_under=10_000)
        assert False, "a cut reply must not be reused"
    except TypeError:  # next(None): no client to call
        pass

    row = {"id": "x", "lake": "l", "db_id": "d", "question": "q", "gold_sql": "s",
           "gold": {"status": "ok", "rows": 1, "hash": "h"}, "literals": []}
    judged = {"items": [{"item": "t.c", "options": [{"name": "d.t.b", "sources": [], "decoy": False,
                                                      "votes": [None], "verdict": "failed"}]}]}
    assert label.label(row, {"items": []}, judged, {"swaps": []})["checks"]["no_vote"] == 1


def test_not_asked_skips_tables_named_by_their_columns_or_only_joined():
    from labeler.label import label

    row = {"id": "x", "lake": "l", "db_id": "d", "question": "q", "gold_sql": "s",
           "gold": {"status": "ok", "rows": 1, "hash": "h"}, "literals": []}
    items = [{"item": "schools", "role": "table", "words": None, "note_only": False},
             {"item": "schools.City", "role": "filter", "words": "city of Adelanto", "note_only": False},
             {"item": "account", "role": "table", "words": None, "note_only": False},
             {"item": "account.account_id", "role": "join", "words": None, "note_only": False},
             {"item": "frpm", "role": "table", "words": None, "note_only": False}]
    out = label(row, {"items": items}, {"items": []}, {"swaps": []})
    assert out["underspecified"]["not_asked"] == ["frpm"]


def test_a_coded_value_inside_a_longer_word_is_not_spelled():
    from labeler.label import spelled

    assert not spelled("M", "How many male customers are there?")
    assert not spelled("F", "How many female students are there?")
    assert not spelled("EUR", "What percentage of KAM customers pay in euros?")
    assert spelled("Alameda", "Which schools are in Alameda County?")
    assert spelled("cat", "How many cats are there?")
    assert spelled("%Hey%", "Songs with the word hey in the title")
    assert spelled("", "anything")


def test_literals_skip_function_arguments_and_iif_outputs():
    sql = ("SELECT IIF(T2.mtgoCode IS NOT NULL, 'YES', 'NO') FROM cards AS T1 INNER JOIN sets AS T2"
           " ON T2.code = T1.setCode WHERE T1.name = 'Angel of Mercy'")
    assert literals(sql) == ["Angel of Mercy"]
    assert literals("SELECT AVG(INSTR(T2.fastestLapTime, ':')) FROM results AS T2 WHERE T2.raceId = 'x'") == ["x"]
    assert literals("SELECT player_name FROM Player WHERE (JULIANDAY('now') - JULIANDAY(birthday)) / 365 >= 35") == []
    sql = "SELECT a FROM t WHERE b NOT IN ('p', 'q (x)', 'r') AND lower(g) = lower('Hi')"
    assert literals(sql) == ["p", "q (x)", "r", "Hi"]


def test_link_retries_a_misquoted_span(monkeypatch):
    from labeler import llm
    from labeler.link import link

    row = {"id": "bird_dev-q580", "question": "Name 10 users with the badge name 'Necromancer.'", "evidence": "",
           "gold_sql": "SELECT T1.DisplayName FROM users AS T1 INNER JOIN badges AS T2 ON T1.Id = T2.UserId"
                       " WHERE T2.Name = 'Necromancer' LIMIT 10",
           "tables": ["badges", "users"], "columns": ["badges.Name", "badges.UserId", "users.DisplayName", "users.Id"]}

    def reply(name_words):
        rows = [("badges", "table", "badge"), ("users", "table", "users"), ("badges.Name", "filter", name_words),
                ("users.DisplayName", "answer", "users"), ("users.Id", "join", None), ("badges.UserId", "join", None)]
        return {"items": [{"item": i, "role": r, "words": w, "note_only": False} for i, r, w in rows],
                "computation_gaps": []}

    def fake(prompt, seed, schema, tag="", limit=None):
        return reply("name 'Necromancer'" if seed == 0 else "badge name 'Necromancer.'")

    monkeypatch.setattr(llm, "ask_json", fake)
    out = link(row)
    assert out["tries"] == 2
    assert {i["item"]: i["words"] for i in out["items"]}["badges.Name"] == "badge name 'Necromancer.'"

    monkeypatch.setattr(llm, "ask_json", lambda prompt, seed, schema, tag="", limit=None: reply("name 'Necromancer'"))
    out = link(row)
    assert out["tries"] == 3 and "failed" not in out
    assert {i["item"]: i for i in out["items"]}["badges.Name"]["bad_words"] == "name 'Necromancer'"


def test_holding_finds_a_value_in_a_date_column(tmp_path, monkeypatch):
    from labeler import pool
    from labeler.pool import Lake

    path = tmp_path / "financial.sqlite"
    conn = sqlite3.connect(path)
    conn.execute('CREATE TABLE loan (date DATE, amount INTEGER, "the ""kind""" TEXT, note TEXT)')
    conn.execute("INSERT INTO loan VALUES ('1994-08-25', 100, 'Owner', 'owner')")
    conn.commit()
    conn.close()
    lake = Lake.__new__(Lake)
    lake.name, lake.tables, lake.paths, lake._held = "financial", ["financial.loan"], {"financial": path}, {}
    lake.columns = {"financial.loan": [("date", "DATE"), ("amount", "INTEGER"), ('the "kind"', "TEXT"), ("note", "TEXT")]}
    assert lake.holding("1994-08-25") == ["financial.loan.date"]
    # the one-pass lookup of a very wide lake gives what the scan per value gives
    values = ["1994-08-25", "Owner", "OWNER", "none"]
    scanned = {v: lake.holding(v) for v in values}
    assert scanned["OWNER"] == ['financial.loan.the "kind"', "financial.loan.note"]
    monkeypatch.setattr(pool, "OUT", tmp_path)
    lake._held = {}
    lake.hold(values)
    assert lake._held == scanned and (tmp_path / "emb" / "financial-held.json").exists()


def test_anchor_across_databases_names_each_item_with_its_database(tmp_path):
    from labeler import split_item
    from labeler.gold import anchor, result

    paths = {"harbor": tmp_path / "harbor.sqlite", "weather": tmp_path / "weather.sqlite"}
    for name, create, values in [("harbor", "CREATE TABLE ferries (name TEXT, day TEXT)", ("Iris", "d1")),
                                 ("weather", 'CREATE TABLE daily (day TEXT, "No. kind" TEXT)', ("d1", "Storm"))]:
        conn = sqlite3.connect(paths[name])
        conn.execute(create)
        conn.execute(f"INSERT INTO {create.split()[2]} VALUES (?, ?)", values)
        conn.commit()
        conn.close()
    sql = ('SELECT "harbor"."ferries"."name" FROM "harbor"."ferries" JOIN "weather"."daily" '
           'ON "weather"."daily"."day" = "harbor"."ferries"."day" WHERE "weather"."daily"."No. kind" = \'storm\'')
    got = anchor(paths, sql)
    assert got["tables"] == ["harbor.ferries", "weather.daily"]
    assert "weather.daily.No. kind" in got["columns"]
    assert got["literals"] == [{"text": "storm", "route": "nocase", "column": "weather.daily.No. kind"}]
    assert split_item("weather.daily.No. kind", cross=True) == ("weather.daily", "No. kind")
    assert split_item("daily.No. kind") == ("daily", "No. kind")
    assert result(paths, sql.replace("'storm'", "'Storm'"))["sample"] == [["Iris"]]


def test_values_missing_finds_dropped_gold_values():
    from labeler.values import missing
    gold = "SELECT n FROM t WHERE city = 'Canada' AND kind LIKE '%Boat%' AND y = \"2013\""
    assert missing(gold, "SELECT n FROM u WHERE country = 'United States' AND kind LIKE '%boat%' AND y = '2013'") == ["Canada"]
