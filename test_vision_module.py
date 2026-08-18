"""Test the vision_to_drawing module."""
from vision_to_drawing import (
    extract_json_from_response,
    vision_plan_to_drawing_batches,
    denormalize_points,
    interpolate_points
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

def test_coordinate_denormalization():
    """Test coordinate denormalization from 0-1 to canvas coords."""
    normalized_points = [[0.0, 0.0], [0.5, 0.5], [1.0, 1.0]]
    canvas_points = denormalize_points(normalized_points, 800, 600)
    assert canvas_points[0] == [0, 0]
    assert canvas_points[1] == [400, 300]
    assert canvas_points[2] == [799, 599]
    print("✓ Test 3: Coordinate denormalization - PASSED")

def test_interpolation():
    """Test point interpolation for smoother curves."""
    points = [[0, 0], [100, 100]]
    interpolated = interpolate_points(points, target_density=10)
    assert len(interpolated) >= len(points)
    assert interpolated[0] == points[0]
    assert interpolated[-1] == points[-1]
    print("✓ Test 4: Point interpolation - PASSED")

def test_full_pipeline():
    """Test complete vision response to drawing batches (NEW FORMAT)."""
    vision_response = """
```json
{
  "canvas": {"width": 400, "height": 400},
  "analysis": "Test character",
  "components": [
    {
      "name": "head_contour",
      "order": 10,
      "strokes": [
        {
          "normalized_points": [[0.5, 0.2], [0.6, 0.3], [0.5, 0.4], [0.4, 0.3], [0.5, 0.2]],
          "color": "#000000",
          "brush_size": 4,
          "closed": true
        }
      ]
    },
    {
      "name": "left_eye",
      "order": 30,
      "strokes": [
        {
          "normalized_points": [[0.4, 0.3], [0.45, 0.3]],
          "color": "#000000",
          "brush_size": 2,
          "closed": false
        }
      ]
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
    print("✓ Test 5: Full pipeline (NEW FORMAT) - PASSED")
    print(f"  Generated {len(batches)} batches")

def test_legacy_format():
    """Test backward compatibility with old element-based format."""
    vision_response = """
{
  "canvas": {"width": 400, "height": 400},
  "elements": [
    {
      "order": 1,
      "type": "stroke",
      "points": [[200, 200], [200, 300]],
      "color": "#ff0000",
      "brush_size": 5
    }
  ]
}
"""
    batches = vision_plan_to_drawing_batches(vision_response)
    assert len(batches) > 0
    print("✓ Test 6: Legacy format compatibility - PASSED")

if __name__ == "__main__":
    print("Testing vision_to_drawing module...\n")
    
    try:
        test_json_extraction()
        test_coordinate_denormalization()
        test_interpolation()
        test_full_pipeline()
        test_legacy_format()
        
        print("\n" + "="*50)
        print("ALL TESTS PASSED ✓")
        print("="*50)
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
