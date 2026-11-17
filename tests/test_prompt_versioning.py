"""Session 6.3: the app serves the Langfuse `production` prompt and falls back to Git (no network here)."""
from types import SimpleNamespace

from src.agent.input_guardrail import from_langfuse, load_active_prompt, load_prompt


def fake_langfuse_prompt(file_prompt, version=3):
    return SimpleNamespace(
        name=file_prompt.name, version=version, labels=["production", f"v{file_prompt.semver}"],
        config={**file_prompt.config, "semver": file_prompt.semver, "commit_message": file_prompt.commit_message},
        prompt=[{"role": m.role, "content": m.content} for m in file_prompt.messages])


class FakeLangfuse:
    def __init__(self, prompt=None, fail=False):
        self.prompt, self.fail, self.calls = prompt, fail, []

    def get_prompt(self, name, label, type, cache_ttl_seconds):  # noqa: A002 (same signature as the SDK)
        self.calls.append((name, label, type))
        if self.fail:
            raise ConnectionError("langfuse down")
        return self.prompt


def test_round_trip_matches_the_git_file():
    file_prompt = load_prompt()
    p = from_langfuse(fake_langfuse_prompt(file_prompt))
    assert (p.semver, p.system, p.user("x"), p.config) == (file_prompt.semver, file_prompt.system,
                                                           file_prompt.user("x"), file_prompt.config)
    assert p.source == "langfuse" and p.langfuse_version == 3


def test_app_asks_for_the_production_label(monkeypatch):
    monkeypatch.delenv("PROMPT_SOURCE", raising=False)
    monkeypatch.delenv("PROMPT_LABEL", raising=False)
    lf = FakeLangfuse(fake_langfuse_prompt(load_prompt()))
    prompt, lf_prompt = load_active_prompt(lf)
    assert lf.calls == [("input-guardrail", "production", "chat")]
    assert prompt.source == "langfuse" and lf_prompt is not None


def test_falls_back_to_git_when_langfuse_is_down(monkeypatch):
    monkeypatch.delenv("PROMPT_SOURCE", raising=False)
    prompt, lf_prompt = load_active_prompt(FakeLangfuse(fail=True))
    assert prompt.source == "file" and lf_prompt is None and prompt.semver == load_prompt().semver


def test_file_source_never_calls_langfuse(monkeypatch):
    monkeypatch.setenv("PROMPT_SOURCE", "file")
    lf = FakeLangfuse(fail=True)
    prompt, _ = load_active_prompt(lf)
    assert prompt.source == "file" and lf.calls == []
    assert load_active_prompt(None)[0].source == "file"
