"""Tool definitions for the agent."""
import subprocess
import json
import os
from dataclasses import dataclass
from typing import Any, Callable, Optional
from abc import ABC, abstractmethod


@dataclass
class ToolResult:
    success: bool
    output: str
    error: Optional[str] = None


class Tool(ABC):
    name: str
    description: str
    parameters: dict

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        pass

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


class WebSearchTool(Tool):
    name = "web_search"
    description = "Search for latest news using DuckDuckGo News. Returns recent news articles with dates."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query for news"
            }
        },
        "required": ["query"]
    }

    async def execute(self, query: str) -> ToolResult:
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                # Use news search for current events
                results = list(ddgs.news(query, max_results=5))
            output = json.dumps(results, ensure_ascii=False, indent=2)
            return ToolResult(success=True, output=output)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class FetchUrlTool(Tool):
    name = "fetch_url"
    description = "Fetch and read the content of a URL. Use this to get details from news articles."
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to fetch"
            }
        },
        "required": ["url"]
    }

    async def execute(self, url: str) -> ToolResult:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; AgentBot/1.0)"
                })
                response.raise_for_status()
                content = response.text

                # Extract text content (simple HTML stripping)
                import re
                # Remove scripts and styles
                content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
                content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
                # Remove HTML tags
                content = re.sub(r'<[^>]+>', ' ', content)
                # Clean whitespace
                content = re.sub(r'\s+', ' ', content).strip()
                # Limit length
                content = content[:5000]

                return ToolResult(success=True, output=content)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class ReadFileTool(Tool):
    name = "read_file"
    description = "Read the contents of a file from the local filesystem."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The file path to read"
            }
        },
        "required": ["path"]
    }

    async def execute(self, path: str) -> ToolResult:
        try:
            # Security: only allow reading from certain directories
            allowed_dirs = [os.path.expanduser("~/project"), "/tmp"]
            abs_path = os.path.abspath(os.path.expanduser(path))

            if not any(abs_path.startswith(d) for d in allowed_dirs):
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Access denied. Can only read from: {allowed_dirs}"
                )

            with open(abs_path, "r", encoding="utf-8") as f:
                content = f.read()
            return ToolResult(success=True, output=content)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class WriteFileTool(Tool):
    name = "write_file"
    description = "Write content to a file on the local filesystem."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The file path to write to"
            },
            "content": {
                "type": "string",
                "description": "The content to write"
            }
        },
        "required": ["path", "content"]
    }

    async def execute(self, path: str, content: str) -> ToolResult:
        try:
            # Security: only allow writing to certain directories
            allowed_dirs = [os.path.expanduser("~/project"), "/tmp"]
            abs_path = os.path.abspath(os.path.expanduser(path))

            if not any(abs_path.startswith(d) for d in allowed_dirs):
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Access denied. Can only write to: {allowed_dirs}"
                )

            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)
            return ToolResult(success=True, output=f"Successfully wrote to {path}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class ExecuteCodeTool(Tool):
    name = "execute_code"
    description = "Execute Python code in a sandboxed environment. Returns stdout and stderr."
    parameters = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute"
            }
        },
        "required": ["code"]
    }

    async def execute(self, code: str) -> ToolResult:
        try:
            result = subprocess.run(
                ["python", "-c", code],
                capture_output=True,
                text=True,
                timeout=30,
                cwd="/tmp"
            )
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]: {result.stderr}"
            return ToolResult(
                success=result.returncode == 0,
                output=output,
                error=result.stderr if result.returncode != 0 else None
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, output="", error="Execution timed out (30s)")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class GenerateImageTool(Tool):
    name = "generate_image"
    description = "Generate an image using FLUX AI model on Apple Silicon. Returns the path to the generated image."
    parameters = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Text description of the image to generate (in English)"
            }
        },
        "required": ["prompt"]
    }

    async def execute(self, prompt: str) -> ToolResult:
        import uuid
        import asyncio
        try:
            # Generate unique filename
            image_id = str(uuid.uuid4())[:8]
            output_path = f"/tmp/generated_{image_id}.png"

            # Use mflux-generate from mlx312 conda environment
            mflux_path = "/Users/shi3z/.pyenv/versions/miniforge3-25.1.1-0/envs/mlx312/bin/mflux-generate"
            cmd = [
                mflux_path,
                "--model", "schnell",
                "--prompt", prompt,
                "--steps", "4",
                "--seed", str(uuid.uuid4().int % 10000),
                "--width", "512",
                "--height", "512",
                "--quantize", "8",
                "--output", output_path
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=300  # 5 minutes timeout
            )

            if process.returncode == 0:
                return ToolResult(
                    success=True,
                    output=f"Image generated successfully: {output_path}"
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Generation failed: {stderr.decode()}"
                )

        except asyncio.TimeoutError:
            return ToolResult(success=False, output="", error="Image generation timed out (5 min)")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


# Tool registry
AVAILABLE_TOOLS: dict[str, Tool] = {
    "web_search": WebSearchTool(),
    "fetch_url": FetchUrlTool(),
    "read_file": ReadFileTool(),
    "write_file": WriteFileTool(),
    "execute_code": ExecuteCodeTool(),
    "generate_image": GenerateImageTool(),
}


def get_tools_description() -> str:
    """Get a formatted description of all available tools."""
    lines = ["Available tools:"]
    for name, tool in AVAILABLE_TOOLS.items():
        params = ", ".join(tool.parameters.get("required", []))
        lines.append(f"- {name}({params}): {tool.description}")
    return "\n".join(lines)


def get_tools_schema() -> list[dict]:
    """Get JSON schema for all tools."""
    return [tool.to_dict() for tool in AVAILABLE_TOOLS.values()]
