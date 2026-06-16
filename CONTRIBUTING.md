# Contributing

This is primarily a portfolio prototype, but feedback and small improvements are welcome.

Good contribution areas:

- clearer README or setup instructions,
- safer provider configuration,
- better mock episode examples,
- focused tests for JSON validation, TTS segmentation, or rendering,
- small audio-rendering improvements that keep the project beginner-friendly.

Before opening a pull request:

```bash
python3 -m ai_radio_agent.run_pipeline --mock
python3 -m pytest -q
```

Please do not commit `.env`, `.venv/`, generated mp3/wav/m4a files, API keys, or provider-specific secrets.

For larger feature ideas, open an issue first and describe:

- the user-facing audio experience,
- which pipeline artifact changes,
- how the change can be tested in mock mode.
