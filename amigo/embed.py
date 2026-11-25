"""Card text and embeddings (PLAN.md 2.2)."""

import functools
import logging
import threading

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from . import config

log = logging.getLogger(__name__)

DIM = 768
BATCH = 64
# threads that load or run the model at the same moment crash Python itself
_LOCK = threading.Lock()


def _sentences(head: str, *rest: str | None) -> str:
    return " ".join([head, *(part.strip() for part in rest if part and part.strip())])


def table_text(card: dict) -> str:
    head = f"{card['database_readable']}, {card['readable']}."
    return _sentences(head, card["description"])


def column_text(card: dict) -> str:
    head = f"{card['table_readable']}, {card['readable']}"
    if card["type"]:
        head += f" ({card['type']})"
    samples = card["samples"]
    return _sentences(
        head + ".",
        card["description"],
        card["value_description"],
        f"Examples: {', '.join(str(value) for value in samples)}" if samples else None,
    )


def whole_words() -> dict[str, int]:
    """The tokenizer's whole words, lower case, with their rank in its vocabulary: a byte
    BPE vocabulary lists its merges roughly from the most frequent to the least."""
    rank: dict[str, int] = {}
    for token, number in sorted(_model().tokenizer.get_vocab().items(), key=lambda kv: kv[1]):
        if token.startswith("Ġ") and token[1:].isalpha():
            rank.setdefault(token[1:].lower(), number)
    return rank


def role_text(card: dict) -> str:
    """A column as the link that points at its table names it."""
    return f"{card['words']} ({card['source_table']}): " + column_text(card)


@functools.lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    log.info("loading embedding model %s", config.EMBEDDING_MODEL)
    return SentenceTransformer(
        config.EMBEDDING_MODEL,
        revision=config.EMBEDDING_REVISION,
        model_kwargs={"torch_dtype": "float32"},
    )


def embed(texts: list[str]) -> np.ndarray:
    """L2-normalised float32 vectors, one row per text, so cosine is a dot product."""
    if not texts:
        return np.zeros((0, DIM), dtype=np.float32)
    # granite-embedding-english-r2 takes queries and documents as plain text: its
    # model card shows no prefix and it ships no sentence-transformers prompt config.
    batch = BATCH
    with _LOCK:
        while True:
            try:
                vectors = _model().encode(
                    texts,
                    batch_size=batch,
                    normalize_embeddings=True,
                    # a bar for a lake build, not for every one-text query of a question
                    show_progress_bar=len(texts) > BATCH,
                    convert_to_numpy=True,
                )
                break
            except torch.OutOfMemoryError:
                # the GPU is shared (an LLM server on it): long texts in a big batch do not
                # fit, smaller batches give the same vectors
                if batch == 1:
                    raise
                batch //= 2
                torch.cuda.empty_cache()
                log.warning("embedding: GPU out of memory, batch %d", batch)
    return vectors.astype(np.float32, copy=False)
