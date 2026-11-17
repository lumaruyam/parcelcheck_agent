"""Input guardrail (Session 6): an LLM classifier that screens the merchant's text before the refund model.

Five categories (prompts/input_guardrail.yaml): safe, prompt_injection, abusive, out_of_scope, personal_data.
Only `safe` reaches steps 1-4; everything else goes to a person, never to an automatic refusal.

Gemini on Vertex AI with the user's gcloud login (no API key), structured JSON output, temperature 0,
and the `reason` field before the `category` field so the model explains before it decides.
If the call fails (quota, network), the claim goes to a person: fail closed, money is at stake.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()  # GCP_PROJECT_ID and the guardrail overrides come from .env, like the rest of the code

ROOT = Path(__file__).resolve().parents[2]
PROMPT_PATH = ROOT / "prompts" / "input_guardrail.yaml"
Category = Literal["safe", "prompt_injection", "abusive", "out_of_scope", "personal_data"]
CATEGORIES: list[str] = ["safe", "prompt_injection", "abusive", "out_of_scope", "personal_data"]


class GuardrailVerdict(BaseModel):
    """What the guardrail decides. `reason` comes first: the model writes it before choosing."""

    reason: str
    category: Category

    @property
    def is_allowed(self) -> bool:
        """Only safe messages may reach the refund model."""
        return self.category == "safe"


class PromptMessage(BaseModel):
    role: Literal["system", "user"]
    content: str


class GuardrailPrompt(BaseModel):
    """The versioned prompt. Git (prompts/*.yaml) is the source of truth; Langfuse serves the version
    labelled `production` to the app (Session 6.3, scripts/push_prompt_to_langfuse.py)."""

    name: str
    semver: str
    commit_message: str
    config: dict[str, Any]
    messages: list[PromptMessage]
    source: str = "file"                 # "file" or "langfuse"
    langfuse_version: int | None = None  # Langfuse's own version number, when served from Langfuse

    @property
    def system(self) -> str:
        return next(m.content for m in self.messages if m.role == "system")

    def user(self, message: str) -> str:
        template = next(m.content for m in self.messages if m.role == "user")
        return template.replace("{{message}}", message)


def load_prompt(path: Path = PROMPT_PATH) -> GuardrailPrompt:
    """The prompt as written in Git. The eval harness and CI always use this one (they test the PR)."""
    with open(path, encoding="utf-8") as f:
        return GuardrailPrompt(**yaml.safe_load(f))


def from_langfuse(lf_prompt: Any) -> GuardrailPrompt:
    """Turn a Langfuse chat prompt (pushed by scripts/push_prompt_to_langfuse.py) into a GuardrailPrompt."""
    config = dict(lf_prompt.config or {})
    semver = str(config.pop("semver", "unknown"))
    commit_message = str(config.pop("commit_message", ""))
    messages = [PromptMessage(role=m["role"], content=m["content"]) for m in lf_prompt.prompt
                if isinstance(m, dict) and m.get("role") in ("system", "user")]
    return GuardrailPrompt(name=lf_prompt.name, semver=semver, commit_message=commit_message, config=config,
                           messages=messages, source="langfuse", langfuse_version=lf_prompt.version)


def load_active_prompt(langfuse: Any | None = None, label: str | None = None) -> tuple[GuardrailPrompt, Any]:
    """For the app: the prompt labelled `production` in Langfuse (cached 60 s by the SDK), so a rollback is
    moving the label in Langfuse, with no redeploy. Falls back to the Git file if Langfuse is not configured
    or not reachable. Returns (prompt, langfuse prompt object or None) so traces can link to the version."""
    source = os.getenv("PROMPT_SOURCE", "langfuse" if langfuse is not None else "file").strip().lower()
    if source != "langfuse" or langfuse is None:
        return load_prompt(), None
    file_prompt = load_prompt()
    try:
        lf_prompt = langfuse.get_prompt(file_prompt.name, label=label or os.getenv("PROMPT_LABEL", "production"),
                                        type="chat", cache_ttl_seconds=60)
        return from_langfuse(lf_prompt), lf_prompt
    except Exception:  # noqa: BLE001  (Langfuse down, prompt not pushed yet): the Git version still works
        return file_prompt, None


RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "reason": {"type": "STRING"},
        "category": {"type": "STRING", "enum": CATEGORIES},
    },
    "required": ["reason", "category"],
    "propertyOrdering": ["reason", "category"],  # reason first, so the model "thinks" before deciding
}


class InputGuardrail:
    """Builds the Gemini call once from the prompt file; `check(message)` returns a verdict."""

    def __init__(self, prompt: GuardrailPrompt | None = None) -> None:
        import vertexai
        from vertexai.generative_models import GenerativeModel

        self.prompt = prompt or load_prompt()
        cfg = self.prompt.config
        project = os.getenv("GCP_PROJECT_ID") or os.environ["GOOGLE_CLOUD_PROJECT"]
        vertexai.init(project=project, location=os.getenv("GUARDRAIL_LOCATION", cfg.get("location", "eu")))
        self.model_name = os.getenv("GUARDRAIL_MODEL", cfg["model"])
        self.model = GenerativeModel(self.model_name, system_instruction=self.prompt.system)

    def _config(self, with_ordering: bool = True) -> Any:
        from vertexai.generative_models import GenerationConfig

        schema = dict(RESPONSE_SCHEMA)
        if not with_ordering:
            schema.pop("propertyOrdering")
        return GenerationConfig(temperature=self.prompt.config.get("temperature", 0),
                                response_mime_type="application/json", response_schema=schema)

    def check(self, message: str) -> GuardrailVerdict:
        """Classify one message. Retries on quota errors (429); other errors are raised."""
        try:
            config = self._config()
        except (TypeError, ValueError):  # an older SDK that does not know propertyOrdering
            config = self._config(with_ordering=False)
        for wait in (5, 20, 60, None):
            try:
                out = self.model.generate_content(self.prompt.user(message), generation_config=config)
                return GuardrailVerdict(**json.loads(out.text))
            except Exception as error:  # noqa: BLE001
                if wait is None or "429" not in str(error):
                    raise
                time.sleep(wait)
        raise RuntimeError("unreachable")


def check_or_handover(guard: InputGuardrail | None, message: str) -> GuardrailVerdict:
    """For the app: any failure of the guardrail itself sends the claim to a person (fail closed)."""
    if guard is None:
        return GuardrailVerdict(reason="guardrail disabled", category="safe")
    try:
        return guard.check(message)
    except Exception as error:  # noqa: BLE001
        return GuardrailVerdict(reason=f"guardrail unavailable ({type(error).__name__}): a person checks it",
                                category="out_of_scope")
