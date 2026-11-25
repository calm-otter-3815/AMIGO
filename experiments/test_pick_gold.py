"""One check on the gold-column extractor: python experiments/test_pick_gold.py"""

from pick_prompt import gold_columns  # noqa: E402  (same folder)

SCHEMA = {
    "frpm": ["CDSCode", "County Name", "Enrollment (K-12)", "FRPM Count (K-12)"],
    "schools": ["CDSCode", "County", "School", "FundingType"],
}

# BIRD dev style: aliases, backticked names with spaces, a bare column, a literal
SQL = (
    "SELECT T2.`School`, T1.`FRPM Count (K-12)` FROM frpm AS T1 "
    "INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode "
    "WHERE T2.County = 'Los Angeles' AND FundingType = 'Directly funded' "
    "ORDER BY T1.`Enrollment (K-12)` DESC"
)

tables, columns = gold_columns(SQL, SCHEMA)
assert tables == {"frpm", "schools"}, tables
assert columns == {
    "schools.School",
    "frpm.FRPM Count (K-12)",
    "frpm.CDSCode",
    "schools.CDSCode",
    "schools.County",
    "schools.FundingType",  # bare, resolved against the FROM/JOIN tables
    "frpm.Enrollment (K-12)",
}, columns

# a literal must not become a column, and an unknown table must not appear
tables, columns = gold_columns(
    "SELECT COUNT(*) FROM missing AS T1 WHERE T1.County = 'schools'", SCHEMA
)
assert tables == set(), tables
assert columns == set(), columns

print("ok")
