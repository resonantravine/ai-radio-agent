# ElevenLabs Ready: Yoli's Morning Coffee: Why do some AI hosts sound like they really understand you?

Do not paste `production_script.md` into a single TTS voice. It contains speaker names, delivery notes, and production metadata for human review.

Use `tts_segments.json` for the real dual-host workflow:

1. Generate Host A lines with the Host A voice.
2. Generate Host B lines with the Host B voice.
3. Stitch the audio clips in segment order.
4. Render the full episode with `pause_after_ms` spacing.

## Host A Text

```text
Good morning, Yoli. Your morning coffee is ready. It is eight o'clock, you are on the subway, and yesterday's episode about AI startups left one detail on the table: a founder called memory the new onboarding layer for AI products. So today, instead of another piece of generic tech news, let's stay with that question for a few minutes.
I like that, but I am also a little unsure. Is this really more than knowing that I like tech news?
Let me ask the listener's question gently: isn't that just a regular recommendation algorithm? I clicked something, so it keeps pushing more of the same.
I feel that on a commute. Some mornings I do not want another feed to scroll. I want the show to pick up the thread before I lose it. So a good AI host does not meet me from scratch every morning; it moves yesterday's conversation forward.
But if it remembers too much, doesn't that start to feel uncomfortable?
So understanding you is not a kind of mystery. It is a kind of restraint.
Before the subway doors open, maybe that is today's first cup: sounding like it understands you is not about talking all the time. It is about knowing where to continue.
```

## Host B Text

```text
Maybe we can think of it this way. An AI host starts to feel personal when it remembers where the conversation paused, not when it rushes to sound impressive.
There is a small difference here. A topic label says you like AI. A softer kind of memory notices how you like to enter the question. Maybe you care less about every headline, and more about why a product makes sense in someone's day.
A little, but not quite. A recommendation feed is like a shop window: it rearranges what you might click next. Long-term memory is more like a bookmark inside an ongoing conversation. It helps the show remember why you cared, where you paused, and what kind of explanation feels useful.
Exactly. And maybe that is the quiet value. It is not giving you more content. It is reducing the small morning effort of choosing. Today can be light and clear, but not shallow.
It can. So good memory should not feel like it is secretly collecting everything. It should be controllable, explainable, and easy to turn off. You should be able to see why this episode appeared, and decide what does not need to stay.
Yes. Maybe the next generation of AI hosts will not be defined by how human the voice sounds, but by whether it can gently catch the question you had not finished yesterday.
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
