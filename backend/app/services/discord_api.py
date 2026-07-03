import httpx

from app.config import get_settings

DISCORD_API_BASE = "https://discord.com/api/v10"


def _headers() -> dict[str, str]:
    settings = get_settings()
    return {
        "Authorization": f"Bot {settings.discord_bot_token}",
        "Content-Type": "application/json",
    }


async def register_slash_commands() -> list[dict]:
    settings = get_settings()
    commands = [
        {
            "name": "report",
            "description": "Submit a report",
            "options": [
                {
                    "name": "text",
                    "description": "Report text",
                    "type": 3,
                    "required": True,
                }
            ],
        },
        {
            "name": "status",
            "description": "Check bot status",
        },
    ]
    url = f"{DISCORD_API_BASE}/applications/{settings.discord_application_id}/commands"
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.put(url, headers=_headers(), json=commands)
        response.raise_for_status()
        return response.json()


async def send_followup(
    application_id: str,
    interaction_token: str,
    content: str,
    *,
    ephemeral: bool = False,
    embeds: list[dict] | None = None,
) -> None:
    url = f"{DISCORD_API_BASE}/webhooks/{application_id}/{interaction_token}"
    payload: dict = {"content": content}
    if embeds:
        payload["embeds"] = embeds
    if ephemeral:
        payload["flags"] = 64

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()


async def post_to_channel(channel_id: str, content: str, *, embeds: list[dict] | None = None) -> None:
    url = f"{DISCORD_API_BASE}/channels/{channel_id}/messages"
    payload: dict = {"content": content}
    if embeds:
        payload["embeds"] = embeds

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(url, headers=_headers(), json=payload)
        response.raise_for_status()
