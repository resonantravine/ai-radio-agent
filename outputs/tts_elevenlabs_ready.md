# ElevenLabs Ready: Yoli's Morning Coffee: Why do some AI hosts sound like they really understand you?

Do not paste `production_script.md` into a single TTS voice. It contains speaker names, delivery notes, and production metadata for human review.

Use `tts_segments.json` for the real dual-host workflow:

1. Generate Host A lines with the Host A voice.
2. Generate Host B lines with the Host B voice.
3. Stitch the audio clips in segment order.
4. Render the full episode with `pause_after_ms` spacing.

## Host A Text

```text
Good morning, Yoli.
What does it feel like there this morning?
That sounds like exactly where we should begin.
Yesterday's episode about AI startups left one small question on the table: why are so many AI companies suddenly competing for long-term memory?
So this morning, not another generic tech headline. Just one question to stay with for a few minutes: why do some AI hosts sound like they actually know where to continue?
I like that, but I am also a little unsure. Is this really more than knowing that I like tech news?
Let me ask the listener's question gently: isn't that just a regular recommendation algorithm? I clicked something yesterday, so today it gives me more of the same.
A bookmark inside a conversation. I like that.
I feel that in the morning. Before the day gets noisy, I do not really want another feed to sort through.
I want the show to pick up the thread before I lose it. So a good AI host does not meet me from scratch every morning. It moves yesterday's conversation forward.
But if it remembers too much, doesn't that start to feel uncomfortable?
So understanding you is not a kind of mystery. It is a kind of restraint.
That feels like a good place to leave the morning.
Thanks for spending breakfast with us.
Until then, take it slow.
This has been Breakfast. Thanks for listening.
```

## Host B Text

```text
Good morning. I'm already in the kitchen.
Warm, a little messy, and very alive. There's toast on the counter, coffee starting to bubble, and someone just opened the window. You can hear the street waking up outside.
Maybe we can think of it this way. An AI host does not feel personal only because the voice sounds natural. A smooth voice helps, of course. But the deeper feeling comes from continuity.
There is a small difference here. A topic label says you like AI. A softer kind of memory notices how you like to enter the question.
Maybe you care less about every headline, and more about why a product begins to matter in someone's day.
A little, but not quite. A recommendation feed is like a shop window: it rearranges what you might click next.
Long-term memory is more like a bookmark inside an ongoing conversation. It helps the show remember why you cared, where you paused, and what kind of explanation feels useful.
Exactly. And maybe that is the quiet value. It is not giving you more content. It is reducing the small morning effort of choosing.
While you are making breakfast, the show should not ask you to sort through ten headlines. It should offer one thread that is light enough to enter the day, but still worth thinking about.
It can. So good memory should not feel like it is secretly collecting everything.
It should be controllable, explainable, and easy to turn off. You should be able to see why this episode appeared, and decide what does not need to stay.
Yes. Maybe the next generation of AI hosts will not be defined by how human the voice sounds, but by whether it can gently catch the question you had not finished yesterday.
The coffee's still warm, the toast is almost gone, and the day is just getting started.
We'll be here again soon.
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
