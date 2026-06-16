# AI Radio Agent

A beginner-friendly portfolio demo for an **AI Agent Engineer | Audio Content Generation** role.

The project turns a user topic, memory context, profile, and target duration into a two-host AI radio episode.

In a real AI podcast product, the end user does **not** write Host A / Host B scripts. The scripts are internal generated artifacts used for quality control, TTS segmentation, persona consistency, and audio rendering.

```text
User Preference Agent
→ Memory Agent
→ Recommendation Agent
→ Episode Brief Agent
→ Segment Planner Agent
→ Topic Planner
→ Research / Fact Check
→ Broadcast Context Agent
→ Dialogue Planner Agent
→ Dialogue Writer
→ Persona Agent
→ TTS Segment Export
→ ElevenLabs Segment Generation
→ Audio Assembler / Episode Renderer
→ final_ai_radio_episode.mp3
```

Each agent produces a small JSON artifact in `outputs/`, so the workflow is easy to inspect, debug, and explain in an interview.

The listener hears a natural two-host radio episode. The interviewer can inspect the agent pipeline behind that episode.

The included mock episode is a breakfast-at-home morning sample: at 8:00 AM, the AI radio continues yesterday's AI startup episode by asking why AI companies are competing for long-term memory.

The sample show format is **Yoli's Morning Coffee**: a soft personal morning radio ritual that gives the listener a gentle greeting, reconnects with yesterday's unfinished thread, and offers one useful thought while breakfast is coming together.

The current dialogue prompts intentionally optimize for radio liveliness, not just correctness:

- Host A must include at least one lived reaction from the listener's point of view.
- Host B must use at least one concrete metaphor.
- Each episode should include one specific remembered detail from the previous listening session.

Sound direction:

- Calm but not sleepy.
- Personal but not overly intimate.
- Thoughtful but not academic.
- Warm but not sentimental.
- Clear but not over-explaining.
- Not a tech news anchor, productivity coach, marketing narrator, overly cheerful podcast host, or therapist.

## Why This Is A Good Audio Agent Demo

This project shows the core skills behind AI audio content generation:

- Personalized content planning from listener preferences and memory.
- Modular agent design instead of one giant prompt.
- Internal intermediate representations such as `episode_brief.json`, `segment_plan.json`, `dialogue_plan.json`, and `tts_segments.json`.
- Structured JSON outputs with Pydantic validation.
- A quality and fact-checking step before voice generation.
- A dialogue liveliness evaluation that checks response, tension, clarification, and emotional or experiential movement.
- Clean TTS handoff files that separate human production notes from machine-ready speech text.
- Dual-voice segment generation and final episode rendering.
- Multi-provider LLM support for mock, Gemini, and OpenAI.

## Setup

Use Python 3.10 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
cp .env.example .env
```

For final episode rendering and local ASR transcription on macOS, install ffmpeg:

```bash
brew install ffmpeg
```

The renderer needs both `ffmpeg` and `ffprobe`, which Homebrew's ffmpeg package normally installs together. `faster-whisper` also uses ffmpeg to decode mp3 and other audio files.

## Run In Mock Mode

Mock mode uses built-in deterministic responses. It does not require any API key.

```bash
python -m ai_radio_agent.run_pipeline --mock
```

You can also pass the user-facing product inputs directly:

```bash
python -m ai_radio_agent.run_pipeline --mock --topic "Why do some AI hosts sound like they really understand you?" --duration-minutes 2
```

Main outputs:

```text
outputs/production_script.md
outputs/episode_brief.json
outputs/segment_plan.json
outputs/tts_segments.json
outputs/tts_clean_single_voice.txt
outputs/tts_elevenlabs_ready.md
```

`production_script.md` is for human review. It includes speaker names, personas, delivery notes, and production metadata.

`episode_brief.json` and `segment_plan.json` show how the system turns a user-facing request into an internal episode structure. For a longer 10–20 minute product version, the segment planner would divide the show into multiple timed sections and generate each section separately instead of asking one prompt to produce a full long script.

`tts_segments.json` is the machine-friendly dual-host handoff. Each segment has:

- `speaker`
- `voice_key`
- `text`
- `delivery_note`
- `pause_after_ms`

`tts_clean_single_voice.txt` is only for quick testing with one voice. It removes speaker labels and delivery notes.

The episode content should sound like a radio program, not a portfolio explanation. For example, the hosts should talk naturally about personalized AI radio and listening habits. The agent names belong in `production_script.md`, README, and interview discussion, not in the audio text for a normal listener.

Structured artifacts:

```text
outputs/00_user_preference.json
outputs/00_user_episode_input.json
outputs/00_memory_state.json
outputs/00_recommendation.json
outputs/episode_brief.json
outputs/segment_plan.json
outputs/01_topic_plan.json
outputs/02_broadcast_context.json
outputs/03_research_brief.json
outputs/04_fact_check.json
outputs/05_script_outline.json
outputs/06_dialogue_plan.json
outputs/07_dialogue_script.json
outputs/08_persona_script.json
outputs/09_quality_eval.json
outputs/10_tts_export.json
```

The Host A / Host B files are not user-authored inputs. They are generated intermediate representations that make the pipeline inspectable and debuggable.

## Run With Gemini

Install Gemini support:

```bash
python3 -m pip install -r requirements-gemini.txt
```

Edit `.env`:

```bash
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
LLM_MODEL=gemini-3.1-flash-lite
```

Then run:

```bash
python -m ai_radio_agent.run_pipeline
```

`gemini-3.1-flash-lite` is the default in this project because Google lists Flash-Lite models as structured-output-capable and they are a good fit for low-cost text generation. If your account or region uses a different Flash or Flash-Lite model name, set `LLM_MODEL` in `.env`.

## Run With OpenAI

Install OpenAI support:

```bash
pip install -e '.[openai]'
```

Edit `.env`:

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key_here
LLM_MODEL=gpt-5.5
```

