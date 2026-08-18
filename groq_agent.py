import os
import time
import base64
from typing import Any, Dict, List

import groq


class GroqAgent:
    def __init__(self, api_key: str, model: str, vision_model: str = None):
        if not api_key:
            raise ValueError("Missing GROQ_API_KEY")
        # Use the sync Groq client
        self.client = groq.Groq(api_key=api_key)
        self.model = model
        self.vision_model = vision_model or "qwen/qwen3.6-27b"

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
            # Large output budget so a single response can carry the COMPLETE
            # drawing plan (one krita_batch_draw call with many strokes) instead
            # of truncating and forcing per-stroke round trips. Kept at 4096 so
            # input tokens + max_completion_tokens stay under the org TPM limit
            # (8000 tokens for openai/gpt-oss-120b on the on_demand tier).
            "max_completion_tokens": 4096,
        }

        if tools:
            # `tools` should be a list of ChatCompletionToolParam objects as expected
            params["tools"] = tools

        resp = self._post_with_retry(**params)
        return resp

    def call_model(self, messages: List[Dict], tools: List[Dict] | None = None) -> Dict[str, Any]:
        return self.create_completion(messages, tools)

    def analyze_image(self, image_path: str, prompt: str) -> str:
        """Analyze an image using Groq vision model and return structured drawing plan."""
        # Read and encode image
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        
        # Determine image format
        ext = os.path.splitext(image_path)[1].lower()
        mime_type = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp"
        }.get(ext, "image/png")
        
        # Create vision analysis prompt
        vision_prompt = f"""Analyze this image and provide a STRUCTURED DRAWING PLAN in JSON format for reproducing it in Krita.

USER REQUEST: {prompt}

Create a detailed JSON drawing plan with these fields:

1. canvas: {{width, height}} - dimensions based on image aspect ratio (recommended: 800x600 or similar)
2. analysis: brief text description of the image
3. elements: array of drawable primitives

Each element must have:
- order: number (1, 2, 3...) for drawing sequence (background first, details last)
- type: "stroke" | "ellipse" | "rectangle"
- description: what this element represents
- Position/geometry (depends on type):
  * stroke: "points": [[x,y], [x,y], ...] with 10-20+ points for curves
  * ellipse: "center": [x,y], "width": number, "height": number
  * rectangle: "top_left": [x,y], "width": number, "height": number
- color: hex code (e.g. "#000000" for black lines, "#f5d7b8" for skin)
- For shapes: "outline_color": hex code for the border
- brush_size: integer (2-5 typical)

IMPORTANT RULES:
- Return ONLY valid JSON, no thinking text, no markdown, no explanations
- Use enough points for smooth curves (minimum 10-20 points per curved line)
- Preserve proportions and relative positioning accurately
- Include all visible elements (head, body, arms, legs, facial features, etc.)
- Use appropriate colors from the image
- Order elements logically (background → body → details)

Example structure:
{{
  "canvas": {{"width": 800, "height": 600}},
  "analysis": "Stick figure character in thinking pose",
  "elements": [
    {{
      "order": 1,
      "type": "ellipse",
      "description": "head",
      "center": [400, 150],
      "width": 120,
      "height": 130,
      "outline_color": "#000000",
      "brush_size": 3
    }},
    {{
      "order": 2,
      "type": "stroke",
      "description": "body torso",
      "points": [[400, 215], [400, 350]],
      "color": "#000000",
      "brush_size": 3
    }}
  ]
}}"""

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": vision_prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_data}"
                        }
                    }
                ]
            }
        ]
        
        print(f"Sending image to Groq Vision ({self.vision_model})...")
        resp = self._post_with_retry(
            model=self.vision_model,
            messages=messages,
            max_completion_tokens=4096,
            temperature=0.3,  # Lower temperature for more consistent analysis
            response_format={"type": "json_object"}  # Force JSON mode
        )
        
        content = resp.choices[0].message.content
        print("Vision analysis complete.")
        return content
