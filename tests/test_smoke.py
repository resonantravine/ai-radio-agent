from pathlib import Path
import json
import subprocess
import sys


EXPECTED_OUTPUTS = [
    "00_user_episode_input.json",
    "00_moment_profile.json",
    "00_user_preference.json",
    "00_memory_state.json",
    "00_recommendation.json",
    "episode_brief.json",
    "segment_plan.json",
    "01_topic_plan.json",
    "02_broadcast_context.json",
    "02_timely_context.json",
    "03_research_brief.json",
    "04_fact_check.json",
    "05_script_outline.json",
    "06_dialogue_plan.json",
    "07_dialogue_script.json",
    "08_persona_script.json",
    "09_quality_eval.json",
    "08_tts_input.txt",
    "production_script.md",
    "tts_segments.json",
    "tts_clean_single_voice.txt",
    "tts_elevenlabs_ready.md",
]


def test_mock_pipeline_creates_expected_outputs(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    outputs_dir = tmp_path / "outputs"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ai_radio_agent.run_pipeline",
            "--mock",
            "--output-dir",
            str(outputs_dir),
        ],
        cwd=project_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr

    for filename in EXPECTED_OUTPUTS:
        assert (outputs_dir / filename).exists(), f"Missing output file: {filename}"

    clean_tts = (outputs_dir / "tts_clean_single_voice.txt").read_text(encoding="utf-8")
    assert "Host A:" not in clean_tts
    assert "Host B:" not in clean_tts
    assert "Pause after" not in clean_tts
    assert "Agent" not in clean_tts
    assert "Memory Agent" not in clean_tts
    assert "Recommendation Agent" not in clean_tts
    assert "Good morning, Yoli." in clean_tts
    assert "Good morning. I'm already in the kitchen." in clean_tts
    assert "coffee starting to bubble" in clean_tts
    assert "someone just opened the window" in clean_tts
    assert "recommendation algorithm" in clean_tts
    assert "feel uncomfortable" in clean_tts
    assert "one small question on the table" in clean_tts
    assert "I feel that in the morning" in clean_tts
    assert "That feels like a good place to leave the morning." in clean_tts
    assert "The coffee's still warm" in clean_tts
    assert "Until then, take it slow." in clean_tts
    assert "subway" not in clean_tts.lower()
    assert "shop window" in clean_tts
    assert "bookmark inside an ongoing conversation" in clean_tts

    segments = json.loads((outputs_dir / "tts_segments.json").read_text(encoding="utf-8"))
    assert len(segments["segments"]) >= 12
    first_segment = segments["segments"][0]
    assert set(first_segment) == {
        "speaker",
        "voice_key",
        "text",
        "delivery_note",
        "pause_after_ms",
    }
    assert first_segment["voice_key"] in {"host_a", "host_b"}

    segment_plan = json.loads((outputs_dir / "segment_plan.json").read_text(encoding="utf-8"))
    assert segment_plan["episode_duration_minutes"] == 2
    assert len(segment_plan["segments"]) >= 3

    quality_eval = json.loads((outputs_dir / "09_quality_eval.json").read_text(encoding="utf-8"))
    assert quality_eval["dialogue_liveliness_score"] >= 8
    assert quality_eval["moment_fit_score"] >= 8
    assert quality_eval["content_operation"] == "continue"
    assert quality_eval["semantic_density"] == "low_to_medium"

    moment_profile = json.loads((outputs_dir / "00_moment_profile.json").read_text(encoding="utf-8"))
    assert moment_profile["moment"] == "breakfast"
    assert moment_profile["core_operation"] == "continue"

    timely_context = json.loads((outputs_dir / "02_timely_context.json").read_text(encoding="utf-8"))
    assert timely_context["freshness_required"] is False


def test_mock_lunch_pipeline_uses_midday_brief_sample(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    outputs_dir = tmp_path / "lunch_outputs"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ai_radio_agent.run_pipeline",
            "--mock",
            "--moment",
            "lunch",
            "--output-dir",
            str(outputs_dir),
        ],
        cwd=project_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr

    clean_tts = (outputs_dir / "tts_clean_single_voice.txt").read_text(encoding="utf-8")
    assert "It's Yoli's Midday Brief" in clean_tts
    assert "too many tabs open" in clean_tts
    assert "Let's close fourteen of them." in clean_tts
    assert "It's midday, Yoli. Quick brief for the lunch walk" in clean_tts
    assert "memory is the new onboarding layer" in clean_tts
    assert "lunch specials board" in clean_tts
    assert "Congratulations, you are noodle person forever." in clean_tts
    assert "a little too close to my business" in clean_tts
    assert "what would you want an AI to remember because it helps you continue?" in clean_tts
    assert "Both count." in clean_tts
    assert "Good morning, Yoli." not in clean_tts

    moment_profile = json.loads((outputs_dir / "00_moment_profile.json").read_text(encoding="utf-8"))
    assert moment_profile["moment"] == "lunch"
    assert moment_profile["core_operation"] == "compress"

    timely_context = json.loads((outputs_dir / "02_timely_context.json").read_text(encoding="utf-8"))
    assert timely_context["freshness_required"] is True

    quality_eval = json.loads((outputs_dir / "09_quality_eval.json").read_text(encoding="utf-8"))
    assert quality_eval["content_operation"] == "compress"
    assert quality_eval["semantic_density"] == "medium"


def test_elevenlabs_soft_voice_settings_can_be_overridden(monkeypatch) -> None:
    from ai_radio_agent.tts_elevenlabs import resolve_voice_settings

    host_a_settings = resolve_voice_settings("host_a")
    assert host_a_settings == {
        "stability": 0.72,
        "similarity_boost": 0.72,
        "style": 0.08,
        "use_speaker_boost": False,
        "speed": 0.90,
    }

    monkeypatch.setenv("ELEVENLABS_HOST_A_SPEED", "0.88")
    monkeypatch.setenv("ELEVENLABS_HOST_A_USE_SPEAKER_BOOST", "true")
    overridden = resolve_voice_settings("host_a")
    assert overridden["speed"] == 0.88
    assert overridden["use_speaker_boost"] is True


def test_elevenlabs_segment_export_skips_existing_files(tmp_path: Path, monkeypatch) -> None:
    from ai_radio_agent import tts_elevenlabs

    segments_path = tmp_path / "tts_segments.json"
    output_dir = tmp_path / "segments"
    output_dir.mkdir()
    existing = output_dir / "01_host_a.mp3"
    existing.write_bytes(b"existing audio")
    segments_path.write_text(
        json.dumps(
            {
                "episode_title": "Resume test",
                "segments": [
                    {
                        "speaker": "Host A",
                        "voice_key": "host_a",
                        "text": "Already generated.",
                        "pause_after_ms": 300,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    def fail_if_called(**_: object) -> None:
        raise AssertionError("Existing segment should not be regenerated")

    monkeypatch.setattr(tts_elevenlabs, "export_elevenlabs_audio", fail_if_called)
    tts_elevenlabs.export_segments(
        segments_path=segments_path,
        output_dir=output_dir,
        model_id="test-model",
        output_format="mp3_44100_128",
    )

    assert existing.read_bytes() == b"existing audio"
