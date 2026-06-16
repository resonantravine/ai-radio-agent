# ElevenLabs Ready: 为什么有些 AI 主播听起来像真的懂你？

Do not paste `production_script.md` into a single TTS voice. It contains speaker names, delivery notes, and production metadata for human review.

Use `tts_segments.json` for the real dual-host workflow:

1. Generate Host A lines with the Host A voice.
2. Generate Host B lines with the Host B voice.
3. Stitch the audio clips in segment order.
4. Render the full episode with `pause_after_ms` spacing.

## Host A Text

```text
早上好，欢迎回来。今天这段，适合在地铁上听。我们聊一个有点微妙的问题：一个 AI 主播，到底怎样才算真的懂你？
比如昨天我刚听完一期 AI 创业节目，里面一直在讲公司为什么都在争长期记忆。今天我打开电台，它没有给我一段泛泛的科技新闻。
那我替听众问一句：这不就是普通推荐算法吗？
所以它记住的不是我的标签，而是我理解问题的方式。
这样听起来，价值不是推更多内容，而是减少我的筛选成本。
可是，如果它记得太多，会不会让人不舒服？
这样它才不像在偷偷观察你，而像一个有分寸的主播。
```

## Host B Text

```text
我觉得不只是声音自然。更关键的是，它能不能接住你昨天还没想完的问题。
对，它像是在接着昨天的问题继续讲。不是从零开始，也不是把热门新闻重新洗一遍。
有点像，但不完全一样。普通推荐更像看你刚刚点了什么，然后猜下一个你会点什么。长期记忆更像记住你为什么会关心这件事。
对。比如你连续三天跳过宏观新闻，却听完了所有关于 AI voice 的内容。它不该只说，你喜欢 AI。它应该知道，你真正关心的是声音产品怎么形成陪伴感。
没错。早上八点在地铁上，你可能不想重新选择二十条资讯。你只是想听到一个刚好接得上的解释。
会。所以好的记忆一定要可控、可解释，也要容易关掉。你应该知道它记住了什么，也能决定哪些不要继续用。
所以，下一代 AI 音频最重要的可能不是声音有多像人，而是它能不能逐渐学会用你喜欢的方式，陪你理解世界。
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
