import asyncio
import os
import sys
import threading
from typing import Any, List

import fastmcp
from fastmcp.client import Client as FastMCPClient
from fastmcp.client.transports.stdio import PythonStdioTransport


class KritaMCPClient:
    """Synchronous wrapper around fastmcp.Client using a background event loop.

    It launches server.py using a Python stdio transport and exposes
    `list_tools` and `call_tool` as blocking methods.
    """

    def __init__(self, server_py_path: str):
        self.server_py_path = server_py_path
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._client: FastMCPClient | None = None
        self._started = threading.Event()

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        async def _startup():
            # The MCP stdio client builds a minimal environment when env is
            # None, so pass the parent env explicitly (KRITA_URL et al).
            transport = PythonStdioTransport(self.server_py_path, env=os.environ.copy())
            self._client = FastMCPClient(transport, name="groq-krita-agent")
            # Enter async context to initialize the client/session
            await self._client.__aenter__()

        try:
            self._loop.run_until_complete(_startup())
            self._started.set()
            # Keep loop running to service scheduled coroutines
            self._loop.run_forever()
        except Exception:
            self._started.set()
            raise

    def start(self, wait: float = 5.0):
        if self._thread:
            return
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        # Wait for startup or timeout
        self._started.wait(timeout=wait)
        if not self._client:
            raise RuntimeError("Failed to start MCP client")

    def list_tools(self) -> List[str]:
        if not self._client or not self._loop:
            raise RuntimeError("MCP client not started")

        async def _list():
            tools = await self._client.list_tools()
            return [t.name for t in tools]

        fut = asyncio.run_coroutine_threadsafe(_list(), self._loop)
        return fut.result()

    def list_tools_detailed(self) -> list[dict]:
        """Return a list of tool metadata dicts: name, description, input_schema (if available)."""
        if not self._client or not self._loop:
            raise RuntimeError("MCP client not started")

        async def _list():
            tools = await self._client.list_tools()
            out = []
            for t in tools:
                # Try multiple attribute names for schema / description
                name = getattr(t, "name", None) or getattr(t, "tool_name", None) or str(t)
                desc = getattr(t, "description", None)
                schema = None
                # mcp.types.Tool may expose input_schema or inputSchema
                if hasattr(t, "input_schema"):
                    schema = t.input_schema
                elif hasattr(t, "inputSchema"):
                    schema = t.inputSchema
                elif hasattr(t, "schema"):
                    schema = t.schema

                # Attempt to convert schema to a JSON-like dict if possible
                schema_obj = None
                try:
                    if schema is not None:
                        # Some schema objects may be pydantic models or dict-like
                        if hasattr(schema, "dict"):
                            schema_obj = schema.dict()
                        else:
                            schema_obj = dict(schema)
                except Exception:
                    schema_obj = str(schema)

                out.append({"name": name, "description": desc, "input_schema": schema_obj})
            return out

        fut = asyncio.run_coroutine_threadsafe(_list(), self._loop)
        return fut.result()

    def get_tool_schema(self, name: str):
        """Return input_schema for a given tool name, or None."""
        tools = self.list_tools_detailed()
        for t in tools:
            if t.get("name") == name:
                return t.get("input_schema")
        return None

    def call_tool(self, name: str, arguments: dict | None = None, timeout: float | None = None) -> Any:
        if not self._client or not self._loop:
            raise RuntimeError("MCP client not started")

        async def _call():
            result = await self._client.call_tool(name, arguments or {}, timeout=timeout)
            # Prefer structured data, then data, then text content
            if getattr(result, "structured_content", None):
                return result.structured_content
            if getattr(result, "data", None):
                return result.data
            # Fallback: assemble text blocks
            texts = []
            for c in getattr(result, "content", []) or []:
                try:
                    texts.append(c.text)
                except Exception:
                    texts.append(str(c))
            return "\n".join(texts)

        fut = asyncio.run_coroutine_threadsafe(_call(), self._loop)
        return fut.result()

    def stop(self):
        if not self._client or not self._loop:
            return

        async def _shutdown():
            try:
                await self._client.__aexit__(None, None, None)
            except Exception:
                pass

        fut = asyncio.run_coroutine_threadsafe(_shutdown(), self._loop)
        fut.result()
        # Stop loop
        self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=1.0)
