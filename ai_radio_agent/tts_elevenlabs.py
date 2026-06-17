from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> bool:
        return False

try:
    import certifi
except ImportError:
    certifi = None


DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
DEFAULT_MODEL_ID = "eleven_multilingual_v2"
DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"
DEFAULT_SEGMENT_VOICE_SETTINGS = {
    "host_a": {
        "stability": 0.72,
        "similarity_boost": 0.72,
        "style": 0.08,
        "use_speaker_boost": False,
        "speed": 0.90,
    },
    "host_b": {
        "stability": 0.68,
        "similarity_boost": 0.76,
        "style": 0.10,
        "use_speaker_boost": False,
        "speed": 0.93,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export AI radio script to ElevenLabs TTS audio.")
    parser.add_argument("--input", default="outputs/tts_clean_single_voice.txt", help="Clean TTS input text file.")
    parser.add_argument("--output", default="outputs/09_elevenlabs_audio.mp3", help="Output audio file.")
    parser.add_argument("--segments", default=None, help="Optional tts_segments.json for dual-host segment export.")
    parser.add_argument("--segments-output-dir", default="outputs/elevenlabs_segments", help="Directory for per-segment audio.")
    parser.add_argument("--overwrite-segments", action="store_true", help="Regenerate segment mp3 files even if they already exist.")
    parser.add_argument("--list-voices", action="store_true", help="List available ElevenLabs voices for this API key.")
    parser.add_argument("--voice-id", default=None, help="ElevenLabs voice ID. Defaults to ELEVENLABS_VOICE_ID.")
    parser.add_argument("--model-id", default=None, help="ElevenLabs model ID. Defaults to ELEVENLABS_MODEL_ID.")
    parser.add_argument("--output-format", default=None, help="ElevenLabs output format.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_dotenv()

    try:
        if args.list_voices:
            list_voices()
            return

        if args.segments:
            export_segments(
                segments_path=Path(args.segments),
                output_dir=Path(args.segments_output_dir),
                model_id=args.model_id or os.getenv("ELEVENLABS_MODEL_ID", DEFAULT_MODEL_ID),
                output_format=args.output_format or os.getenv("ELEVENLABS_OUTPUT_FORMAT", DEFAULT_OUTPUT_FORMAT),
                overwrite=args.overwrite_segments,
            )
            return

        input_path = Path(args.input)
        output_path = Path(args.output)
        text = input_path.read_text(encoding="utf-8")

        export_elevenlabs_audio(
            text=text,
            output_path=output_path,
            voice_id=args.voice_id or os.getenv("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID),
            model_id=args.model_id or os.getenv("ELEVENLABS_MODEL_ID", DEFAULT_MODEL_ID),
            output_format=args.output_format or os.getenv("ELEVENLABS_OUTPUT_FORMAT", DEFAULT_OUTPUT_FORMAT),
            voice_settings=resolve_voice_settings("single"),
        )
        print(f"Saved ElevenLabs audio to {output_path}")
    except (OSError, RuntimeError) as exc:
        print(f"ElevenLabs TTS error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def export_segments(
    *,
    segments_path: Path,
    output_dir: Path,
    model_id: str,
    output_format: str,
    overwrite: bool = False,
) -> None:
    ensure_file_exists(segments_path, "TTS segments")
    payload = json.loads(segments_path.read_text(encoding="utf-8"))
    segments = payload.get("segments", [])
    if not segments:
        raise RuntimeError(f"No segments found in {segments_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    for index, segment in enumerate(segments, start=1):
        speaker = segment["speaker"].lower().replace(" ", "_")
        voice_id = resolve_segment_voice(segment)
        voice_key = resolve_segment_voice_key(segment)
        output_path = output_dir / f"{index:02d}_{speaker}.mp3"
        if output_path.exists() and output_path.stat().st_size > 0 and not overwrite:
            print(f"Skipping existing {segment['speaker']} segment {index}: {output_path}")
            continue
        export_elevenlabs_audio(
            text=segment["text"],
            output_path=output_path,
            voice_id=voice_id,
            model_id=model_id,
            output_format=output_format,
            voice_settings=resolve_voice_settings(voice_key),
        )
        print(f"Saved {segment['speaker']} segment {index} with voice {voice_id} to {output_path}")


def ensure_file_exists(path: Path, label: str) -> None:
    if path.exists():
        return
    raise RuntimeError(
        f"{label} file not found: {path}. Current directory: {Path.cwd()}. "
        "Run the pipeline first from the project root, for example: "
        "cd /Users/martaliu/Documents/Codex/2026-06-15/please-upgrade-this-ai-radio-agent && "
        "python3 -m ai_radio_agent.run_pipeline --mock"
    )


def list_voices() -> None:
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("Missing ELEVENLABS_API_KEY. Add it to .env before listing voices.")

    request = urllib.request.Request(
        "https://api.elevenlabs.io/v1/voices",
        method="GET",
        headers={"xi-api-key": api_key},
    )
    try:
        context = build_ssl_context()
        with urllib.request.urlopen(request, timeout=60, context=context) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ElevenLabs voice list failed with HTTP {exc.code}: {detail}") from exc

    voices = payload.get("voices", [])
    if not voices:
        print("No voices returned by ElevenLabs.")
        return

    print("Available ElevenLabs voices:")
    for voice in voices:
        labels = voice.get("labels") or {}
        label_text = ", ".join(f"{key}={value}" for key, value in sorted(labels.items()))
        category = voice.get("category", "unknown")
        preview = voice.get("preview_url") or ""
        print(f"- {voice.get('name')} | id={voice.get('voice_id')} | category={category} | {label_text}")
        if preview:
            print(f"  preview={preview}")


def resolve_segment_voice(segment: dict[str, object]) -> str:
    speaker = str(segment.get("speaker", ""))
    voice_key = resolve_segment_voice_key(segment)
    voice = str(segment.get("voice_id_or_name", "")).strip()
    if voice and voice not in {"Host A voice", "Host B voice"}:
        return voice
    if voice_key == "host_a" or speaker == "Host A":
        return os.getenv("ELEVENLABS_HOST_A_VOICE_ID", DEFAULT_VOICE_ID)
    if voice_key == "host_b" or speaker == "Host B":
        return os.getenv("ELEVENLABS_HOST_B_VOICE_ID", os.getenv("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID))
    return os.getenv("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID)


def resolve_segment_voice_key(segment: dict[str, object]) -> str:
    speaker = str(segment.get("speaker", ""))
    voice_key = str(segment.get("voice_key", "")).strip()
    if voice_key:
        return voice_key
    if speaker == "Host A":
        return "host_a"
    if speaker == "Host B":
        return "host_b"
    return "single"


def resolve_voice_settings(voice_key: str) -> dict[str, object] | None:
    defaults = DEFAULT_SEGMENT_VOICE_SETTINGS.get(voice_key, {})
    prefix = "ELEVENLABS"
    if voice_key == "host_a":
        prefix = "ELEVENLABS_HOST_A"
    elif voice_key == "host_b":
        prefix = "ELEVENLABS_HOST_B"

    settings: dict[str, object] = dict(defaults)
    apply_float_setting(settings, "stability", os.getenv(f"{prefix}_STABILITY"))
    apply_float_setting(settings, "similarity_boost", os.getenv(f"{prefix}_SIMILARITY_BOOST"))
    apply_float_setting(settings, "style", os.getenv(f"{prefix}_STYLE"))
    apply_float_setting(settings, "speed", os.getenv(f"{prefix}_SPEED"))
    apply_bool_setting(settings, "use_speaker_boost", os.getenv(f"{prefix}_USE_SPEAKER_BOOST"))
    return settings or None


def apply_float_setting(settings: dict[str, object], key: str, raw_value: str | None) -> None:
    if raw_value is None or raw_value.strip() == "":
        return
    try:
        settings[key] = float(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"Invalid ElevenLabs voice setting {key}={raw_value!r}; expected a number.") from exc


def apply_bool_setting(settings: dict[str, object], key: str, raw_value: str | None) -> None:
    if raw_value is None or raw_value.strip() == "":
        return
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        settings[key] = True
        return
    if normalized in {"0", "false", "no", "off"}:
        settings[key] = False
        return
    raise RuntimeError(f"Invalid ElevenLabs voice setting {key}={raw_value!r}; expected true or false.")


def export_elevenlabs_audio(
    *,
    text: str,
    output_path: Path,
    voice_id: str,
    model_id: str,
    output_format: str,
    voice_settings: dict[str, object] | None = None,
) -> None:
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing ELEVENLABS_API_KEY. Add it to .env before running ElevenLabs TTS."
        )

    if not text.strip():
        raise RuntimeError("TTS input is empty. Run the pipeline first.")

    query = urllib.parse.urlencode({"output_format": output_format})
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?{query}"
    request_payload: dict[str, object] = {
        "text": text,
        "model_id": model_id,
    }
    if voice_settings:
        request_payload["voice_settings"] = voice_settings
    payload = json.dumps(request_payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
    )

    try:
        context = build_ssl_context()
        with urllib.request.urlopen(request, timeout=120, context=context) as response:
            audio = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ElevenLabs TTS failed with HTTP {exc.code}: {detail}") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(audio)


def build_ssl_context() -> ssl.SSLContext | None:
    if certifi is None:
        return None
    return ssl.create_default_context(cafile=certifi.where())


if __name__ == "__main__":
    main()
