from __future__ import annotations

import json
import shlex
import subprocess
from pathlib import Path
from typing import Any

from app.config import settings
from app.core.exceptions import EditorError, ProcessingError
from app.core.filesystem import (
    ensure_user_dirs,
    new_job_id,
    output_dir,
    projects_dir,
    temp_dir,
    video_path,
)
from app.dependencies import CurrentUser
from app.modules.editor.schemas import EditingPlan, Operation


class EditorService:
    def __init__(self, user: CurrentUser) -> None:
        self.user = user
        ensure_user_dirs(user.id)

    def save_plan(self, video_id: str, plan: EditingPlan) -> str:
        job_id = new_job_id()
        pdir = projects_dir(self.user.id)
        pdir.mkdir(parents=True, exist_ok=True)
        payload = {"job_id": job_id, "video_id": video_id, "plan": plan.model_dump()}
        (pdir / f"{job_id}.json").write_text(json.dumps(payload))
        return job_id

    def load_plan(self, job_id: str) -> dict[str, Any]:
        pdir = projects_dir(self.user.id)
        pfile = pdir / f"{job_id}.json"
        if not pfile.exists():
            raise EditorError("Plan not found.")
        return json.loads(pfile.read_text())

    def validate(self, plan: EditingPlan) -> dict[str, Any]:
        errors = plan.validate_plan()
        return {"valid": not errors, "errors": errors}

    def build_ffmpeg_args(
        self,
        input_path: Path,
        output_path: Path,
        plan: EditingPlan,
    ) -> list[str]:
        """Build a single ffmpeg command chain from the editing plan.

        Operations are applied sequentially via filter_complex where feasible.
        Audio replacement / background music use additional -i inputs.
        """
        args: list[str] = [settings.ffmpeg_path, "-y"]
        extra_inputs: list[str] = []
        filter_parts: list[str] = []
        amix_inputs = 0
        has_audio_replace = any(o.type == "replace_audio" for o in plan.operations)
        has_bg_music = any(o.type == "add_background_music" for o in plan.operations)

        # Preload audio inputs in order of appearance
        audio_input_labels: list[str] = []
        for op in plan.operations:
            if op.type in ("replace_audio", "add_background_music"):
                ap = op.parameters.get("audio_path", "")
                extra_inputs.extend(["-i", str(ap)])
                audio_input_labels.append(f"[{len(audio_input_labels) + 1}:a]")

        args.extend(["-i", str(input_path)])
        args.extend(extra_inputs)

        video_label = "[0:v]"
        audio_label = "[0:a]"
        audio_idx = 0
        filter_index = 0

        for op in plan.operations:
            p = op.parameters
            out_v = f"v{filter_index}"
            out_a = f"a{filter_index}"

            if op.type == "trim":
                s = float(p["start"])
                e = float(p["end"])
                filter_parts.append(
                    f"{video_label}trim=start={s}:end={e},setpts=PTS-STARTPTS[{out_v}0];"
                    f"{audio_label}atrim=start={s}:end={e},asetpts=PTS-STARTPTS[{out_a}0]"
                )
                video_label = f"[{out_v}0]"
                audio_label = f"[{out_a}0]"

            elif op.type == "cut":
                s = float(p["start"])
                e = float(p["end"])
                # cut = keep before start and after end
                filter_parts.append(
                    f"{video_label}trim=0:end={s},setpts=PTS-STARTPTS[vpre{filter_index}];"
                    f"{video_label}trim=start={e},setpts=PTS-STARTPTS[vpost{filter_index}];"
                    f"[vpre{filter_index}][vpost{filter_index}]concat=n=2:v=1:a=0[{out_v}];"
                    f"{audio_label}atrim=0:end={s},asetpts=PTS-STARTPTS[apre{filter_index}];"
                    f"{audio_label}atrim=start={e},asetpts=PTS-STARTPTS[apost{filter_index}];"
                    f"[apre{filter_index}][apost{filter_index}]concat=n=2:v=0:a=1[{out_a}]"
                )
                video_label = f"[{out_v}]"
                audio_label = f"[{out_a}]"

            elif op.type == "remove_segment":
                s = float(p["start"])
                e = float(p["end"])
                filter_parts.append(
                    f"{video_label}trim=0:end={s},setpts=PTS-STARTPTS[vpre{filter_index}];"
                    f"{video_label}trim=start={e},setpts=PTS-STARTPTS[vpost{filter_index}];"
                    f"[vpre{filter_index}][vpost{filter_index}]concat=n=2:v=1:a=0[{out_v}];"
                    f"{audio_label}atrim=0:end={s},asetpts=PTS-STARTPTS[apre{filter_index}];"
                    f"{audio_label}atrim=start={e},asetpts=PTS-STARTPTS[apost{filter_index}];"
                    f"[apre{filter_index}][apost{filter_index}]concat=n=2:v=0:a=1[{out_a}]"
                )
                video_label = f"[{out_v}]"
                audio_label = f"[{out_a}]"

            elif op.type == "replace_audio":
                audio_label = audio_input_labels[audio_idx]
                audio_idx += 1

            elif op.type == "add_background_music":
                bg = audio_input_labels[audio_idx]
                audio_idx += 1
                vol = float(p.get("volume", 0.5))
                filter_parts.append(
                    f"{audio_label}volume=1.0[ao{filter_index}];"
                    f"{bg}volume={vol}[bg{filter_index}];"
                    f"[ao{filter_index}][bg{filter_index}]amix=inputs=2:duration=first[{out_a}]"
                )
                audio_label = f"[{out_a}]"

            elif op.type == "volume":
                level = float(p["level"])
                filter_parts.append(f"{audio_label}volume={level}[{out_a}]")
                audio_label = f"[{out_a}]"

            elif op.type == "speed":
                factor = float(p["factor"])
                filter_parts.append(
                    f"{video_label}setpts=PTS/{factor}[{out_v}];"
                    f"{audio_label}atempo={_atempo_chain(factor)}[{out_a}]"
                )
                video_label = f"[{out_v}]"
                audio_label = f"[{out_a}]"

            elif op.type == "resize":
                w = int(p["width"])
                h = int(p["height"])
                filter_parts.append(f"{video_label}scale={w}:{h}[{out_v}]")
                video_label = f"[{out_v}]"

            elif op.type == "crop":
                w = int(p["width"])
                h = int(p["height"])
                x = int(p.get("x", 0))
                y = int(p.get("y", 0))
                filter_parts.append(f"{video_label}crop={w}:{h}:{x}:{y}[{out_v}]")
                video_label = f"[{out_v}]"

            elif op.type == "rotate":
                deg = int(p["degrees"])
                transpose = {90: 1, 180: 4, 270: 2}[deg]
                filter_parts.append(f"{video_label}transpose={transpose}[{out_v}]")
                video_label = f"[{out_v}]"

            elif op.type == "text_overlay":
                text = str(p["text"]).replace(":", "\\:").replace("'", "\\'")
                x = int(p.get("x", 10))
                y = int(p.get("y", 10))
                fontsize = int(p.get("fontsize", 24))
                color = str(p.get("color", "white"))
                draw = (
                    f"drawtext=text='{text}':x={x}:y={y}:fontsize={fontsize}"
                    f":fontcolor={color}:box=1:boxcolor=black@0.4"
                )
                filter_parts.append(f"{video_label}{draw}[{out_v}]")
                video_label = f"[{out_v}]"

            elif op.type == "fade":
                ftype = p.get("type", "in")
                dur = float(p.get("duration", 1.0))
                start = float(p.get("start", 0))
                if ftype == "in":
                    filter_parts.append(
                        f"{video_label}fade=t=in:st={start}:d={dur}[{out_v}]"
                    )
                else:
                    filter_parts.append(
                        f"{video_label}fade=t=out:st={start}:d={dur}[{out_v}]"
                    )
                video_label = f"[{out_v}]"

            elif op.type == "compress":
                # handled via output codec args
                pass

            filter_index += 1

        # Final mapping
        final_v = video_label if video_label != "[0:v]" else "[0:v]"
        final_a = audio_label if audio_label != "[0:a]" else "[0:a]"

        if filter_parts:
            args.extend(["-filter_complex", ";".join(filter_parts)])
            args.extend(["-map", final_v])
            if has_audio_replace or has_bg_music or any(o.type in ("volume", "speed", "trim", "cut", "remove_segment", "add_background_music") for o in plan.operations):
                args.extend(["-map", final_a])
        else:
            args.extend(["-map", "0:v", "-map", "0:a"])

        # Codec / quality
        crf = 23
        for o in plan.operations:
            if o.type == "compress":
                crf = int(o.parameters.get("crf", 28))
        args.extend(["-c:v", "libx264", "-crf", str(crf), "-preset", "medium", "-pix_fmt", "yuv420p"])
        args.extend(["-c:a", "aac", "-b:a", "128k"])
        args.extend(["-movflags", "+faststart"])
        args.append(str(output_path))
        return args

    def process(self, video_id: str, plan: EditingPlan, job_id: str) -> Path:
        src = video_path(self.user.id, video_id)
        if not src.exists():
            raise ProcessingError("Source video not found.")
        odir = output_dir(self.user.id)
        odir.mkdir(parents=True, exist_ok=True)
        output = odir / f"{job_id}.mp4"
        args = self.build_ffmpeg_args(src, output, plan)
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=1800,
                check=False,
            )
        except (subprocess.SubprocessError, OSError) as exc:
            raise ProcessingError(f"FFmpeg failed to start: {exc}") from exc
        if result.returncode != 0 or not output.exists():
            stderr_tail = (result.stderr or "")[-500:]
            raise ProcessingError(f"FFmpeg error. {stderr_tail}")
        return output


def _atempo_chain(factor: float) -> str:
    """atempo accepts 0.5-2.0; chain for larger ranges."""
    if 0.5 <= factor <= 2.0:
        return f"{factor}"
    parts: list[str] = []
    remaining = factor
    while remaining > 2.0:
        parts.append("2.0")
        remaining /= 2.0
    while remaining < 0.5:
        parts.append("0.5")
        remaining /= 0.5
    parts.append(f"{remaining}")
    return ",".join(f"atempo={p}" for p in parts)
