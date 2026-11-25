"""Link graph from PLAN.md section 2.2: declared foreign keys and inferred links."""

import heapq
import logging
import math
import re
import sqlite3
import zlib
from collections import Counter, defaultdict

from tqdm import tqdm

from .index import normalise
from .profile import quote as _quote

log = logging.getLogger(__name__)

# The plain reading of "whose values are contained in it" as "mostly contained".
# Measured over BIRD dev: real relationships sit at 0.56 and above, coincidental
# overlaps at 0.48 and below. The share is stored so this choice stays visible.
MIN_SHARE = 0.5

# The semantic design's link rule (section 3): a column almost all of whose values sit
# in another table's column points at it, whatever the names say: a trades column named
# for what it does (ISPAIDFROM) can hold account ids no name rule reads. A key pointing
# into a far larger id space scores near 0 once the distinct-count ratio is multiplied
# in, so containment alone is the gate.
CONTAINED = 0.95
# Fewer distinct values than this sit inside some key by chance, and a flag or a small
# code is no pointer.
MIN_DISTINCT = 20
# A column with fewer values still points at a key when the odds that chance put them
# all in it are below this: see small_links.
SMALL_CHANCE = 0.01
# Values kept per column to test containment: the ones with the smallest hash, so every
# column samples the same values (a bottom-k sketch) and a contained column's sample
# sits in its target.
SKETCH = 256
# A key: a different value on at least this share of its table's rows. Not strictly
# unique, as a warehouse table keeps a row per version of the thing a key names.
KEY_SHARE = 0.9
# An id counting up: whole numbers from 0 or 1 with at most a tenth of them missing.
COUNTER_SHARE = 0.9
# The last word of a column named as a key: TERM_CODE, port_id, instance_uuid.
KEY_WORDS = {"id", "key", "uuid", "fk", "ref", "code", "no", "num"}
# A key the judge is shown: a different value on at least this share of its rows (a cut
# or a history table repeats some), holding at least JUDGE_SHARE of the column's values;
# at most JUDGE_CANDIDATES keys a call.
KEYLIKE = 0.5
JUDGE_SHARE = 0.5
JUDGE_CANDIDATES = 8

NON_ALNUM = re.compile(r"[^a-z0-9]")
# a name's words: Host_city_ID and hostCityId are both host, city, id
WORD = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|[0-9]+")


def quality(link, source: dict, target: dict) -> float:
    """How good one link is to join on: 1.0 when declared, else containment times
    cardinality proportion, the join-quality measure of the join-discovery work (Flores,
    Nadal and Romero 2023; Freyja 2024): a Y/N flag sitting inside a key scores 1.0 on
    containment alone, and only the proportion of the two distinct counts catches it.
    """
    if link["kind"] == "declared":
        return 1.0
    # the semantic layer's links: the share of values contained (found by the values, or
    # judged off the descriptions), or the gate for a name
    if link["kind"] in ("values", "judged", "name"):
        return link["score"]
    low, high = sorted((source["distinct_count"] or 0, target["distinct_count"] or 0))
    return link["score"] * low / high if high else 0.0


def declared(
    conn: sqlite3.Connection, table: str, tables: list[str]
) -> list[tuple[int, str, str, str]]:
    """(constraint, from column, to table, to column) per declared foreign key column.

    The columns of one constraint share its number: a composite key is one join.
    """
    real_name = {name.lower(): name for name in tables}
    links = []
    for row in conn.execute(f"PRAGMA foreign_key_list({_quote(table)})"):
        constraint, target, from_column, to_column = row[0], row[2], row[3], row[4]
        # SQLite compares table names case-insensitively, so League.country_id
        # may name "country" while the table is "Country".
        to_table = real_name.get(target.lower())
        if to_table is None:
            raise ValueError(
                f"declared: foreign key {table}.{from_column} -> {target} "
                f"names a table that is not in the database"
            )
        if to_column is None:
            to_column = _primary_key(conn, to_table, table, from_column)
        # Spider ships three declared foreign keys naming a column that isn't
        # actually on the target table (e.g. baseball_1 fielding_postseason.team_id
        # -> player.team_id, where player has no team_id). Skip those rather
        # than raising, so build doesn't die on someone else's bad schema.
        to_columns = {row[1].lower() for row in conn.execute(f"PRAGMA table_info({_quote(to_table)})")}
        if to_column.lower() not in to_columns:
            log.warning(
                "declared: foreign key %s.%s -> %s.%s names a column that does not "
                "exist, skipped",
                table, from_column, to_table, to_column,
            )
            continue
        links.append((constraint, from_column, to_table, to_column))
    return list(dict.fromkeys(links))


