import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))

import latency  # noqa: E402


def test_windows_and_flags():
    got = latency.windows(["a", "b"], {"a": 2.0, "b": 3.0}, 10.0)
    assert got == {"a": (5.0, 7.0), "b": (7.0, 10.0)}
    calm = [{"t": t, "vllm_running": 1, "vllm_waiting": 0, "vllm_requests_total": t // 4,
             "cpu_usage_usec": t * 1_500_000, "tree_cpu_s": t} for t in range(12)]
    assert latency.flagged(got["b"], calm, logged=1) is None
    busy = [dict(m, vllm_waiting=1) if m["t"] == 8 else m for m in calm]
    assert latency.flagged(got["b"], busy, logged=1) == "vLLM busy"
    assert latency.flagged(got["b"], calm, logged=0) == "other requests"
    hot = [dict(m, cpu_usage_usec=m["t"] * 3_000_000) for m in calm]
    assert latency.flagged(got["b"], hot, logged=1) == "CPU busy"


def test_flags_ignore_neighbour_requests_and_far_samples():
    # own request ends at 9; the questions before and after end theirs at 7.2 and 10.7
    done = lambda t: (t >= 7.2) + (t >= 9) + (t >= 10.7)
    mon = [{"t": t, "vllm_running": 1, "vllm_waiting": 0, "vllm_requests_total": done(t)} for t in range(13)]
    assert latency.flagged((7.5, 10.5), mon, logged=1) is None
    assert latency.flagged((7.5, 10.5), mon, logged=0) == "other requests"
    hot = [{"t": 0, "cpu_usage_usec": 0, "tree_cpu_s": 0}, {"t": 3600, "cpu_usage_usec": 10**10, "tree_cpu_s": 0}]
    assert latency.flagged((5.0, 8.0), hot, logged=0) is None  # the monitor stopped: no sample near the window
