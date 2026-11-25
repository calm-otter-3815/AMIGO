import dataclasses
import json
import logging
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

import numpy as np

from amigo import answer, bundle, clarify, config, guide, interpret, judge, llm, route, serve, solve

QUESTIONS = [
    {"question": "how many books", "SQL": "SELECT COUNT(*) AS n FROM books;", "db_id": "lib"},
    {"question": "who joined first", "SQL": "SELECT 2", "db_id": "lib"},
]

TABLES = {
    1: {
        "name": "books",
        "readable": "books",
        "database": "lib",
        "database_readable": "city library",
        "row_count": 120,
        "description": "books held by the library",
        "database_path": None,  # filled in once the tmp source db exists
    },
    2: {
        "name": "AllReaders",
        "readable": "readers",
        "database": "lib",
        "database_readable": "city library",
        "row_count": 40,
    },
    3: {
        "name": "loans",
        "readable": "loans",
        "database": "lib",
        "database_readable": "city library",
        "row_count": 900,
        "description": "loans of the library's books",
    },
}

COLUMNS = {
    1: {
        "table_id": 1,
        "name": "Title",
        "readable": "title",
        "kind": "text",
        "description": "the book's title",
        "value_description": "",
        "distinct_count": 2,
        "empty_share": 0.0,
        "is_unique": 1,
        "samples": json.dumps(["Emma", "Dune"]),
    },
    2: {
        "table_id": 1,
        "name": "Author",
        "readable": "author",
        "kind": "text",
        "description": "the book's author",
        "value_description": "",
        "distinct_count": 2,
        "empty_share": 0.0,
        "is_unique": 0,
        "samples": json.dumps([]),
    },
    3: {
        "table_id": 2,
        "name": "reader",
        "readable": "reader",
        "kind": "text",
        "description": "the reader's name",
        "value_description": "",
        "distinct_count": 2,
        "empty_share": 0.0,
        "is_unique": 0,
        "samples": json.dumps([]),
    },
    4: {
        "table_id": 2,
        "name": "joined",
        "readable": "joined",
        "kind": "date",
        "description": "the day the reader joined",
        "value_description": "",
        "distinct_count": 2,
        "empty_share": 0.0,
        "is_unique": 0,
        "samples": json.dumps([]),
    },
    **{
        column_id: {
            "table_id": 3,
            "name": name,
            "readable": name.lower(),
            "kind": "number",
            "description": description,
            "value_description": "",
            "distinct_count": 2,
            "empty_share": 0.0,
            "is_unique": 0,
            "samples": json.dumps([]),
        }
        for column_id, name, description in (
            (5, "Total", "every loan of the book"),
            (6, "Domestic", "loans to readers of this library"),
            (7, "Transit", "loans sent on to another library"),
        )
    },
}


class FakeProbe:
    tables = TABLES
    columns = COLUMNS
    links = []

    def path(self, kind: str, card_id: int) -> str:
        if kind == "table":
            return f"lib.{TABLES[card_id]['name']}"
        column = COLUMNS[card_id]
        return f"lib.{TABLES[column['table_id']]['name']}.{column['name']}"

    column_ids = {
        "lib.books.Title": 1,
        "lib.books.Author": 2,
        "lib.AllReaders.reader": 3,
        "lib.AllReaders.joined": 4,
        "lib.loans.Total": 5,
        "lib.loans.Domestic": 6,
        "lib.loans.Transit": 7,
    }
    table_ids = {"lib.books": 1, "lib.AllReaders": 2, "lib.loans": 3}

    def find(self, name: str) -> tuple[str, int]:
        if name in self.table_ids:
            return "table", self.table_ids[name]
        if name in self.column_ids:
            return "column", self.column_ids[name]
        raise KeyError(name)

    # the text values stored, and the columns storing each
    stored: dict[str, list[int]] = {"Achebe": [2]}

    def lookup_value(self, text: str) -> list[int]:
        return self.stored.get(text, [])

    def split_value(self, text: str) -> list:
        return []

    def lookup_words(self, text: str, skip=()) -> dict:
        return {}

    def search_cards(self, text: str):
        return [], np.zeros(len(TABLES))


def fake_stage1(probe, question, log_path, entities=None) -> bundle.Stage1:
    return bundle.Stage1(
        entities=[],
        column_scores=[],
        ranked=[[1]],
        order=[1],
        bridges=set(),
        details={1: ['matches "books"']},
        not_found=[],
    )


REAL_GUIDED = serve._guided


