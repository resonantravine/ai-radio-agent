from pathlib import Path
import json
import subprocess
import sys


EXPECTED_OUTPUTS = [
    "00_user_preference.json",
    "00_memory_state.json",
    "00_recommendation.json",
    "01_topic_plan.json",
    "02_research_brief.json",
    "03_fact_check.json",
    "04_script_outline.json",
    "05_dialogue_script.json",
    "06_persona_script.json",
    "07_quality_eval.json",
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

    segments = json.loads((outputs_dir / "tts_segments.json").read_text(encoding="utf-8"))
    first_segment = segments["segments"][0]
    assert set(first_segment) == {
        "speaker",
        "voice_key",
        "text",
        "delivery_note",
        "pause_after_ms",
    }
    assert first_segment["voice_key"] in {"host_a", "host_b"}
