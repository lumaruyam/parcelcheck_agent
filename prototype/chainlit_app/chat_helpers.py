"""Small, testable pieces of the chat (no Chainlit import): what the user typed, and the claim history.

The history is a local JSONL file (one claim per line, newest last). It never goes to Git: data/runtime/
is ignored. It keeps what a merchant or a reviewer needs to find a claim again, not the photo.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
HISTORY_PATH = Path(os.getenv("CLAIMS_HISTORY_PATH", ROOT / "data" / "runtime" / "claims_history.jsonl"))

GREETINGS = {"hi", "hello", "hey", "bonjour", "salut", "hola", "good morning", "coucou"}
HISTORY_WORDS = {"history", "my claims", "claims", "historique", "mes réclamations", "mes reclamations"}
HELP_WORDS = {"help", "menu", "start", "aide", "restart"}
PERSON_WORDS = {"person", "human", "agent"}
SWITCH_WORDS = {"switch off", "switch on"}

RESULT_LABEL = {"refund_executed": "✅ Refund paid", "message_sent": "✉️ Decision sent",
                "queued_for_human": "🧑‍💼 With a person"}
LEVEL_LABEL = {"L4_auto": "L4", "L2_human_approves": "L2", "L1_human_decides": "L1"}


CATEGORY_HINTS = {
    "ceramics": ("mug", "cup", "plate", "bowl", "vase", "ceramic", "porcelain", "teapot", "tasse", "assiette"),
    "glassware": ("glass", "bottle", "jar", "verre", "wine glass"),
    "electronics": ("phone", "headphone", "earbud", "laptop", "tablet", "speaker", "charger", "camera", "screen"),
    "cosmetics": ("perfume", "cream", "lipstick", "makeup", "parfum", "palette"),
    "clothing": ("shirt", "dress", "jacket", "jeans", "sweater", "t-shirt", "pull"),
    "books": ("book", "novel", "livre", "comic"),
    "toys": ("toy", "lego", "doll", "puzzle", "jouet"),
    "shoes": ("shoe", "sneaker", "boot", "chaussure"),
}


def guess_category(text: str) -> str | None:
    """The item category the merchant's sentence points to (first match), or None: only a suggestion."""
    low = text.lower()
    for category, words in CATEGORY_HINTS.items():
        if any(word in low for word in words):
            return category
    return None


def intent_of(text: str) -> str:
    """What the merchant typed: a command we know, or free text to read as a claim."""
    low = " ".join(text.lower().strip().strip("!?.").split())
    if not low:
        return "empty"
    if low in SWITCH_WORDS:
        return "switch"
    if low in PERSON_WORDS:
        return "person"
    if low in HISTORY_WORDS:
        return "history"
    if low in HELP_WORDS:
        return "help"
    if low in GREETINGS:
        return "greeting"
    if text.strip().startswith("{"):
        return "json"
    if low.upper().startswith("DEMO-") and len(low) <= 8:
        return "demo"
    return "free_text"


def history_entry(claim: dict[str, Any], result: dict[str, Any], trace_url: str | None = None,
                  now: datetime | None = None) -> dict[str, Any]:
    """One line of history, from a claim and the agent's result (works for hand-overs too)."""
    decision = result.get("decision") or {}
    return {
        "at": (now or datetime.now()).isoformat(timespec="seconds"),
        "case_id": claim.get("case_id") or "message",
        "item": claim.get("item_category") or "—",
        "value_eur": claim.get("item_value_eur"),
        "action": result.get("action"),
        "trust_level": result.get("trust_level"),
        "decision": decision.get("decision"),
        "clause": decision.get("clause"),
        "amount_eur": decision.get("amount_eur"),
        "guardrail": result.get("guardrail"),
        "trace_url": trace_url,
    }


def save_history(entry: dict[str, Any], path: Path | None = None) -> None:
    path = path or HISTORY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_history(path: Path | None = None, limit: int = 10) -> list[dict[str, Any]]:
    """The last `limit` entries, newest first. A broken line is skipped, never a crash."""
    path = path or HISTORY_PATH
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return list(reversed(rows[-limit:]))


def history_markdown(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "📜 **No claims yet.** File one with **📦 File a claim** or try an example."
    lines = ["📜 **Your last claims** (newest first)", "",
             "| When | Claim | Item · value | Result | Amount | Level | Trace |",
             "|---|---|---|---|---|---|---|"]
    for r in rows:
        when = str(r.get("at", ""))[5:16].replace("T", " ")
        value = f"€{r['value_eur']:.2f}" if isinstance(r.get("value_eur"), (int, float)) else "—"
        result = RESULT_LABEL.get(str(r.get("action")), str(r.get("action")))
        if r.get("guardrail"):
            result += f" ({r['guardrail']})"
        amount = f"€{float(r['amount_eur']):.2f}" if r.get("amount_eur") is not None else "—"
        level = LEVEL_LABEL.get(str(r.get("trust_level")), str(r.get("trust_level") or "—"))
        trace = f"[open]({r['trace_url']})" if r.get("trace_url") else "—"
        lines.append(f"| {when} | {r.get('case_id')} | {r.get('item')} · {value} | {result} | {amount} | {level} | {trace} |")
    return "\n".join(lines)
