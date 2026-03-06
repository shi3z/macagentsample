"""Ollama API Client with streaming support."""
import httpx
import json
from typing import AsyncGenerator, Optional
from dataclasses import dataclass

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "gpt-oss:20b-long"


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class ChatResponse:
    content: str
    thinking: Optional[str] = None
    done: bool = False


class OllamaClient:
    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = DEFAULT_MODEL):
        self.base_url = base_url
        self.model = model
        self.timeout = httpx.Timeout(120.0, connect=10.0)

    async def chat(
        self,
        messages: list[dict],
        stream: bool = True,
        temperature: float = 0.7,
        num_ctx: int = 32768,
    ) -> AsyncGenerator[ChatResponse, None]:
        """Send chat request with streaming."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_ctx": num_ctx,
            }
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        msg = data.get("message", {})
                        yield ChatResponse(
                            content=msg.get("content", ""),
                            thinking=msg.get("thinking"),
                            done=data.get("done", False),
                        )

    async def chat_sync(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        num_ctx: int = 32768,
    ) -> ChatResponse:
        """Send chat request without streaming."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": num_ctx,
            }
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            msg = data.get("message", {})
            return ChatResponse(
                content=msg.get("content", ""),
                thinking=msg.get("thinking"),
                done=True,
            )

    async def health_check(self) -> bool:
        """Check if Ollama is running."""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                response = await client.get(f"{self.base_url}/")
                return response.status_code == 200
        except Exception:
            return False