def _primary_key(
    conn: sqlite3.Connection, to_table: str, table: str, from_column: str
) -> str:
    # A NULL "to" in PRAGMA foreign_key_list means the target's primary key.
    keys = [row[1] for row in conn.execute(f"PRAGMA table_info({_quote(to_table)})") if row[5]]
    if len(keys) != 1:
        raise ValueError(
            f"declared: foreign key {table}.{from_column} -> {to_table} names no target "
            f"column and {to_table} has {len(keys)} primary-key columns"
        )
    return keys[0]


def inferred(
    conn: sqlite3.Connection, columns: list[dict], declared_pairs: set[tuple[int, int]]
) -> list[tuple[int, int, float]]:
    # Two rules. Text columns are linked on containment alone: the value index
    # holds only text, and a shared vocabulary is already evidence. Integer
    # columns are linked only when the names agree and the key side really is a
    # key, because plain integer containment is dominated by autoincrement ids
    # covering the same range -- measured over BIRD dev it gave 1 correct link
    # in 577.
    text = [card for card in columns if card["kind"] == "text"]
    keys = [card for card in text if card["is_unique"]]
    key_texts = {card["id"]: _texts(conn, card["table"], card["name"]) for card in keys}
    key_values = {i: _normalised(texts) for i, texts in key_texts.items()}
    # Whole numbers written as decimals ("12.0") are numbers stored as text, and link as
    # numbers do: only where the names agree, as small counts sit inside any id range.
    decimals = {i for i, texts in key_texts.items() if _decimals(texts)}

    links = []
    for card in tqdm(text, desc="links", leave=False):
        candidates = [
            key
            for key in keys
            if key["table"] != card["table"]
            and (card["id"], key["id"]) not in declared_pairs
            and (key["id"], card["id"]) not in declared_pairs
            and not _both_keys_named_id(card, key)
        ]
        if not candidates:
            continue
        texts = key_texts.get(card["id"]) or _texts(conn, card["table"], card["name"])
        values = key_values.get(card["id"]) or _normalised(texts)
        if not values:
            continue
        own = _decimals(texts)
        numbers = [key for key in candidates if own or key["id"] in decimals]
        best = max((_name_fit(card, key) for key in numbers), default=0)
        candidates = [
            key for key in candidates if key not in numbers or (best and _name_fit(card, key) == best)
        ]
        for key in candidates:
            share = len(values & key_values[key["id"]]) / len(values)
            if share >= MIN_SHARE:
                links.append((card["id"], key["id"], share))
    integer = _integer_links(conn, columns, declared_pairs)
    log.info(
        "inferred %d links from %d text columns and %d links from number columns",
        len(links), len(text), len(integer),
    )
    return links + integer


