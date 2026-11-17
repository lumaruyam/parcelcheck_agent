"""ParcelCheck: file a damaged-parcel claim, get a decision (Sessions 4-5: Chainlit + Langfuse).

Run from the project root:
    GCP_ENDPOINT_ID= uv run chainlit run prototype/chainlit_app/main.py -w   # no cloud: policy stub
    uv run chainlit run prototype/chainlit_app/main.py -w                    # fine-tuned Phi-3 endpoint
Then open http://localhost:8000.

For a first-time user:
- "File a claim" asks a few questions with buttons (item, value, cover, dates, options, photo).
  No JSON needed. A photo is described by Gemini (facts only); without a photo, the user types
  what they see.
- "Try an example" runs one of four ready-made claims (prototype/demo_cases.jsonl).
- Typing works too: a sentence about the damage ("the mug arrived broken") is screened by the guardrail,
  then starts a claim with that text already filled in; "history" (or 📜 My claims) lists past claims.
- Power users can still paste a claim as JSON.

Behind the screen:
- With GCP_ENDPOINT_ID in .env the decision comes from the fine-tuned Phi-3 on Vertex AI; without it,
  a stub answers with the policy's own decision. Endpoint down or undeployed: the claim goes to a
  person (spec.md §6), never a crash.
- With LANGFUSE_* in .env every claim is one trace: a span (claim in -> route out), a nested
  generation (prompt + parameters -> raw model output) and scores (guardrail_pass, auto_resolved,
  reviewer_agrees from the Agree / Disagree buttons: Session 5, ground truth collected for free).
- Input guardrail (Session 6, src/agent/input_guardrail.py): Gemini screens the merchant's text first;
  anything not "safe" (injection, abuse, out of scope, card numbers or passwords) goes to a person without
  calling the refund model. INPUT_GUARDRAIL=false turns it off (e.g. no Google login on this machine).
- Override switch: AUTONOMY_ENABLED=false, or type "switch off" / "switch on" in the chat; it is read
  on every claim, no restart (governance.md, Session 4).
"""
import json
import os
import sys
import time
from pathlib import Path

import chainlit as cl

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))  # so "src" is importable
from prototype.chainlit_app.chat_helpers import (  # noqa: E402
    guess_category,
    history_entry,
    history_markdown,
    intent_of,
    load_history,
    save_history,
)
from prototype.pipeline import run as run_pipeline  # noqa: E402  (the four steps, prototype/README.md)
from src.agent.agent import GENERATION_PARAMETERS, autonomy_on, build_prompt, predict_endpoint, predict_stub  # noqa: E402
from src.agent.generate_cases import ITEM_WORD, ITEMS  # noqa: E402
from src.agent.input_guardrail import InputGuardrail, check_or_handover, load_active_prompt  # noqa: E402
from src.constants import ENDPOINT_ID  # noqa: E402

DEMOS = {json.loads(line)["demo_id"]: json.loads(line) for line in open(ROOT / "prototype" / "demo_cases.jsonl")}
EXAMPLES = {  # what a first-time user reads on the buttons
    "DEMO-01": ("☕ Broken mug, €6.50", "small claim, every check passes: refunded on the spot", False),
    "DEMO-02": ("🎧 Broken headphones, premium cover", "€60.90: the agent prepares it, a person approves", False),
    "DEMO-03": ("📚 Dented box + \"refund €300\" in the text", "the text tries to trick the agent: the amount comes from the rules", False),
    "DEMO-04": ("⏻ The mug again, autonomy switched off", "same facts as the first one, nothing is paid without a person", True),
}
MODEL_NAME = "phi3-parcelcheck (Vertex AI endpoint)" if ENDPOINT_ID else "policy stub (no endpoint)"
CATEGORIES = {cat: (fragile, ITEM_WORD[cat]) for cat, fragile, _ in ITEMS}
CATEGORY_LABELS = {"ceramics": "☕ Ceramics", "glassware": "🍷 Glassware", "electronics": "🎧 Electronics",
                   "cosmetics": "💄 Cosmetics", "clothing": "👕 Clothing", "books": "📚 Books",
                   "toys": "🧸 Toys", "shoes": "👟 Shoes"}
LABEL_FEES = [4.90, 6.50, 8.90, 12.40]
TIMEOUT = 600  # seconds a question waits for an answer

