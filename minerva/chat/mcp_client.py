import asyncio
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from minerva.common.logger import get_logger
from minerva.common.exceptions import ChatEngineError

logger = get_logger(__name__)

try:
    from fastmcp import Client as FastMCPClient
except ImportError as error:
    logger.error("FastMCP not installed. Run: pip install fastmcp")
    raise ImportError("fastmcp is required for MCP client functionality") from error


@dataclass
class MCPToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any]

    def to_openai_format(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }


class MCPConnectionError(ChatEngineError):
    pass


class MCPToolExecutionError(ChatEngineError):
    pass


class MCPClient:
    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip('/')
        self.mcp_endpoint = f"{self.server_url}/mcp"
        self._client: Optional[FastMCPClient] = None
        self._tools_cache: Optional[List[MCPToolDefinition]] = None

    def _create_client(self) -> FastMCPClient:
        return FastMCPClient(self.mcp_endpoint)

    async def check_connection(self) -> bool:
        try:
            client = self._create_client()
            async with client:
                tools = await client.list_tools()
                logger.info(f"MCP connection successful: {len(tools)} tools available")
                return True
        except Exception as e:
            logger.error(f"MCP connection failed: {e}")
            return False

    async def get_tool_definitions(self) -> List[MCPToolDefinition]:
        if self._tools_cache:
            return self._tools_cache

        try:
            client = self._create_client()
            async with client:
                tools = await client.list_tools()

                tool_definitions = []
                for tool in tools:
                    tool_def = MCPToolDefinition(
                        name=tool.name,
                        description=tool.description or "",
                        parameters=tool.inputSchema if hasattr(tool, 'inputSchema') else {}
                    )
                    tool_definitions.append(tool_def)

                self._tools_cache = tool_definitions
                logger.info(f"Retrieved {len(tool_definitions)} tool definitions from MCP server")

                return tool_definitions

        except Exception as e:
            logger.error(f"Failed to fetch tool definitions: {e}")
            raise MCPConnectionError(f"Unable to connect to MCP server at {self.mcp_endpoint}: {e}") from e

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        try:
            client = self._create_client()
            async with client:
                logger.info(f"Calling MCP tool: {tool_name}")
                result = await client.call_tool(tool_name, arguments)

                parsed_result = self._parse_tool_result(result)
                return parsed_result

        except Exception as e:
            logger.error(f"Tool execution failed for {tool_name}: {e}")
            raise MCPToolExecutionError(f"Failed to execute tool {tool_name}: {e}") from e

    def _parse_tool_result(self, result) -> Any:
        if hasattr(result, 'content'):
            content_items = result.content

            if not content_items or len(content_items) == 0:
                return {"error": "No content returned from tool"}

            all_results = []
            for item in content_items:
                if hasattr(item, 'text'):
                    try:
                        parsed = json.loads(item.text)
                        all_results.append(parsed)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse content item as JSON: {e}")
                        all_results.append({"text": item.text})

            if len(all_results) == 1:
                return all_results[0] if not isinstance(all_results[0], list) else all_results[0]
            return all_results

        if hasattr(result, 'data'):
            return result.data

        return result

    def check_connection_sync(self) -> bool:
        try:
            return asyncio.run(self.check_connection())
        except Exception as e:
            logger.error(f"Synchronous connection check failed: {e}")
            return False

    def get_tool_definitions_sync(self) -> List[MCPToolDefinition]:
        try:
            return asyncio.run(self.get_tool_definitions())
        except Exception as e:
            logger.error(f"Synchronous tool definitions fetch failed: {e}")
            raise MCPConnectionError(f"Failed to fetch tool definitions: {e}") from e

    def call_tool_sync(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        try:
            return asyncio.run(self.call_tool(tool_name, arguments))
        except Exception as e:
            logger.error(f"Synchronous tool call failed: {e}")
            raise MCPToolExecutionError(f"Failed to call tool {tool_name}: {e}") from e
