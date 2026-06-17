from __future__ import annotations

import argparse
import math
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


WIDTH = 1280
HEIGHT = 720
FPS = 15


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a simple audio-reactive portfolio video.")
    parser.add_argument("--audio", required=True, help="Input mp3/wav audio file.")
    parser.add_argument("--output", required=True, help="Output mp4 file.")
    parser.add_argument("--poster", default=None, help="Optional poster png output.")
    parser.add_argument("--title", default="Yoli's Midday Brief")
    parser.add_argument("--subtitle", default="Why AI memory matters now")
    parser.add_argument("--moment", default="Lunch")
    parser.add_argument("--operation", default="Compress + update")
    parser.add_argument("--accent", default="#ffb84d")
    parser.add_argument("--duration", type=float, default=None, help="Optional max duration in seconds.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    render_video(
        audio_path=Path(args.audio),
        output_path=Path(args.output),
        poster_path=Path(args.poster) if args.poster else None,
        title=args.title,
        subtitle=args.subtitle,
        moment=args.moment,
        operation=args.operation,
        accent=args.accent,
        max_duration=args.duration,
    )
    print(f"Saved video to {args.output}")
    if args.poster:
        print(f"Saved poster to {args.poster}")


def render_video(
    *,
    audio_path: Path,
    output_path: Path,
    poster_path: Path | None,
    title: str,
    subtitle: str,
    moment: str,
    operation: str,
    accent: str,
    max_duration: float | None,
) -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required to render video.")
    if not audio_path.exists():
        raise RuntimeError(f"Audio file not found: {audio_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if poster_path is not None:
        poster_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="ai-radio-video-") as tmp:
        wav_path = Path(tmp) / "audio.wav"
        convert_to_wav(audio_path, wav_path, max_duration=max_duration)
        samples, sample_rate, duration = load_mono_wav(wav_path)
        if max_duration is not None:
            duration = min(duration, max_duration)

        energies = frame_energies(samples, sample_rate, duration, FPS)
        frame_count = len(energies)
        ffmpeg = subprocess.Popen(
            [
                "ffmpeg",
                "-y",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "-s",
                f"{WIDTH}x{HEIGHT}",
                "-r",
                str(FPS),
                "-i",
                "-",
                "-i",
                str(audio_path),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                str(output_path),
            ],
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert ffmpeg.stdin is not None
        poster_image: Image.Image | None = None
        for index, energy in enumerate(energies):
            img = draw_frame(
                index=index,
                frame_count=frame_count,
                energy=energy,
                energies=energies,
                title=title,
                subtitle=subtitle,
                moment=moment,
                operation=operation,
                accent=accent,
            )
            if index == min(frame_count - 1, FPS * 2):
                poster_image = img.copy()
            ffmpeg.stdin.write(img.tobytes())
        ffmpeg.stdin.close()
        stderr = ffmpeg.stderr.read().decode("utf-8", errors="replace") if ffmpeg.stderr else ""
        code = ffmpeg.wait()
        if code != 0:
            raise RuntimeError(stderr.strip() or "ffmpeg video render failed")

        if poster_path is not None:
            (poster_image or draw_frame(
                index=0,
                frame_count=max(frame_count, 1),
                energy=0.2,
                energies=energies,
                title=title,
                subtitle=subtitle,
                moment=moment,
                operation=operation,
                accent=accent,
            )).save(poster_path)


def convert_to_wav(audio_path: Path, wav_path: Path, *, max_duration: float | None) -> None:
    command = ["ffmpeg", "-y", "-i", str(audio_path)]
    if max_duration is not None:
        command.extend(["-t", f"{max_duration:.3f}"])
    command.extend(["-ac", "1", "-ar", "22050", "-c:a", "pcm_s16le", str(wav_path)])
    run(command)


def load_mono_wav(wav_path: Path) -> tuple[np.ndarray, int, float]:
    with wave.open(str(wav_path), "rb") as wav:
        sample_rate = wav.getframerate()
        frames = wav.getnframes()
        raw = wav.readframes(frames)
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return samples, sample_rate, frames / sample_rate


def frame_energies(samples: np.ndarray, sample_rate: int, duration: float, fps: int) -> list[float]:
    frame_count = max(1, int(math.ceil(duration * fps)))
    window = max(1, int(sample_rate / fps))
    values = []
    for i in range(frame_count):
        start = i * window
        chunk = samples[start : start + window]
        if len(chunk) == 0:
            values.append(0.0)
            continue
        values.append(float(np.sqrt(np.mean(chunk * chunk))))
    high = np.percentile(values, 95) if values else 1.0
    high = max(float(high), 0.001)
    normalized = [min(1.0, v / high) for v in values]
    smoothed: list[float] = []
    previous = 0.0
    for value in normalized:
        previous = previous * 0.78 + value * 0.22
        smoothed.append(previous)
    return smoothed


def draw_frame(
    *,
    index: int,
    frame_count: int,
    energy: float,
    energies: list[float],
    title: str,
    subtitle: str,
    moment: str,
    operation: str,
    accent: str,
) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), "#101419")
    draw = ImageDraw.Draw(img)
    accent_rgb = hex_to_rgb(accent)

    for y in range(HEIGHT):
        blend = y / HEIGHT
        r = int(16 + blend * 18)
        g = int(20 + blend * 24)
        b = int(25 + blend * 18)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    pulse = 0.35 + energy * 0.65
    draw.rounded_rectangle((70, 62, WIDTH - 70, HEIGHT - 62), radius=36, outline=(55, 65, 72), width=2)
    draw.rounded_rectangle((92, 84, WIDTH - 92, HEIGHT - 84), radius=28, fill=(18, 23, 28))

    font_title = load_font(62)
    font_subtitle = load_font(34)
    font_small = load_font(24)
    font_tiny = load_font(19)

    draw.text((132, 126), title, font=font_title, fill=(246, 247, 240))
    draw.text((136, 202), subtitle, font=font_subtitle, fill=(190, 200, 202))

    pill = f"{moment.upper()} / {operation.upper()}"
    pill_w = int(draw.textlength(pill, font=font_small)) + 44
    draw.rounded_rectangle((136, 270, 136 + pill_w, 318), radius=24, fill=(*accent_rgb, 42), outline=accent_rgb, width=1)
    draw.text((158, 281), pill, font=font_tiny, fill=(252, 238, 214))

    draw_waveform(draw, energies, index, accent_rgb, pulse)
    draw_hosts(draw, energy, accent_rgb)

    progress = index / max(frame_count - 1, 1)
    draw.rounded_rectangle((136, 626, WIDTH - 136, 634), radius=4, fill=(44, 52, 58))
    draw.rounded_rectangle((136, 626, 136 + int((WIDTH - 272) * progress), 634), radius=4, fill=accent_rgb)
    draw.text((136, 656), "AI Radio Agent / generated script -> segmented TTS -> rendered episode", font=font_tiny, fill=(128, 140, 144))
    return img