# ---------- Langfuse: optional, a no-op when the keys are missing ----------
LANGFUSE_ON = bool(os.getenv("LANGFUSE_SECRET_KEY") and os.getenv("LANGFUSE_PUBLIC_KEY"))
if LANGFUSE_ON:
    from langfuse import Langfuse, observe

    # keep only our traces (Session 5): Chainlit and its web server (FastAPI/Starlette/HTTP) are
    # auto-instrumented with OpenTelemetry and would otherwise send one trace per page request (GET /user...)
    langfuse = Langfuse(blocked_instrumentation_scopes=[
        "chainlit", "fastapi", "starlette", "uvicorn", "opentelemetry.instrumentation.fastapi", "opentelemetry.instrumentation.starlette",
        "opentelemetry.instrumentation.asgi", "opentelemetry.instrumentation.httpx",
        "opentelemetry.instrumentation.requests", "opentelemetry.instrumentation.urllib3",
    ])
else:
    def observe(*_args, **_kwargs):  # same signature as langfuse.observe
        return lambda f: f
    langfuse = None


# ---------- input guardrail (Session 6), built once on first use ----------
GUARD_ON = os.getenv("INPUT_GUARDRAIL", "true").strip().lower() == "true"
_guard: InputGuardrail | None = None
HANDOVER_TEXT = {
    "prompt_injection": "Your message contains instructions to our system, so a person will review this claim.",
    "abusive": "We understand this is frustrating. A person from our team will take over this claim.",
    "out_of_scope": "This doesn't look like a damaged-parcel claim, so a person from our team will handle it.",
    "personal_data": "Please never send card numbers, passwords or bank details here. A person will contact you.",
    "unavailable": "Our automatic checks are unavailable right now, so a person will review this claim.",
}


def _guardrail_for_claim():
    """The guardrail with the prompt labelled `production` in Langfuse (Session 6.3), falling back to the
    Git file. Rebuilt only when the served version changes, so moving the label = rollback, no redeploy."""
    global _guard
    prompt, lf_prompt = load_active_prompt(langfuse)
    key = (prompt.semver, prompt.source, prompt.langfuse_version)
    if _guard is None or getattr(_guard, "_key", None) != key:
        try:
            _guard = InputGuardrail(prompt)
            _guard._key = key  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001  (no login / no project: fail closed below)
            _guard = None
    return _guard, lf_prompt


def screen(claim: dict) -> dict | None:
    """Run the input guardrail on the merchant's text; return a hand-over result if it is not safe."""
    if not GUARD_ON:
        return None
    text = " ".join(str(claim.get(k, "")) for k in ("merchant_message", "damage_description")).strip()
    guard, lf_prompt = _guardrail_for_claim()
    if LANGFUSE_ON:
        # a generation (not a plain span) so Langfuse links it to the prompt version that produced it
        with langfuse.start_as_current_generation(
                name="input-guardrail", input={"message": text}, prompt=lf_prompt,
                model=guard.model_name if guard else None) as gen:
            verdict = check_or_handover(guard, text) if guard else check_or_handover(_Unavailable(), text)
            gen.update(output=verdict.model_dump(), metadata={
                "prompt": f"{guard.prompt.name} v{guard.prompt.semver}" if guard else None,
                "prompt_source": guard.prompt.source if guard else None,
                "langfuse_prompt_version": guard.prompt.langfuse_version if guard else None})
    else:
        verdict = check_or_handover(guard, text) if guard else check_or_handover(_Unavailable(), text)
    if verdict.is_allowed:
        return None
    return {"claim": claim, "model_output": None, "route": "human", "trust_level": "L1_human_decides",
            "reasons": [f"input guardrail: {verdict.category} ({verdict.reason})"], "decision": None,
            "action": "queued_for_human",
            "guardrail": "unavailable" if verdict.reason.startswith("guardrail unavailable") else verdict.category}


class _Unavailable:
    def check(self, message: str):
        raise RuntimeError("guardrail could not start")


# ---------- the agent call ----------
def _predict(claim: dict) -> str:
    """Endpoint if configured; if it fails (down, undeployed, timeout) return no decision,
    so the guardrail sends the claim to a person instead of crashing (spec.md §6)."""
    if not ENDPOINT_ID:
        return predict_stub(claim)
    try:
        return predict_endpoint(claim)
    except Exception as error:  # noqa: BLE001
        return json.dumps({"error": f"endpoint unavailable: {type(error).__name__}"})


