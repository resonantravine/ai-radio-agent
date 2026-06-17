from __future__ import annotations

import argparse
import json
import re
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
    parser.add_argument("--live-sfx-dir", default=None, help="Optional breakfast live texture SFX directory.")
    parser.add_argument("--midday-sfx-dir", default=None, help="Optional Yoli's Midday Brief music and SFX directory.")
    parser.add_argument("--outro-audio", default=None, help="Optional soft outro music bed.")
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
            live_sfx_dir=Path(args.live_sfx_dir) if args.live_sfx_dir else None,
            midday_sfx_dir=Path(args.midday_sfx_dir) if args.midday_sfx_dir else None,
            outro_audio_path=Path(args.outro_audio) if args.outro_audio else None,
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
    live_sfx_dir: Path | None = None,
    midday_sfx_dir: Path | None = None,
    outro_audio_path: Path | None = None,
) -> dict[str, Any]:
    ensure_file_exists(segments_path, "TTS segments")
    episode_data = json.loads(segments_path.read_text(encoding="utf-8"))
    segments = episode_data.get("segments", [])
    if not segments:
        raise RuntimeError(f"No segments found in {segments_path}")

    check_ffmpeg()
    if shutil.which("ffprobe") is None or live_sfx_dir is not None or midday_sfx_dir is not None or outro_audio_path is not None:
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
            live_sfx_dir=live_sfx_dir,
            midday_sfx_dir=midday_sfx_dir,
            outro_audio_path=outro_audio_path,
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
    live_sfx_dir: Path | None,
    midday_sfx_dir: Path | None,
    outro_audio_path: Path | None,
) -> dict[str, Any]:
    if intro_audio_path is not None:
        ensure_file_exists(intro_audio_path, "Intro audio")
    if live_sfx_dir is not None and not live_sfx_dir.exists():
        raise RuntimeError(f"Live SFX directory not found: {live_sfx_dir}")
    if midday_sfx_dir is not None and not midday_sfx_dir.exists():
        raise RuntimeError(f"Midday SFX directory not found: {midday_sfx_dir}")
    if outro_audio_path is not None:
        ensure_file_exists(outro_audio_path, "Outro audio")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_segments: list[dict[str, Any]] = []
    current_ms = 0

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
            rendered_duration_ms = get_audio_duration_ms(normalized_path)

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
                    "start_ms": current_ms,
                    "end_ms": current_ms + rendered_duration_ms,
                    "rendered_duration_ms": rendered_duration_ms,
                    "pause_after_ms": pause_after_ms,
                    "normalization": "ffmpeg loudnorm",
                }
            )
            current_ms += rendered_duration_ms + pause_after_ms

        concat_list = tmp_dir / "concat.txt"
        concat_list.write_text(
            "\n".join(f"file '{escape_concat_path(path)}'" for path in concat_items) + "\n",
            encoding="utf-8",
        )
        needs_texture_mix = (
            intro_audio_path is not None
            or live_sfx_dir is not None
            or midday_sfx_dir is not None
            or outro_audio_path is not None
        )
        no_intro_output = tmp_dir / "episode_no_intro.mp3" if needs_texture_mix else output_path
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

        effective_voice_start_ms = voice_start_ms if intro_audio_path is not None else 0
        texture_events = build_texture_events(
            live_sfx_dir=live_sfx_dir,
            midday_sfx_dir=midday_sfx_dir,
            outro_audio_path=outro_audio_path,
            segments=manifest_segments,
            voice_start_ms=effective_voice_start_ms,
        )
        if needs_texture_mix:
            run_ffmpeg(
                build_ffmpeg_texture_mix_command(
                    episode_path=no_intro_output,
                    intro_audio_path=intro_audio_path,
                    output_path=output_path,
                    intro_gain_db=intro_gain_db,
                    intro_fade_ms=intro_fade_ms,
                    voice_start_ms=effective_voice_start_ms,
                    intro_total_ms=intro_total_ms,
                    events=texture_events,
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
        "voice_start_ms": effective_voice_start_ms if intro_audio_path else None,
        "live_sfx_dir": str(live_sfx_dir) if live_sfx_dir else None,
        "midday_sfx_dir": str(midday_sfx_dir) if midday_sfx_dir else None,
        "outro_audio": str(outro_audio_path) if outro_audio_path else None,
        "texture_events": [
            {key: str(value) if isinstance(value, Path) else value for key, value in event.items()}
            for event in texture_events
        ],
        "segments": manifest_segments,
    }
    manifest_path = output_path.with_name("final_episode_manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def run_ffmpeg(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffmpeg failed")


def build_ffmpeg_texture_mix_command(
    *,
    episode_path: Path,
    intro_audio_path: Path | None,
    output_path: Path,
    intro_gain_db: float,
    intro_fade_ms: int,
    voice_start_ms: int,
    intro_total_ms: int,
    events: list[dict[str, Any]],
) -> list[str]:
    inputs = [episode_path]
    if intro_audio_path is not None:
        inputs.append(intro_audio_path)
    inputs.extend(Path(event["path"]) for event in events)

    filter_parts = [f"[0:a]adelay={voice_start_ms}|{voice_start_ms}[voice]"]
    mix_labels = ["[voice]"]

    next_input_index = 1
    if intro_audio_path is not None:
        intro_label = f"bed{len(mix_labels)}"
        filter_parts.append(
            build_overlay_filter(
                input_index=next_input_index,
                label=intro_label,
                start_ms=0,
                gain_db=intro_gain_db,
                fade_in_ms=intro_fade_ms,
                fade_out_ms=intro_fade_ms,
                duration_ms=intro_total_ms,
            )
        )
        mix_labels.append(f"[{intro_label}]")
        next_input_index += 1

    for event in events:
        label = f"bed{len(mix_labels)}"
        filter_parts.append(
            build_overlay_filter(
                input_index=next_input_index,
                label=label,
                start_ms=int(event["start_ms"]),
                gain_db=float(event["gain_db"]),
                fade_in_ms=int(event.get("fade_in_ms", 250)),
                fade_out_ms=int(event.get("fade_out_ms", 700)),
                duration_ms=event.get("duration_ms"),
            )
        )
        mix_labels.append(f"[{label}]")
        next_input_index += 1

    filter_parts.append(
        "".join(mix_labels)
        + f"amix=inputs={len(mix_labels)}:duration=longest:dropout_transition=0:normalize=0,"
        + "loudnorm=I=-18:LRA=11:TP=-1.5[a]"
    )
    filter_complex = ";".join(filter_parts)

    command = ["ffmpeg", "-y"]
    for path in inputs:
        command.extend(["-i", str(path)])
    command.extend(
        [
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
    )
    return command


def build_overlay_filter(
    *,
    input_index: int,
    label: str,
    start_ms: int,
    gain_db: float,
    fade_in_ms: int,
    fade_out_ms: int,
    duration_ms: int | None,
) -> str:
    start_ms = max(0, start_ms)
    effects = []
    if duration_ms is not None:
        duration_sec = max(0.1, duration_ms / 1000)
        effects.append(f"atrim=0:{duration_sec:.3f}")
    effects.extend(["asetpts=PTS-STARTPTS", f"volume={gain_db}dB"])
    if fade_in_ms > 0:
        effects.append(f"afade=t=in:st=0:d={fade_in_ms / 1000:.3f}")
    if duration_ms is not None and fade_out_ms > 0:
        fade_out_start = max(0.0, (duration_ms - fade_out_ms) / 1000)
        effects.append(f"afade=t=out:st={fade_out_start:.3f}:d={fade_out_ms / 1000:.3f}")
    effects.append(f"adelay={start_ms}|{start_ms}")
    return f"[{input_index}:a]{','.join(effects)}[{label}]"


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
        "[voice][intro]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0,"
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


def build_texture_events(
    *,
    live_sfx_dir: Path | None,
    midday_sfx_dir: Path | None,
    outro_audio_path: Path | None,
    segments: list[dict[str, Any]],
    voice_start_ms: int,
) -> list[dict[str, Any]]:
    if midday_sfx_dir is not None:
        return build_midday_texture_events(
            midday_sfx_dir=midday_sfx_dir,
            outro_audio_path=outro_audio_path,
            segments=segments,
            voice_start_ms=voice_start_ms,
        )
    return build_breakfast_texture_events(
        live_sfx_dir=live_sfx_dir,
        outro_audio_path=outro_audio_path,
        segments=segments,
        voice_start_ms=voice_start_ms,
    )


def build_breakfast_texture_events(
    *,
    live_sfx_dir: Path | None,
    outro_audio_path: Path | None,
    segments: list[dict[str, Any]],
    voice_start_ms: int,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if live_sfx_dir is not None:
        files = {
            "room": live_sfx_dir / "01_morning_kitchen_room_tone_12s_soft.wav",
            "street": live_sfx_dir / "02_distant_window_street_waking_8s_soft.wav",
            "coffee": live_sfx_dir / "03_coffee_starting_to_bubble_4s_soft.wav",
            "kettle": live_sfx_dir / "04_kettle_soft_click_and_steam_2s_distant.wav",
            "cloth": live_sfx_dir / "05_host_small_cloth_movement_1s_subtle.wav",
            "toast": live_sfx_dir / "06_toast_on_plate_counter_touch_1p5s_soft.wav",
            "cup": live_sfx_dir / "07_ceramic_cup_spoon_transition_1p2s_alt.wav",
            "window": live_sfx_dir / "08_window_open_soft_air_shift_2p5s.wav",
        }
        for label, path in files.items():
            ensure_file_exists(path, f"Breakfast SFX {label}")

        host_b_kitchen = find_segment_by_text(segments, "Warm, a little messy")
        host_b_first = find_segment_by_text(segments, "Good morning. I'm already in the kitchen.")
        host_a_begin = find_segment_by_text(segments, "That sounds like exactly where we should begin.")
        host_a_ending = find_segment_by_text(segments, "That feels like a good place")
        host_b_coffee = find_segment_by_text(segments, "The coffee's still warm")
        host_a_thanks = find_segment_by_text(segments, "Thanks for spending breakfast")

        opening_room_start = max(0, voice_start_ms - 500)
        events.extend(
            [
                event(files["room"], opening_room_start, -18, "opening room tone", 12000, 1000, 2000),
                event(files["room"], opening_room_start + 10500, -20, "opening room tone extension", 12000, 800, 2000),
                event(files["cloth"], voice_start_ms + host_b_first["start_ms"] - 250, -12, "small cloth movement", 1000, 120, 350),
                event(files["toast"], voice_start_ms + host_b_kitchen["start_ms"] + 3000, -13, "toast counter touch", 1500, 200, 650),
                event(files["coffee"], voice_start_ms + host_b_kitchen["start_ms"] + 4300, -12, "coffee bubbling", 4000, 300, 900),
                event(files["window"], voice_start_ms + host_b_kitchen["start_ms"] + 7200, -14, "window air shift", 2500, 400, 1000),
                event(files["street"], voice_start_ms + host_b_kitchen["start_ms"] + 9100, -17, "distant street waking", 8000, 700, 1600),
                event(files["cup"], voice_start_ms + host_a_begin["start_ms"] - 650, -12, "opening cup transition", 1200, 100, 500),
                event(files["room"], voice_start_ms + host_a_ending["start_ms"] - 500, -22, "ending room tone", 12000, 900, 2500),
                event(files["kettle"], voice_start_ms + host_b_coffee["start_ms"] + 1100, -15, "ending kettle click and steam", 2000, 200, 900),
                event(files["cup"], voice_start_ms + host_a_thanks["start_ms"] - 550, -15, "ending cup transition", 1200, 100, 550),
            ]
        )

    if outro_audio_path is not None:
        ensure_file_exists(outro_audio_path, "Outro audio")
        host_a_until = find_segment_by_text(segments, "Until then, take it slow.")
        events.append(
            event(outro_audio_path, voice_start_ms + host_a_until["start_ms"] - 300, -9, "soft outro bed", 9000, 1200, 3500)
        )
    return events


def build_midday_texture_events(
    *,
    midday_sfx_dir: Path,
    outro_audio_path: Path | None,
    segments: list[dict[str, Any]],
    voice_start_ms: int,
) -> list[dict[str, Any]]:
    files = {
        "ambience": midday_sfx_dir / "amb_lunch_walk_45s.mp3",
        "boundary": midday_sfx_dir / "sfx_boundary_thin_bed_8s.mp3",
        "crosswalk": midday_sfx_dir / "sfx_distant_crosswalk.mp3",
        "lunch_board": midday_sfx_dir / "sfx_lunch_specials_board.mp3",
        "tabs": midday_sfx_dir / "sfx_soft_tab_closing_clicks.mp3",
        "main_bgm": midday_sfx_dir / "yoli_midday_main_bgm_loop_32s.mp3",
        "outro": outro_audio_path or midday_sfx_dir / "yoli_midday_outro_bed_12s.mp3",
        "outro_logo": midday_sfx_dir / "yoli_midday_sonic_logo_outro_3s.mp3",
    }
    for label, path in files.items():
        ensure_file_exists(path, f"Midday audio asset {label}")

    first_line = find_segment_by_text(segments, "It's Yoli's Midday Brief")
    main_start = find_segment_by_text(segments, "It's midday, Yoli.")
    lunch_board = find_optional_segment_by_text(segments, "A recommendation system is like the lunch specials board")
    crosswalk = find_optional_segment_by_text(segments, "Okay, give me the lunch-walk version")
    boundary = find_optional_segment_by_text(segments, "That sounds useful. Also")
    afternoon_takeaway = find_optional_segment_by_text(segments, "So this afternoon")
    tabs_outro = find_optional_segment_by_text(segments, "Take that one with you")
    final_logo = segments[-1]

    events: list[dict[str, Any]] = []

    # Very low ambience loops to keep the walk space alive without becoming foreground.
    for start in range(0, max(voice_start_ms + final_logo["end_ms"] + 2000, 45000), 43000):
        events.append(event(files["ambience"], start, -31, "midday lunch-walk ambience", 45000, 1200, 1800))

    # Low main BGM loops under the body of the brief.
    main_bgm_start = voice_start_ms + main_start["start_ms"] - 250
    body_end = voice_start_ms + (boundary or final_logo)["start_ms"]
    loop_start = max(0, main_bgm_start)
    while loop_start < body_end + 12000:
        events.append(event(files["main_bgm"], loop_start, -28, "midday main BGM loop", 32000, 700, 1200))
        loop_start += 30000

    events.extend(
        [
            event(files["tabs"], voice_start_ms + first_line["start_ms"] + 4200, -20, "intro tab closing clicks", 1200, 50, 400),
        ]
    )
    if lunch_board is not None:
        events.append(event(files["lunch_board"], voice_start_ms + lunch_board["start_ms"] - 450, -23, "lunch specials board cue", 1800, 120, 500))
    if crosswalk is not None:
        events.append(event(files["crosswalk"], voice_start_ms + crosswalk["start_ms"] + 900, -29, "distant crosswalk cue", 2000, 300, 900))
    if boundary is not None:
        events.append(event(files["boundary"], voice_start_ms + boundary["start_ms"] - 300, -24, "boundary thin bed", 8000, 700, 1200))
    outro_start_segment = tabs_outro or afternoon_takeaway
    if outro_start_segment is not None:
        outro_start_ms = max(0, voice_start_ms + outro_start_segment["start_ms"] - 250)
        events.append(
            event(files["outro"], outro_start_ms, -22, "midday outro bed", 8000, 900, 2600)
        )
    if tabs_outro is not None:
        events.append(event(files["tabs"], voice_start_ms + tabs_outro["start_ms"] + 4200, -32, "outro single tab click", 500, 40, 300))
    return events


def event(
    path: Path,
    start_ms: int,
    gain_db: float,
    description: str,
    duration_ms: int | None,
    fade_in_ms: int,
    fade_out_ms: int,
) -> dict[str, Any]:
    return {
        "path": path,
        "start_ms": max(0, int(start_ms)),
        "gain_db": gain_db,
        "description": description,
        "duration_ms": duration_ms,
        "fade_in_ms": fade_in_ms,
        "fade_out_ms": fade_out_ms,
    }


def find_segment_by_text(segments: list[dict[str, Any]], text_start: str) -> dict[str, Any]:
    for segment in segments:
        if str(segment.get("text", "")).startswith(text_start):
            return segment
    raise RuntimeError(f"Could not find segment starting with: {text_start}")


def find_optional_segment_by_text(segments: list[dict[str, Any]], text_start: str) -> dict[str, Any] | None:
    for segment in segments:
        if str(segment.get("text", "")).startswith(text_start):
            return segment
    return None


def get_audio_duration_ms(path: Path) -> int:
    result = subprocess.run(["ffmpeg", "-i", str(path)], capture_output=True, text=True)
    match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr)
    if not match:
        raise RuntimeError(f"Could not read audio duration for {path}")
    hours, minutes, seconds = match.groups()
    duration_sec = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    return int(round(duration_sec * 1000))


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