def draw_waveform(draw: ImageDraw.ImageDraw, energies: list[float], index: int, accent_rgb: tuple[int, int, int], pulse: float) -> None:
    x0, y0, x1, y1 = 136, 372, WIDTH - 136, 520
    bars = 72
    bar_gap = 5
    bar_w = ((x1 - x0) - (bars - 1) * bar_gap) / bars
    for i in range(bars):
        source_index = max(0, min(len(energies) - 1, index - bars + i + 1))
        value = energies[source_index] if energies else 0.0
        height = 12 + value * (y1 - y0 - 14)
        x = x0 + i * (bar_w + bar_gap)
        cy = (y0 + y1) / 2
        alpha = 0.28 + (i / bars) * 0.72
        color = tuple(int(90 + (c - 90) * alpha * pulse) for c in accent_rgb)
        draw.rounded_rectangle((x, cy - height / 2, x + bar_w, cy + height / 2), radius=4, fill=color)


def draw_hosts(draw: ImageDraw.ImageDraw, energy: float, accent_rgb: tuple[int, int, int]) -> None:
    left = (WIDTH - 286, 144)
    right = (WIDTH - 188, 144)
    size_a = 42 + int(energy * 12)
    size_b = 38 + int((1 - min(energy, 0.8)) * 8)
    draw.ellipse((left[0] - size_a, left[1] - size_a, left[0] + size_a, left[1] + size_a), fill=accent_rgb)
    draw.ellipse((right[0] - size_b, right[1] - size_b, right[0] + size_b, right[1] + size_b), fill=(124, 190, 205))
    draw.text((WIDTH - 340, 214), "Host A", font=load_font(20), fill=(220, 226, 224))
    draw.text((WIDTH - 224, 214), "Host B", font=load_font(20), fill=(220, 226, 224))


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    cleaned = value.strip().lstrip("#")
    if len(cleaned) != 6:
        return (255, 184, 77)
    return tuple(int(cleaned[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def run(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Command failed")


if __name__ == "__main__":
    main()
