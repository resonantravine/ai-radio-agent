from __future__ import annotations

import argparse
import json
import re
import string
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

COVERAGE_BLOCK_THRESHOLD = 0.90
COVERAGE_WARNING_THRESHOLD = 0.95
SEGMENT_MAJOR_MISSING_THRESHOLD = 0.55
SEGMENT_WARNING_THRESHOLD = 0.70

LEAKAGE_PATTERNS = [
    ("Host A", re.compile(r"\bhost\s*a\b", re.IGNORECASE)),
    ("Host B", re.compile(r"\bhost\s*b\b", re.IGNORECASE)),
    ("Host label with colon", re.compile(r"\bhost\s*[ab]\s*:", re.IGNORECASE)),
    ("Pause", re.compile(r"\bpause\b", re.IGNORECASE)),
    ("pause after", re.compile(r"\bpause\s+after\b", re.IGNORECASE)),
    ("delivery note", re.compile(r"\bdelivery\s+note\b", re.IGNORECASE)),
    ("speaker", re.compile(r"\bspeaker\b", re.IGNORECASE)),
    ("voice key", re.compile(r"\bvoice\s+key\b", re.IGNORECASE)),
    ("tts segment", re.compile(r"\btts\s+segment\b", re.IGNORECASE)),
    ("json", re.compile(r"\bjson\b", re.IGNORECASE)),
    ("markdown", re.compile(r"\bmarkdown\b", re.IGNORECASE)),
    ("bracket", re.compile(r"\bbracket\b", re.IGNORECASE)),
]