def _integer_links(
    conn: sqlite3.Connection, columns: list[dict], declared_pairs: set[tuple[int, int]]
) -> list[tuple[int, int, float]]:
    numbers = [card for card in columns if card["kind"] == "number"]
    # one part of a composite primary key is not a key: only a unique column is
    key_values = {
        card["id"]: _numbers(conn, card["table"], card["name"])
        for card in numbers
        if card["is_unique"]
    }
    keys = [card for card in numbers if key_values.get(card["id"])]

    links = []
    for card in tqdm(numbers, desc="links", leave=False):
        candidates = [
            key
            for key in keys
            if key["table"] != card["table"]
            and _name_fit(card, key)
            and not _both_keys_named_id(card, key)
        ]
        if not candidates:
            continue
        # post_id starts both "posts" and "postHistory": the table it names wins, even
        # when that link is declared and so is not inferred again here
        best = max(_name_fit(card, key) for key in candidates)
        candidates = [
            key
            for key in candidates
            if _name_fit(card, key) == best
            and (card["id"], key["id"]) not in declared_pairs
            and (key["id"], card["id"]) not in declared_pairs
        ]
        if not candidates:
            continue
        values = key_values.get(card["id"]) or _numbers(conn, card["table"], card["name"])
        # A one-value column (a constant 1, say) sits inside every id key.
        if len(values) < 2:
            continue
        for key in candidates:
            share = len(values & key_values[key["id"]]) / len(values)
            if share >= MIN_SHARE:
                links.append((card["id"], key["id"], share))
    return links


def contained(
    conn: sqlite3.Connection, columns: list[dict], declared_pairs: set[tuple[int, int]]
) -> list[tuple[int, int, float]]:
    """(column, key, share) where at least CONTAINED of a column's values sit in a key
    of another table.

    Of the columns holding it, the one it covers most of is where it points, as a key
    sits inside every wider id space too; columns tied on that hold the same values, and
    each is kept. That column has to be a key, a different value on nearly every row:
    a column repeating the values, holding them more tightly than any key, makes this
    one a copy of an attribute (a city, a count), not a pointer, and joining on a
    repeated value joins many rows to many. Only text points at text and numbers at
    numbers. A column the schema says where it points is left to the declaration.

    Numbers land in a key by chance as often as the numbers next to them do: counts,
    heights and a table's own row numbers sit inside any key that holds nearly every
    number around them. Such a key takes a name that agrees; see _by_chance.
    """
    card_of = {card["id"]: card for card in columns}
    pointing = {a for a, _ in declared_pairs}
    sample, near = {}, {}
    for card in tqdm(columns, desc="contained", leave=False):
        values = _plain(conn, card)
        if values:
            sample[card["id"]] = heapq.nsmallest(SKETCH, values, key=_hash)
            if card["kind"] == "number":
                near[card["id"]] = _neighbours(sample[card["id"]])
    wanted = set().union(*sample.values(), *near.values())
    holders: dict[str, set[int]] = defaultdict(set)
    size = {}
    for card in tqdm(columns, desc="contained", leave=False):
        if card["id"] in sample:
            values = _plain(conn, card)
            size[card["id"]] = len(values)
            for value in wanted & values:
                holders[value].add(card["id"])
    keys = {c for c, n in size.items() if n >= KEY_SHARE * card_of[c]["rows"]}
    tried = sum(card_of[c]["kind"] == "number" for c in keys)

    links = []
    for column, values in sample.items():
        if column in pointing:
            continue
        card = card_of[column]
        hits = Counter(
            target
            for value in values
            for target in holders[value]
            if card_of[target]["table"] != card["table"]
            and card_of[target]["kind"] == card["kind"]
            and (column, target) not in declared_pairs
            and (target, column) not in declared_pairs
        )
        share = {t: n / len(values) for t, n in hits.items() if n >= CONTAINED * len(values)}
        if not share:
            continue
        # a sample can miss the few values outside the target; none covers more than all
        cover = {t: min(1.0, s * size[column] / size[t]) for t, s in share.items()}
        tightest = [t for t in sorted(share) if cover[t] == max(cover.values())]
        nearby = Counter(t for value in near.get(column, ()) for t in holders[value])
        links += [
            (column, t, round(share[t], 3))
            for t in tightest
            if t in keys
            and not _both_keys_named_id(card, card_of[t])
            and (
                column not in near
                or not _by_chance(hits[t], len(values), nearby[t] / len(near[column]), tried)
                or _name_fit(card, card_of[t])
            )
        ]
    log.info("contained: %d links from %d columns with enough values", len(links), len(sample))
    return links