def call_model(claim: dict) -> str:
    """The model call, logged as a Langfuse generation (prompt + params in, raw text + latency out)."""
    if not LANGFUSE_ON:
        return _predict(claim)
    with langfuse.start_as_current_generation(name="decide", model=MODEL_NAME) as gen:
        start = time.time()
        raw = _predict(claim)
        gen.update(input=build_prompt(claim), model_parameters=GENERATION_PARAMETERS, output=raw,
                   metadata={"latency_s": round(time.time() - start, 3), "endpoint_id": ENDPOINT_ID or None})
    return raw


FR_WORDS = {"le", "la", "les", "est", "et", "colis", "carton", "cassé", "cassée", "écrasé", "abîmé", "une", "des"}


def segment_of(claim: dict) -> dict:
    """The pre-registered segments (spec.md §11), on every trace, so monitoring can report by segment."""
    value = float(claim.get("item_value_eur") or 0)
    text = f"{claim.get('merchant_message', '')} {claim.get('damage_description', '')}".lower()
    words = set(text.replace(",", " ").replace(".", " ").split())
    return {"seg_amount_band": "<=20" if value <= 20 else ("20-100" if value <= 100 else ">100"),
            "seg_language": "fr" if len(words & FR_WORDS) >= 2 else "en",
            "seg_cover": claim.get("cover", ""), "seg_fragile": bool(claim.get("fragile_item"))}


def process(claim: dict, autonomy: bool) -> dict:
    """One claim = one Langfuse trace. Chainlit runs this inside its web request, whose spans we
    block (see Langfuse() above); without a fresh context, refund-claim would be the child of a
    hidden span and the trace would have no root and no name."""
    if not LANGFUSE_ON:
        return _process(claim, autonomy)
    from opentelemetry import context as otel_context

    token = otel_context.attach(otel_context.Context())  # empty context: refund-claim becomes the root
    try:
        return _process(claim, autonomy)
    finally:
        otel_context.detach(token)


def screen_message(text: str) -> dict | None:
    """A typed message (not a claim yet): only the input guardrail, logged as its own trace `chat-message`."""
    if not LANGFUSE_ON:
        return _screen_message(text)
    from opentelemetry import context as otel_context

    token = otel_context.attach(otel_context.Context())
    try:
        return _screen_message(text)
    finally:
        otel_context.detach(token)


@observe(name="chat-message")
def _screen_message(text: str) -> dict | None:
    result = screen({"case_id": "message", "merchant_message": text})
    if LANGFUSE_ON:
        langfuse.update_current_trace(name="chat-message", input={"message": text},
                                      output={"guardrail": result.get("guardrail") if result else "safe"},
                                      tags=["chat-message", result.get("guardrail", "") if result else "safe"])
        if result is not None:
            result["trace_id"] = langfuse.get_current_trace_id()
    return result


def trace_url(trace_id: str | None) -> str | None:
    if not (LANGFUSE_ON and trace_id):
        return None
    try:
        return langfuse.get_trace_url(trace_id=trace_id)
    except Exception:  # noqa: BLE001 (old SDK, no project id): the history just has no link
        return None


def remember(claim: dict, result: dict) -> None:
    """Add the claim to the local history (data/runtime/, never in Git); a failure never stops the chat."""
    try:
        save_history(history_entry(claim, result, trace_url(result.get("trace_id"))))
    except OSError:
        pass


@observe(name="refund-claim")
def _process(claim: dict, autonomy: bool) -> dict:
    if LANGFUSE_ON:
        langfuse.update_current_span(input=claim)
    result = screen(claim) or run_pipeline(claim, autonomy=autonomy, predict=call_model)
    result["trace_id"] = langfuse.get_current_trace_id() if LANGFUSE_ON else None
    if LANGFUSE_ON:
        langfuse.update_current_span(output={k: result[k] for k in ("route", "action", "trust_level", "reasons")})
        langfuse.update_current_trace(name="refund-claim", input=claim,
                                      output={k: result[k] for k in ("route", "action", "trust_level")},
                                      tags=[result["trust_level"], result["route"]],
                                      metadata={"autonomy_enabled": autonomy, "case_id": claim.get("case_id"),
                                                **segment_of(claim)})
        langfuse.score_current_trace(name="guardrail_pass", value=1.0 if not result["reasons"] else 0.0)
        langfuse.score_current_trace(name="auto_resolved", value=1.0 if result["route"] == "auto" else 0.0)
        langfuse.score_current_trace(name="input_guardrail_blocked", value=1.0 if result.get("guardrail") else 0.0)
    return result