Then run:

```bash
python -m ai_radio_agent.run_pipeline
```

Use OpenAI mode only if you have API credits. You can replace `LLM_MODEL` with any lower-cost text model your account supports. Mock mode is best for demos, tests, and interviews where you want predictable output.

## JSON Reliability

Every agent is asked to return JSON matching a Pydantic schema.

The runner also:

- extracts JSON from plain text or fenced code blocks,
- validates the result with Pydantic,
- retries once if parsing or validation fails,
- logs the failing agent and error,
- saves raw failed model output under `outputs/debug/`.

This makes model failures visible instead of mysterious.

The quality evaluator includes `dialogue_liveliness_score`, which asks whether the episode feels like two hosts responding to each other, with some tension, clarification, and lived movement, instead of two voices reading adjacent paragraphs.

## TTS Is Optional

The pipeline stops at reviewable and TTS-ready files. TTS is a separate optional step.

You can add speech synthesis with:

- OpenAI TTS,
- ElevenLabs,
- Doubao,
- local macOS `say`,
- or any other voice provider.

TTS is intentionally not required because the portfolio goal is to show the content-generation agent workflow first.

Important: do not paste a dual-host production script directly into one TTS voice. It may read labels like `Host A` or delivery notes aloud. Use `tts_segments.json` for a real two-voice workflow, or `tts_clean_single_voice.txt` only for a quick single-voice test.

### ElevenLabs TTS

ElevenLabs TTS is implemented as a separate optional command. First run the pipeline:

```bash
python -m ai_radio_agent.run_pipeline --mock
```

Then add your ElevenLabs key to `.env`:

```env
ELEVENLABS_API_KEY=your_key_here
ELEVENLABS_VOICE_ID=JBFqnCBsd6RMkjVDRZzb
ELEVENLABS_HOST_A_VOICE_ID=JBFqnCBsd6RMkjVDRZzb
ELEVENLABS_HOST_B_VOICE_ID=EXAVITQu4vr4xnSDxMaL
ELEVENLABS_MODEL_ID=eleven_multilingual_v2
ELEVENLABS_OUTPUT_FORMAT=mp3_44100_128

ELEVENLABS_HOST_A_STABILITY=0.72
ELEVENLABS_HOST_A_SIMILARITY_BOOST=0.72
ELEVENLABS_HOST_A_STYLE=0.08
ELEVENLABS_HOST_A_USE_SPEAKER_BOOST=false
ELEVENLABS_HOST_A_SPEED=0.90

ELEVENLABS_HOST_B_STABILITY=0.68
ELEVENLABS_HOST_B_SIMILARITY_BOOST=0.76
ELEVENLABS_HOST_B_STYLE=0.10
ELEVENLABS_HOST_B_USE_SPEAKER_BOOST=false
ELEVENLABS_HOST_B_SPEED=0.93
```

For a two-host show, choose voices that are obviously different, for example one male-coded voice and one female-coded voice. List the voices available to your account:

```bash
python -m ai_radio_agent.tts_elevenlabs --list-voices
```

Then copy two different voice IDs into `ELEVENLABS_HOST_A_VOICE_ID` and `ELEVENLABS_HOST_B_VOICE_ID`.

The voice ID controls who is speaking. The `voice_settings` values control how that voice speaks for this request. The defaults above aim for a softer morning-radio delivery: slightly slower, less boosted, stable, and not too performative. You can A/B test by changing only these `.env` values.

Export a quick single-voice audio test:

```bash
python -m ai_radio_agent.tts_elevenlabs
```

Default output:

```text
outputs/09_elevenlabs_audio.mp3
```

This command reads `outputs/tts_clean_single_voice.txt` by default. It is useful for checking pacing and pronunciation, but it is not the final two-host workflow.

