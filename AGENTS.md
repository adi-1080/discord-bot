# Agent instructions for Abstrabit

## Project

Discord slash-command bot with FastAPI backend and React dashboard.

## Stack

- Python 3.12 + FastAPI, managed with **uv** (not pip/venv)
- React + TypeScript + Vite frontend
- Neon Postgres via SQLAlchemy async
- Deployed on Render

## Commands

```bash
# Backend
cd backend && uv sync
uv run uvicorn app.main:app --reload --port 8000

# Add dependency
uv add <package>

# Frontend
cd frontend && npm install && npm run dev

# Build frontend into backend/static for production
cd frontend && npm run build && cp -r dist/* ../backend/static/
```

## Key paths

- Interactions endpoint: `backend/app/routes/interactions.py`
- Command handlers: `backend/app/services/commands.py`
- Discord API: `backend/app/services/discord_api.py`
- Retry loop: `backend/app/services/retry.py`
- Dashboard API: `backend/app/routes/dashboard.py`
- Frontend pages: `frontend/src/pages/`

## Conventions

- Never log or expose secrets (bot token, webhook URLs, JWT secret)
- Always verify Discord Ed25519 signatures on interactions
- Defer slow work (type 5) and follow up via webhook
- Dedup on `interaction_id` before processing
- Use `uv add` for Python deps; commit `uv.lock`

## Environment

Copy `.env.example` to `backend/.env` for local development.