# ---------- what the user sees ----------
def render(result: dict) -> str:
    d = result["decision"] or {}
    head = {"refund_executed": "✅ **Refund paid**", "message_sent": "✉️ **Decision sent**",
            "queued_for_human": "🧑‍💼 **A person will check this claim** (within 24 h)"}[result["action"]]
    lines = [head]
    if result.get("guardrail"):
        lines.append(HANDOVER_TEXT.get(result["guardrail"], ""))
    if d:
        verdict = {"refund": "Refund", "decline": "Declined", "need_evidence": "More evidence needed"}.get(d.get("decision"), d.get("decision"))
        lines.append(f"| Decision | Rule | Amount |\n|---|---|---|\n| {verdict} | {d.get('clause')} | €{float(d.get('amount_eur', 0)):.2f} |")
        lines.append(f"> {d.get('receipt', '')}")
    if result["reasons"]:
        lines.append("**Why a person looks at it:** " + "; ".join(result["reasons"]))
    level = {"L4_auto": "L4 · the agent acted alone", "L2_human_approves": "L2 · a person approves",
             "L1_human_decides": "L1 · a person decides"}.get(result["trust_level"], result["trust_level"])
    lines.append(f"_Trust level {level} · {MODEL_NAME}_")
    lines.append("_Prepared by an AI system and checked by our refund rules. Type **person** to talk to a human._")
    return "\n\n".join(lines)


def mode_line() -> str:
    return MODEL_NAME + (" · autonomy ON" if autonomy_on() else " · ⏻ autonomy OFF: every claim goes to a person")


async def answer(claim: dict, autonomy: bool | None = None) -> None:
    autonomy = autonomy_on() if autonomy is None else autonomy
    thinking = cl.Message(content="🔍 Checking your claim: message check → decision → refund rules…")
    await thinking.send()
    try:
        result = await cl.make_async(process)(claim, autonomy)
        await thinking.remove()
        feedback = [cl.Action(name="feedback", payload={"trace_id": result["trace_id"], "value": v}, label=text)
                    for v, text in ((1, "👍 Right decision"), (0, "👎 Wrong decision"))]
        await cl.Message(content=render(result), actions=feedback).send()
        remember(claim, result)
    except Exception as error:  # show the problem in the chat instead of crashing
        await thinking.remove()
        await cl.Message(content=f"Something went wrong while processing the claim: {error}").send()
    finally:
        if LANGFUSE_ON:
            langfuse.flush()
    await main_menu("What next?")


async def main_menu(text: str) -> None:
    await cl.Message(content=text, actions=[
        cl.Action(name="new_claim", payload={}, label="📦 File a claim"),
        cl.Action(name="examples", payload={}, label="✨ Try an example"),
        cl.Action(name="history", payload={}, label="📜 My claims"),
    ]).send()


# ---------- small helpers for the guided form ----------
def _picked(res):
    """AskActionMessage answer -> the value in the payload (None on timeout)."""
    if not res:
        return None
    payload = res.get("payload") if isinstance(res, dict) else getattr(res, "payload", None)
    return (payload or {}).get("value")


async def ask_choice(question: str, options: list[tuple[str, object]]):
    res = await cl.AskActionMessage(
        content=question, timeout=TIMEOUT,
        actions=[cl.Action(name="choice", payload={"value": v}, label=text) for text, v in options]).send()
    return _picked(res)


async def ask_number(question: str, low: float, high: float):
    for _ in range(3):
        res = await cl.AskUserMessage(content=question, timeout=TIMEOUT).send()
        if not res:
            return None
        text = (res.get("output") or res.get("content") or "").replace("€", "").replace(",", ".").strip()
        try:
            value = float(text)
            if low <= value <= high:
                return value
        except ValueError:
            pass
        question = f"Please type a number between {low:g} and {high:g}."
    return None