def _fake_guided(fanout):
    """A stand-in for the guided search: its leaves are `fanout()`'s interpretations, and the
    run waits for the person's ticks as the real one does."""
    def guided(run):
        fan = fanout()
        fan = run.fan = solve.FanOut(fan.interpretations, fan.dropped,
                                     fan.stopped or (None if fan.interpretations else serve.NOTHING))
        run.entities = run.stage.entities
        run.kept = {one.id: one for one in fan.interpretations}
        run.live = list(run.kept)
        run.emit("interpretations", entities=[], guided=True, **dataclasses.asdict(fan))
        if not run.live:
            return fan
        run.waiting = True
        run.chosen.clear()
        run.emit("paused", ids=run.live, guided=True)
        run.chosen.wait()
        return None if run.cancelled.is_set() else fan
    return guided


def _guided_with(cards):
    """The guided search's leaves are `cards()`, for one test."""
    return mock.patch.object(serve, "_guided", _fake_guided(lambda: solve.FanOut(cards(), [], None)))


def interpretation(name: str, tables: tuple[str, ...] = ("lib.books",)) -> solve.Interpretation:
    return solve.Interpretation(
        id=name,
        bindings=[
            solve.Binding(
                entity="e1", column="lib.books.Title", reason="titles live here", value="Dune"
            )
        ],
        tables=list(tables),
    )


# the same binding over two table sets: only the person can say which
TWO = solve.FanOut(
    [interpretation("i1"), interpretation("i2", ("lib.books", "lib.shelves"))],
    ["i3: no such column"],
    None,
)
STOPPED = solve.FanOut([], [], None)

def fake_query(
    probe, question, entities, one, log_path, rewrite=None, stop=None, chosen=False
) -> answer.Result:
    log = logging.getLogger("amigo.answer")
    log.info("sql %s try %d: %s", one.id, 1, "no such column: x")
    log.info("sql %s try %d: %d rows", one.id, 2, 1)
    return answer.Result(one, "counts the books", "SELECT COUNT(*) FROM books", ["n"], [(2,)], False, None)


def _get(port: int, path: str) -> object:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=10) as reply:
        return json.load(reply)


def _get_status(port: int, path: str) -> tuple[int, object]:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=10) as reply:
            return reply.status, json.load(reply)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


def _read_until(stream, kinds: list[str], seen: list[str]) -> dict:
    while True:
        line = stream.readline()
        if not line:
            raise AssertionError(f"the stream closed before {kinds}, saw {seen}")
        if not line.startswith(b"data: "):
            continue
        event = json.loads(line[len(b"data: ") :])
        seen.append(event["type"])
        if event["type"] in kinds:
            return event


def _post(port: int, path: str, body: dict) -> tuple[int, dict]:
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as reply:
            return reply.status, json.load(reply)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


