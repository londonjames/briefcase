"""
usage_logger — Python port of the canonical TS usage-logger.

Records one row per Claude call to the central `claude-usage` Turso DB, tagged
with (app, feature), so spend can be attributed to the exact thing that caused
it. Cost is computed locally from the price table below — this module never
calls a paid API, and if USAGE_DB_URL is unset it silently no-ops.

Writes happen on a daemon thread so a slow logging call never delays a request.

Env:
    USAGE_DB_URL    libsql://claude-usage-<org>.turso.io
    USAGE_DB_TOKEN  Turso auth token
"""

import os
import threading
import time

import requests

# $ per 1M tokens. cacheRead = in*0.1, 5m cacheWrite = in*1.25
PRICES = {
    "claude-fable-5": (10, 50),
    "claude-opus-5": (5, 25),
    "claude-sonnet-5": (3, 15),
    "claude-opus-4-8": (5, 25),
    "claude-opus-4-7": (5, 25),
    "claude-opus-4-6": (5, 25),
    "claude-sonnet-4": (3, 15),
    "claude-haiku-4-5": (1, 5),
}

INSERT = """INSERT INTO usage_events
  (ts, app, feature, model, input_tokens, output_tokens,
   cache_read_tokens, cache_write_tokens, cost_usd, latency_ms,
   request_id, source)
  VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"""


def _price_for(model):
    best, best_len = (3, 15), -1
    for prefix, p in PRICES.items():
        if model.startswith(prefix) and len(prefix) > best_len:
            best, best_len = p, len(prefix)
    return best


def _cost_usd(model, usage):
    p_in, p_out = _price_for(model)
    return (
        (usage.get("input_tokens", 0) or 0) * p_in
        + (usage.get("output_tokens", 0) or 0) * p_out
        + (usage.get("cache_read_input_tokens", 0) or 0) * p_in * 0.1
        + (usage.get("cache_creation_input_tokens", 0) or 0) * p_in * 1.25
    ) / 1_000_000


def _arg(v):
    if v is None:
        return {"type": "null", "value": None}
    if isinstance(v, bool):
        return {"type": "integer", "value": str(int(v))}
    if isinstance(v, int):
        return {"type": "integer", "value": str(v)}
    if isinstance(v, float):
        return {"type": "float", "value": v}
    return {"type": "text", "value": str(v)}


def _write(args):
    url = os.environ.get("USAGE_DB_URL")
    if not url:
        return
    endpoint = url.replace("libsql://", "https://").rstrip("/") + "/v2/pipeline"
    try:
        requests.post(
            endpoint,
            headers={"Authorization": "Bearer " + os.environ.get("USAGE_DB_TOKEN", "")},
            json={
                "requests": [
                    {"type": "execute", "stmt": {"sql": INSERT, "args": [_arg(a) for a in args]}},
                    {"type": "close"},
                ]
            },
            timeout=10,
        )
    except Exception:
        # A logging system must never break the app. Swallow.
        pass


def record(app, feature, message, latency_ms, source=None):
    """Log one Claude call. `message` is an SDK Message (or a stream's final one)."""
    if not os.environ.get("USAGE_DB_URL"):
        return
    try:
        u = getattr(message, "usage", None)
        usage = {
            "input_tokens": getattr(u, "input_tokens", 0) or 0,
            "output_tokens": getattr(u, "output_tokens", 0) or 0,
            "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", 0) or 0,
            "cache_creation_input_tokens": getattr(u, "cache_creation_input_tokens", 0) or 0,
        }
        model = getattr(message, "model", "unknown") or "unknown"
        args = [
            int(time.time() * 1000),
            app,
            feature,
            model,
            usage["input_tokens"],
            usage["output_tokens"],
            usage["cache_read_input_tokens"],
            usage["cache_creation_input_tokens"],
            float(_cost_usd(model, usage)),
            int(latency_ms),
            getattr(message, "id", None),
            source,
        ]
        threading.Thread(target=_write, args=(args,), daemon=True).start()
    except Exception:
        pass


def tracked(app, feature, source=None):
    """Context manager timing a call; hand it the message with .log(message).

    with tracked("briefcase", "team-extract") as t:
        msg = client.messages.create(...)
        t.log(msg)
    """
    return _Tracked(app, feature, source)


class _Tracked:
    def __init__(self, app, feature, source):
        self.app, self.feature, self.source = app, feature, source

    def __enter__(self):
        self.start = time.time()
        return self

    def log(self, message):
        record(self.app, self.feature, message, (time.time() - self.start) * 1000, self.source)

    def __exit__(self, *exc):
        return False