def small_links(
    conn: sqlite3.Connection,
    columns: list[dict],
    declared_pairs: set[tuple[int, int]],
    linked: set[tuple[int, int]],
) -> list[tuple[int, int, float]]:
    """(column, key, share) for a number column with too few values for contained(): a
    few people's ids among thousands. Every value sits in a key of another table, and
    the key is sparse enough in the values' range that chance would not put them there.

    n values on R numbers of their range and step land in a key holding k of those R
    with odds (k / R) ** n, times the keys tried; the odds must stay under SMALL_CHANCE. Of the
    keys that pass, the one the values cover most of is where it points, ties kept. A
    column one of its own table's keys holds points into its own table, not out of it.
    Pairs already linked, either way, are left as they are.
    """
    card_of = {card["id"]: card for card in columns}
    pointing = {a for a, _ in declared_pairs}
    whole = {}
    for card in columns:
        rows, distinct = card["rows"] or 0, card["distinct_count"] or 0
        small = 2 <= distinct < MIN_DISTINCT and card["id"] not in pointing
        if card["kind"] == "number" and (small or (rows and distinct >= KEY_SHARE * rows)):
            numbers = _numbers(conn, card["table"], card["name"])
            if numbers and all(float(n).is_integer() for n in numbers):
                whole[card["id"]] = {int(n) for n in numbers}
    keys = [
        c for c, values in whole.items()
        if card_of[c]["rows"] and len(values) >= KEY_SHARE * card_of[c]["rows"]
    ]

    links = []
    for column, values in whole.items():
        card = card_of[column]
        if column in pointing or not 2 <= len(values) < MIN_DISTINCT:
            continue
        if all(1800 <= v <= 2100 for v in values):
            continue
        holding = [k for k in keys if k != column and values <= whole[k]]
        if any(card_of[k]["table"] == card["table"] for k in holding):
            continue
        passed = [
            k
            for k in holding
            if (column, k) not in linked
            and (k, column) not in linked
            and not _both_keys_named_id(card, card_of[k])
            and _chance(values, whole[k]) * len(keys) <= SMALL_CHANCE
        ]
        if passed:
            fewest = min(len(whole[k]) for k in passed)
            tightest = [k for k in passed if len(whole[k]) == fewest]
            links += [(column, k, round(len(values) / fewest, 3)) for k in tightest]
    log.info("small links: %d", len(links))
    return links


def agreeing(
    conn: sqlite3.Connection,
    columns: list[dict],
    declared_pairs: set[tuple[int, int]],
    sure: set[tuple[int, int]],
) -> list[tuple[int, int, float]]:
    """(column, key, share) where the names and the values agree: the column is named for
    a key of another table (TERM_CODE for ACADEMIC_TERMS_ALL.TERM_CODE, port_id for
    PORTS.id), the key is its table's primary key or named as one, and at least CONTAINED
    of the column's values sit in it. contained() follows the values alone, to the key
    they cover most of, and needs MIN_DISTINCT of them; a name that agrees points past a
    tighter copy of the key, at a key the column uses a few values of, and with a few
    values.

    Two columns both named just id agree because both count up, not because one points at
    the other. A few small numbers sit in any id counting up from 1, and any column of
    them sits in two such ids of different tables: the values cannot tell which one the
    column means, and it is left unlinked. A key with a sure link to a larger key the
    column also agrees with is a copy of it, reached through that link.
    """
    card_of = {card["id"]: card for card in columns}
    pointing = {a for a, _ in declared_pairs}
    plain = [card for card in columns if card["kind"] in ("text", "number")]
    keyed = [card for card in plain if card["rows"] and _named_key(card)]
    every = {}

    def values(card: dict) -> set[str]:
        if card["id"] not in every:
            every[card["id"]] = _plain(conn, card, least=1) or set()
        return every[card["id"]]

    links = []
    for card in tqdm(plain, desc="agreeing", leave=False):
        if card["id"] in pointing:
            continue
        fit = [
            key
            for key in keyed
            if key["table"] != card["table"]
            and key["kind"] == card["kind"]
            and not _norm(card["name"]) == _norm(key["name"]) == "id"
            and (card["id"], key["id"]) not in declared_pairs
            and (key["id"], card["id"]) not in declared_pairs
            and _name_fit(card, key) == 3
        ]
        own = fit and values(card)
        if not own:
            continue
        share, counter = {}, set()
        for key in fit:
            held = values(key)
            if len(held) < KEY_SHARE * key["rows"]:
                continue
            counts = card["kind"] == "number" and _counts_up(held)
            if counts and len(own) < MIN_DISTINCT:
                continue
            if (s := len(own & held) / len(own)) >= CONTAINED:
                share[key["id"]] = s
                if counts:
                    counter.add(key["id"])
        targets = [
            k for k in share if not any((k, j) in sure and len(every[j]) > len(every[k]) for j in share)
        ]
        if len({card_of[k]["table"] for k in targets}) > 1 and len(counter & set(targets)) >= 2:
            continue
        links += [(card["id"], k, round(share[k], 3)) for k in targets]
    log.info("agreeing: %d links", len(links))
    return links


