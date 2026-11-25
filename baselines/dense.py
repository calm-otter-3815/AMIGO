"""Dense table retrieval: the k tables whose card vectors are closest to the question.

The plainest retriever, with the lake's own table vectors (embed.table_text), so it
differs from AMIGO only in how tables are chosen. k is fixed in advance, not tuned.
"""

from .lake import lap, record


def run(lake, question, log_path, k=3):
    ranked = lake.rank_tables(question)
    lap("search")
    return record([table.path for table, _ in ranked[:k]])
