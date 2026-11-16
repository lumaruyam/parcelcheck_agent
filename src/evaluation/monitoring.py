"""Four monitoring layers from the Langfuse traces (Sessions 6 + 7, `06_07_experiments_operations.md` §3).

One row per claim = one `refund-claim` trace with its scores. `layer_table()` turns a week of traces into the
rows that page someone; `by_segment()` reports a metric per pre-registered segment (never the average alone).
Business metrics (leakage, cost per case) come from the weekly human sample, not from the traces.
"""
from __future__ import annotations

import base64
import json
import os
import random
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd

SCORES = ["guardrail_pass", "auto_resolved", "input_guardrail_blocked", "reviewer_agrees"]
SEGMENTS = ["seg_language", "seg_amount_band", "seg_cover", "seg_fragile"]


def _get(host: str, path: str, params: dict[str, Any], pk: str, sk: str) -> dict[str, Any]:
    url = f"{host.rstrip('/')}{path}?{urllib.parse.urlencode(params)}"
    token = base64.b64encode(f"{pk}:{sk}".encode()).decode()
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310 (Langfuse public API, https)
        return dict(json.loads(r.read().decode()))


def _paged(host: str, path: str, params: dict[str, Any], pk: str, sk: str, max_pages: int = 20) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        body = _get(host, path, {**params, "page": page, "limit": 100}, pk, sk)
        out += body.get("data", [])
        if page >= int(body.get("meta", {}).get("totalPages", 1)):
            break
    return out


def fetch(days: int = 7) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Traces named refund-claim and their scores, for the last `days` days (keys from .env)."""
    host = os.getenv("LANGFUSE_HOST") or os.getenv("LANGFUSE_BASE_URL") or "https://cloud.langfuse.com"
    pk, sk = os.environ["LANGFUSE_PUBLIC_KEY"], os.environ["LANGFUSE_SECRET_KEY"]
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    traces = _paged(host, "/api/public/traces", {"name": "refund-claim", "fromTimestamp": since}, pk, sk)
    try:
        scores = _paged(host, "/api/public/v2/scores", {"fromTimestamp": since}, pk, sk)
    except Exception:  # noqa: BLE001  (older deployments only have the v1 endpoint)
        scores = _paged(host, "/api/public/scores", {"fromTimestamp": since}, pk, sk)
    return traces, scores


def to_frame(traces: list[dict[str, Any]], scores: list[dict[str, Any]]) -> pd.DataFrame:
    by_trace: dict[str, dict[str, float]] = {}
    for s in scores:
        if s.get("name") in SCORES and s.get("traceId"):
            by_trace.setdefault(s["traceId"], {})[s["name"]] = float(s.get("value") or 0)
    rows = []
    for t in traces:
        meta, out = t.get("metadata") or {}, t.get("output") or {}
        reasons = out.get("reasons") if isinstance(out, dict) else None
        rows.append({
            "trace_id": t.get("id"), "timestamp": pd.to_datetime(t.get("timestamp")),
            "latency_s": float(t.get("latency") or 0), "route": out.get("route") if isinstance(out, dict) else None,
            "trust_level": out.get("trust_level") if isinstance(out, dict) else None,
            "unavailable": any("unavailable" in str(r) for r in (reasons or [])),
            "autonomy_enabled": meta.get("autonomy_enabled"),
            **{k: meta.get(k) for k in SEGMENTS}, **{k: by_trace.get(t.get("id", ""), {}).get(k) for k in SCORES},
        })
    return pd.DataFrame(rows)


def demo_frame(n: int = 200, seed: int = 7) -> pd.DataFrame:
    """Synthetic week, clearly labelled DEMO: to show the notebook without Langfuse access. Never a result."""
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        lang = rng.choices(["fr", "en"], [0.55, 0.45])[0]
        band = rng.choices(["<=20", "20-100", ">100"], [0.45, 0.4, 0.15])[0]
        blocked = rng.random() < 0.04
        auto = (not blocked) and band == "<=20" and rng.random() < 0.7
        rows.append({"trace_id": f"DEMO-{i:03d}", "timestamp": pd.Timestamp("2026-11-16") + pd.Timedelta(hours=rng.uniform(0, 160)),
                     "latency_s": rng.lognormvariate(1.3, 0.45), "route": "auto" if auto else "human",
                     "trust_level": "L4_auto" if auto else rng.choice(["L2_human_approves", "L1_human_decides"]),
                     "unavailable": rng.random() < 0.01, "autonomy_enabled": True, "seg_language": lang,
                     "seg_amount_band": band, "seg_cover": rng.choices(["standard", "premium"], [0.8, 0.2])[0],
                     "seg_fragile": rng.random() < 0.4, "guardrail_pass": float(auto or rng.random() < 0.3),
                     "auto_resolved": float(auto), "input_guardrail_blocked": float(blocked),
                     "reviewer_agrees": (float(rng.random() < (0.9 if lang == "en" else 0.8)) if rng.random() < 0.3 else None)})
    return pd.DataFrame(rows)


def layer_table(df: pd.DataFrame) -> pd.DataFrame:
    """The rows of 06_07 §3.1 that can be computed from traces, with their paging threshold and status."""
    n = len(df)
    p95 = float(df["latency_s"].quantile(0.95)) if n else float("nan")
    unavailable = float(df["unavailable"].mean()) if n else 0.0
    rev = df["reviewer_agrees"].dropna()
    fr = df[df["seg_language"] == "fr"]
    en = df[df["seg_language"] == "en"]
    gap = (float(fr["auto_resolved"].mean()) / float(en["auto_resolved"].mean())
           if len(fr) and len(en) and float(en["auto_resolved"].mean()) > 0 else float("nan"))
    rows = [
        ("Product & guardrails", "claims this week", n, "—", None),
        ("Product & guardrails", "L4 share (auto_resolved)", df["auto_resolved"].mean(), "watch vs 40 % criterion", None),
        ("Product & guardrails", "input guardrail blocked", df["input_guardrail_blocked"].mean(), "watch by category", None),
        ("Product & guardrails", "FR / EN ratio of L4 share", gap, "page if < 0.67 (FR gap > 1.5×)", (gap < 1 / 1.5) if gap == gap else None),
        ("Product & guardrails", "wrong automatic refunds", "from the weekly sample", "page if > 0", None),
        ("Model quality", "reviewer agreement (👍)", rev.mean() if len(rev) else float("nan"), "page if falling 2 weeks", None),
        ("Model quality", "reviewer-graded claims", len(rev), "—", None),
        ("Infrastructure", "p95 latency (s)", p95, "page if > 15 s", (p95 > 15) if p95 == p95 else None),
        ("Infrastructure", "'unavailable' hand-overs", unavailable, "page if > 5 % in an hour", unavailable > 0.05),
        ("Business", "leakage € / 1,000 · cost per case", "from the weekly sample", "page if > €630 / 1,000", None),
    ]
    out = pd.DataFrame(rows, columns=["layer", "metric", "value", "threshold", "pages_someone"])
    out["status"] = out["pages_someone"].map({True: "🔴 page", False: "✅", None: "—"})
    return out.drop(columns="pages_someone")


def by_segment(df: pd.DataFrame, metric: str = "auto_resolved") -> pd.DataFrame:
    """One metric per pre-registered segment: the Simpson and fairness check (never the average alone)."""
    parts = []
    for seg in SEGMENTS:
        g = df.groupby(seg)[metric].agg(["mean", "count"]).reset_index().rename(columns={seg: "value"})
        g.insert(0, "segment", seg.removeprefix("seg_"))
        parts.append(g)
    return pd.concat(parts, ignore_index=True)
