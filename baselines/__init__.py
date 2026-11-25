"""Single-answer baselines, re-implemented on AMIGO's lakes.

Each method reads only the question and the lake (the same layer cards AMIGO reads),
never the gold, and returns one result per question. Records use the format of
experiments/eval_lakes.py, so one scorer serves AMIGO and every baseline.
"""
