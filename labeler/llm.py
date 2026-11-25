"""The local judge: Qwen3.8-27B served by vLLM on this machine, behind its OpenAI-style API.

Start the server in tmux (vLLM lives in its own env, ~/vllm-env, so AMIGO's torch is
untouched; CUDA_HOME points at the CUDA that pip installed there, and the flashinfer
sampler is off because it compiles code at start):
  CU=~/vllm-env/lib/python3.12/site-packages/nvidia/cu13
  tmux new -d -s qwen "export CUDA_HOME=$CU PATH=$HOME/vllm-env/bin:$CU/bin:\\$PATH \\
      HF_HUB_OFFLINE=1 VLLM_USE_FLASHINFER_SAMPLER=0; ~/vllm-env/bin/vllm serve Qwen/Qwen3.8-27B-FP8 \\
      --revision 017b9c7af6b5689d5dd426a76e0bc077eb5ca20a --served-model-name qwen3.8-27b-fp8 qwen \\
      --max-model-len 32768 --gpu-memory-utilization 0.92 --language-model-only \\
      --reasoning-parser qwen3 --speculative-config '{\\"method\\":\\"mtp\\",\\"num_speculative_tokens\\":3}' \\
      --structured-outputs-config '{\\"backend\\":\\"xgrammar\\",\\"disable_any_whitespace\\":true}' \\
      --max-num-seqs 128 2>&1 | tee ~/logs/qwen.log"
Compact JSON (no free whitespace): with it allowed, a reply could fill its whole length with
blank lines inside the JSON (seen 2026-10-14 on a CORE-T table purpose).

The FP8 checkpoint (Qwen's own, 8-bit weights) halves the weight memory, so about twice
as many long thinking calls fit at once. Thinking is on at reasoning effort xhigh, with the sampling the model card gives for
thinking mode. A vote is one seeded sample, so best of three is three seeds. Replies are
cached by (prompt, seed, schema, settings) in runs/labeler/cache-<run>.jsonl with the thinking
text, so a rerun makes no new call and every label can be traced to its reasoning.
"""

import hashlib
import itertools
import json
import os
import threading
import urllib.request

from openai import BadRequestError, OpenAI

from labeler import OUT, RUN

# another port when 8000 is taken; several comma-separated when several servers share the calls
URLS = os.environ.get("LABEL_URL", "http://localhost:8000/v1").split(",")
MODEL = "qwen"
# one cache file per run (cache-bird_dev.jsonl, ...), so its name says what it holds; also one
# per machine: two nodes appending to one file on shared storage can mix lines
CACHE = OUT / os.environ.get("LABEL_CACHE", f"cache-{RUN.name}.jsonl")
CHECKPOINT = "Qwen/Qwen3.8-27B-FP8@017b9c7af6b5689d5dd426a76e0bc077eb5ca20a"  # part of the cache key
SETTINGS = {
    "temperature": 1.0, "top_p": 0.95, "max_tokens": 28_000, "reasoning_effort": "xhigh",
    "extra_body": {"top_k": 20, "min_p": 0.0, "chat_template_kwargs": {"enable_thinking": True}},
}

_clients = itertools.cycle([OpenAI(base_url=url, api_key="local", timeout=3600, max_retries=2) for url in URLS])
_lock = threading.Lock()
_cache: dict[str, dict] | None = None
used = {"open": 0, "calls": 0, "cached": 0, "tokens": 0, "cut": 0}  # live totals for the progress bars


def _load() -> dict[str, dict]:
    global _cache
    if _cache is None:
        _cache = {}
        if CACHE.exists():
            for line in CACHE.read_text().splitlines():
                try:
                    one = json.loads(line)
                except json.JSONDecodeError:  # a line cut short when a run was killed mid-write
                    continue
                _cache[one["key"]] = one
    return _cache


def _key(prompt: str, seed: int, schema: dict | None, limit: int | None) -> str:
    return hashlib.sha256(json.dumps([CHECKPOINT, prompt, seed, schema, SETTINGS] + ([limit] if limit else [])).encode()).hexdigest()


def ask(prompt: str, seed: int = 0, schema: dict | None = None, tag: str = "", limit: int | None = None,
        finished_under: int | None = None) -> str | None:
    """The model's final answer to `prompt`; None when thinking ran out of room. `tag`
    (step and question) is stored with the reply for reading, not part of the key.
    `limit` caps the tokens of one call below SETTINGS' max_tokens. `finished_under`: a
    reply cached for the same call under that smaller limit is reused when it finished,
    since the cap never cut it (same prompt and seed, same reply)."""
    key = _key(prompt, seed, schema, limit)
    with _lock:
        if key in _load():
            used["cached"] += 1
            return _cache[key]["reply"]
        smaller = _cache.get(_key(prompt, seed, schema, finished_under)) if finished_under else None
        if smaller and smaller["reply"] is not None:
            used["cached"] += 1
            return smaller["reply"]
    extra = dict(SETTINGS["extra_body"])
    if schema:
        extra["response_format"] = {"type": "json_schema", "json_schema": {"name": "answer", "schema": schema}}
    with _lock:
        used["open"] += 1
    try:
        out = next(_clients).chat.completions.create(
            model=MODEL, seed=seed, messages=[{"role": "user", "content": prompt}],
            **{k: v for k, v in SETTINGS.items() if k != "extra_body"} | ({"max_tokens": limit} if limit else {}),
            extra_body=extra,
        )
    except BadRequestError as e:  # a long prompt leaves less than max_tokens: retry with what fits
        room = 0 if limit else _room(prompt)
        if room <= 0:
            raise ValueError(f"prompt does not fit: {e}") from e
        return ask(prompt, seed, schema, tag, room)
    finally:
        with _lock:
            used["open"] -= 1
    choice = out.choices[0]
    reply = (choice.message.content or "").strip() if choice.finish_reason == "stop" else None
    one = {"key": key, "tag": tag, "seed": seed, "tokens": out.usage.completion_tokens, "reply": reply,
           "thinking": getattr(choice.message, "reasoning", None) or "", "prompt": prompt}
    with _lock:
        used["calls"] += 1
        used["tokens"] += one["tokens"]
        used["cut"] += reply is None
        _cache[key] = one
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        with CACHE.open("a") as f:
            f.write(json.dumps(one) + "\n")
    return reply


def _room(prompt: str) -> int:
    """Output tokens left in the server's context after `prompt` (the error message only
    gives a lower bound on the prompt's size, so ask the server for the exact count)."""
    body = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": prompt}]}).encode()
    request = urllib.request.Request(URLS[0].removesuffix("/v1") + "/tokenize", body, {"Content-Type": "application/json"})
    reply = json.load(urllib.request.urlopen(request, timeout=60))
    return reply["max_model_len"] - reply["count"] - 16


def ask_json(prompt: str, seed: int = 0, schema: dict | None = None, tag: str = "", limit: int | None = None,
             finished_under: int | None = None):
    """The reply parsed as JSON, code fences stripped; ValueError when there is none."""
    reply = ask(prompt, seed, schema, tag, limit, finished_under)
    if reply is None:
        raise ValueError("thinking ran out of room")
    text = reply.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)
