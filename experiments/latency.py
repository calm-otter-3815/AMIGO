"""Latency runs: the question picker and the load monitor. Standard library only; no gold.

  .venv/bin/python experiments/latency.py pick LAKE QFILE OUT [N]   N rows of LAKE (default 32)
  .venv/bin/python experiments/latency.py watch PID OUT              one JSON line a second until PID ends

`pick` takes random.Random(2026).sample(sorted(ids), N) of the LAKE ids in QFILE and writes
those rows in that order. `watch` logs vLLM's queue and request counts, the cgroup's CPU and
memory, and the CPU time of PID's process tree; paper_results.py latency reads it.
"""

import json
import os
import random
import re
import sys
import time
import urllib.request
from pathlib import Path

VLLM = os.environ.get("QWEN_URL", "http://localhost:8000/v1").removesuffix("/v1") + "/metrics"
# the cgroup of the SLURM job the timed commands run in
CGROUP = Path(os.environ.get("LATENCY_CGROUP", "/sys/fs/cgroup/system.slice/node04_slurmstepd.scope/job_109716"))
TICK = os.sysconf("SC_CLK_TCK")


def pick(lake: str, qfile: str, out: str, n: str = "32") -> None:
    rows = {r["id"]: r for r in map(json.loads, filter(None, Path(qfile).read_text().split("\n"))) if r["lake"] == lake}
    chosen = random.Random(2026).sample(sorted(rows), int(n))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text("".join(json.dumps(rows[q]) + "\n" for q in chosen))
    print(f"{len(chosen)} {lake} questions into {out}")


def vllm() -> dict:
    try:
        with urllib.request.urlopen(VLLM, timeout=2) as reply:
            text = reply.read().decode()
    except OSError:
        return {}
    names = {"num_requests_running": "vllm_running", "num_requests_waiting": "vllm_waiting",
             "request_success_total": "vllm_requests_total", "prefix_cache_hits_total": "prefix_hits",
             "prefix_cache_queries_total": "prefix_queries"}
    out = dict.fromkeys(names.values(), 0.0)
    for name, value in re.findall(r"^vllm:(\w+)\{[^}]*\} (\S+)$", text, re.M):
        if name in names:
            out[names[name]] += float(value)
    return out


def cgroup() -> dict:
    out = {}
    try:
        out["cpu_usage_usec"] = int(re.search(r"usage_usec (\d+)", (CGROUP / "cpu.stat").read_text()).group(1))
        out["cpu_pressure_avg10"] = float(re.search(r"some avg10=(\S+)", (CGROUP / "cpu.pressure").read_text()).group(1))
        out["memory"] = int((CGROUP / "memory.current").read_text())
    except (OSError, AttributeError):
        pass
    return out


def tree_cpu(root: int) -> float:
    """utime + stime in seconds of root and every process below it."""
    stats = {}
    for proc in Path("/proc").iterdir():
        if proc.name.isdigit():
            try:
                fields = (proc / "stat").read_text().rpartition(")")[2].split()
            except OSError:
                continue
            stats[int(proc.name)] = (int(fields[1]), int(fields[11]) + int(fields[12]))
    keep = {root}
    grew = True
    while grew:
        grew = False
        for pid, (parent, _) in stats.items():
            if parent in keep and pid not in keep:
                keep.add(pid)
                grew = True
    total = sum(stats[p][1] for p in keep if p in stats)
    return total / TICK


def windows(order: list[str], seconds: dict[str, float], end: float) -> dict[str, tuple[float, float]]:
    """Each question's (start, end), for questions run one after another in `order` and
    saved together at `end`: walked back from the end by each question's seconds."""
    out = {}
    for qid in reversed(order):
        out[qid] = (end - seconds[qid], end)
        end -= seconds[qid]
    return out


def flagged(window: tuple[float, float], monitor: list[dict], logged: int) -> str | None:
    """Why a timed question ran under load (section 9.3 of the night plan), or None: vLLM
    held 2 requests or more, finished more requests than the method logged, or the rest of
    the cgroup used more than 1 CPU on average. Requests are counted between samples inside
    the window: the samples just outside it also hold the requests of the questions before
    and after. A sample more than 2 s outside the window (the monitor stopped) is not used."""
    start, end = window
    before = [m for m in monitor if start - 2 <= m["t"] <= start]
    after = [m for m in monitor if end <= m["t"] <= end + 2]
    inside = [m for m in monitor if start <= m["t"] <= end]
    if any(m.get("vllm_running", 0) + m.get("vllm_waiting", 0) >= 2 for m in inside):
        return "vLLM busy"
    if len(inside) >= 2 and inside[-1].get("vllm_requests_total", 0) - inside[0].get("vllm_requests_total", 0) > logged:
        return "other requests"
    if not before or not after:
        return None
    a, b = before[-1], after[0]
    if "cpu_usage_usec" in a and "cpu_usage_usec" in b and b["t"] > a["t"]:
        rest = (b["cpu_usage_usec"] - a["cpu_usage_usec"]) / 1e6 - (b["tree_cpu_s"] - a["tree_cpu_s"])
        if rest / (b["t"] - a["t"]) > 1:
            return "CPU busy"
    return None


def watch(pid: str, out: str) -> None:
    pid_ = int(pid)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "a") as f:
        while Path(f"/proc/{pid_}").exists():
            line = {"t": round(time.time(), 2), **vllm(), **cgroup(), "tree_cpu_s": tree_cpu(pid_)}
            f.write(json.dumps(line) + "\n")
            f.flush()
            time.sleep(1)


if __name__ == "__main__":
    {"pick": pick, "watch": watch}[sys.argv[1]](*sys.argv[2:])
