from ai_radio_agent.asr_transcribe import build_markdown, format_timestamp


def test_format_timestamp() -> None:
    assert format_timestamp(0) == "00:00.000"
    assert format_timestamp(65.5) == "01:05.500"
    assert format_timestamp(3661.25) == "01:01:01.250"


def test_build_markdown_includes_required_sections() -> None:
    result = {
        "audio_file": "final_ai_radio_episode_morning.mp3",
        "detected_language": "en",
        "language_probability": 0.98,
        "segments": [
            {
                "start": 0.0,
                "end": 2.5,
                "start_formatted": "00:00.000",
                "end_formatted": "00:02.500",
                "text": "Good morning.",
            }
        ],
        "full_transcript": "Good morning.",
    }

    markdown = build_markdown(result)

    assert "final_ai_radio_episode_morning.mp3" in markdown
    assert "Detected language" in markdown
    assert "Timestamped segments" in markdown
    assert "Full transcript" in markdown
    assert "Good morning." in markdown
    assert "tts_segments.json" in markdown
