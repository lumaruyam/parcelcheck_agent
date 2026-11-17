"""Push a versioned prompt from Git to Langfuse Prompt Management (Session 6.3).

Git (prompts/*.yaml, with semver) is the source of truth. This script creates a new Langfuse version with
the labels `v<semver>` and, unless --no-production, `production`. The app serves the `production` label,
so promoting or rolling back a prompt = moving that label in Langfuse (UI or this script), no redeploy.

    uv run python -m scripts.push_prompt_to_langfuse                       # prompts/input_guardrail.yaml
    uv run python -m scripts.push_prompt_to_langfuse --no-production       # push as a candidate only
    uv run python -m scripts.push_prompt_to_langfuse --dry-run

If a version with the same semver is already in Langfuse, nothing is pushed (re-running is safe).
Semver: MAJOR = output contract changes (categories, JSON fields), MINOR = behaviour, PATCH = wording.
"""
import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.agent.input_guardrail import PROMPT_PATH, load_prompt

load_dotenv()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", default=str(PROMPT_PATH))
    ap.add_argument("--no-production", action="store_true", help="do not move the production label")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    p = load_prompt(Path(a.file))
    labels = [f"v{p.semver}"] + ([] if a.no_production else ["production"])
    messages = [{"role": m.role, "content": m.content} for m in p.messages]
    config = {**p.config, "semver": p.semver, "commit_message": p.commit_message}
    print(f"{p.name} v{p.semver} · labels {labels} · {len(messages)} messages · model {p.config.get('model')}")
    if a.dry_run:
        return

    from langfuse import Langfuse

    lf = Langfuse()
    if not lf.auth_check():
        sys.exit("Langfuse keys not valid (check LANGFUSE_* in .env)")
    try:
        existing = lf.get_prompt(p.name, label=f"v{p.semver}", type="chat", cache_ttl_seconds=0)
        print(f"Already in Langfuse as version {existing.version} (label v{p.semver}): nothing pushed.")
        if not a.no_production and "production" not in (existing.labels or []):
            print("Note: it is not the production version. Move the label in the Langfuse UI to promote it.")
        return
    except Exception:  # noqa: BLE001  (not found: push it)
        pass
    kwargs = dict(name=p.name, type="chat", prompt=messages, config=config, labels=labels)
    try:
        created = lf.create_prompt(**kwargs, commit_message=p.commit_message)
    except TypeError:  # older SDK without commit_message
        created = lf.create_prompt(**kwargs)
    lf.flush()
    print(f"Pushed {p.name} v{p.semver} as Langfuse version {created.version} with labels {labels}")


if __name__ == "__main__":
    main()
