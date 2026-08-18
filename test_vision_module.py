"""Test the vision_to_drawing module."""
from vision_to_drawing import (
    extract_json_from_response,
    vision_plan_to_drawing_batches,
    normalize_coordinates,
    create_ellipse_stroke_approximation
)

def test_json_extraction():
    """Test JSON extraction from various response formats."""
    # Test with markdown code block
    response1 = """Here is the analysis:
```json
{
  "canvas": {"width": 800, "height": 600},
  "elements": [{"type": "ellipse", "center": [400, 300], "width": 100, "height": 100, "color": "#ff0000"}]
}
```
"""
    result = extract_json_from_response(response1)
    assert "canvas" in result
    assert "elements" in result
    print("✓ Test 1: JSON in code block - PASSED")
    
    # Test with raw JSON
    response2 = '{"canvas": {"width": 800, "height": 600}, "elements": []}'
    result = extract_json_from_response(response2)
    assert "canvas" in result
    print("✓ Test 2: Raw JSON - PASSED")

def test_coordinate_normalization():
    """Test coordinate scaling."""
    points = [[100, 100], [200, 200]]
    normalized = normalize_coordinates(points, 400, 400, 800, 800)
    assert normalized[0] == [200, 200]
    assert normalized[1] == [400, 400]
    print("✓ Test 3: Coordinate normalization - PASSED")

def test_ellipse_creation():
    """Test ellipse stroke generation."""
    points = create_ellipse_stroke_approximation([100, 100], 50, 50, 12)
    assert len(points) == 13  # 12 points + 1 to close
    assert points[0] == points[-1]  # Should be closed
    print("✓ Test 4: Ellipse creation - PASSED")

def test_full_pipeline():
    """Test complete vision response to drawing batches."""
    vision_response = """
```json
{
  "canvas": {"width": 400, "height": 400},
  "elements": [
    {
      "order": 1,
      "type": "ellipse",
      "center": [200, 200],
      "width": 100,
      "height": 100,
      "outline_color": "#000000",
      "brush_size": 3
    },
    {
      "order": 2,
      "type": "stroke",
      "points": [[150, 250], [150, 350]],
      "color": "#ff0000",
      "brush_size": 5
    }
  ]
}
```
"""
    batches = vision_plan_to_drawing_batches(vision_response)
    assert len(batches) > 0
    assert all("color" in b for b in batches)
    assert all("strokes" in b for b in batches)
    assert batches[-1]["complete"] == True
    print("✓ Test 5: Full pipeline - PASSED")
    print(f"  Generated {len(batches)} batches")

if __name__ == "__main__":
    print("Testing vision_to_drawing module...\n")
    
    try:
        test_json_extraction()
        test_coordinate_normalization()
        test_ellipse_creation()
        test_full_pipeline()
        
        print("\n" + "="*50)
        print("ALL TESTS PASSED ✓")
        print("="*50)
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
