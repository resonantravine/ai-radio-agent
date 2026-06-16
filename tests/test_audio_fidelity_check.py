import json
from pathlib import Path

from ai_radio_agent.audio_fidelity_check import build_fidelity_report, build_markdown_report


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_audio_fidelity_report_passes_for_matching_transcript(tmp_path: Path) -> None:
    segments_path = tmp_path / "tts_segments.json"
    asr_path = tmp_path / "transcript_morning.json"
    write_json(
        segments_path,
        {
            "segments": [
                {
                    "speaker": "Host A",
                    "voice_key": "host_a",
                    "text": "Good morning, Yoli. Your morning coffee is ready.",
                },
                {
                    "speaker": "Host B",
                    "voice_key": "host_b",
                    "text": "Maybe we can think of it this way. Memory is a bookmark inside a conversation.",
                },
            ]
        },
    )
    write_json(
        asr_path,
        {
            "detected_language": "en",
            "language_probability": 0.98,
            "full_transcript": (
                "Good morning Yoli. Your morning coffee is ready. "
                "Maybe we can think of it this way. Memory is a bookmark inside a conversation."
            ),
        },
    )

    report = build_fidelity_report(
        segments_path=segments_path,
        asr_path=asr_path,
        expected_language="en",
    )

    assert report["ready_for_publish"] is True
    assert report["text_coverage"]["status"] == "pass"
    assert report["label_leakage"]["status"] == "pass"
    assert report["missing_segments"]["status"] == "pass"


def test_audio_fidelity_report_blocks_label_leakage(tmp_path: Path) -> None:
    segments_path = tmp_path / "tts_segments.json"
    asr_path = tmp_path / "transcript_morning.json"
    write_json(
        segments_path,
        {"segments": [{"speaker": "Host A", "text": "Good morning, Yoli."}]},
    )
    write_json(
        asr_path,
        {
            "detected_language": "en",
            "language_probability": 0.99,
            "full_transcript": "Host A colon Good morning Yoli pause after five hundred milliseconds.",
        },
    )

    report = build_fidelity_report(
        segments_path=segments_path,
        asr_path=asr_path,
        expected_language="en",
    )

    assert report["ready_for_publish"] is False
    assert "label_leakage_detected" in report["blocking_issues"]
    assert "Host A" in report["label_leakage"]["matches"]
    assert "Pause" in report["label_leakage"]["matches"]


def test_audio_fidelity_report_blocks_major_missing_segment(tmp_path: Path) -> None:
    segments_path = tmp_path / "tts_segments.json"
    asr_path = tmp_path / "transcript_morning.json"
    write_json(
        segments_path,
        {
            "segments": [
                {
                    "speaker": "Host A",
                    "text": "Yesterday's episode about AI startups left one small question on the table.",
                },
                {
                    "speaker": "Host B",
                    "text": "Long-term memory is like a bookmark inside an ongoing conversation.",
                },
            ]
        },
    )
    write_json(
        asr_path,
        {
            "detected_language": "en",
            "language_probability": 0.98,
            "full_transcript": "Yesterday's episode about AI startups left one small question on the table.",
        },
    )

    report = build_fidelity_report(
        segments_path=segments_path,
        asr_path=asr_path,
        expected_language="en",
    )
    markdown = build_markdown_report(report)

    assert report["ready_for_publish"] is False
    assert "major_segment_missing" in report["blocking_issues"]
    assert report["missing_segments"]["segments"][0]["severity"] == "major"
    assert "Audio Fidelity Report" in markdown
    assert "Low-Confidence Segments" in markdown
