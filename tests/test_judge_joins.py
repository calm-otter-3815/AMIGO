from types import SimpleNamespace

from amigo import candidates as C
from amigo import judge, llm, solve


def test_chosen_keeps_the_ways_said_yes():
    # crossing (1) joins port (2) by its departure or its arrival port: two ways
    table = {"database": "ferries", "row_count": 9, "description": ""}
    probe = SimpleNamespace(
        tables={1: {**table, "name": "crossing"}, 2: {**table, "name": "port"}},
        columns={10: {"name": "depart_id", "table_id": 1, "description": "the port it leaves from"},
                 12: {"name": "crossing_id", "table_id": 1, "description": ""},
                 11: {"name": "arrive_id", "table_id": 1, "description": "the port it arrives at"},
                 20: {"name": "port_id", "table_id": 2, "description": ""},
                 21: {"name": "name", "table_id": 2, "description": ""}})
    graph = SimpleNamespace(references={10: {2}, 11: {2}})
    depart, arrive = solve.Join(((10, 20),), 1.0), solve.Join(((11, 20),), 1.0)
    memo = {(1, 2): [("one", (depart,)), ("one", (arrive,))]}
    one = C.Candidate(database="d", tables=(1, 2), holders=(C.Holder(0, 1, 12, 0.0, ""),
                                                             C.Holder(1, 2, 21, 0.0, "")),
                      edges=((1, 2),), cost=1.0)
    stage = SimpleNamespace(entities=[llm.Entity(attribute="crossings", literal=None),
                                      llm.Entity(attribute="port name", literal=None)])
    asked = []

    def call(prompt, schema, *args, check=None, **kw):
        asked.append(prompt)
        result = schema.model_validate({"1": [2]})
        check(result)
        return result

    real, llm.call = llm.call, call
    try:
        found, info = judge.chosen(probe, graph, "crossings arriving at Elm", stage, [one], memo, None)
    finally:
        llm.call = real
    assert len(asked) == 1 and "  2. ferries.crossing.arrive_id = ferries.port.port_id (the port it arrives at)" in asked[0]
    assert [one.extra["ways"][(1, 2)] for one in found] == [("one", (arrive,))]
    assert info == {"joins": 1, "refused": 0, "ways": 1, "capped": 0}


def test_decompose_reads_one_value_per_concept():
    reply = llm.Concepts.model_validate({"concepts": [
        {"concept": "book"}, {"concept": "book's author", "text": "Chinua Achebe"},
        {"concept": "book's borrowing date", "from": "2023-01-01"}]})
    entities = [llm._entity(one) for one in reply.concepts]
    assert entities[0].literal is None
    assert (entities[1].literal.kind, entities[1].literal.text) == ("text", "Chinua Achebe")
    assert (entities[2].literal.kind, entities[2].literal.date_start, entities[2].literal.date_end) == ("date", "2023-01-01", None)
