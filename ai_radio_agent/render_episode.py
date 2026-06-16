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
    parser.add_argument("--intro-audio", default=None, help="Optional soft intro music or room-tone bed.")
    parser.add_argument("--intro-gain-db", type=float, default=-18.0, help="Gain applied to optional intro audio.")
    parser.add_argument("--intro-fade-ms", type=int, default=3000, help="Fade in/out duration for optional intro audio.")
    parser.add_argument("--voice-start-ms", type=int, default=3000, help="When the first voice starts if intro audio is used.")
    parser.add_argument("--intro-total-ms", type=int, default=13000, help="Total intro bed duration if intro audio is used.")
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
            intro_audio_path=Path(args.intro_audio) if args.intro_audio else None,
            intro_gain_db=args.intro_gain_db,
            intro_fade_ms=args.intro_fade_ms,
            voice_start_ms=args.voice_start_ms,
            intro_total_ms=args.intro_total_ms,
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
    intro_audio_path: Path | None = None,
    intro_gain_db: float = -18.0,
    intro_fade_ms: int = 3000,
    voice_start_ms: int = 3000,
    intro_total_ms: int = 13000,
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
            intro_audio_path=intro_audio_path,
            intro_gain_db=intro_gain_db,
            intro_fade_ms=intro_fade_ms,
            voice_start_ms=voice_start_ms,
            intro_total_ms=intro_total_ms,
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

    if intro_audio_path is not None:
        ensure_file_exists(intro_audio_path, "Intro audio")
        final_audio = apply_intro_audio(
            AudioSegment=AudioSegment,
            episode_audio=final_audio,
            intro_audio_path=intro_audio_path,
            gain_db=intro_gain_db,
            fade_ms=intro_fade_ms,
            voice_start_ms=voice_start_ms,
            intro_total_ms=intro_total_ms,
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
        "intro_audio": str(intro_audio_path) if intro_audio_path else None,
        "intro_gain_db": intro_gain_db if intro_audio_path else None,
        "voice_start_ms": voice_start_ms if intro_audio_path else None,
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
    intro_audio_path: Path | None,
    intro_gain_db: float,
    intro_fade_ms: int,
    voice_start_ms: int,
    intro_total_ms: int,
) -> dict[str, Any]:
    if intro_audio_path is not None:
        ensure_file_exists(intro_audio_path, "Intro audio")

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
        no_intro_output = tmp_dir / "episode_no_intro.mp3" if intro_audio_path else output_path
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
                str(no_intro_output),
            ]
        )

        if intro_audio_path is not None:
            run_ffmpeg(
                build_ffmpeg_intro_mix_command(
                    episode_path=no_intro_output,
                    intro_audio_path=intro_audio_path,
                    output_path=output_path,
                    intro_gain_db=intro_gain_db,
                    intro_fade_ms=intro_fade_ms,
                    voice_start_ms=voice_start_ms,
                    intro_total_ms=intro_total_ms,
                )
            )

        if wav_output_path is not None:
            wav_output_path.parent.mkdir(parents=True, exist_ok=True)
            if intro_audio_path is None:
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
            else:
                run_ffmpeg(["ffmpeg", "-y", "-i", str(output_path), "-c:a", "pcm_s16le", str(wav_output_path)])

    manifest = {
        "episode_title": episode_data.get("episode_title", "AI Radio Episode"),
        "segments_path": str(segments_path),
        "audio_dir": str(audio_dir),
        "output_mp3": str(output_path),
        "output_wav": str(wav_output_path) if wav_output_path else None,
        "target_dbfs": target_dbfs,
        "renderer": "ffmpeg-only",
        "note": "ffprobe was not found, so the renderer used an ffmpeg-only fallback.",
        "intro_audio": str(intro_audio_path) if intro_audio_path else None,
        "intro_gain_db": intro_gain_db if intro_audio_path else None,
        "voice_start_ms": voice_start_ms if intro_audio_path else None,
        "segments": manifest_segments,
    }
    manifest_path = output_path.with_name("final_episode_manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def run_ffmpeg(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffmpeg failed")


def build_ffmpeg_intro_mix_command(
    *,
    episode_path: Path,
    intro_audio_path: Path,
    output_path: Path,
    intro_gain_db: float,
    intro_fade_ms: int,
    voice_start_ms: int,
    intro_total_ms: int,
) -> list[str]:
    fade_sec = max(0.0, min(intro_fade_ms / 1000, intro_total_ms / 2000))
    total_sec = max(0.1, intro_total_ms / 1000)
    fade_out_start_sec = max(0.0, total_sec - fade_sec)
    filter_complex = (
        f"[0:a]adelay={voice_start_ms}|{voice_start_ms}[voice];"
        f"[1:a]atrim=0:{total_sec:.3f},asetpts=PTS-STARTPTS,"
        f"volume={intro_gain_db}dB,"
        f"afade=t=in:st=0:d={fade_sec:.3f},"
        f"afade=t=out:st={fade_out_start_sec:.3f}:d={fade_sec:.3f}[intro];"
        "[voice][intro]amix=inputs=2:duration=longest:dropout_transition=0,"
        "loudnorm=I=-18:LRA=11:TP=-1.5[a]"
    )
    return [
        "ffmpeg",
        "-y",
        "-i",
        str(episode_path),
        "-i",
        str(intro_audio_path),
        "-filter_complex",
        filter_complex,
        "-map",
        "[a]",
        "-c:a",
        "libmp3lame",
        "-b:a",
        "192k",
        str(output_path),
    ]


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


def apply_intro_audio(
    *,
    AudioSegment: Any,
    episode_audio: Any,
    intro_audio_path: Path,
    gain_db: float,
    fade_ms: int,
    voice_start_ms: int,
    intro_total_ms: int,
) -> Any:
    intro = AudioSegment.from_file(intro_audio_path)
    intro_bed = build_intro_bed(
        AudioSegment=AudioSegment,
        intro=intro,
        duration_ms=intro_total_ms,
        gain_db=gain_db,
        fade_ms=fade_ms,
    )
    episode_with_space = AudioSegment.silent(duration=voice_start_ms) + episode_audio
    return episode_with_space.overlay(intro_bed, position=0)


def build_intro_bed(
    *,
    AudioSegment: Any,
    intro: Any,
    duration_ms: int,
    gain_db: float,
    fade_ms: int,
) -> Any:
    if len(intro) == 0:
        return AudioSegment.silent(duration=duration_ms)

    bed = intro
    while len(bed) < duration_ms:
        bed += intro
    bed = bed[:duration_ms].apply_gain(gain_db)
    safe_fade_ms = max(0, min(fade_ms, duration_ms // 2))
    if safe_fade_ms:
        bed = bed.fade_in(safe_fade_ms).fade_out(safe_fade_ms)
    return bed


if __name__ == "__main__":
    main()