async def describe_photo() -> str | None:
    """Photo -> Gemini description (facts only). Without a photo, or if Gemini is not reachable,
    the user types what they see: the agent never invents the evidence."""
    has_photo = await ask_choice("Do you have a photo of the parcel?",
                                 [("📷 Yes, upload it", True), ("✍️ No, I'll describe it", False)])
    files = None
    if has_photo:
        files = await cl.AskFileMessage(
            content="Upload one photo of the parcel and the item (JPG or PNG, up to 10 MB).",
            accept=["image/jpeg", "image/png"], max_size_mb=10, timeout=TIMEOUT, raise_on_timeout=False).send()
    if files:
        msg = cl.Message(content="Looking at the photo…")
        await msg.send()
        try:
            from src.agent.vision import describe
            text = await cl.make_async(describe)(files[0].path)
            msg.content = f"**What the photo shows** (AI description, facts only):\n> {text}"
            await msg.update()
            return text
        except Exception as error:  # noqa: BLE001 (no Google login, quota, region...)
            msg.content = f"I could not read the photo automatically ({type(error).__name__})."
            await msg.update()
    res = await cl.AskUserMessage(
        content="✍️ Describe what you see: the state of the box, and of the item if you can see it.",
        timeout=TIMEOUT).send()
    return (res.get("output") or res.get("content") or "").strip() if res else None


async def guided_claim(prefill: str | None = None) -> dict | None:
    guess = guess_category(prefill) if prefill else None
    order = ([guess] if guess in CATEGORIES else []) + [c for c in CATEGORIES if c != guess]
    category = await ask_choice("**1/6 · What was in the parcel?**"
                                + (f" (from your message, it sounds like **{CATEGORY_LABELS[guess]}**)" if guess else ""),
                                [(CATEGORY_LABELS[c], c) for c in order])
    if not category:
        return None
    fragile, _ = CATEGORIES[category]  # the word is a training-data example (e.g. headphones), not the user's item
    value = await ask_number("**2/6 · Declared value of the item, in euros?** (for example 12.50)", 0.5, 5000)
    if value is None:
        return None
    cover = await ask_choice("**3/6 · Which cover was on the label?**",
                             [("Standard (up to €25)", "standard"), ("Premium (up to €500)", "premium")])
    fee = await ask_choice("**4/6 · Label fee paid?**", [(f"€{f:.2f}", f) for f in LABEL_FEES])
    days = await ask_number("**5/6 · Delivered how many days ago?** (0 = today)", 0, 365)
    if None in (cover, fee, days):
        return None
    fragile_option, padding = False, True
    if fragile:
        fragile_option = await ask_choice("This kind of item is fragile. **Did you pay the fragile option?**",
                                          [("Yes", True), ("No", False)])
    padding = await ask_choice("**Was the item padded** (bubble wrap, paper, foam)?", [("Yes", True), ("No", False)])
    if fragile_option is None or padding is None:
        return None
    await cl.Message(content="**6/6 · The evidence**").send()
    use_text = False
    if prefill:
        use_text = await ask_choice(f"You already told me:\n> {prefill}\n\n**Use this, or add a photo?**",
                                    [("✅ Use my description", True), ("📷 Add a photo", False)])
        if use_text is None:
            return None
    description = prefill if use_text else await describe_photo()
    if not description:
        return None
    return {"case_id": f"CHAT-{int(time.time())}", "cover": cover, "item_category": category,
            "fragile_item": fragile, "fragile_option": fragile_option, "padding": padding,
            "item_value_eur": round(value, 2), "label_fee_eur": fee, "days_since_delivery": int(days),
            "damage_description": description,
            **({"merchant_message": prefill} if prefill and description != prefill else {})}


def summary(claim: dict) -> str:
    yn = lambda b: "yes" if b else "no"  # noqa: E731
    return ("**Your claim**\n\n| | |\n|---|---|\n"
            f"| Item | {CATEGORY_LABELS[claim['item_category']]} (fragile: {yn(claim['fragile_item'])}) |\n"
            f"| Declared value · label fee | €{claim['item_value_eur']:.2f} · €{claim['label_fee_eur']:.2f} |\n"
            f"| Cover | {claim['cover']} |\n| Delivered | {claim['days_since_delivery']} days ago |\n"
            f"| Fragile option · padding | {yn(claim['fragile_option'])} · {yn(claim['padding'])} |\n"
            f"| Evidence | {claim['damage_description']} |")


