from __future__ import annotations

import json
import re
from typing import Any

from app.config import settings
from app.core.exceptions import AIError
from app.modules.editor.schemas import EditingPlan

SYSTEM_PROMPT = (
    "You are a video editing assistant. Convert the user's natural-language instruction "
    "into a JSON editing plan. Only output JSON matching this schema: "
    '{"operations":[{"type":"<operation>","parameters":{...}}]}. '
    "Supported types: trim, cut, remove_segment, replace_audio, add_background_music, "
    "volume, speed, resize, crop, rotate, text_overlay, fade, compress. "
    "Never output shell commands or FFmpeg commands. Times are in seconds. "
    "Respond ONLY with the JSON object."
)


class AIService:
    def __init__(self) -> None:
        if not settings.ai_enabled:
            raise AIError("AI is not configured.")

    def parse_instruction(self, instruction: str) -> EditingPlan:
        if not settings.ai_enabled:
            raise AIError("AI is not configured.")
        provider = settings.ai_provider.lower()
        if provider == "openai":
            return self._openai(instruction)
        raise AIError(f"Unsupported AI provider: {settings.ai_provider}")

    def _openai(self, instruction: str) -> EditingPlan:
        try:
            import httpx
        except ImportError as exc:
            raise AIError("httpx is not installed.") from exc
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {settings.ai_api_key}"}
        payload = {
            "model": settings.ai_model or "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": instruction},
            ],
            "temperature": 0.2,
        }
        try:
            resp = httpx.post(url, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
        except Exception as exc:
            raise AIError(f"AI request failed: {exc}") from exc
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return _extract_plan(content)


def _extract_plan(content: str) -> EditingPlan:
    # Find JSON object in the response
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        raise AIError("AI did not return a valid plan.")
    try:
        obj = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise AIError("AI returned invalid JSON.") from exc
    return EditingPlan(**obj)
