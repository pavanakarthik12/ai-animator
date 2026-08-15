import os
from typing import Any, Dict, List

import groq


class GroqAgent:
    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise ValueError("Missing GROQ_API_KEY")
        # Use the sync Groq client
        self.client = groq.Groq(api_key=api_key)
        self.model = model

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

        resp = self.client.chat.completions.create(**params)
        return resp

    def call_model(self, messages: List[Dict], tools: List[Dict] | None = None) -> Dict[str, Any]:
        return self.create_completion(messages, tools)