def _named_key(card: dict) -> bool:
    words = _words(card["name"])
    return bool(card["is_pk"]) or bool(words and words[-1] in KEY_WORDS)


def candidates(
    conn: sqlite3.Connection,
    columns: list[dict],
    declared_pairs: set[tuple[int, int]],
    sure: set[tuple[int, int]],
) -> dict[int, list[tuple[int, float]]]:
    """column -> [(key, share)]: the keys a column no rule settles may point at, for the
    judge to choose from. A key is a column of another table with a different value on
    at least KEYLIKE of its rows, holding at least JUDGE_SHARE of the column's values, all
    of them when it has fewer than MIN_DISTINCT. At most JUDGE_CANDIDATES per column:
    names that agree first, then the keys its values cover most of.

    Values alone cannot settle these: small numbers sit in many ids, a key may be cut or
    kept twice, a code repeats in a table about something else. Left out are a column the
    schema says where it points, one with a sure link to a key its name agrees with, a
    table's own id counting up (every wider id holds it), and a column whose keys all
    have a sure link already. Text and numbers compare as text: an id kept as text points
    at a number key.
    """
    card_of = {card["id"]: card for card in columns}
    settled = {a for a, _ in declared_pairs} | {
        a for a, b in sure if _name_fit(card_of[a], card_of[b]) == 3
    }
    values = {card["id"]: found for card in columns if (found := _plain(conn, card, least=1))}
    keylike = [c for c, v in values.items() if len(v) >= KEYLIKE * card_of[c]["rows"]]
    open_columns = [
        c for c, v in values.items()
        if c not in settled
        and not (card_of[c]["is_unique"] and card_of[c]["kind"] == "number" and _counts_up(v))
    ]
    sample = {c: heapq.nsmallest(SKETCH, values[c], key=_hash) for c in open_columns}
    wanted = set().union(*sample.values()) if sample else set()
    holders: dict[str, set[int]] = defaultdict(set)
    for key in keylike:
        for value in wanted & values[key]:
            holders[value].add(key)
    found = {}
    for column in open_columns:
        card, own = card_of[column], values[column]
        need = 1.0 if len(own) < MIN_DISTINCT else JUDGE_SHARE
        hits = Counter(
            key
            for value in sample[column]
            for key in holders[value]
            if card_of[key]["table"] != card["table"]
            and (column, key) not in declared_pairs
            and (key, column) not in declared_pairs
            and not _both_keys_named_id(card, card_of[key])
        )
        # the sample shortlists; the share is counted on every value
        share = {
            key: s
            for key, n in hits.items()
            if n >= need * len(sample[column]) / 2
            and (s := len(own & values[key]) / len(own)) >= need
        }
        fit = {key: max(_name_fit(card, card_of[key]), _name_fit(card_of[key], card)) for key in share}
        shown = sorted(
            share, key=lambda key: (-(fit[key] > 0), -share[key] * len(own) / len(values[key]), key)
        )[:JUDGE_CANDIDATES]
        if any((column, key) not in sure and (key, column) not in sure for key in shown):
            found[column] = [(key, round(share[key], 3)) for key in shown]
    log.info("candidates: %d columns for the judge", len(found))
    return found


