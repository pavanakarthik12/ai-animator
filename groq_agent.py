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
        from PIL import Image
        import io
        
        # Load and resize image if too large
        try:
            img = Image.open(image_path)
            
            # Calculate size - aim for 192px max (very small) to stay under token limit
            max_size = 192
            width, height = img.size
            
            if width > max_size or height > max_size:
                if width > height:
                    new_width = max_size
                    new_height = int(height * (max_size / width))
                else:
                    new_height = max_size
                    new_width = int(width * (max_size / height))
                
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                print(f"Resized image: {width}x{height} → {new_width}x{new_height}")
            
            # Convert to bytes with compression
            img_bytes = io.BytesIO()
            # Convert to RGB if needed (for JPEG)
            if img.mode in ('RGBA', 'LA', 'P'):
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = rgb_img
            
            # Use JPEG with lower quality to reduce size
            img.save(img_bytes, format='JPEG', quality=60, optimize=True)
            image_data = base64.b64encode(img_bytes.getvalue()).decode("utf-8")
            mime_type = "image/jpeg"
            
        except Exception as e:
            print(f"Error loading image, using original: {e}")
            # Fallback to original method
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            
            ext = os.path.splitext(image_path)[1].lower()
            mime_type = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".webp": "image/webp"
            }.get(ext, "image/png")
        
        # Minimal prompt to stay under token limit
        vision_prompt = f"""JSON only:
{{"canvas":{{"width":<w>,"height":<h>}},"components":[{{"name":"part","order":1,"strokes":[{{"normalized_points":[[0.5,0.2],...],"color":"#000","brush_size":4,"closed":false}}]}}]}}
Extract head,eyes,nose,mouth,hair,body,arms,legs. Coords 0-1. 15+ pts/curve."""

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
        
        full_content = ""
        is_json_mode = True
        
        try:
            # Try with JSON mode first
            resp = self._post_with_retry(
                model=self.vision_model,
                messages=messages,
                max_completion_tokens=2000,  # Reduced to stay under TPM limit
                temperature=0.1,
                response_format={"type": "json_object"}
            )
        except Exception as e:
            error_msg = str(e)
            if "json_validate_failed" in error_msg or "Failed to validate JSON" in error_msg:
                print("JSON mode failed, retrying without JSON mode constraint...")
                is_json_mode = False
                # Retry without JSON mode - rely on extraction
                resp = self._post_with_retry(
                    model=self.vision_model,
                    messages=messages,
                    max_completion_tokens=2000,
                    temperature=0.1
                )
            else:
                raise
        
        content = resp.choices[0].message.content
        full_content += content
        finish_reason = resp.choices[0].finish_reason
        
        # Continuation loop if response is truncated
        continuation_count = 0
        max_continuations = 5
        
        while finish_reason == "length" and continuation_count < max_continuations:
            print(f"Response truncated. Requesting continuation {continuation_count + 1}/{max_continuations}...")
            
            # Append the assistant's partial response
            messages.append({"role": "assistant", "content": content})
            
            # Ask it to continue exactly where it left off
            messages.append({
                "role": "user",
                "content": "Your previous response was truncated due to length limits. Please continue EXACTLY where you left off. Do not repeat anything you've already output, and do not start a new JSON object. Just output the continuation."
            })
            
            # We must drop JSON mode for continuations since the continuation is just a fragment, not a valid JSON object by itself
            resp = self._post_with_retry(
                model=self.vision_model,
                messages=messages,
                max_completion_tokens=2000,
                temperature=0.1
            )
            
            content = resp.choices[0].message.content
            # Sometimes models prepend a codeblock markdown to continuations
            clean_content = content
            if clean_content.startswith("```json\n"):
                clean_content = clean_content[8:]
            elif clean_content.startswith("```\n"):
                clean_content = clean_content[4:]
                
            full_content += clean_content
            finish_reason = resp.choices[0].finish_reason
            continuation_count += 1
            
        if finish_reason == "length":
            print("Warning: Reached maximum continuations. Plan may still be truncated.")
            
        print("Vision analysis complete.")
        return full_content
