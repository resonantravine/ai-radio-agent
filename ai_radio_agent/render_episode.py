from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


TARGET_DBFS = -18.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render ElevenLabs segments into a final AI radio episode.")
    parser.add_argument("--segments", default="outputs/tts_segments.json", help="Path to tts_segments.json.")
    parser.add_argument("--audio-dir", default="outputs/elevenlabs_segments", help="Directory containing segment mp3 files.")
    parser.add_argument("--output", default="outputs/final_ai_radio_episode.mp3", help="Final mp3 output path.")
    parser.add_argument("--wav-output", default=None, help="Optional final wav output path.")
    parser.add_argument("--target-dbfs", type=float, default=TARGET_DBFS, help="Simple loudness target for each segment.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        render_episode(
            segments_path=Path(args.segments),
            audio_dir=Path(args.audio_dir),
            output_path=Path(args.output),
            wav_output_path=Path(args.wav_output) if args.wav_output else None,
            target_dbfs=args.target_dbfs,
        )
        print(f"Saved final episode to {args.output}")
    except RuntimeError as exc:
        print(f"Episode render error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def render_episode(
    *,
    segments_path: Path,
    audio_dir: Path,
    output_path: Path,
    wav_output_path: Path | None = None,
    target_dbfs: float = TARGET_DBFS,
) -> dict[str, Any]:
    ensure_file_exists(segments_path, "TTS segments")
    episode_data = json.loads(segments_path.read_text(encoding="utf-8"))
    segments = episode_data.get("segments", [])
    if not segments:
        raise RuntimeError(f"No segments found in {segments_path}")

    check_ffmpeg()
    if shutil.which("ffprobe") is None:
        return render_with_ffmpeg_only(
            episode_data=episode_data,
            segments=segments,
            audio_dir=audio_dir,
            segments_path=segments_path,
            output_path=output_path,
            wav_output_path=wav_output_path,
            target_dbfs=target_dbfs,
        )

    try:
        from pydub import AudioSegment
    except ImportError as exc:
        raise RuntimeError(
            "Could not import pydub AudioSegment. Install/update dependencies with: "
            "python3 -m pip install -r requirements.txt. "
            f"Original import error: {exc}"
        ) from exc

    final_audio = AudioSegment.silent(duration=0)
    manifest_segments: list[dict[str, Any]] = []

    for index, segment in enumerate(segments, start=1):
        audio_path = find_segment_audio(audio_dir, index, segment)
        try:
            audio = AudioSegment.from_file(audio_path)
        except FileNotFoundError as exc:
            raise RuntimeError(
                "Could not load audio because ffmpeg/ffprobe is missing. "
                "On macOS, install it with: brew install ffmpeg"
            ) from exc
        normalized = normalize_audio(audio, target_dbfs=target_dbfs)
        pause_after_ms = int(segment.get("pause_after_ms", 500))

        final_audio += normalized
        final_audio += AudioSegment.silent(duration=pause_after_ms)

        manifest_segments.append(
            {
                "index": index,
                "speaker": segment.get("speaker"),
                "voice_key": segment.get("voice_key"),
                "text": segment.get("text"),
                "audio_file": str(audio_path),
                "source_duration_ms": len(audio),
                "rendered_duration_ms": len(normalized),
                "pause_after_ms": pause_after_ms,
                "source_dbfs": round(audio.dBFS, 2) if audio.dBFS != float("-inf") else None,
                "rendered_dbfs": round(normalized.dBFS, 2) if normalized.dBFS != float("-inf") else None,
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        final_audio.export(output_path, format="mp3")
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Could not export audio because ffmpeg is missing. "
            "On macOS, install it with: brew install ffmpeg"
        ) from exc
    if wav_output_path is not None:
        wav_output_path.parent.mkdir(parents=True, exist_ok=True)
        final_audio.export(wav_output_path, format="wav")

    manifest = {
        "episode_title": episode_data.get("episode_title", "AI Radio Episode"),
        "segments_path": str(segments_path),
        "audio_dir": str(audio_dir),
        "output_mp3": str(output_path),
        "output_wav": str(wav_output_path) if wav_output_path else None,
        "target_dbfs": target_dbfs,
        "total_duration_ms": len(final_audio),
        "segments": manifest_segments,
    }
    manifest_path = output_path.with_name("final_episode_manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def ensure_file_exists(path: Path, label: str) -> None:
    if path.exists():
        return
    raise RuntimeError(
        f"{label} file not found: {path}. Current directory: {Path.cwd()}. "
        "Run this command from the project root or use absolute paths. "
        "Project root: /Users/martaliu/Documents/Codex/2026-06-15/please-upgrade-this-ai-radio-agent"
    )


def check_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "Missing required audio tool: ffmpeg. Install ffmpeg, or use a Python distribution that includes it."
        )


def render_with_ffmpeg_only(
    *,
    episode_data: dict[str, Any],
    segments: list[dict[str, Any]],
    audio_dir: Path,
    segments_path: Path,
    output_path: Path,
    wav_output_path: Path | None,
    target_dbfs: float,
) -> dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_segments: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="ai-radio-render-") as tmp:
        tmp_dir = Path(tmp)
        concat_items: list[Path] = []

        for index, segment in enumerate(segments, start=1):
            audio_path = find_segment_audio(audio_dir, index, segment)
            normalized_path = tmp_dir / f"{index:02d}_normalized.wav"
            pause_path = tmp_dir / f"{index:02d}_pause.wav"
            pause_after_ms = int(segment.get("pause_after_ms", 500))

            run_ffmpeg(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(audio_path),
                    "-af",
                    f"loudnorm=I={target_dbfs}:LRA=11:TP=-1.5",
                    "-ar",
                    "44100",
                    "-ac",
                    "2",
                    str(normalized_path),
                ]
            )
            concat_items.append(normalized_path)

            if pause_after_ms > 0:
                run_ffmpeg(
                    [
                        "ffmpeg",
                        "-y",
                        "-f",
                        "lavfi",
                        "-i",
                        "anullsrc=channel_layout=stereo:sample_rate=44100",
                        "-t",
                        f"{pause_after_ms / 1000:.3f}",
                        str(pause_path),
                    ]
                )
                concat_items.append(pause_path)

            manifest_segments.append(
                {
                    "index": index,
                    "speaker": segment.get("speaker"),
                    "voice_key": segment.get("voice_key"),
                    "text": segment.get("text"),
                    "audio_file": str(audio_path),
                    "pause_after_ms": pause_after_ms,
                    "normalization": "ffmpeg loudnorm",
                }
            )

        concat_list = tmp_dir / "concat.txt"
        concat_list.write_text(
            "\n".join(f"file '{escape_concat_path(path)}'" for path in concat_items) + "\n",
            encoding="utf-8",
        )
        run_ffmpeg(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list),
                "-c:a",
                "libmp3lame",
                "-b:a",
                "192k",
                str(output_path),
            ]
        )
        if wav_output_path is not None:
            wav_output_path.parent.mkdir(parents=True, exist_ok=True)
            run_ffmpeg(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(concat_list),
                    "-c:a",
                    "pcm_s16le",
                    str(wav_output_path),
                ]
            )

    manifest = {
        "episode_title": episode_data.get("episode_title", "AI Radio Episode"),
        "segments_path": str(segments_path),
        "audio_dir": str(audio_dir),
        "output_mp3": str(output_path),
        "output_wav": str(wav_output_path) if wav_output_path else None,
        "target_dbfs": target_dbfs,
        "renderer": "ffmpeg-only",
        "note": "ffprobe was not found, so the renderer used an ffmpeg-only fallback.",
        "segments": manifest_segments,
    }
    manifest_path = output_path.with_name("final_episode_manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def run_ffmpeg(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffmpeg failed")


def escape_concat_path(path: Path) -> str:
    return str(path).replace("'", "'\\''")


def find_segment_audio(audio_dir: Path, index: int, segment: dict[str, Any]) -> Path:
    speaker_slug = str(segment.get("speaker", "")).lower().replace(" ", "_")
    expected = audio_dir / f"{index:02d}_{speaker_slug}.mp3"
    if expected.exists():
        return expected

    matches = sorted(audio_dir.glob(f"{index:02d}_*.mp3"))
    if matches:
        return matches[0]

    raise RuntimeError(
        f"Missing audio for segment {index}. Expected {expected}. "
        "Generate segments first with: python3 -m ai_radio_agent.tts_elevenlabs --segments outputs/tts_segments.json"
    )


def normalize_audio(audio: Any, *, target_dbfs: float) -> Any:
    if audio.dBFS == float("-inf"):
        return audio
    gain = target_dbfs - audio.dBFS
    return audio.apply_gain(gain)


if __name__ == "__main__":
    main()
