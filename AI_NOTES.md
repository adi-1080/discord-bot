# AI Notes — Abstrabit Discord Bot

## Tools and models used

- **Cursor** with Claude (Composer) for end-to-end implementation
- Split: AI generated scaffold, backend services, frontend pages, and docs; human review expected for Discord credentials, Neon/Render setup, and live testing

## Key decisions (human-directed via plan)

1. **FastAPI + uv + single Render service** — One deployable unit serves both the interactions endpoint and the React dashboard as static files, avoiding CORS and multi-service complexity on free tier.

2. **Defer-all pattern for slash commands** — Every `APPLICATION_COMMAND` returns type 5 immediately, then processes in a background task. This handles Render cold starts and mirror/channel latency without hitting Discord's 3-second timeout.

3. **Discord webhook for mirror channel** (not Slack) — Per plan preference; second Discord channel receives mirrored notifications via incoming webhook URL stored in guild config.

## Hardest bug / wrong turn

**Passlib + bcrypt 5.x compatibility:** Initial auth used `passlib` with `bcrypt 5.x`, which fails because passlib reads `bcrypt.__about__.__version__` (removed in bcrypt 5). **Fix:** Dropped passlib and hash passwords directly with the `bcrypt` library.

**Double JSON parse on interactions:** Reading `request.body()` consumes the stream; calling `request.json()` afterward can fail or return empty. **Fix:** Use `json.loads(body)` on the raw bytes after signature verification.

## What I'd improve with more time

- Guild/channel picker via Discord OAuth instead of manual ID entry
- SSE instead of polling for dashboard logs
- Stretch goals: modals, buttons, AI triage, multi-server isolation UI
- Structured JSON logging and Sentry-free error tracking table

## Prompt excerpt (architecture)

> Build interactions endpoint that verifies Ed25519, dedups on interaction ID, defers immediately, and retries failed mirror posts with exponential backoff — treat it as something that runs unattended.
