# ElevenLabs Ready: 为什么有些 AI 主播听起来像真的懂你？

Do not paste `production_script.md` into a single TTS voice. It contains speaker names, delivery notes, and production metadata for human review.

Use `tts_segments.json` for the real dual-host workflow:

1. Generate Host A lines with the Host A voice.
2. Generate Host B lines with the Host B voice.
3. Stitch the audio clips in segment order.
4. Render the full episode with `pause_after_ms` spacing.

## Host A Text

```text
早上八点，你在地铁上，耳机刚戴好。昨天你听了一期 AI 创业的节目，里面一直提到一个词：长期记忆。今天你再打开 AI 电台，它没有给你推一条泛泛的科技新闻，而是接着昨天那个问题往下讲：为什么 AI 公司都在争长期记忆？
所以它懂的不是我喜欢科技新闻这么简单？
那我替听众问一句：这不就是普通推荐算法吗？我点过什么，它就继续推什么。
也就是说，好的 AI 主播不是每天重新认识我一次，而是能接着昨天的对话往前走。
可是，如果它记得太多，会不会让人有点不舒服？
这样听起来，懂你不是一种神秘感，而是一种分寸感。
地铁到站之前，这也许就是今天最值得记住的一句话：真正像懂你，不是一直说，而是知道从哪里继续。
```

## Host B Text

```text
这个瞬间其实很关键。一个 AI 主播听起来像懂你，不只是因为它声音自然，而是因为它知道你昨天听到了哪里，今天可能还在想什么。
对。那只是标签。更深一点的理解是：你喜欢怎样进入一个问题。比如你不是想听所有 AI 新闻，你更关心一个产品为什么成立，背后的用户需求是什么，以及它和普通工具有什么区别。
有点像，但不完全一样。普通推荐更像看行为记录：你点了什么、停留多久、跳过了什么。长期记忆更像保存一条连续的思路：你为什么关心这个问题，你上次追问到哪里，你更喜欢被怎样解释。
对。它不只是生成更多内容，而是减少你的筛选成本。早上通勤的时候，你不需要重新告诉它我想听什么。它已经知道，今天这段内容最好轻一点、清楚一点，但不要太浅。
会。所以真正好的记忆不应该是偷偷记住一切，而应该是可控的、可解释的、可以被删除的。你应该知道它为什么推荐这段内容，也能决定哪些东西不要被记住。
是的。未来的 AI 主播，最重要的可能不是声音多像真人，而是它能不能在合适的时候，接住你昨天还没想完的问题。
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
