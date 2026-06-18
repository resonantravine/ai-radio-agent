# AI Radio Agent Project Rules

## Demo And Release Workflow

- Keep the repository lightweight. Do not commit generated `.mp3`, `.wav`, `.m4a`, `.mp4`, poster images, ElevenLabs segment directories, or sound packs unless the user explicitly asks.
- Put large demo media in the GitHub Release assets. Commit only code, docs, production scripts, clean TTS JSON, and small inspectable artifacts that are meant to live in git.
- For README demo presentation, prefer GitHub `user-attachments` MP4 URLs embedded as `<video src="..."></video>` blocks, matching the Podcastfy-style README pattern. Use release-hosted poster images only as a fallback when an attachment URL is unavailable.
- For release notes, prefer appending new demo assets and updating the review path. Do not delete or overwrite existing release assets without explicit user approval.
- For the daily radio demos, preserve the conceptual mapping:
  - Breakfast = continue
  - Lunch = compress + update
  - Dinner = transform
- Keep production scripts and TTS JSON separate. Production scripts may contain host labels, delivery notes, sound labels, timecodes, and mix notes. TTS JSON must contain only clean spoken text, speaker metadata, delivery notes, and pauses.
- Before publishing a demo, validate the TTS JSON and run relevant tests when available.

## Approval Boundaries

Ask for explicit user approval before:

- deleting files,
- overwriting online content,
- sending email,
- opening or sending a pull request,
- publishing a new release.

Updating an existing release by adding new assets and editing notes is acceptable when the user has already asked for the release to be updated. Still stop for approval before deleting or replacing existing release assets.

## Repeated-Task Diagnosis Mode

If a similar task has already been attempted multiple times, switch to diagnosis mode before editing:

1. Summarize what changed so far.
2. Identify the exact error or failing behavior.
3. List the minimum files involved.
4. Do not modify files yet.
5. Propose the smallest possible fix.
6. Wait for user approval before editing.

## Working Tree Hygiene

- The repo may contain unrelated generated `outputs/` changes. Do not include them in commits unless they are directly part of the requested change.
- Stage narrowly and verify staged files before committing.
- If git transport fails but GitHub API works, explain the fallback clearly and verify the remote commit contents afterward.
