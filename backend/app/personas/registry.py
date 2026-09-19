"""Persona registry: load, validate, and serve authored persona nodes."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import ValidationError

from app.personas.schema import PersonaNode

logger = logging.getLogger(__name__)

DEFINITIONS_DIR = Path(__file__).parent / "definitions"


class PersonaLoadError(RuntimeError):
    pass


def load_personas(directory: Path | None = None) -> dict[str, PersonaNode]:
    """Load and validate every persona YAML in the definitions directory.

    Fails loudly on a malformed persona rather than silently skipping it — a
    missing persona is a silent blind spot, which is precisely the failure mode
    this product exists to prevent.
    """
    directory = directory or DEFINITIONS_DIR
    if not directory.is_dir():
        raise PersonaLoadError(f"Persona directory not found: {directory}")

    nodes: dict[str, PersonaNode] = {}
    errors: list[str] = []

    for path in sorted(directory.glob("*.yaml")):
        try:
            raw = yaml.safe_load(path.read_text())
        except yaml.YAMLError as exc:
            errors.append(f"{path.name}: invalid YAML: {exc}")
            continue

        if not isinstance(raw, dict):
            errors.append(f"{path.name}: expected a mapping at the top level")
            continue

        try:
            node = PersonaNode.model_validate(raw)
        except ValidationError as exc:
            errors.append(f"{path.name}: {exc}")
            continue

        if node.id in nodes:
            errors.append(f"{path.name}: duplicate persona id {node.id!r}")
            continue
        if node.id != path.stem:
            errors.append(f"{path.name}: id {node.id!r} does not match filename")
            continue

        nodes[node.id] = node

    if errors:
        raise PersonaLoadError("Persona validation failed:\n  " + "\n  ".join(errors))

    if not nodes:
        raise PersonaLoadError(f"No persona definitions found in {directory}")

    logger.info("Loaded %d personas (%d mandatory)", len(nodes), len(mandatory_ids(nodes)))
    return nodes


def mandatory_ids(nodes: dict[str, PersonaNode]) -> list[str]:
    """Personas always included in K regardless of relevance (§6.2)."""
    return [n.id for n in nodes.values() if n.mandatory]


@lru_cache(maxsize=1)
def get_registry() -> dict[str, PersonaNode]:
    return load_personas()


def reload_registry() -> dict[str, PersonaNode]:
    get_registry.cache_clear()
    return get_registry()
