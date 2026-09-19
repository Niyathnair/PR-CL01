"""crowdLens API entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.llm.auth import MissingCredentialsError, describe_credential, resolve_credential
from app.llm.client import LLMClient
from app.personas.registry import get_registry
from app.store import RunStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
)
logger = logging.getLogger("crowdlens")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail at startup with setup instructions rather than at the first persona
    # call with an opaque 401.
    try:
        credential = resolve_credential()
    except MissingCredentialsError as exc:
        logger.error("%s", exc)
        raise

    logger.info("Anthropic auth: %s", describe_credential(credential))
    if credential.is_subscription:
        logger.info(
            "Using a personal Claude subscription token. Appropriate for local use; "
            "a multi-user deployment needs its own ANTHROPIC_API_KEY."
        )

    registry = get_registry()
    logger.info("Persona registry: %d nodes", len(registry))

    app.state.llm = LLMClient(credential)
    app.state.store = RunStore()
    app.state.runs = RunStore()

    yield

    # Shutdown must not fail on a client that has no aclose (e.g. a test double).
    closer = getattr(app.state.llm, "aclose", None)
    if closer is not None:
        await closer()


app = FastAPI(
    title="crowdLens",
    description=(
        "Proactive backlash simulation for marketing copy. Simulates a population "
        "of audience personas and reports what they understood, how they felt, and "
        "what exactly triggered them.\n\n"
        "**The Risk Index is an ordinal index from simulated reactions — not a "
        "probability, and not survey data.**"
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router, prefix="/v1")


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "crowdLens",
        "docs": "/docs",
        "health": "/v1/health",
    }
