from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


FENCED_JSON_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_json(raw: str) -> Any:
    """Extract JSON from plain text, fenced code, or explanatory model output."""
    text = raw.strip()
    if not text:
        raise ValueError("model returned an empty response")

    fenced = FENCED_JSON_RE.findall(text)
    candidates = [item.strip() for item in fenced] if fenced else []
    candidates.append(text)

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    start = min([idx for idx in [text.find("{"), text.find("[")] if idx != -1], default=-1)
    if start == -1:
        raise ValueError("no JSON object or array found in model output")

    opener = text[start]
    closer = "}" if opener == "{" else "]"
    end = text.rfind(closer)
    if end <= start:
        raise ValueError("could not find the end of the JSON payload")

    snippet = text[start : end + 1]
    return json.loads(snippet)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