class TestServe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.folder = folder = Path(cls._tmp.name)
        (folder / "dev.json").write_text(json.dumps(QUESTIONS))
        with sqlite3.connect(folder / "lib.sqlite") as source:
            source.execute("CREATE TABLE books (Title)")
            source.executemany("INSERT INTO books VALUES (?)", [("Emma",), ("Dune",)])
        TABLES[1]["database_path"] = str(folder / "lib.sqlite")
        cls.fanout = TWO
        cls._patches = [
            mock.patch.object(config, "RUNS_DIR", folder),
            mock.patch.object(
                config,
                "lake",
                lambda name: {"questions": folder / "dev.json", "databases": [folder / "lib.sqlite"]},
            ),
            mock.patch.object(serve, "Probe", lambda name: FakeProbe()),
            mock.patch.object(serve.Lake, "graph", lambda self: None),
            mock.patch.object(bundle, "stage1", fake_stage1),
            mock.patch.object(llm, "decompose", lambda *args: llm.Decomposition(entities=[])),
            mock.patch.object(serve, "_guided", _fake_guided(lambda: cls.fanout)),
            mock.patch.object(answer, "query", fake_query),
            mock.patch.object(answer, "say", lambda *args: None),
            mock.patch.object(answer, "summaries", lambda probe, question, entities, cards, log_path: cards),
            mock.patch.object(answer, "present", lambda *args: "FINAL TEXT"),
        ]
        for patch in cls._patches:
            patch.start()
        cls.site = serve.Site(["toy"], 0)
        cls.port = cls.site.server_address[1]
        threading.Thread(target=cls.site.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.site.shutdown()
        cls.site.server_close()
        for patch in cls._patches:
            patch.stop()
        cls._tmp.cleanup()

    def test_cancel_drops_the_run_in_flight_and_frees_the_server(self):
        self.assertEqual(
            _post(self.port, "/cancel", {}), (409, {"error": "no run is in progress"})
        )
        type(self).fanout = TWO
        self.assertEqual(_post(self.port, "/ask", {"question": "how many books"})[0], 200)
        seen: list[str] = []
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/events", timeout=10) as stream:
            _read_until(stream, ["paused", "error"], seen)
            self.assertEqual(_post(self.port, "/cancel", {})[0], 200)
            _read_until(stream, ["cancelled", "error"], seen)
            # a cancelled run ends the stream, the way done and error do
            self.assertEqual(stream.read().strip(), b"")
        run = self.site.current
        self.assertTrue(run.finished)
        # a step still in flight when cancel landed: whatever it emits next is dropped
        run.emit("log", text="late")
        self.assertNotIn("late", [event.get("text") for event in run.events])
        # the next run starts right away
        type(self).fanout = STOPPED
        self.assertEqual(_post(self.port, "/ask", {"question": "who joined first"})[0], 200)
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/events", timeout=10) as stream:
            self.assertEqual(_read_until(stream, ["done", "error"], [])["text"], "FINAL TEXT")

    def test_gold_comes_from_the_label(self):
        gold = _get(self.port, "/gold?question=how+many+books")
        self.assertEqual(gold["tables"], ["lib.books"])
        self.assertEqual(gold["answer"], {"columns": ["n"], "rows": [[2]], "count": 1})
        self.assertEqual(_get(self.port, "/gold?question=not+listed"), {})

    def test_lake_and_questions(self):
        self.assertEqual(_get(self.port, "/questions"), ["how many books", "who joined first"])
        self.assertEqual(
            _get(self.port, "/lake"),
            {
                "name": "toy",
                "databases": [
                    {
                        "name": "lib",
                        "readable": "city library",
                        "tables": [
                            {
                                "id": 2,
                                "name": "AllReaders",
                                "readable": "readers",
                                "path": "lib.AllReaders",
                                "rows": 40,
                            },
                            {
                                "id": 1,
                                "name": "books",
                                "readable": "books",
                                "path": "lib.books",
                                "rows": 120,
                            },
                            {
                                "id": 3,
                                "name": "loans",
                                "readable": "loans",
                                "path": "lib.loans",
                                "rows": 900,
                            },
                        ],
                    }
                ],
            },
        )

    def test_table_returns_the_card_and_5_rows_from_the_source_db(self):
        body = _get(self.port, "/table?id=1")
        self.assertEqual(
            {key: body[key] for key in ("name", "readable", "description", "row_count", "database")},
            {
                "name": "books",
                "readable": "books",
                "description": "books held by the library",
                "row_count": 120,
                "database": "lib",
            },
        )
        self.assertEqual(len(body["columns"]), 2)
        self.assertEqual(
            body["columns"][0],
            {
                "name": "Title",
                "readable": "title",
                "kind": "text",
                "description": "the book's title",
                "value_description": "",
                "distinct_count": 2,
                "empty_share": 0.0,
                "is_unique": True,
                "samples": ["Emma", "Dune"],
            },
        )
        self.assertEqual(body["header"], ["Title"])
        self.assertLessEqual(len(body["rows"]), 5)
        self.assertEqual(body["rows"], [["Emma"], ["Dune"]])
        self.assertEqual(_get_status(self.port, "/table?id=999")[0], 400)

    def test_rows_pages_and_searches_the_source_table(self):
        with mock.patch.object(serve, "PAGE", 1):
            first = _get(self.port, "/rows?lake=toy&table=1&page=0")
            self.assertEqual((first["rows"], first["matched"], first["pages"]), ([["Emma"]], 2, 2))
            self.assertEqual(_get(self.port, "/rows?lake=toy&table=1&page=1")["rows"], [["Dune"]])
            # a search is a plain substring, case aside; a page past the end shows the last one
            found = _get(self.port, "/rows?lake=toy&table=1&q=UN&page=5")
            self.assertEqual((found["rows"], found["matched"], found["page"]), ([["Dune"]], 1, 0))
            self.assertEqual(_get(self.port, "/rows?lake=toy&table=1&q=%25")["matched"], 0)
        self.assertEqual(_get_status(self.port, "/rows?lake=toy&table=x")[0], 400)

    def test_a_run_pauses_then_queries_the_chosen_interpretations(self):
        type(self).fanout = TWO
        status, body = _post(self.port, "/ask", {"question": "how many books"})
        self.assertEqual((status, body), (200, {"run": self.site.current.number}))
        seen: list[str] = []
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/events", timeout=10) as stream:
            fan = _read_until(stream, ["interpretations", "error"], seen)
            self.assertEqual([one["id"] for one in fan["interpretations"]], ["i1", "i2"])
            paused = _read_until(stream, ["paused", "error"], seen)
            self.assertEqual(paused["ids"], ["i1", "i2"])
            self.assertEqual(
                _post(self.port, "/ask", {"question": "another"}),
                (409, {"error": "a run is in progress"}),
            )
            self.assertEqual(_post(self.port, "/query", {"ids": ["nope"]})[0], 400)
            self.assertEqual(_post(self.port, "/query", {"ids": []})[0], 400)
            # a tab still on an older run cannot choose in this one
            stale = {"ids": ["i1"], "run": self.site.current.number - 1}
            self.assertEqual(_post(self.port, "/query", stale)[0], 409)
            self.assertEqual(_post(self.port, "/query", {"ids": ["i1"]})[0], 200)
            rows = _read_until(stream, ["rows", "error"], seen)
            self.assertEqual(
                (rows["id"], rows["sentence"], rows["rows"]), ("i1", "counts the books", [[2]])
            )
            done = _read_until(stream, ["done", "error"], seen)
        self.assertEqual(done["text"], "FINAL TEXT")
        wanted = ["run", "bundle", "interpretations", "paused", "selected", "querying", "sql", "sql", "rows", "done"]
        self.assertEqual([kind for kind in seen if kind in wanted], wanted)
        self.assertEqual(_get(self.port, "/calls"), [])

        # the finished run: the user says which interpretation is the answer
        self.assertEqual(_post(self.port, "/choose", {"id": "nope"})[0], 409)
        self.assertEqual(_post(self.port, "/choose", {"id": "i1"}), (200, {"id": "i1"}))
        lines = [
            json.loads(text)
            for text in (self.folder / "ask_toy.jsonl").read_text().splitlines()
        ]
        self.assertEqual(
            {key: lines[-1][key] for key in ("kind", "question", "id", "tables")},
            {"kind": "chosen", "question": "how many books", "id": "i1", "tables": ["lib.books"]},
        )
        self.assertEqual(sorted(lines[-1]["bindings"]), ["e1"])
        self.assertEqual(
            {key: self.site.current.events[-1][key] for key in ("type", "id")},
            {"type": "chosen", "id": "i1"},
        )
        # a `chosen` line is not a model call, so it never reaches /calls or /usage
        self.assertEqual(_get(self.port, "/calls"), [])

    def test_guided_mode_waits_for_the_places_to_be_approved(self):
        with mock.patch.object(serve, "_guided", REAL_GUIDED), \
                mock.patch.object(judge, "judge", lambda *args: []), \
                mock.patch.object(guide, "automatic", lambda *args: []):
            self.assertEqual(_post(self.port, "/ask", {"question": "how many books", "guided": True})[0], 200)
            seen: list[str] = []
            with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/events", timeout=10) as stream:
                _read_until(stream, ["places_paused", "error"], seen)
                # one list of places per part, and the toy question has none
                self.assertEqual(_post(self.port, "/approve", {"keep": [[]]})[0], 400)
                self.assertEqual(_post(self.port, "/approve", {"keep": None}), (200, {"approved": True}))
                self.assertEqual(_post(self.port, "/approve", {"keep": None})[0], 409)
                _read_until(stream, ["done", "error"], seen)
        wanted = ["candidates", "places", "places_paused", "interpretations", "done"]
        self.assertEqual([kind for kind in seen if kind in wanted], wanted)

    def test_a_replayed_run_takes_the_earlier_parts_and_places_without_asking(self):
        fixed = [{"attribute": "books", "literal": None}]
        with mock.patch.object(serve, "_guided", REAL_GUIDED), \
                mock.patch.object(judge, "judge", lambda *args: []), \
                mock.patch.object(guide, "automatic", lambda *args: []):
            body = {"question": "how many books", "check": True, "guided": True,
                    "replay": {"parts": fixed, "places": None, "forks": []}}
            self.assertEqual(_post(self.port, "/ask", body)[0], 200)
            seen: list[str] = []
            with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/events", timeout=10) as stream:
                approved = _read_until(stream, ["approved", "error"], seen)
                _read_until(stream, ["done", "error"], seen)
        self.assertNotIn("parts_paused", seen)
        self.assertNotIn("places_paused", seen)
        self.assertEqual(approved["keep"], None)


    def test_check_mode_pauses_on_the_parts_and_the_bundle_uses_the_fixed_ones(self):
        type(self).fanout = STOPPED
        given: list = []

        def watched_stage1(probe, question, log_path, entities=None):
            given.append(entities)
            return fake_stage1(probe, question, log_path)

        folded = llm.Decomposition(entities=[llm.Entity(attribute="Batman's colour", literal=None)])
        fixed = [
            {"attribute": "colour", "literal": None},
            {"attribute": "character's name", "literal": {"kind": "text", "text": "Batman"}},
        ]
        with mock.patch.object(bundle, "stage1", watched_stage1), mock.patch.object(
            llm, "decompose", lambda *args: folded
        ):
            self.assertEqual(
                _post(self.port, "/ask", {"question": "What colour is Batman?", "check": True})[0],
                200,
            )
            seen: list[str] = []
            with urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}/events", timeout=10
            ) as stream:
                paused = _read_until(stream, ["parts_paused", "error"], seen)
                self.assertEqual(paused["entities"], [folded.entities[0].model_dump()])
                self.assertEqual(given, [])
                # a part with no words, or a value of the wrong shape, is refused
                for bad in [
                    {"attribute": " ", "literal": None},
                    {"attribute": "colour", "literal": {"kind": "date", "text": "red"}},
                ]:
                    self.assertEqual(_post(self.port, "/parts", {"entities": [bad]})[0], 400)
                self.assertEqual(_post(self.port, "/parts", {"entities": fixed})[0], 200)
                _read_until(stream, ["done", "error"], seen)
        self.assertEqual(given, [[llm.Entity.model_validate(one) for one in fixed]])
        self.assertEqual(
            _post(self.port, "/parts", {"entities": fixed}),
            (409, {"error": "no run is waiting for its parts"}),
        )

    def test_a_stopped_fan_out_goes_straight_to_done(self):
        type(self).fanout = STOPPED
        self.assertEqual(_post(self.port, "/ask", {"question": "who joined first"})[0], 200)
        seen: list[str] = []
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/events", timeout=10) as stream:
            fan = _read_until(stream, ["interpretations", "error"], seen)
            self.assertTrue(fan["stopped"].startswith("No interpretation in this lake"))
            done = _read_until(stream, ["done", "error"], seen)
        self.assertEqual(done["text"], "FINAL TEXT")
        self.assertNotIn("paused", seen)


    def test_a_run_asked_after_a_cancel_starts_once_the_stopped_worker_is_out(self):
        type(self).fanout = STOPPED
        gate = threading.Event()

        def slow_cards(*args):
            gate.wait(10)
            return []

        with _guided_with(slow_cards):
            self.assertEqual(_post(self.port, "/ask", {"question": "how many books"})[0], 200)
            seen: list[str] = []
            with urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}/events", timeout=10
            ) as stream:
                _read_until(stream, ["bundle", "error"], seen)
                self.assertEqual(_post(self.port, "/cancel", {})[0], 200)
                _read_until(stream, ["cancelled", "error"], seen)
            stopped = self.site.current
            # the step is still in flight: the new run waits, or it would take its log lines
            self.assertEqual(_post(self.port, "/ask", {"question": "who joined first"})[0], 200)
            seen = []
            with urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}/events", timeout=10
            ) as stream:
                _read_until(stream, ["held", "error"], seen)
                gate.set()
                self.assertEqual(_read_until(stream, ["done", "error"], seen)["text"], "FINAL TEXT")
        self.assertFalse(stopped.thread.is_alive())
        self.assertEqual(seen[:2], ["held", "run"])

    def test_events_keeps_a_waiting_stream_alive_with_a_comment(self):
        type(self).fanout = TWO
        with mock.patch.object(serve, "WAIT", 0.1):
            self.assertEqual(_post(self.port, "/ask", {"question": "how many books"})[0], 200)
            seen: list[str] = []
            with urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}/events", timeout=10
            ) as stream:
                _read_until(stream, ["paused", "error"], seen)
                # the pause emits nothing: the comment is the write that notices a closed page
                self.assertIn(b": keep-alive\n", [stream.readline() for _ in range(2)])
                self.assertEqual(_post(self.port, "/query", {"ids": ["i1"]})[0], 200)
                _read_until(stream, ["done", "error"], seen)

    def test_missing_source_database_is_a_json_error(self):
        # table 2 has no database_path at all, table 1's file is gone
        status, body = _get_status(self.port, "/table?id=2")
        self.assertEqual(status, 400)
        self.assertIn("error", body)
        with mock.patch.dict(self.site.lakes["toy"].sources, {}, clear=True):
            gold = _get(self.port, "/gold?question=how+many+books")
        self.assertIn("error", gold["answer"])

    # ---- follow-up routing; named to sort after every test above ----

    def _finished(self, question: str = "how many books", ids: tuple = ("i1",)) -> list[str]:
        """One finished run on the two-interpretation fan-out, with `ids` queried."""
        type(self).fanout = TWO
        self.assertEqual(_post(self.port, "/ask", {"question": question})[0], 200)
        seen: list[str] = []
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/events", timeout=10) as stream:
            _read_until(stream, ["paused", "error"], seen)
            self.assertEqual(_post(self.port, "/query", {"ids": list(ids)})[0], 200)
            _read_until(stream, ["done", "error"], seen)
        return seen

    def _follow(self, seen: list[str], body: dict) -> dict:
        """POST /follow and read the run it starts to its end."""
        status, reply = _post(self.port, "/follow", body)
        self.assertEqual((status, "run" in reply), (200, True))
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/events", timeout=10) as stream:
            return _read_until(stream, ["done", "error"], seen)

    def _decide(self, word: str, question: str, calls: list):
        def decide(probe, original, turns, result, text, log_path):
            calls.append((original, [turn["axis"] for turn in turns], result.interpretation.id, text))
            line = {
                "label": f"route {text[:40]}",
                "usage": {"input_tokens": 3, "output_tokens": 2, "reasoning_tokens": 0},
            }
            with log_path.open("a") as handle:
                handle.write(json.dumps(line) + "\n")
            return {"route": word, "question": question, "why": route.WHY[word]}

        return decide

    def test_z_a_rewrite_reruns_the_sql_on_the_same_interpretation(self):
        self._finished()
        calls, queried = [], []

        def watched_query(probe, question, entities, one, log_path, rewrite=None, stop=None, chosen=False):
            queried.append((question, one.id))
            return fake_query(probe, question, entities, one, log_path)

        def never(*args, **kwargs):
            raise AssertionError("a rewrite must not go near the pipeline")

        follow = "how many books with their titles"
        with mock.patch.object(serve.route, "decide", self._decide("rewrite", follow, calls)):
            status, decision = _post(self.port, "/route", {"text": "show the titles too"})
        self.assertEqual(status, 200)
        self.assertEqual(
            decision,
            {"route": "rewrite", "question": follow, "why": route.WHY["rewrite"]},
        )
        self.assertEqual(calls, [("how many books", [], "i1", "show the titles too")])
        seen: list[str] = []
        with mock.patch.object(bundle, "stage1", never), _guided_with(never), mock.patch.object(answer, "query", watched_query):
            done = self._follow(seen, {"question": follow, "route": "rewrite"})
        self.assertEqual(done["text"], "FINAL TEXT")
        self.assertEqual(seen, ["run", "route", "selected", "querying", "sql", "sql", "rows", "done"])
        self.assertEqual(queried, [(follow, "i1")])
        run = self.site.current
        self.assertEqual(run.question, follow)
        # the page learns which interpretation the new SQL follows
        selected = next(event for event in run.events if event["type"] == "selected")
        self.assertEqual([one["id"] for one in selected["interpretations"]], ["i1"])
        self.assertEqual(run.rewrite[1].id, "i1")
        # the bindings were made for the earlier question, so its SQL rides along
        self.assertEqual(run.rewrite[2:], ("how many books", "SELECT COUNT(*) FROM books"))
        self.assertEqual(run.earlier, run.rewrite[2:])
        self.assertIn(
            "route show the titles too", [call["label"] for call in _get(self.port, "/calls")]
        )

    def test_z_follow_honours_a_route_the_page_overrode(self):
        self._finished()
        calls = []
        follow = "how many readers joined last year"
        with mock.patch.object(serve.route, "decide", self._decide("rewrite", follow, calls)):
            self.assertEqual(_post(self.port, "/route", {"text": "and the readers"})[0], 200)
            type(self).fanout = STOPPED
            seen: list[str] = []
            self._follow(seen, {"question": follow, "route": "restart"})
        # the click routed the other way, and no second model call was made for it
        self.assertEqual(len(calls), 1)
        self.assertEqual(seen[:3], ["run", "route", "bundle"])
        self.assertIn("interpretations", seen)
        self.assertEqual(self.site.current.rewrite, None)

    def test_z_route_and_follow_need_one_finished_answered_run(self):
        type(self).fanout = STOPPED
        self.assertEqual(_post(self.port, "/ask", {"question": "who joined first"})[0], 200)
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/events", timeout=10) as stream:
            _read_until(stream, ["done", "error"], [])
        # the run finished without a single row, so there is nothing to follow up on
        self.assertEqual(_post(self.port, "/route", {"text": "and the titles"})[0], 409)
        self.assertEqual(
            _post(self.port, "/follow", {"question": "how many titles", "route": "rewrite"})[0], 409
        )
        # two interpretations queried and none chosen: the server cannot tell which one
        self._finished(ids=("i1", "i2"))
        status, body = _post(self.port, "/route", {"text": "and the titles"})
        self.assertEqual((status, body), (409, {"error": "pick an interpretation first"}))
        self.assertEqual(_post(self.port, "/choose", {"id": "i2"}), (200, {"id": "i2"}))
        calls = []
        with mock.patch.object(serve.route, "decide", self._decide("rewrite", "how many titles", calls)):
            self.assertEqual(_post(self.port, "/route", {"text": "and the titles"})[0], 200)
        self.assertEqual(calls[0][2], "i2")
        seen: list[str] = []
        self._follow(seen, {"question": "how many titles", "route": "rewrite"})
        self.assertEqual(self.site.current.rewrite[1].id, "i2")

    def test_z_a_chosen_interpretation_that_errored_names_itself(self):
        def failing_query(probe, question, entities, one, log_path, rewrite=None, stop=None, chosen=False):
            return answer.Result(one, "", "SELECT nope", [], [], False, "no such column: nope")

        with mock.patch.object(answer, "query", failing_query):
            self._finished(ids=("i1", "i2"))
        self.assertEqual(_post(self.port, "/choose", {"id": "i2"}), (200, {"id": "i2"}))
        status, body = _post(self.port, "/route", {"text": "and the titles"})
        self.assertEqual(status, 409)
        self.assertIn("i2", body["error"])

    def test_z_a_route_model_error_is_502_and_leaves_the_run_alone(self):
        self._finished()
        before = self.site.current

        def boom(*args):
            raise llm.ModelError("route: no model here")

        with mock.patch.object(serve.route, "decide", boom):
            status, body = _post(self.port, "/route", {"text": "show the titles too"})
        self.assertEqual((status, body), (502, {"error": "route: no model here"}))
        self.assertIs(self.site.current, before)
        self.assertTrue(before.finished)

    def test_z_follow_refuses_a_question_that_points_back_at_the_chat(self):
        self._finished()
        status, body = _post(
            self.port, "/follow", {"question": "the books in list 1", "route": "rewrite"}
        )
        self.assertEqual(status, 400)
        self.assertIn("list", body["error"])
        self.assertEqual(
            _post(self.port, "/follow", {"question": "how many titles", "route": "sideways"})[0], 400
        )
        self.assertEqual(_post(self.port, "/follow", {"route": "rewrite"})[0], 400)

    def test_z_a_rewrite_whose_sql_fails_keeps_the_error(self):
        self._finished()
        follow = "how many books with their titles"

        def failing_query(probe, question, entities, one, log_path, rewrite=None, stop=None, chosen=False):
            return answer.Result(one, "", "SELECT nope", [], [], False, "no such column: nope")

        runs = self.site.runs
        seen: list[str] = []
        with mock.patch.object(answer, "query", failing_query):
            done = self._follow(seen, {"question": follow, "route": "rewrite"})
        self.assertEqual(done["text"], "FINAL TEXT")
        self.assertEqual(seen, ["run", "route", "selected", "querying", "rows", "done"])
        self.assertEqual(self.site.runs, runs + 1)
        self.assertEqual(self.site.current.results[0].error, "no such column: nope")
        self.assertEqual(self.site.current.question, follow)
        # the run answered nothing, but "start over" is still open to it
        type(self).fanout = STOPPED
        over: list[str] = []
        self._follow(over, {"question": follow, "route": "restart"})
        self.assertEqual(over[:3], ["run", "route", "bundle"])

    def test_z_every_follow_up_writes_one_route_line_to_the_log(self):
        self._finished()
        follow = "how many books with their titles"
        before = [
            line
            for line in (self.folder / "ask_toy.jsonl").read_text().splitlines()
            if json.loads(line).get("kind") == "route"
        ]
        self._follow([], {"question": follow, "route": "rewrite"})
        lines = [
            json.loads(line)
            for line in (self.folder / "ask_toy.jsonl").read_text().splitlines()
            if json.loads(line).get("kind") == "route"
        ]
        self.assertEqual(len(lines), len(before) + 1)
        self.assertEqual(
            lines[-1],
            {
                "kind": "route",
                "original": "how many books",
                "route": "rewrite",
                "question": follow,
                "why": route.WHY["rewrite"],
            },
        )

    def test_settings_switch_the_model_and_lane_of_the_next_call(self):
        with mock.patch.object(llm, "models", lambda: ("gpt-6-luna", "gpt-5-nano")), mock.patch.object(
            config, "LLM_MODEL", "gpt-6-luna"
        ), mock.patch.object(config, "LLM_SERVICE_TIER", "flex"), mock.patch.object(config, "THINKING", None):
            self.assertEqual(sorted(_get(self.port, "/settings")["models"]), ["gpt-5-nano", "gpt-6-luna", "qwen3.8-27b-fp8"])
            # the local Qwen is offered with no price, on its one lane
            self.assertEqual(_post(self.port, "/settings", {"model": "qwen3.8-27b-fp8", "lane": "fast"})[0], 400)
            self.assertEqual(_post(self.port, "/settings", {"model": "qwen3.8-27b-fp8"})[1]["lane"], "flex")
            # thinking: only a level this model takes; a model without it goes back to each step's own
            self.assertEqual(_post(self.port, "/settings", {"thinking": "high"})[0], 400)
            self.assertEqual(_post(self.port, "/settings", {"thinking": "xhigh"})[1]["thinking"], "xhigh")
            self.assertIsNone(_post(self.port, "/settings", {"model": "gpt-5-nano"})[1]["thinking"])
            # no Fast lane for this model, and no model the endpoint does not serve
            self.assertEqual(_post(self.port, "/settings", {"model": "gpt-5-nano", "lane": "fast"})[0], 400)
            self.assertEqual(_post(self.port, "/settings", {"model": "o3", "lane": "flex"})[0], 400)
            status, settings = _post(self.port, "/settings", {"model": "gpt-5-nano", "lane": "default"})
            self.assertEqual((status, settings["model"], settings["lane"]), (200, "gpt-5-nano", "default"))
            self.assertEqual((config.LLM_MODEL, config.LLM_SERVICE_TIER), ("gpt-5-nano", "default"))
            # a field left out keeps its value; a model without the lane in use goes to flex
            self.assertEqual(_post(self.port, "/settings", {"model": "gpt-6-luna"})[1]["lane"], "default")
            self.assertEqual(_post(self.port, "/settings", {"lane": "fast"})[1]["model"], "gpt-6-luna")
            self.assertEqual(_post(self.port, "/settings", {"model": "gpt-5-nano"})[1]["lane"], "flex")
        self.assertTrue(all("flex" in lanes for lanes in config.LLM_PRICES.values()))
        self.assertIn(config.LLM_MODEL, {**config.LLM_PRICES, **config.LOCAL_MODELS})


