# Hotfix: JSON Mode and Thinking Tags

## Issue
The Qwen 3.6 27B vision model has a "thinking mode" that wraps responses in `<think>` tags, which interfered with JSON parsing:

```
<think>
The user wants a JSON drawing plan...
I need to break this down into primitives...
</think>
{
  "canvas": {...}
}
```

This caused JSON parsing errors because the `<think>` tags aren't valid JSON.

## Solution

### 1. Enable JSON Mode (Primary Fix)
Updated `groq_agent.py` to use Groq's JSON mode feature:

```python
resp = self._post_with_retry(
    model=self.vision_model,
    messages=messages,
    response_format={"type": "json_object"}  # Forces JSON-only output
)
```

This tells the model to return ONLY valid JSON, no thinking tags.

### 2. Improved JSON Extraction (Backup)
Enhanced `vision_to_drawing.py` to handle edge cases:

- **Remove `<think>` tags**: Strips thinking mode output if it appears
- **Fix trailing commas**: Common JSON error fixed automatically
- **Multiple extraction methods**: Code blocks → raw JSON → cleaned JSON

```python
def extract_json_from_response(response: str):
    # Remove <think> tags
    response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
    
    # Try code blocks, then raw JSON
    # Auto-fix trailing commas
    ...
```

### 3. Better Error Messages
Improved error handling in `main.py`:
- Clear error message if JSON parsing fails
- Shows preview of what was received
- Suggests model configuration fix

## Testing

Created `test_json_extraction.py` to verify:

```bash
python test_json_extraction.py
```

Results:
```
✓ Test 1: Response with <think> tags - PASSED
✓ Test 2: Response with trailing comma - PASSED  
✓ Test 3: Normal JSON - PASSED
```

## Files Modified

1. **groq_agent.py** - Added `response_format={"type": "json_object"}`
2. **vision_to_drawing.py** - Enhanced JSON extraction with `<think>` tag removal
3. **test_json_extraction.py** - New test file

## Expected Behavior Now

With `response_format={"type": "json_object"}`:
- Model returns ONLY JSON
- No thinking tags
- Valid JSON structure
- Ready for parsing

If thinking tags still appear (rare):
- Extraction automatically strips them
- Trailing commas auto-fixed
- Still successfully parses

## Testing Your Image Again

The same command should now work:

```bash
python test_reference_drawing.py "C:\Users\pavan\OneDrive\Pictures\Screenshots 1\Screenshot 2026-08-18 115136.png"
```

Expected output:
```
========== IMAGE REFERENCE MODE ==========
Reference image: ...
Sending image to Groq Vision (qwen/qwen3.6-27b)...
Vision analysis complete.

--- Vision Analysis ---
{
  "canvas": {"width": 800, "height": 800},
  "analysis": "Stick figure in thinking pose...",
  "elements": [...]
}

Converting vision analysis to drawing commands...
Created X drawing batches from Y elements
...
```

## Why JSON Mode?

According to [Groq's documentation](https://console.groq.com/docs/vision), qwen/qwen3.6-27b supports JSON mode:

> The qwen/qwen3.6-27b model supports JSON mode! 

This ensures structured output perfect for our drawing plan format.

## Status
✅ **FIXED** - JSON mode enabled, extraction improved, ready for testing