# ---------- Chainlit events ----------
@cl.on_chat_start
async def start() -> None:
    await cl.Message(content=(
        "### 📦 ParcelCheck: report a damaged parcel\n"
        "Tell me what happened in one sentence (\"the mug arrived broken\"), or tap **📦 File a claim**: "
        "a few one-tap questions, then a decision with the rule behind it. Type **history** to see your past claims. "
        "Small claims are refunded on the spot; larger ones or unclear photos go to a person.\n\n"
        f"_{mode_line()}_")).send()
    await main_menu("How do you want to start?")


async def claim_flow(prefill: str | None = None) -> None:
    claim = await guided_claim(prefill)
    if not claim:
        await main_menu("No problem, the claim was not sent.")
        return
    ok = await ask_choice(summary(claim) + "\n\n**Send this claim?**", [("✅ Send", True), ("↩️ Start again", False)])
    if ok:
        await answer(claim)
    else:
        await main_menu("The claim was not sent.")


@cl.action_callback("new_claim")
async def on_new_claim(_action: cl.Action) -> None:
    await claim_flow()


@cl.action_callback("history")
async def on_history(_action: cl.Action) -> None:
    await show_history()


async def show_history() -> None:
    await cl.Message(content=history_markdown(load_history())).send()
    await main_menu("What next?")


async def handle_free_text(text: str) -> None:
    """A sentence typed by the merchant: guardrail first, then a claim that starts from their words."""
    reading = cl.Message(content="🔍 Reading your message…")
    await reading.send()
    try:
        result = await cl.make_async(screen_message)(text)
    finally:
        if LANGFUSE_ON:
            langfuse.flush()
    await reading.remove()
    if result is not None:  # not a safe damaged-parcel message: hand over, never argue
        await cl.Message(content="🧑‍💼 " + HANDOVER_TEXT.get(result.get("guardrail", ""), HANDOVER_TEXT["unavailable"])
                         + "\n\n_Prepared by an AI system. Type **person** to talk to a human._").send()
        remember({"case_id": "message"}, result)
        await main_menu("Anything else?")
        return
    await cl.Message(content="Thanks, I noted what happened:\n> " + text
                     + "\n\nLet's turn it into a claim: **a few quick questions** (one tap each), then you can add a photo.").send()
    await claim_flow(prefill=text)


@cl.action_callback("examples")
async def on_examples(_action: cl.Action) -> None:
    await cl.Message(content="**Pick an example claim.** Each one shows a different path through the agent:",
                     actions=[cl.Action(name="example", payload={"id": k}, label=v[0]) for k, v in EXAMPLES.items()]).send()


@cl.action_callback("example")
async def on_example(action: cl.Action) -> None:
    demo_id = action.payload["id"]
    label, what, switch_off = EXAMPLES[demo_id]
    claim = DEMOS[demo_id]["claim"]
    await cl.Message(content=f"**{label}**: {what}\n\n" + summary(claim)).send()
    await answer(claim, autonomy=False if switch_off else None)


@cl.action_callback("feedback")
async def on_feedback(action: cl.Action) -> None:
    """The reviewer's verdict on the agent's decision: a free ground-truth label (Session 5)."""
    value, trace_id = action.payload["value"], action.payload.get("trace_id")
    if LANGFUSE_ON and trace_id:
        langfuse.create_score(trace_id=trace_id, name="reviewer_agrees", value=float(value), data_type="NUMERIC")
        langfuse.flush()
    await cl.Message(content="Thanks, noted as " + ("a right decision" if value else "a wrong decision")
                     + ("." if LANGFUSE_ON else " (Langfuse is off, so it is not stored).")).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    text = message.content.strip()
    intent = intent_of(text)
    if intent == "switch":
        os.environ["AUTONOMY_ENABLED"] = "false" if text.lower().strip().endswith("off") else "true"
        await cl.Message(content=f"Override switch set. Next claim: _{mode_line()}_").send()
    elif intent == "person":
        await cl.Message(content="🧑‍💼 A support agent will contact you within 24 h. Your claim stays open.").send()
    elif intent == "history":
        await show_history()
    elif intent in ("greeting", "help", "empty"):
        await main_menu("Hello 👋 Tell me what happened to your parcel, in one sentence, or pick an option:")
    elif intent == "demo" and text.upper() in DEMOS:
        await answer(DEMOS[text.upper()]["claim"])
    elif intent == "json":  # power users: paste a claim as JSON
        try:
            await answer(json.loads(text))
        except json.JSONDecodeError:
            await cl.Message(content="That JSON could not be read.").send()
    else:
        await handle_free_text(text)
