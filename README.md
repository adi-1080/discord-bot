# Abstrabit — Discord Slash-Command Bot

A full-stack web app and Discord bot that handles slash commands via Discord's Interactions Endpoint, records every command, responds in Discord, mirrors notifications to a second Discord channel, and provides an admin dashboard for configuration and live logs.

## Features

- **Discord Interactions Endpoint** with Ed25519 signature verification and PING/PONG support
- **Slash commands:** `/report <text>` and `/status`
- **Deferred responses** for work that exceeds Discord's 3-second window
- **Interaction deduplication** by interaction ID
- **Retry queue** for failed mirror/channel posts
- **Admin dashboard** (JWT auth) with live command log and guild configuration
- **Mirror notifications** to a second Discord channel via webhook

## Tech stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy (async), uv
- **Frontend:** React, TypeScript, Vite
- **Database:** Neon Postgres (free tier)
- **Hosting:** Render (free tier)

## Environment variables

Copy `.env.example` to `backend/.env` and fill in values:

| Variable | Description |
|----------|-------------|
| `DISCORD_APPLICATION_ID` | Discord application ID |
| `DISCORD_PUBLIC_KEY` | Discord application public key (for signature verification) |
| `DISCORD_BOT_TOKEN` | Bot token (never expose client-side) |
| `DATABASE_URL` | Neon Postgres URL (`postgresql+asyncpg://...`) |
| `JWT_SECRET` | Secret for admin JWT tokens |
| `ADMIN_EMAIL` | Seeded admin email |
| `ADMIN_PASSWORD` | Seeded admin password |
| `APP_URL` | Public app URL (e.g. `http://localhost:8000` locally) |
| `ENVIRONMENT` | `development` or `production` |

## Run locally

### Prerequisites

- [uv](https://docs.astral.sh/uv/)
- Node.js 18+
- Neon Postgres database (or local Postgres with asyncpg URL)

### Backend

```bash
cd backend
cp ../.env.example .env   # edit with your values
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

### Frontend (dev)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — API requests proxy to `:8000`.

### Discord local testing

Discord requires a public HTTPS endpoint. Use a tunnel:

```bash
ngrok http 8000
# or: cloudflared tunnel --url http://localhost:8000
```

Set the **Interactions Endpoint URL** in the Discord Developer Portal to:

```
https://<your-tunnel-host>/api/discord/interactions
```

## Discord setup

1. Create an application at [Discord Developer Portal](https://discord.com/discord/developer/applications)
2. Create a bot and copy **Application ID**, **Public Key**, and **Bot Token**
3. Enable **Interactions Endpoint URL** (your deployed or tunneled URL)
4. Log into the dashboard → **Settings** → invite the bot to your server
5. Enter **Guild ID**, **Channel ID**, and **Mirror Webhook URL**
6. Click **Register commands**

### Bot invite

After saving guild config, use the invite link in Settings, or:

```
https://discord.com/api/oauth2/authorize?client_id=YOUR_APP_ID&permissions=3072&scope=bot%20applications.commands
```

### Mirror webhook

In your second Discord channel: **Edit Channel → Integrations → Webhooks → New Webhook**. Copy the webhook URL into the dashboard.

## Deploy to Render

1. Push this repo to GitHub
2. Create a [Neon](https://neon.tech) project and copy the connection string (use `postgresql+asyncpg://` prefix)
3. Connect the repo to [Render](https://render.com) using `render.yaml`, or create a Web Service manually:
   - **Build:** see `render.yaml`
   - **Start:** `cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Set all environment variables in Render
5. Set Discord Interactions Endpoint URL to `https://<your-app>.onrender.com/api/discord/interactions`

**Note:** Render's free tier sleeps after inactivity. Wake the service before testing Discord interactions.

## Testing

1. Open the deployed URL (or http://localhost:5173 in dev)
2. Log in with your `ADMIN_EMAIL` / `ADMIN_PASSWORD`
3. Configure guild settings and register commands
4. In Discord, run `/report This is urgent` and `/status`
5. Check the dashboard for logged commands and actions

### Default admin (change in production)

- Email: `admin@example.com`
- Password: `changeme`

## Project structure

```
backend/app/          FastAPI application
frontend/src/       React dashboard
render.yaml         Render deployment config
.env.example        Environment template
```

## Security

- All Discord interaction requests are verified with Ed25519 signatures
- Bot token, public key internals, and webhook URLs are server-side only
- Webhook URLs are masked in dashboard API responses
- Duplicate interaction IDs are ignored to prevent double-processing
