"""The Chainlit app must start from a fresh clone: offline mode (no endpoint, no keys) answers a claim end to end."""
import asyncio
import importlib

import pytest


@pytest.fixture
def app(monkeypatch, tmp_path):
    for key in ("GCP_ENDPOINT_ID", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"):
        monkeypatch.setenv(key, "")
    monkeypatch.setenv("INPUT_GUARDRAIL", "false")
    monkeypatch.setenv("CLAIMS_HISTORY_PATH", str(tmp_path / "history.jsonl"))
    import prototype.chainlit_app.chat_helpers as helpers
    import prototype.chainlit_app.main as main

    importlib.reload(helpers)
    return importlib.reload(main)


def test_app_imports_and_decides_offline(app):
    claim = app.DEMOS[next(iter(app.DEMOS))]["claim"]
    result = app.process(claim, True)
    assert result["action"] in {"refund_executed", "message_sent", "queued_for_human"}
    assert "Decision" in app.render(result) or "person" in app.render(result).lower()


def test_typed_message_is_screened_before_a_claim(app):
    assert asyncio.iscoroutinefunction(app.handle_free_text)
    assert app.screen_message("the mug arrived broken") is None  # guardrail off offline: goes on to the claim
