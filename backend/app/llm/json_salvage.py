"""Recovery of truncated JSON objects from LLM responses.

A persona response that hits the token limit mid-object would otherwise void the
whole reaction. Since the fan-out degrades gracefully (§18.3), losing one
persona is survivable — but recovering it is cheap and usually correct, because
the useful fields tend to be emitted before the long prose ones.
"""

from __future__ import annotations

import json
from typing import Any


def extract_json_block(text: str) -> str:
    """Pull the outermost JSON object out of a response that may wrap it in prose
    or a markdown fence."""
    text = text.strip()

    if "```" in text:
        # Take the content of the first fenced block.
        parts = text.split("```")
        if len(parts) >= 2:
            candidate = parts[1]
            if candidate.startswith("json"):
                candidate = candidate[4:]
            text = candidate.strip()

    start = text.find("{")
    if start == -1:
        return text
    return text[start:]


def salvage_truncated_json_object(text: str) -> dict[str, Any] | None:
    """Parse a JSON object, repairing truncation if needed.

    Walks the text tracking string/escape state and bracket depth, discards any
    trailing partial key-value pair, and closes open brackets. Returns None if
    nothing parseable can be recovered.
    """
    text = extract_json_block(text)
    if not text:
        return None

    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    stack: list[str] = []
    in_string = False
    escaped = False
    # Offset just past the last structurally complete value at depth >= 1.
    last_safe = -1

    for i, ch in enumerate(text):
        if escaped:
            escaped = False
            continue
        if ch == "\\" and in_string:
            escaped = True
            continue
        if ch == '"':
            in_string = not in_string
            if not in_string and stack:
                last_safe = i
            continue
        if in_string:
            continue

        if ch in "{[":
            stack.append(ch)
        elif ch in "}]":
            if stack:
                stack.pop()
            last_safe = i
        elif ch in ",":
            last_safe = i - 1 if last_safe < i else last_safe
        elif ch.isdigit() or ch in "eE.+-" or ch in "truefalsnl":
            if stack:
                last_safe = i

    if not stack or last_safe < 0:
        return None

    candidate = text[: last_safe + 1].rstrip().rstrip(",")

    # Close whatever is still open, innermost first.
    closers = {"{": "}", "[": "]"}
    repair = "".join(closers[ch] for ch in reversed(stack))

    for attempt in (candidate + repair, candidate.rstrip('"') + repair):
        try:
            parsed = json.loads(attempt)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue

    return None
