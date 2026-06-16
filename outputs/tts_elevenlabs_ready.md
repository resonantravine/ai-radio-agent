# ElevenLabs Ready: Why do some AI hosts sound like they really understand you?

Do not paste `production_script.md` into a single TTS voice. It contains speaker names, delivery notes, and production metadata for human review.

Use `tts_segments.json` for the real dual-host workflow:

1. Generate Host A lines with the Host A voice.
2. Generate Host B lines with the Host B voice.
3. Stitch the audio clips in segment order.
4. Render the full episode with `pause_after_ms` spacing.

## Host A Text

```text
It is eight in the morning. You are on the subway, headphones on. Yesterday you listened to an episode about AI startups, and one phrase kept coming up: long-term memory. Today, when you open your AI radio, it does not hand you generic tech news. It continues yesterday's question: why are AI companies competing over long-term memory?
So it is not as simple as knowing that I like tech news?
Let me ask the listener's question: isn't that just a regular recommendation algorithm? I clicked something, so it keeps pushing more of the same.
So a good AI host does not meet me from scratch every morning. It can move yesterday's conversation forward.
But if it remembers too much, doesn't that start to feel uncomfortable?
So understanding you is not a kind of mystery. It is a kind of restraint.
Before the subway doors open, maybe that is today's line to keep: sounding like it understands you is not about talking all the time. It is about knowing where to continue.
```

## Host B Text

```text
That moment matters. An AI host sounds like it understands you not just because the voice is natural, but because it knows where you left off yesterday and what you might still be thinking about today.
Right. That is only a label. A deeper kind of understanding is knowing how you like to enter a question. Maybe you do not want every AI headline. You care about why a product makes sense, what user need it answers, and how it differs from an ordinary tool.
A little, but not quite. Recommendation is often about behavior records: what you clicked, how long you stayed, what you skipped. Long-term memory is more like preserving a continuous line of thought: why you cared, where you last followed up, and how you prefer something to be explained.
Exactly. It is not just generating more content. It is reducing your filtering cost. On a morning commute, you do not want to explain again what you want to hear. It should already know that today's episode needs to be light, clear, but not shallow.
It can. That is why good memory should never feel like secretly remembering everything. It should be controllable, explainable, and deletable. You should know why it recommended something, and you should decide what should not be remembered.
Yes. The next generation of AI hosts may not be defined by how human the voice sounds, but by whether it can catch the question you had not finished yesterday, at the right moment.
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
