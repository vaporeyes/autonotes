# ABOUTME: Async HTTP client for the Obsidian Local REST API plugin.
# ABOUTME: Handles Bearer auth, self-signed SSL, and all vault/command operations.

import httpx

from app.config import settings


class ObsidianClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.obsidian_api_url,
            headers={"Authorization": f"Bearer {settings.obsidian_api_key}"},
            verify=False,
            timeout=30.0,
        )

    async def health_check(self) -> dict:
        resp = await self._client.get("/")
        resp.raise_for_status()
        return resp.json()

    async def get_note(self, path: str) -> dict:
        resp = await self._client.get(
            f"/vault/{path}",
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()

    async def get_note_raw(self, path: str) -> str:
        resp = await self._client.get(f"/vault/{path}")
        resp.raise_for_status()
        return resp.text

    async def list_folder(self, path: str, recursive: bool = False) -> list[str]:
        folder = path.strip("/")
        url = f"/vault/{folder}/" if folder else "/vault/"
        resp = await self._client.get(url)
        resp.raise_for_status()
        data = resp.json()
        prefix = f"{folder}/" if folder else ""

        results = []
        for name in data.get("files", []):
            full_path = prefix + name
            if name.endswith("/") and recursive:
                results.extend(await self.list_folder(full_path, recursive=True))
            else:
                results.append(full_path)
        return results

    async def put_note(self, path: str, content: str) -> None:
        resp = await self._client.put(
            f"/vault/{path}",
            content=content,
            headers={"Content-Type": "text/markdown"},
        )
        resp.raise_for_status()

    async def patch_note(
        self,
        path: str,
        content: str,
        heading: str | None = None,
        insertion_position: str = "end",
    ) -> None:
        headers = {
            "Content-Type": "text/markdown",
            "Content-Insertion-Position": insertion_position,
        }
        if heading:
            headers["Heading"] = heading
        resp = await self._client.patch(
            f"/vault/{path}",
            content=content,
            headers=headers,
        )
        resp.raise_for_status()

    async def list_commands(self) -> list[dict]:
        resp = await self._client.get("/commands/")
        resp.raise_for_status()
        return resp.json().get("commands", [])

    async def execute_command(self, command_id: str) -> None:
        resp = await self._client.post(f"/commands/{command_id}/")
        resp.raise_for_status()

    async def search(self, query: str) -> list[dict]:
        resp = await self._client.post("/search/simple/", json={"query": query})
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        await self._client.aclose()


obsidian_client = ObsidianClient()
