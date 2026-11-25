"""The column chosen for each part of the question, as a binding records it.

The pick step that once chose these columns with an LLM is gone; interpret.py and solve.py
still record a part's place in these shapes.
"""

from pydantic import BaseModel

# the queries the server writes at once, one per interpretation the person ticked
WORKERS = 8


class PickedColumn(BaseModel):
    column: str
    reason: str


class PickedEntity(BaseModel):
    entity: str
    columns: list[PickedColumn]


class Pick(BaseModel):
    entities: list[PickedEntity]