PUNCTUATION_TRANSLATION = str.maketrans("", "", string.punctuation)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare rendered-audio ASR transcript with tts_segments.json."
    )
    parser.add_argument(
        "--segments",
        default="outputs/tts_segments.json",
        help="Path to tts_segments.json. Default: outputs/tts_segments.json",
    )
    parser.add_argument(
        "--asr",
        default=None,
        help="Path to ASR transcript JSON. Defaults to the newest outputs/transcript_*.json file.",
    )
    parser.add_argument(
        "--out-json",
        default="outputs/audio_fidelity_report.json",
        help="Path for JSON report. Default: outputs/audio_fidelity_report.json",
    )
    parser.add_argument(
        "--out-md",
        default="outputs/audio_fidelity_report.md",
        help="Path for Markdown report. Default: outputs/audio_fidelity_report.md",
    )
    parser.add_argument(
        "--expected-language",
        default="en",
        help="Expected ASR language code. Default: en",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    segments_path = Path(args.segments)
    asr_path = Path(args.asr) if args.asr else find_latest_asr_json(Path("outputs"))
    out_json_path = Path(args.out_json)
    out_md_path = Path(args.out_md)

    try:
        report = build_fidelity_report(
            segments_path=segments_path,
            asr_path=asr_path,
            expected_language=args.expected_language,
        )
    except RuntimeError as exc:
        print(f"Audio fidelity check error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    out_json_path.parent.mkdir(parents=True, exist_ok=True)
    out_md_path.parent.mkdir(parents=True, exist_ok=True)
    out_json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md_path.write_text(build_markdown_report(report), encoding="utf-8")

    print(f"Saved audio fidelity JSON report to {out_json_path}")
    print(f"Saved audio fidelity Markdown report to {out_md_path}")
    print(f"Ready for publish: {'Yes' if report['ready_for_publish'] else 'No'}")


def build_fidelity_report(
    *,
    segments_path: Path,
    asr_path: Path,
    expected_language: str = "en",
) -> dict[str, Any]:
    segments_data = load_json_file(segments_path, "TTS segments")
    asr_data = load_json_file(asr_path, "ASR transcript")
    segments = extract_tts_segments(segments_data)
    if not segments:
        raise RuntimeError(f"No TTS segments found in {segments_path}")

    expected_text = " ".join(segment["text"] for segment in segments).strip()
    observed_text = extract_asr_text(asr_data)
    if not observed_text:
        raise RuntimeError(f"No transcript text found in {asr_path}")

    text_coverage = check_text_coverage(expected_text, observed_text)
    label_leakage = check_label_leakage(observed_text)
    missing_segments = check_missing_segments(segments, observed_text)
    language = check_language(asr_data, expected_language)

    blocking_issues: list[str] = []
    warnings: list[str] = []

    if text_coverage["coverage_ratio"] < COVERAGE_BLOCK_THRESHOLD:
        blocking_issues.append("coverage_ratio_below_threshold")
    elif text_coverage["coverage_ratio"] < COVERAGE_WARNING_THRESHOLD:
        warnings.append("coverage_ratio_below_preferred_threshold")

    if label_leakage["status"] == "fail":
        blocking_issues.append("label_leakage_detected")

    major_missing = [
        segment for segment in missing_segments["segments"] if segment["severity"] == "major"
    ]
    minor_mismatch = [
        segment for segment in missing_segments["segments"] if segment["severity"] == "minor"
    ]
    if major_missing:
        blocking_issues.append("major_segment_missing")
    if minor_mismatch:
        warnings.append("one_or_more_segments_have_low_fuzzy_match")

    if language["status"] == "fail":
        blocking_issues.append("language_mismatch")
    elif language["status"] == "warning":
        warnings.append("language_mismatch_low_confidence")

    return {
        "source_of_truth": str(segments_path),
        "asr_probe": str(asr_path),
        "ready_for_publish": not blocking_issues,
        "blocking_issues": blocking_issues,
        "warnings": warnings,
        "text_coverage": text_coverage,
        "label_leakage": label_leakage,
        "missing_segments": missing_segments,
        "language": language,
    }


def load_json_file(path: Path, label: str) -> Any:
    if not path.exists():
        raise RuntimeError(
            f"{label} file not found: {path}. Run from the project root or pass an absolute path."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def find_latest_asr_json(outputs_dir: Path) -> Path:
    candidates = sorted(
        outputs_dir.glob("transcript_*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise RuntimeError(
            "No ASR transcript JSON found. Expected outputs/transcript_*.json or pass --asr."
        )
    return candidates[0]


def extract_tts_segments(data: Any) -> list[dict[str, Any]]:
    raw_segments = data.get("segments", []) if isinstance(data, dict) else data
    segments: list[dict[str, Any]] = []
    if not isinstance(raw_segments, list):
        return segments

    for index, segment in enumerate(raw_segments, start=1):
        if not isinstance(segment, dict):
            continue
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        segments.append(
            {
                "segment_id": segment.get("segment_id") or segment.get("id") or f"seg_{index:03d}",
                "speaker": segment.get("speaker") or segment.get("voice_key") or "unknown",
                "voice_key": segment.get("voice_key"),
                "text": text,
            }
        )
    return segments


def extract_asr_text(data: Any) -> str:
    if not isinstance(data, dict):
        return ""
    if data.get("full_transcript"):
        return str(data["full_transcript"]).strip()
    segments = data.get("segments", [])
    if isinstance(segments, list):
        return " ".join(
            str(segment.get("text", "")).strip()
            for segment in segments
            if isinstance(segment, dict) and segment.get("text")
        ).strip()
    return ""


def check_text_coverage(expected_text: str, observed_text: str) -> dict[str, Any]:
    expected_tokens = tokenize(expected_text)
    observed_tokens = tokenize(observed_text)
    expected_counts = Counter(expected_tokens)
    observed_counts = Counter(observed_tokens)
    covered_count = sum(
        min(count, observed_counts.get(token, 0)) for token, count in expected_counts.items()
    )
    coverage_ratio = covered_count / len(expected_tokens) if expected_tokens else 0.0

    if coverage_ratio < COVERAGE_BLOCK_THRESHOLD:
        status = "block_publish"
    elif coverage_ratio < COVERAGE_WARNING_THRESHOLD:
        status = "warning"
    else:
        status = "pass"

    return {
        "expected_word_count": len(expected_tokens),
        "asr_word_count": len(observed_tokens),
        "covered_word_count": covered_count,
        "coverage_ratio": round(coverage_ratio, 4),
        "status": status,
    }


def check_label_leakage(observed_text: str) -> dict[str, Any]:
    matches: list[str] = []
    for label, pattern in LEAKAGE_PATTERNS:
        if pattern.search(observed_text):
            matches.append(label)
    return {
        "status": "fail" if matches else "pass",
        "matches": matches,
    }


def check_missing_segments(
    segments: list[dict[str, Any]],
    observed_text: str,
) -> dict[str, Any]:
    observed_tokens = tokenize(observed_text)
    low_confidence_segments: list[dict[str, Any]] = []

    for segment in segments:
        segment_tokens = tokenize(segment["text"])
        match_score = segment_match_score(segment_tokens, observed_tokens)
        if match_score >= SEGMENT_WARNING_THRESHOLD:
            continue

        severity = "major" if (
            match_score < SEGMENT_MAJOR_MISSING_THRESHOLD and len(segment_tokens) >= 8
        ) else "minor"
        low_confidence_segments.append(
            {
                "segment_id": segment["segment_id"],
                "speaker": segment["speaker"],
                "voice_key": segment.get("voice_key"),
                "text": truncate(segment["text"], 180),
                "word_count": len(segment_tokens),
                "match_score": round(match_score, 4),
                "severity": severity,
            }
        )

    if any(segment["severity"] == "major" for segment in low_confidence_segments):
        status = "block_publish"
    elif low_confidence_segments:
        status = "warning"
    else:
        status = "pass"

    return {
        "status": status,
        "segments": low_confidence_segments,
    }


def check_language(asr_data: Any, expected_language: str) -> dict[str, Any]:
    detected = asr_data.get("detected_language") if isinstance(asr_data, dict) else None
    probability = asr_data.get("language_probability") if isinstance(asr_data, dict) else None
    if not detected:
        return {
            "status": "unknown",
            "expected_language": expected_language,
            "detected_language": None,
            "language_probability": None,
        }

    detected_normalized = str(detected).lower()
    expected_normalized = expected_language.lower()
    probability_value = float(probability) if isinstance(probability, (int, float)) else None
    matches = detected_normalized == expected_normalized

    if matches:
        status = "pass"
    elif probability_value is not None and probability_value >= 0.80:
        status = "fail"
    else:
        status = "warning"

    return {
        "status": status,
        "expected_language": expected_language,
        "detected_language": detected,
        "language_probability": probability_value,
    }


def normalize_text(text: str) -> str:
    normalized = text.lower()
    normalized = normalized.replace("’", "'").replace("‘", "'")
    normalized = normalized.replace("“", '"').replace("”", '"')
    normalized = normalized.translate(PUNCTUATION_TRANSLATION)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def tokenize(text: str) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []
    return normalized.split()


def segment_match_score(segment_tokens: list[str], observed_tokens: list[str]) -> float:
    if not segment_tokens or not observed_tokens:
        return 0.0

    segment_text = " ".join(segment_tokens)
    token_overlap_score = token_overlap(segment_tokens, observed_tokens)
    if len(segment_tokens) <= 5:
        return max(token_overlap_score, sequence_ratio(segment_text, " ".join(observed_tokens)))

    window_sizes = sorted(
        {
            max(1, int(len(segment_tokens) * 0.75)),
            len(segment_tokens),
            max(1, int(len(segment_tokens) * 1.25)),
        }
    )
    best_sequence_score = 0.0
    for window_size in window_sizes:
        step = max(1, window_size // 3)
        for start in range(0, max(1, len(observed_tokens) - window_size + 1), step):
            observed_window = observed_tokens[start : start + window_size]
            best_sequence_score = max(
                best_sequence_score,
                sequence_ratio(segment_text, " ".join(observed_window)),
            )

    return max(token_overlap_score, best_sequence_score)


def token_overlap(segment_tokens: list[str], observed_tokens: list[str]) -> float:
    segment_counts = Counter(segment_tokens)
    observed_counts = Counter(observed_tokens)
    covered_count = sum(
        min(count, observed_counts.get(token, 0)) for token, count in segment_counts.items()
    )
    return covered_count / len(segment_tokens) if segment_tokens else 0.0


def sequence_ratio(left: str, right: str) -> float:
    return SequenceMatcher(None, left, right).ratio()


def truncate(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 3].rstrip() + "..."


def build_markdown_report(report: dict[str, Any]) -> str:
    ready = "Yes" if report["ready_for_publish"] else "No"
    coverage = report["text_coverage"]
    leakage = report["label_leakage"]
    missing = report["missing_segments"]
    language = report["language"]

    lines = [
        "# Audio Fidelity Report",
        "",
        "## Verdict",
        "",
        f"Ready for publish: **{ready}**",
        "",
        "## Summary",
        "",
        "| Check | Status | Notes |",
        "|---|---|---|",
        (
            f"| Text coverage | {coverage['status']} | "
            f"{coverage['coverage_ratio']:.0%} coverage "
            f"({coverage['covered_word_count']}/{coverage['expected_word_count']} expected words) |"
        ),
        (
            f"| Label leakage | {leakage['status']} | "
            f"{', '.join(leakage['matches']) if leakage['matches'] else 'No blocked labels detected'} |"
        ),
        (
            f"| Missing segments | {missing['status']} | "
            f"{len(missing['segments'])} low-confidence segment(s) |"
        ),
        (
            f"| Language | {language['status']} | "
            f"expected {language['expected_language']}, detected {language.get('detected_language') or 'unknown'} |"
        ),
        "",
        "## Blocking Issues",
        "",
    ]

    if report["blocking_issues"]:
        lines.extend(f"- {issue}" for issue in report["blocking_issues"])
    else:
        lines.append("- None")

    lines.extend(["", "## Warnings", ""])
    if report["warnings"]:
        lines.extend(f"- {warning}" for warning in report["warnings"])
    else:
        lines.append("- None")

    if missing["segments"]:
        lines.extend(["", "## Low-Confidence Segments", ""])
        for segment in missing["segments"]:
            lines.append(
                f"- {segment['segment_id']} ({segment['speaker']}): "
                f"score {segment['match_score']:.2f}, {segment['severity']} — "
                f"{segment['text']}"
            )

    lines.extend(
        [
            "",
            "## Suggested Next Step",
            "",
            suggested_next_step(report),
            "",
            "## Notes",
            "",
            "`tts_segments.json` is the source of truth. The ASR transcript is a post-render quality probe, so low fuzzy scores should be reviewed before assuming the audio is wrong.",
            "",
        ]
    )
    return "\n".join(lines)


def suggested_next_step(report: dict[str, Any]) -> str:
    if "label_leakage_detected" in report["blocking_issues"]:
        return "Rebuild TTS from `tts_segments.json` and confirm production labels or delivery notes were not sent to the voice provider."
    if "coverage_ratio_below_threshold" in report["blocking_issues"]:
        return "Review the rendered audio and re-render any missing or truncated segments."
    if "major_segment_missing" in report["blocking_issues"]:
        return "Review the low-confidence segment list and regenerate the affected ElevenLabs clips."
    if report["warnings"]:
        return "Review the warnings and listen to the low-confidence areas before publishing."
    return "No action needed. The rendered audio appears faithful to the TTS segments."


if __name__ == "__main__":
    main()
