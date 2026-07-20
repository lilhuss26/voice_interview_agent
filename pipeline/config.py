"""Environment configuration for the pipeline service.

Validation is deliberately LAZY. get_settings() never raises for a missing
value; callers that actually need a secret ask for it via require(). This is
the lesson from agent/config/llm.py, where import-time construction made the
API key mandatory just to import the module — which is why tests/conftest.py
has to seed a dummy one. Importing pipeline.config must always be free.
"""

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    """Raised when a required environment variable is missing or unusable."""


def _split_allowlist(raw: str) -> frozenset[str]:
    return frozenset(part.strip().lower() for part in raw.split(",") if part.strip())


@dataclass(frozen=True)
class Settings:
    gmail_credentials: str
    gmail_token: str
    gmail_token_b64: str
    db_path: str
    pubsub_topic: str
    webhook_audience: str
    pubsub_sa_email: str
    allowlist: frozenset[str]
    github_token: str
    github_repo: str
    anthropic_api_key: str
    autowatch: bool

    # Env var name -> attribute, so require() can report the name the user
    # actually sets rather than the Python attribute.
    _ENV_NAMES = {
        "GMAIL_CREDENTIALS": "gmail_credentials",
        "GMAIL_TOKEN": "gmail_token",
        "GMAIL_TOKEN_B64": "gmail_token_b64",
        "DB_PATH": "db_path",
        "PUBSUB_TOPIC": "pubsub_topic",
        "WEBHOOK_AUDIENCE": "webhook_audience",
        "PUBSUB_SA_EMAIL": "pubsub_sa_email",
        "ALLOWLIST": "allowlist",
        "GITHUB_TOKEN": "github_token",
        "GITHUB_REPO": "github_repo",
        "ANTHROPIC_API_KEY": "anthropic_api_key",
    }

    def require(self, *env_names: str) -> None:
        """Raise ConfigError naming every missing var at once.

        Reporting them one per run turns configuring a fresh deploy into a
        guessing game, so collect first and raise once.
        """
        missing = []
        for name in env_names:
            attr = self._ENV_NAMES.get(name)
            if attr is None:
                raise KeyError(f"unknown setting {name!r}")
            if not getattr(self, attr):
                missing.append(name)
        if missing:
            raise ConfigError(
                "missing required environment variable(s): " + ", ".join(sorted(missing))
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv()
    return Settings(
        gmail_credentials=os.getenv("GMAIL_CREDENTIALS", "credentials.json"),
        gmail_token=os.getenv("GMAIL_TOKEN", "pipeline/token.json"),
        gmail_token_b64=os.getenv("GMAIL_TOKEN_B64", ""),
        db_path=os.getenv("DB_PATH", "pipeline/pipeline.db"),
        pubsub_topic=os.getenv("PUBSUB_TOPIC", ""),
        webhook_audience=os.getenv("WEBHOOK_AUDIENCE", ""),
        pubsub_sa_email=os.getenv("PUBSUB_SA_EMAIL", ""),
        allowlist=_split_allowlist(os.getenv("ALLOWLIST", "")),
        github_token=os.getenv("GITHUB_TOKEN", ""),
        github_repo=os.getenv("GITHUB_REPO", ""),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        autowatch=os.getenv("PIPELINE_AUTOWATCH", "0") == "1",
    )
