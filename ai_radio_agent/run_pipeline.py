from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> bool:
        return False

from ai_radio_agent.agents import AGENT_ORDER, run_agent
from ai_radio_agent.json_utils import write_json
from ai_radio_agent.providers import get_provider
from ai_radio_agent.schemas import PersonaNotes, QualityEvaluation, TTSExport


LOGGER = logging.getLogger("ai_radio_agent")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the AI Radio Agent pipeline.")
    parser.add_argument("--mock", action="store_true", help="Run with the built-in mock provider.")
    parser.add_argument("--provider", choices=["mock", "openai", "gemini"], help="Override LLM_PROVIDER.")
    parser.add_argument("--output-dir", default=None, help="Where generated artifacts should be saved.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_pipeline(
        provider_name="mock" if args.mock else args.provider,
        output_dir=Path(args.output_dir) if args.output_dir else None,
    )


def run_pipeline(provider_name: str | None = None, output_dir: Path | None = None) -> dict[str, Any]:
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    provider = get_provider(provider_name)
    target_dir = output_dir or Path(os.getenv("OUTPUT_DIR", "outputs"))
    target_dir.mkdir(parents=True, exist_ok=True)

    LOGGER.info("Running AI radio pipeline with provider=%s", provider.name)
    context: dict[str, Any] = {
        "project_goal": "Create a personalized AI radio episode script for an audio content generation portfolio demo.",
        "listener_experience_rule": (
            "The listener should hear a natural two-host radio conversation, not an explanation of the internal agent pipeline. "
            "Do not mention names like User Preference Agent, Memory Agent, Recommendation Agent, or TTS Export in dialogue text. "
            "Those names are only for portfolio artifacts such as production_script.md and README."
        ),
    }
    results: dict[str, Any] = {}

    for agent_name in AGENT_ORDER:
        LOGGER.info("Running %s", agent_name)
        result = run_agent(
            agent_name=agent_name,
            provider=provider,
            context=context,
            output_dir=target_dir,
        )
        payload = result.model_dump()
        context[agent_name] = payload
        results[agent_name] = payload

    write_tts_exports(
        output_dir=target_dir,
        persona=PersonaNotes.model_validate(results["persona_agent"]),
        quality=QualityEvaluation.model_validate(results["quality_evaluator"]),
        legacy_export=TTSExport.model_validate(results["tts_export"]),
    )
    write_json(target_dir / "00_pipeline_manifest.json", {"provider": provider.name, "files": sorted(p.name for p in target_dir.glob("*.json"))})
    LOGGER.info("Done. Main TTS test file: %s", target_dir / "tts_clean_single_voice.txt")
    return results


def write_tts_exports(
    *,
    output_dir: Path,
    persona: PersonaNotes,
    quality: QualityEvaluation,
    legacy_export: TTSExport,
) -> None:
    title = legacy_export.episode_title
    voice_key_by_host = {"Host A": "host_a", "Host B": "host_b"}

    segments = [
        {
            "speaker": line.host,
            "voice_key": voice_key_by_host[line.host],
            "text": line.line,
            "delivery_note": persona.host_a_persona if line.host == "Host A" else persona.host_b_persona,
            "pause_after_ms": 900,
        }
        for line in persona.revised_lines
    ]

    production_script = build_production_script(
        title=title,
        persona=persona,
        quality=quality,
        segments=segments,
        voice_notes=legacy_export.voice_notes,
    )
    clean_text = "\n\n".join(segment["text"] for segment in segments) + "\n"

    (output_dir / "production_script.md").write_text(production_script, encoding="utf-8")
    write_json(output_dir / "tts_segments.json", {"episode_title": title, "segments": segments})
    (output_dir / "tts_clean_single_voice.txt").write_text(clean_text, encoding="utf-8")
    (output_dir / "08_tts_input.txt").write_text(clean_text, encoding="utf-8")
    (output_dir / "tts_elevenlabs_ready.md").write_text(
        build_elevenlabs_ready_doc(title=title, segments=segments),
        encoding="utf-8",
    )


def build_production_script(
    *,
    title: str,
    persona: PersonaNotes,
    quality: QualityEvaluation,
    segments: list[dict[str, Any]],
    voice_notes: list[str],
) -> str:
    lines = [
        f"# {title}",
        "",
        "## Host Personas",
        "",
        f"- Host A: {persona.host_a_persona}",
        f"- Host B: {persona.host_b_persona}",
        "",
        "## Style Rules",
        "",
    ]
    lines.extend(f"- {rule}" for rule in persona.style_rules)
    lines.extend(["", "## Production Dialogue", ""])
    for segment in segments:
        lines.append(f"**{segment['speaker']}** ({segment['delivery_note']})")
        lines.append("")
        lines.append(segment["text"])
        lines.append("")
        lines.append(f"_Pause after: {segment['pause_after_ms']} ms_")
        lines.append("")
    lines.extend(["## Voice Notes", ""])
    lines.extend(f"- {note}" for note in voice_notes)
    lines.extend(["", "## Quality Evaluation", ""])
    lines.append(f"- Score: {quality.score}/10")
    lines.append(f"- Ready for TTS: {quality.ready_for_tts}")
    return "\n".join(lines).strip() + "\n"


def build_elevenlabs_ready_doc(*, title: str, segments: list[dict[str, Any]]) -> str:
    host_a_lines = [segment["text"] for segment in segments if segment["speaker"] == "Host A"]
    host_b_lines = [segment["text"] for segment in segments if segment["speaker"] == "Host B"]
    return f"""# ElevenLabs Ready: {title}

Do not paste `production_script.md` into a single TTS voice. It contains speaker names, delivery notes, and production metadata for human review.

Use `tts_segments.json` for the real dual-host workflow:

1. Generate Host A lines with the Host A voice.
2. Generate Host B lines with the Host B voice.
3. Stitch the audio clips in segment order.
4. Render the full episode with `pause_after_ms` spacing.

## Host A Text

```text
{chr(10).join(host_a_lines)}
```

## Host B Text

```text
{chr(10).join(host_b_lines)}
```

## Quick Single-Voice Test

For a fast proof of concept, use:

```bash
python -m ai_radio_agent.tts_elevenlabs --input outputs/tts_clean_single_voice.txt
```

This quick test removes speaker labels and delivery notes, but it will not sound like a true two-host conversation.

## Generate Separate Voice Clips

After setting `ELEVENLABS_HOST_A_VOICE_ID` and `ELEVENLABS_HOST_B_VOICE_ID` in `.env`, run:

```bash
python -m ai_radio_agent.tts_elevenlabs --segments outputs/tts_segments.json
```

This creates one mp3 per dialogue segment in:

```text
outputs/elevenlabs_segments/
```

Then stitch those clips together in filename order, inserting each segment's `pause_after_ms` as spacing.

## Render The Final Episode

After generating the ElevenLabs segments, run:

```bash
python -m ai_radio_agent.render_episode --segments outputs/tts_segments.json --audio-dir outputs/elevenlabs_segments --output outputs/final_ai_radio_episode.mp3
```

Final output:

```text
outputs/final_ai_radio_episode.mp3
outputs/final_episode_manifest.json
```
"""


if __name__ == "__main__":
    main()