class TestTwoLakes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        folder = Path(cls._tmp.name)
        for name, question in (("lib", "how many books"), ("zoo", "how many pandas")):
            (folder / f"{name}.json").write_text(
                json.dumps([{"question": question, "sql": "SELECT 1", "db_id": name}])
            )
        cls._patches = [
            mock.patch.object(config, "RUNS_DIR", folder),
            mock.patch.object(
                config,
                "lake",
                lambda name: {"questions": folder / f"{name}.json", "databases": []},
            ),
            mock.patch.object(serve, "Probe", lambda name: FakeProbe()),
            mock.patch.object(serve.Lake, "graph", lambda self: None),
            mock.patch.object(llm, "decompose", lambda *args: llm.Decomposition(entities=[])),
            mock.patch.object(bundle, "stage1", fake_stage1),
            mock.patch.object(serve, "_guided", _fake_guided(lambda: solve.FanOut([], [], None))),
            mock.patch.object(answer, "present", lambda *args: "FINAL TEXT"),
        ]
        for patch in cls._patches:
            patch.start()
        cls.site = serve.Site(["lib", "zoo"], 0)
        cls.port = cls.site.server_address[1]
        threading.Thread(target=cls.site.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.site.shutdown()
        cls.site.server_close()
        for patch in cls._patches:
            patch.stop()
        cls._tmp.cleanup()

    def test_each_lake_has_its_own_questions(self):
        self.assertEqual(_get(self.port, "/lakes"), ["lib", "zoo"])
        self.assertEqual(_get(self.port, "/questions?lake=zoo"), ["how many pandas"])
        # no lake named: the first one served
        self.assertEqual(_get(self.port, "/questions"), ["how many books"])
        self.assertEqual(_get(self.port, "/lake?lake=zoo")["name"], "zoo")

    def test_a_run_names_the_lake_it_asks(self):
        self.assertEqual(
            _post(self.port, "/ask", {"lake": "nope", "question": "x"}),
            (400, {"error": "lake 'nope' is not served"}),
        )
        self.assertEqual(
            _post(self.port, "/ask", {"lake": "zoo", "question": "how many pandas"})[0], 200
        )
        seen: list[str] = []
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/events", timeout=10) as stream:
            started = _read_until(stream, ["run", "error"], seen)
            self.assertEqual(started["lake"], "zoo")
            done = _read_until(stream, ["done", "error"], seen)
        self.assertEqual(done["text"], "FINAL TEXT")


class TestUsageTotals(unittest.TestCase):
    def test_sums_tokens_and_prices_each_line_by_its_model_and_lane(self):
        lines = [
            {"model": "gpt-6-luna", "service_tier": "flex",
             "usage": {"input_tokens": 100, "cached_tokens": 40, "output_tokens": 20, "reasoning_tokens": 5}},
            # older-style line: no cached_tokens or service_tier, so the lane set now
            {"model": "gpt-6-luna", "usage": {"input_tokens": 50, "output_tokens": 10, "reasoning_tokens": 0}},
            # served on the fast lane under its old name
            {"model": "gpt-5-mini", "service_tier": "priority",
             "usage": {"input_tokens": 1000, "output_tokens": 0, "reasoning_tokens": 0}},
        ]
        with mock.patch.object(config, "LLM_SERVICE_TIER", "flex"):
            totals = serve.usage_totals(lines)
        self.assertEqual(totals["calls"], 3)
        self.assertEqual(totals["input_tokens"], 1150)
        self.assertEqual(totals["cached_tokens"], 40)
        self.assertEqual(totals["output_tokens"], 30)
        self.assertEqual(totals["reasoning_tokens"], 5)
        self.assertAlmostEqual(totals["dollars"], (110 * 0.05 + 40 * 0.005 + 30 * 0.25 + 1000 * 0.45) / 1e6)

if __name__ == "__main__":
    unittest.main()
