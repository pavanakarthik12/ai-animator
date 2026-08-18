"""Test JSON extraction with thinking tags."""
from vision_to_drawing import extract_json_from_response

# Test 1: Response with <think> tags
test_response_1 = """<think>
This is thinking content that should be removed.
The user wants JSON.
</think>
{
  "canvas": {"width": 800, "height": 600},
  "elements": [{"type": "ellipse", "center": [400, 300]}]
}
"""

print("Test 1: Response with <think> tags")
try:
    result = extract_json_from_response(test_response_1)
    print("✓ Success! Extracted JSON")
    print(f"  Canvas: {result['canvas']}")
    print(f"  Elements: {len(result['elements'])}")
except Exception as e:
    print(f"✗ Failed: {e}")

# Test 2: Response with trailing comma (common JSON error)
test_response_2 = """{
  "canvas": {"width": 800, "height": 600},
  "elements": [
    {"type": "ellipse", "center": [400, 300]},
  ]
}"""

print("\nTest 2: Response with trailing comma")
try:
    result = extract_json_from_response(test_response_2)
    print("✓ Success! Fixed trailing comma")
    print(f"  Canvas: {result['canvas']}")
except Exception as e:
    print(f"✗ Failed: {e}")

# Test 3: Normal JSON
test_response_3 = """{
  "canvas": {"width": 800, "height": 600},
  "elements": []
}"""

print("\nTest 3: Normal JSON")
try:
    result = extract_json_from_response(test_response_3)
    print("✓ Success!")
    print(f"  Canvas: {result['canvas']}")
except Exception as e:
    print(f"✗ Failed: {e}")

print("\n" + "="*50)
print("All JSON extraction tests completed!")
