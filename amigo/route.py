"""Where typed words go after a finished run: the same interpretation again, or a cold start."""

import re
import string
from pathlib import Path

from pydantic import BaseModel

from . import answer, clarify, config, llm
from .probe import Probe

# a follow-up question names things by what they are, so it can be asked on its own
BANNED = re.compile(
    r"\b(?:lists?|options?)\s+\d+\b|\bthis conversation\b|\b(?:shown|listed|mentioned) above\b",
    re.IGNORECASE,
)

WHY = {
    "rewrite": "what it asks for is in the tables the last answer already uses",
    "restart": "what it asks for is not in the tables the last answer uses, or could mean more than one of their columns",
}


class Routed(BaseModel):
    route: str
    question: str


def _flat(text: str) -> str:
    return " ".join(text.lower().split())


def decide(
    probe: Probe,
    original: str,
    turns: list[dict],
    result: answer.Result,
    text: str,
    log_path: Path,
) -> dict:
    """One call that says whether the typed words need only new SQL, and words the question."""
    template = string.Template((config.PROMPTS_DIR / "route.txt").read_text())
    one = result.interpretation

    def check(reply: Routed) -> None:
        if reply.route not in WHY:
            raise llm.ModelError(
                f"model returned route {reply.route!r}, which must be one of {sorted(WHY)}"
            )
        if not reply.question.strip() or _flat(reply.question) == _flat(original):
            raise llm.ModelError(
                "a follow-up question must hold text and differ from the original question"
            )
        hits = BANNED.findall(reply.question)
        if hits:
            raise llm.ModelError(
                f"the question carries {hits}, so it points back at this conversation"
                " instead of naming things by what they are"
            )

    reply = llm.call(
        template.substitute(
            original=original,
            turns=clarify.turn_lines(turns),
            sql=result.sql,
            columns=", ".join(result.columns) or "none",
            context=answer.context(
                probe,
                one.tables,
                [c for binding in one.bindings for c in binding.columns],
                one.joins,
                one.either,
            ),
            reply=text,
        ),
        Routed,
        log_path,
        f"route {text[:40]}",
        check=check,
    )
    return {
        "route": reply.route,
        "question": reply.question.strip(),
        "why": WHY[reply.route],
    }
