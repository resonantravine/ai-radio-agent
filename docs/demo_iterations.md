# Demo Iterations

This project is best understood as an iterative audio agent prototype, not a one-shot generated podcast.

The final result, **Yoli's Morning Coffee**, came from several rounds of content, dialogue, TTS, and audio-rendering refinement. Each version shows a different product or engineering lesson.

## Recommended Demo Assets

The generated mp3 files are intentionally not committed to Git because audio files make the repository heavy. For a portfolio repo, upload the selected mp3 files as GitHub Release assets, then paste the release links into the table below.

Suggested release title:

```text
AI Radio Agent Demo Audio
```

Suggested release asset names:

| Stage | Release Asset Name | What It Shows |
| --- | --- | --- |
| 1. Early dual-host render | `01_basic_dual_host.mp3` | Basic two-voice pipeline: generated script, segmented TTS, assembled episode. Useful as the "before" sample. |
| 2. Dialogue liveliness pass | `02_dialogue_liveliness.mp3` | Better host interaction, more lived reaction, stronger metaphor, and clearer memory continuity. |
| 3. Soft morning identity | `03_morning_coffee_intro.mp3` | The show becomes **Yoli's Morning Coffee**, with a personal greeting and soft intro bed. |
| 4. Final live texture mix | `04_final_live_texture_mix.mp3` | Final portfolio sample: breakfast-at-home scene, dual voices, intro/outro music, subtle kitchen texture, and a more live radio feel. |

## Iteration Story

### 1. From Pipeline Demo To Listenability

The first working version proved the technical chain:

```text
topic and memory context
-> generated Host A / Host B script
-> tts_segments.json
-> ElevenLabs segment generation
-> audio assembly
-> final mp3
```

At this stage, the output worked technically, but it still felt like two AI voices taking turns reading a script. The content explained the project idea too directly, which was good for an interview artifact but not ideal for a normal listener.

### 2. From Explanation To Conversation

The next pass improved the dialogue layer:

- Host A had to express at least one lived reaction, not only ask questions.
- Host B had to use at least one concrete metaphor.
- The episode had to include one specific remembered detail from the previous listening session.
- The quality evaluator added `dialogue_liveliness_score`.

This moved the episode closer to a real two-host conversation. The important shift was not only better wording; it was a better intermediate representation: the pipeline now planned response, tension, clarification, and emotional movement before TTS.

### 3. From Generic AI Radio To A Show Identity

The project then moved from "AI podcast generation" toward a repeatable format:

```text
Yoli's Morning Coffee
```

The show identity is:

- calm but not sleepy,
- personal but not overly intimate,
- thoughtful but not academic,
- warm but not sentimental,
- clear but not over-explaining.

This is where the product started feeling less like "an AI generated a podcast" and more like "a personal morning audio ritual continued yesterday's unfinished thought."

### 4. From Clean TTS To Live Audio Space

The final pass added a restrained audio-rendering layer:

- intro bed,
- kitchen room tone,
- distant street texture,
- coffee bubbling,
- window air shift,
- cup/spoon transitions,
- soft outro bed.

These sounds are not part of the spoken script and are not sent to TTS. They are mixed by the renderer after voice generation. This keeps `tts_segments.json` clean while allowing the final episode to feel more live and spatial.

## Why This Matters For Audio Agent Work

This demo shows that AI audio products are not only about text generation or voice synthesis. A good audio agent pipeline needs several controllable layers:

- **Content planning:** What should this listener hear today?
- **Memory continuity:** What unfinished thread should the show continue?
- **Dialogue planning:** How do two hosts respond to each other naturally?
- **Persona control:** What should each host feel like across episodes?
- **TTS segmentation:** What should be sent to each voice, and what should never be read aloud?
- **Rendering:** How do timing, loudness, pauses, music, and texture shape the final listening experience?
- **Evaluation:** Is the result clear, natural, non-creepy, and ready for audio?

The portfolio point is that the host script is not a user-authored input. It is an internal generated artifact used to control quality, TTS, timing, and audio rendering.

## GitHub Release Checklist

Before publishing:

1. Run the mock pipeline and tests.
2. Generate the final ElevenLabs segments if needed.
3. Render the final live texture episode.
4. Create a GitHub Release named `AI Radio Agent Demo Audio`.
5. Upload the 3-4 selected mp3 files as release assets.
6. Add the release URL to the README demo section.

Useful local commands:

```bash
python3 -m ai_radio_agent.run_pipeline --mock
python3 -m pytest -q

python3 -m ai_radio_agent.tts_elevenlabs \
  --segments outputs/tts_segments.json \
  --segments-output-dir outputs/elevenlabs_segments_breakfast_live

python3 -m ai_radio_agent.render_episode \
  --segments outputs/tts_segments.json \
  --audio-dir outputs/elevenlabs_segments_breakfast_live \
  --output outputs/04_final_live_texture_mix.mp3 \
  --intro-audio outputs/audio_assets/yoli_morning_coffee_intro_bed.mp3 \
  --live-sfx-dir outputs/audio_assets/breakfast_live_sfx_pack \
  --outro-audio outputs/audio_assets/breakfast_soft_outro_bed_v1.mp3
```
