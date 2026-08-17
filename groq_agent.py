import os
import time
from typing import Any, Dict, List

import groq


class GroqAgent:
    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise ValueError("Missing GROQ_API_KEY")
        # Use the sync Groq client
        self.client = groq.Groq(api_key=api_key)
        self.model = model

    def _post_with_retry(self, **params) -> Any:
        """Call the Groq API, retrying on 429 rate-limit errors with backoff."""
        max_retries = 5
        base_delay = 2.0
        for attempt in range(max_retries + 1):
            try:
                return self.client.chat.completions.create(**params)
            except Exception as e:
                status = getattr(getattr(e, "response", None), "status_code", None)
                if status != 429 or attempt >= max_retries:
                    raise
                retry_after = None
                try:
                    retry_after = float(e.response.headers.get("retry-after", ""))
                except Exception:
                    pass
                delay = retry_after if retry_after and retry_after > 0 else base_delay * (2 ** attempt)
                print(f"Groq rate limited (429); retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(delay)
        raise RuntimeError("Unreachable")

    def create_completion(self, messages: List[Dict], tools: List[Dict] | None = None) -> Dict[str, Any]:
        # Use the chat completions endpoint. Do NOT force a JSON response here —
        # the model may return either a JSON tool call (when it wants to invoke a tool)
        # or a natural-language final response. We instruct the model in the system
        # prompt to emit JSON only when making a tool call.
        params: Dict[str, Any] = {
            "messages": messages,
            "model": self.model,
            "disable_tool_validation": True,
            "tool_choice": "auto",
            "max_completion_tokens": 1024,
        }

        if tools:
            # `tools` should be a list of ChatCompletionToolParam objects as expected
            params["tools"] = tools

        resp = self._post_with_retry(**params)
        return resp

    def call_model(self, messages: List[Dict], tools: List[Dict] | None = None) -> Dict[str, Any]:
        return self.create_completion(messages, tools)