def _chance(values: set[int], key: set[int]) -> float:
    """The odds a key holds these values by chance: each lands on one of the key's
    values in their range, counted in the values' own step, as round numbers (30, 50,
    100) only ever land on round numbers."""
    low, high = min(values), max(values)
    step = math.gcd(*(v - low for v in values))
    held = sum(low <= v <= high and (v - low) % step == 0 for v in key)
    return (held / ((high - low) // step + 1)) ** len(values)


def _neighbours(sample: list[str]) -> list[str]:
    """The numbers one step below and above each sampled number, in the sample's own step,
    as round numbers (30, 50, 100) only ever sit next to round numbers."""
    numbers = [int(v) for v in sample]
    low = min(numbers)
    step = math.gcd(*(v - low for v in numbers)) or 1
    return [str(v + d) for v in numbers for d in (-step, step)]


def _by_chance(hits: int, n: int, near: float, tried: int) -> bool:
    """Whether chance explains `hits` of n sampled numbers sitting in a key that holds a
    `near` share of their neighbours: each number lands in it as often as the numbers next
    to it do, so the odds of that many hits or more, times the keys tried, are above
    SMALL_CHANCE. A key holding nearly every number around the values holds them whatever
    they mean; one with gaps between them, that they all avoid, is where they point."""
    odds = sum(math.comb(n, x) * near**x * (1 - near) ** (n - x) for x in range(hits, n + 1))
    return odds * tried > SMALL_CHANCE


def _counts_up(values: set[str]) -> bool:
    """Whole numbers from 0 or 1 with few gaps: the ids a table numbers its rows with."""
    numbers = [int(v) for v in values]
    low, high = min(numbers), max(numbers)
    return low <= 1 and len(numbers) >= COUNTER_SHARE * (high - low + 1)


def named(columns: list[dict], declared_pairs: set[tuple[int, int]]) -> list[tuple[int, int]]:
    """(column, key) for links no values can check, out of an empty column or into an
    empty table: stem_id points to the table named stem or stems, at its column id.

    The key is the column the rest of the name names, and it has to be a key: unique,
    declared, or named id (an empty table has no values to be unique).
    """
    pointing = {a for a, _ in declared_pairs}
    by_table: dict[str, list[dict]] = defaultdict(list)
    for card in columns:
        by_table[card["table"]].append(card)
    links = []
    for card in columns:
        if card["id"] in pointing:
            continue
        for table, keys in by_table.items():
            if table == card["table"]:
                continue
            for key in keys:
                a, k = _norm(card["name"]), _norm(key["name"])
                if not (
                    (card["kind"] == "empty" or key["rows"] == 0)
                    and (key["is_unique"] or key["is_pk"] or k == "id")
                    and len(a) > len(k)
                    and a.endswith(k)
                    and _stem_names(a[: len(a) - len(k)], _norm(table))
                    and (card["id"], key["id"]) not in declared_pairs
                    and (key["id"], card["id"]) not in declared_pairs
                ):
                    continue
                links.append((card["id"], key["id"]))
    log.info("named: %d links onto or out of empty tables", len(links))
    return links


def _plain(conn: sqlite3.Connection, card: dict, least: int = MIN_DISTINCT) -> set[str] | None:
    """A column's distinct values as text, a number and its digits alike; None when the
    column can point nowhere: fewer than `least` values, a measure with fractions, or
    years."""
    if card["kind"] not in ("text", "number") or (card["distinct_count"] or 0) < least:
        return None
    if card["kind"] == "number":
        numbers = _numbers(conn, card["table"], card["name"])
        if any(isinstance(n, float) and not n.is_integer() for n in numbers):
            return None
        values = {str(int(n)) for n in numbers}
    else:
        values = _values(conn, card["table"], card["name"])
    if len(values) < least or all(v.isdecimal() and 1800 <= int(v) <= 2100 for v in values):
        return None
    return values


def _hash(value: str) -> int:
    # not hash(): Python salts it per process, and the sample has to be the same each build
    return zlib.crc32(value.encode())


def _stem_names(prefix: str, table: str) -> bool:
    """The prefix names the table, singular or plural: country against country,
    countries; class against classes."""
    return table in (prefix, prefix + "s", prefix + "es") or (
        prefix.endswith("y") and table == prefix[:-1] + "ies"
    )


def _norm(name: str) -> str:
    return NON_ALNUM.sub("", name.lower())


def _both_keys_named_id(card: dict, key: dict) -> bool:
    """Two tables' own keys that are both just "id": their values overlap because both
    count up from 1, not because one points at the other. A column named id that is not
    unique (one row per student in a takes table) can still point at a key."""
    return card["is_unique"] and _norm(card["name"]) == _norm(key["name"]) == "id"


def _words(name: str) -> list[str]:
    return [word.lower() for word in WORD.findall(name)]


def _role(card: dict, key: dict) -> int:
    """1 when the column is a role of the key: Host_city_ID ends with the key city.City_ID,
    caused_by_ship_id with ship and the key's bare id. Only an id names a row of another
    table, so Launch_year is no link to budget.Year; a table's own key points nowhere."""
    words, wanted = _words(card["name"]), _words(key["name"])
    if wanted == ["id"]:
        wanted = [w for w in _words(key["table"]) if not w.isdigit()] + ["id"]
    own = [w for w in _words(card["table"]) if not w.isdigit()] + ["id"]
    return int(
        wanted[-1] == "id"
        and words != own
        and len(words) > len(wanted)
        and words[-len(wanted):] == wanted
    )


def _name_fit(card: dict, key: dict) -> int:
    """3 when the names agree outright, 2 when the prefix only starts the table's name
    (Essn against table employee), 1 when the column is a role of the key, 0 when they
    disagree.

    Equal names, or one is the other prefixed by the table it points at:
    department_id against id on table department(s), either way round. Also the
    key naming itself: match_season.Team against team.Team_id.
    """
    a, k = _norm(card["name"]), _norm(key["name"])
    if a == k or k == a + "id":
        return 3
    if a.endswith(k):
        prefix, table = a[: len(a) - len(k)], _norm(key["table"])
    elif k.endswith(a):
        prefix, table = k[: len(k) - len(a)], _norm(card["table"])
    else:
        return _role(card, key)
    if _stem_names(prefix, table):
        return 3
    return 2 if table.startswith(prefix) else _role(card, key)


def _numbers(conn: sqlite3.Connection, table: str, column: str) -> set[int | float]:
    # Some ids are stored as REAL (1.0); Python compares 1 == 1.0, so one set works.
    c = _quote(column)
    rows = conn.execute(
        f"SELECT DISTINCT {c} FROM {_quote(table)} WHERE typeof({c}) IN ('integer', 'real')"
    )
    return {value for (value,) in rows}


def _texts(conn: sqlite3.Connection, table: str, column: str) -> set[str]:
    c = _quote(column)
    rows = conn.execute(
        f"SELECT DISTINCT {c} FROM {_quote(table)} "
        f"WHERE typeof({c}) = 'text' AND trim({c}) <> ''"
    )
    return {value for (value,) in rows}


def _values(conn: sqlite3.Connection, table: str, column: str) -> set[str]:
    return _normalised(_texts(conn, table, column))


def _normalised(texts: set[str]) -> set[str]:
    return {text for value in texts if (text := normalise(whole(value)))}


def _decimals(texts: set[str]) -> bool:
    return bool(texts) and all(WHOLE.fullmatch(value.strip()) for value in texts)


WHOLE = re.compile(r"-?\d+\.0+")


def whole(value: str) -> str:
    """An id written as a decimal ("149.0") as the id it is ("149"): the dot would
    otherwise be dropped as punctuation, and 149.0 read as 1490."""
    return value.split(".")[0] if WHOLE.fullmatch(value.strip()) else value
