"""Anthropic credential resolution.

crowdLens authenticates to Claude using the developer's existing Claude
credentials rather than a raw API key pasted into a .env file.

Resolution order:

1. ``CLAUDE_CODE_OAUTH_TOKEN`` — a Claude subscription OAuth token, produced by
   running ``claude setup-token``. This is the intended path for local
   development: the token belongs to your Claude account and no API key needs
   to exist on disk.
2. ``ANTHROPIC_AUTH_TOKEN`` — an explicitly supplied bearer token, for gateways
   or proxies that mint their own.
3. ``ANTHROPIC_API_KEY`` — a standard API key. The fallback, and the only
   option that is appropriate for a multi-user deployment (see below).

If none resolve, we fail at startup with setup instructions rather than at the
first persona call with an opaque 401.

**Deployment note.** A subscription OAuth token is tied to one Claude account
and is not licensed for serving other people's traffic. It is the right
credential for you running crowdLens locally. If crowdLens is ever deployed to
serve multiple users, that deployment needs its own ANTHROPIC_API_KEY.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

CredentialKind = Literal["oauth", "auth_token", "api_key"]

_SETUP_HELP = """
No Anthropic credentials found.

Recommended (uses your existing Claude subscription, no API key on disk):

    claude setup-token

then export the token it prints:

    export CLAUDE_CODE_OAUTH_TOKEN='<token>'

Alternatively, for a deployment serving multiple users, set a standard API key:

    export ANTHROPIC_API_KEY='sk-ant-...'
""".strip()


class MissingCredentialsError(RuntimeError):
    """Raised at startup when no Anthropic credential can be resolved."""

    def __init__(self) -> None:
        super().__init__(_SETUP_HELP)


@dataclass(frozen=True)
class Credential:
    """A resolved Anthropic credential.

    ``value`` is deliberately excluded from repr so that a credential landing in
    a log line, traceback, or error payload does not leak the secret.
    """

    kind: CredentialKind
    value: str
    source_env_var: str

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"Credential(kind={self.kind!r}, source={self.source_env_var!r}, value=<redacted>)"

    @property
    def is_subscription(self) -> bool:
        """True when this credential is tied to a personal Claude account."""
        return self.kind == "oauth"

    def client_kwargs(self) -> dict[str, str]:
        """Keyword arguments for ``anthropic.AsyncAnthropic``."""
        if self.kind == "api_key":
            return {"api_key": self.value}
        # Both OAuth subscription tokens and explicit bearer tokens are passed
        # as auth_token; the SDK sends them as `Authorization: Bearer ...`.
        return {"auth_token": self.value}


def resolve_credential(env: dict[str, str] | None = None) -> Credential:
    """Resolve an Anthropic credential from the environment.

    Raises:
        MissingCredentialsError: if no credential is present.
    """
    env = env if env is not None else dict(os.environ)

    for var, kind in (
        ("CLAUDE_CODE_OAUTH_TOKEN", "oauth"),
        ("ANTHROPIC_AUTH_TOKEN", "auth_token"),
        ("ANTHROPIC_API_KEY", "api_key"),
    ):
        value = (env.get(var) or "").strip()
        if value:
            return Credential(kind=kind, value=value, source_env_var=var)  # type: ignore[arg-type]

    raise MissingCredentialsError()


def describe_credential(cred: Credential) -> str:
    """A human-readable, secret-free description for startup logs and /health."""
    if cred.kind == "oauth":
        return f"Claude subscription OAuth token (from {cred.source_env_var})"
    if cred.kind == "auth_token":
        return f"bearer token (from {cred.source_env_var})"
    return f"Anthropic API key (from {cred.source_env_var})"
