import httpx


async def send_webhook_message(webhook_url: str, content: str, *, embeds: list[dict] | None = None) -> None:
    payload: dict = {"content": content}
    if embeds:
        payload["embeds"] = embeds

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(webhook_url, json=payload)
        response.raise_for_status()
