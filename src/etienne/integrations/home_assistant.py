import httpx


class HomeAssistantClient:
    def __init__(self, url: str, token: str):
        self.client = httpx.AsyncClient(
            base_url=url,
            headers={
                "Authorization": f"Bearer {token}",
            },
        )

    async def get_state(self, entity_id: str) -> dict:
        response = await self.client.get(
            f"/api/states/{entity_id}"
        )
        response.raise_for_status()
        return response.json()

    async def call_service(
        self,
        domain: str,
        service: str,
        data: dict,
    ):
        response = await self.client.post(
            f"/api/services/{domain}/{service}",
            json=data,
        )
        response.raise_for_status()

    async def close(self):
        await self.client.aclose()