"""Agent core loop with ReAct-style reasoning."""
import json
import re
from typing import AsyncGenerator, Optional
from dataclasses import dataclass, field

from .tools import AVAILABLE_TOOLS, ToolResult, get_tools_description
from .prompts import get_system_prompt, format_tool_result


@dataclass
class AgentMessage:
    role: str
    content: str
    tool_call: Optional[dict] = None
    tool_result: Optional[ToolResult] = None


@dataclass
class AgentState:
    messages: list[dict] = field(default_factory=list)
    max_iterations: int = 10
    current_iteration: int = 0


class Agent:
    def __init__(self, ollama_client, rag_retriever=None):
        self.ollama = ollama_client
        self.rag = rag_retriever
        self.tools = AVAILABLE_TOOLS.copy()

        # Add RAG tool if available
        if self.rag:
            from .tools import Tool, ToolResult

            class RAGSearchTool(Tool):
                name = "rag_search"
                description = "Search through uploaded documents for relevant information."
                parameters = {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["query"]
                }

                def __init__(self, retriever):
                    self.retriever = retriever

                async def execute(self, query: str) -> ToolResult:
                    try:
                        results = await self.retriever.search(query)
                        return ToolResult(success=True, output=json.dumps(results, ensure_ascii=False))
                    except Exception as e:
                        return ToolResult(success=False, output="", error=str(e))

            self.tools["rag_search"] = RAGSearchTool(self.rag)

    def _extract_tool_call(self, content: str) -> Optional[dict]:
        """Extract tool call from assistant response."""
        # Look for JSON block with tool call
        pattern = r'```json\s*(\{[^`]+\})\s*```'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                if "tool" in data and "args" in data:
                    return data
            except json.JSONDecodeError:
                pass

        # Also try inline JSON
        pattern = r'\{"tool":\s*"[^"]+",\s*"args":\s*\{[^}]+\}\}'
        match = re.search(pattern, content)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        return None

    def _infer_tool_from_thinking(self, thinking: str, user_message: str) -> Optional[dict]:
        """Infer tool call from thinking content when model doesn't output JSON."""
        from datetime import datetime
        thinking_lower = thinking.lower()
        message_lower = user_message.lower()

        # Check if user wants to generate an image
        image_keywords_ja = ['画像', '絵', 'イラスト', '描いて', '生成', '作って', 'アニメ', 'リアル', 'っぽく', '風に', 'スタイル']
        image_keywords_en = ['image', 'picture', 'draw', 'generate', 'create', 'illustration', 'anime', 'realistic', 'style']
        # Style modifiers that imply image generation even without explicit keywords
        style_modifiers = ['アニメ', 'リアル', 'っぽく', '風に', 'anime', 'realistic']
        is_style_request = any(kw in message_lower for kw in style_modifiers)
        if is_style_request or (any(kw in message_lower for kw in image_keywords_ja + image_keywords_en) and
            any(kw in thinking_lower for kw in ['generate_image', 'image', 'picture', 'draw', 'create', 'style', 'anime'])):
                # Convert Japanese prompt to simple English description
                prompt = user_message
                # Handle style modifiers
                if 'アニメ' in prompt or 'anime' in prompt.lower():
                    prompt = "anime style cat, cute, colorful"
                elif 'リアル' in prompt or 'realistic' in prompt.lower():
                    prompt = "photorealistic cat, detailed fur, natural lighting"
                else:
                    prompt = prompt.replace('の画像を生成して', '').replace('の絵を描いて', '').replace('画像生成して', '').replace('を描いて', '')
                    # Simple translation for common terms
                    prompt = prompt.replace('猫', 'cat').replace('犬', 'dog').replace('山', 'mountain').replace('海', 'ocean').replace('空', 'sky').replace('花', 'flower')
                return {"tool": "generate_image", "args": {"prompt": prompt.strip() or "a cute cat"}}

        # Check if model wants to use web_search
        if any(kw in thinking_lower for kw in ['web_search', 'search', 'news', 'current']):
            # Add current date to search query for news
            now = datetime.now()
            date_suffix = now.strftime("%Y年%m月")
            query = f"{user_message} {date_suffix}"
            return {"tool": "web_search", "args": {"query": query}}

        return None

    async def _execute_tool(self, tool_call: dict) -> ToolResult:
        """Execute a tool and return result."""
        tool_name = tool_call.get("tool")
        args = tool_call.get("args", {})

        if tool_name not in self.tools:
            return ToolResult(
                success=False,
                output="",
                error=f"Unknown tool: {tool_name}"
            )

        tool = self.tools[tool_name]
        return await tool.execute(**args)

    async def run(
        self,
        user_message: str,
        history: list[dict] = None,
        stream: bool = True,
    ) -> AsyncGenerator[str, None]:
        """Run the agent loop with streaming output."""
        state = AgentState()

        # Initialize messages with system prompt
        state.messages = [{"role": "system", "content": get_system_prompt()}]

        # Add history if provided
        if history:
            state.messages.extend(history)

        # Add user message
        state.messages.append({"role": "user", "content": user_message})

        while state.current_iteration < state.max_iterations:
            state.current_iteration += 1

            # Collect full response (content and thinking)
            full_response = ""
            full_thinking = ""

            if stream:
                async for chunk in self.ollama.chat(state.messages, stream=True):
                    full_response += chunk.content
                    if chunk.thinking:
                        full_thinking += chunk.thinking
                    yield chunk.content
                    if chunk.done:
                        break
            else:
                response = await self.ollama.chat_sync(state.messages)
                full_response = response.content
                full_thinking = response.thinking or ""
                yield full_response

            # Check for tool call in content first
            tool_call = self._extract_tool_call(full_response)

            # If no tool call in content but thinking suggests tool use, infer the tool
            if not tool_call and not full_response and full_thinking:
                tool_call = self._infer_tool_from_thinking(full_thinking, user_message)

            if tool_call:
                # Execute tool
                yield f"\n[Executing {tool_call['tool']}...]\n"
                result = await self._execute_tool(tool_call)

                # Format result
                result_text = result.output if result.success else f"Error: {result.error}"
                formatted_result = format_tool_result(tool_call["tool"], result_text)

                yield f"{formatted_result}\n"

                # Add assistant message (use thinking if content is empty) and tool result to history
                assistant_content = full_response if full_response else f"[Thinking: {full_thinking[:200]}...]"
                state.messages.append({"role": "assistant", "content": assistant_content})
                state.messages.append({
                    "role": "user",
                    "content": f"Tool result:\n{result_text}\n\nBased on this result, provide a helpful response to the user. Do not use tools again unless necessary."
                })
            else:
                # No tool call, we're done
                state.messages.append({"role": "assistant", "content": full_response})
                break

    async def run_sync(
        self,
        user_message: str,
        history: list[dict] = None,
    ) -> str:
        """Run agent and return complete response."""
        result = []
        async for chunk in self.run(user_message, history, stream=False):
            result.append(chunk)
        return "".join(result)
