from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator

OperationType = Literal[
    "trim",
    "cut",
    "remove_segment",
    "replace_audio",
    "add_background_music",
    "volume",
    "speed",
    "resize",
    "crop",
    "rotate",
    "text_overlay",
    "fade",
    "compress",
]


class Operation(BaseModel):
    type: OperationType
    parameters: dict[str, Any] = Field(default_factory=dict)


class EditingPlan(BaseModel):
    operations: list[Operation] = Field(default_factory=list)

    def validate_plan(self) -> list[str]:
        errors: list[str] = []
        for i, op in enumerate(self.operations):
            errs = validate_operation(op)
            for e in errs:
                errors.append(f"Operation {i} ({op.type}): {e}")
        return errors


def _num(params: dict[str, Any], key: str) -> Optional[float]:
    val = params.get(key)
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _require(params: dict[str, Any], key: str) -> Optional[float]:
    return _num(params, key)


def validate_operation(op: Operation) -> list[str]:
    p = op.parameters
    errors: list[str] = []

    def need(*keys: str) -> None:
        for k in keys:
            if p.get(k) is None:
                errors.append(f"missing parameter '{k}'")

    def positive(key: str) -> None:
        v = _num(p, key)
        if v is not None and v <= 0:
            errors.append(f"'{key}' must be positive")

    def non_negative(key: str) -> None:
        v = _num(p, key)
        if v is not None and v < 0:
            errors.append(f"'{key}' must be non-negative")

    if op.type == "trim":
        need("start", "end")
        non_negative("start")
        non_negative("end")
        s, e = _num(p, "start"), _num(p, "end")
        if s is not None and e is not None and e <= s:
            errors.append("'end' must be greater than 'start'")

    elif op.type == "cut":
        need("start", "end")
        non_negative("start")
        non_negative("end")
        s, e = _num(p, "start"), _num(p, "end")
        if s is not None and e is not None and e <= s:
            errors.append("'end' must be greater than 'start'")

    elif op.type == "remove_segment":
        need("start", "end")
        non_negative("start")
        non_negative("end")
        s, e = _num(p, "start"), _num(p, "end")
        if s is not None and e is not None and e <= s:
            errors.append("'end' must be greater than 'start'")

    elif op.type == "replace_audio":
        need("audio_path")
        if not isinstance(p.get("audio_path"), str) or not p["audio_path"]:
            errors.append("'audio_path' must be a string")

    elif op.type == "add_background_music":
        need("audio_path")
        if not isinstance(p.get("audio_path"), str) or not p["audio_path"]:
            errors.append("'audio_path' must be a string")
        v = _num(p, "volume")
        if v is not None and (v < 0 or v > 5):
            errors.append("'volume' must be between 0 and 5")

    elif op.type == "volume":
        need("level")
        v = _num(p, "level")
        if v is not None and (v < 0 or v > 10):
            errors.append("'level' must be between 0 and 10")

    elif op.type == "speed":
        need("factor")
        v = _num(p, "factor")
        if v is not None and (v <= 0 or v > 20):
            errors.append("'factor' must be between 0.1 and 20")

    elif op.type == "resize":
        need("width", "height")
        if p.get("width") is not None and int(p["width"]) <= 0:
            errors.append("'width' must be positive")
        if p.get("height") is not None and int(p["height"]) <= 0:
            errors.append("'height' must be positive")

    elif op.type == "crop":
        need("width", "height")
        if p.get("width") is not None and int(p["width"]) <= 0:
            errors.append("'width' must be positive")
        if p.get("height") is not None and int(p["height"]) <= 0:
            errors.append("'height' must be positive")
        non_negative("x")
        non_negative("y")

    elif op.type == "rotate":
        need("degrees")
        d = p.get("degrees")
        if d not in (90, 180, 270):
            errors.append("'degrees' must be 90, 180, or 270")

    elif op.type == "text_overlay":
        need("text")
        if not isinstance(p.get("text"), str) or not p["text"].strip():
            errors.append("'text' must be a non-empty string")
        non_negative("x")
        non_negative("y")
        s = _num(p, "start")
        e = _num(p, "end")
        if s is not None and e is not None and e < s:
            errors.append("'end' must be >= 'start'")

    elif op.type == "fade":
        t = p.get("type", "in")
        if t not in ("in", "out"):
            errors.append("'type' must be 'in' or 'out'")
        non_negative("duration")
        d = _num(p, "duration")
        if d is not None and d <= 0:
            errors.append("'duration' must be positive")

    elif op.type == "compress":
        crf = p.get("crf", 28)
        if not isinstance(crf, (int, float)) or crf < 0 or crf > 51:
            errors.append("'crf' must be between 0 and 51")

    return errors
