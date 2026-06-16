from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

DEFAULT_MODEL = "base"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe AI radio episode audio with local ASR (faster-whisper)."
    )
    parser.add_argument(
        "--audio",
        required=True,
        help="Path to the episode audio file (for example outputs/final_ai_radio_episode_morning.mp3).",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path for the markdown transcript (for example outputs/transcript_morning.md).",
    )
    parser.add_argument(
        "--json-output",
        default=None,
        help="Optional JSON output path. Defaults to the markdown path with a .json extension.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Whisper model size: tiny, base, small, medium, large-v3, etc. Default: base.",
    )
    parser.add_argument(
        "--device",
        default="auto",
        help="Compute device: auto, cpu, or cuda. Default: auto.",
    )
    parser.add_argument(
        "--language",
        default=None,
        help="Optional language code (for example en). Auto-detect if omitted.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    audio_path = Path(args.audio)
    markdown_path = Path(args.output)
    json_path = Path(args.json_output) if args.json_output else markdown_path.with_suffix(".json")

    try:
        result = transcribe_audio(
            audio_path=audio_path,
            model_name=args.model,
            device=args.device,
            language=args.language,
        )
    except RuntimeError as exc:
        print(f"ASR transcription error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    markdown_path.write_text(build_markdown(result), encoding="utf-8")
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Saved markdown transcript to {markdown_path}")
    print(f"Saved JSON transcript to {json_path}")
    if result.get("detected_language"):
        print(f"Detected language: {result['detected_language']}")


def transcribe_audio(
    *,
    audio_path: Path,
    model_name: str = DEFAULT_MODEL,
    device: str = "auto",
    language: str | None = None,
) -> dict[str, Any]:
    ensure_file_exists(audio_path, "Audio")
    check_ffmpeg()

    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "Missing faster-whisper. Install project dependencies with: python3 -m pip install -r requirements.txt"
        ) from exc

    print(f"Loading Whisper model '{model_name}' (this may take a moment the first time)...")
    model = WhisperModel(model_name, device=device)

    print(f"Transcribing {audio_path}...")
    segments_iter, info = model.transcribe(
        str(audio_path),
        language=language,
        vad_filter=True,
    )

    segments: list[dict[str, Any]] = []
    transcript_parts: list[str] = []
    for segment in segments_iter:
        text = segment.text.strip()
        if not text:
            continue
        segments.append(
            {
                "start": round(segment.start, 3),
                "end": round(segment.end, 3),
                "start_formatted": format_timestamp(segment.start),
                "end_formatted": format_timestamp(segment.end),
                "text": text,
            }
        )
        transcript_parts.append(text)

    detected_language = info.language if info.language else None
    language_probability = round(info.language_probability, 4) if info.language_probability else None

    return {
        "audio_file": audio_path.name,
        "audio_path": str(audio_path),
        "model": model_name,
        "detected_language": detected_language,
        "language_probability": language_probability,
        "segments": segments,
        "full_transcript": " ".join(transcript_parts).strip(),
    }


def build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# ASR Transcript",
        "",
        f"**Audio file:** {result['audio_file']}",
    ]

    if result.get("detected_language"):
        language_line = f"**Detected language:** {result['detected_language']}"
        if result.get("language_probability") is not None:
            probability_pct = round(result["language_probability"] * 100, 1)
            language_line += f" (confidence: {probability_pct}%)"
        lines.append(language_line)

    lines.extend(
        [
            "",
            "> ASR is a quality check for rendered audio. The source of truth is still `tts_segments.json`.",
            "",
            "## Timestamped segments",
            "",
        ]
    )

    if result["segments"]:
        for segment in result["segments"]:
            lines.append(
                f"[{segment['start_formatted']} → {segment['end_formatted']}] {segment['text']}"
            )
    else:
        lines.append("_No speech detected._")

    lines.extend(
        [
            "",
            "## Full transcript",
            "",
            result["full_transcript"] or "_No speech detected._",
            "",
        ]
    )
    return "\n".join(lines)


def format_timestamp(seconds: float) -> str:
    total_seconds = max(0.0, float(seconds))
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    secs = total_seconds % 60
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
    return f"{minutes:02d}:{secs:06.3f}"


def ensure_file_exists(path: Path, label: str) -> None:
    if path.exists():
        return
    raise RuntimeError(
        f"{label} file not found: {path}. Current directory: {Path.cwd()}. "
        "Run this command from the project root or use absolute paths."
    )


def check_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "Missing required audio tool: ffmpeg. Install it with: brew install ffmpeg"
        )


if __name__ == "__main__":
    main()