For true dual-host audio, use `outputs/tts_segments.json`:

1. Generate each Host A segment with `ELEVENLABS_HOST_A_VOICE_ID`.
2. Generate each Host B segment with `ELEVENLABS_HOST_B_VOICE_ID`.
3. Render the clips in segment order.
4. Insert each segment's `pause_after_ms` between clips.

You can generate separate Host A / Host B clips with:

```bash
python -m ai_radio_agent.tts_elevenlabs --segments outputs/tts_segments.json
```

This writes one mp3 per dialogue segment to:

```text
outputs/elevenlabs_segments/
```

See `outputs/tts_elevenlabs_ready.md` after running the pipeline. If ElevenLabs is unavailable or no API key is configured, the main agent pipeline still works.

### Render Final Episode

After generating ElevenLabs segments, render the complete two-host episode:

```bash
python -m ai_radio_agent.render_episode --segments outputs/tts_segments.json --audio-dir outputs/elevenlabs_segments --output outputs/final_ai_radio_episode.mp3
```

Optional soft intro music or room tone:

```bash
python -m ai_radio_agent.render_episode \
  --segments outputs/tts_segments.json \
  --audio-dir outputs/elevenlabs_segments \
  --output outputs/final_ai_radio_episode.mp3 \
  --intro-audio path/to/soft_intro.mp3
```

The intro bed fades in quietly, starts the first voice after about three seconds, then fades out. Keep intro audio subtle: 3-5 seconds of soft piano, ambient texture, room tone, or a tiny cup/spoon cue works better than a full podcast jingle.

Optional WAV export:

```bash
python -m ai_radio_agent.render_episode --segments outputs/tts_segments.json --audio-dir outputs/elevenlabs_segments --output outputs/final_ai_radio_episode.mp3 --wav-output outputs/final_ai_radio_episode.wav
```

Renderer outputs:

```text
outputs/final_ai_radio_episode.mp3
outputs/final_ai_radio_episode.wav
outputs/final_episode_manifest.json
```

The renderer preserves segment order, normalizes segment loudness, inserts the configured pauses, and never reads speaker labels aloud because it uses only the generated mp3 clips.

### ASR transcript check

After rendering a final episode, you can transcribe the audio locally with `faster-whisper`. This step is a **quality check** for the rendered audio. It is **not** the original source of truth for the episode text.

The source of truth is still:

- `outputs/tts_segments.json` for machine-ready speech text
- `outputs/script.md` and `outputs/production_script.md` for human review

For generated TTS audio, compare the ASR transcript with `tts_segments.json` to detect:

- missing text
- wrong pronunciation
- accidental reading of speaker labels
- music or SFX interference

Example:

```bash
python3 -m ai_radio_agent.asr_transcribe \
  --audio outputs/final_ai_radio_episode_morning.mp3 \
  --output outputs/transcript_morning.md
```

Outputs:

```text
outputs/transcript_morning.md
outputs/transcript_morning.json
```

The markdown file includes the audio file name, detected language, timestamped segments, and a clean full transcript section. The JSON file contains the same data in a machine-friendly format for diffing or tooling.

Optional flags:

- `--model base` — Whisper model size (`tiny`, `base`, `small`, `medium`, `large-v3`, etc.)
- `--language en` — force a language instead of auto-detecting
- `--device auto` — use `cpu` or `cuda` if needed

The first run downloads the selected Whisper model. No OpenAI API key or paid ASR service is required.

## Test

```bash
pytest
```

The smoke test runs the full mock pipeline and verifies that the expected output files are created.

## Project Structure

```text
ai_radio_agent/
  agents.py        # agent order, prompts, validation, retry, debug logging
  providers.py     # LLMProvider, MockProvider, OpenAIProvider, GeminiProvider
  schemas.py       # Pydantic schemas for all agent artifacts
  json_utils.py    # robust JSON extraction helpers
  run_pipeline.py  # CLI entry point
  tts_elevenlabs.py # optional ElevenLabs single-voice or segmented export
  render_episode.py # audio assembler / final episode renderer
  asr_transcribe.py # optional local ASR quality check for rendered audio
tests/
  test_smoke.py
```

## Interview Talking Points

This demo maps directly to AI audio agent and prompt evaluation work:

- **Agent orchestration:** each step has a clear input, output, and responsibility.
- **Prompt engineering:** each agent is constrained to produce schema-valid artifacts.
- **Evaluation:** the quality evaluator checks readiness before TTS.
- **Dialogue quality:** `dialogue_liveliness_score` measures whether the hosts react, clarify, challenge, and move emotionally through the topic.
- **Reliability:** failed JSON is retried and saved for debugging.
- **Production mindset:** mock mode supports local testing while real providers support Gemini and OpenAI.
