"""Convert vision analysis JSON into Krita MCP drawing commands."""
import json
import re
from typing import Dict, List, Any


def extract_json_from_response(response: str) -> Dict[str, Any]:
    """Extract JSON from vision model response, handling markdown code blocks and thinking tags."""
    # Remove <think> tags if present (Qwen thinking mode)
    import re
    response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
    
    # Remove </think> orphan tags
    response = response.replace('</think>', '').replace('<think>', '')
    
    # Try to find JSON in code blocks first
    code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
    if code_block_match:
        json_str = code_block_match.group(1)
        return json.loads(json_str)
    
    # Try to find raw JSON object
    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if json_match:
        json_str = json_match.group(0)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # If direct parse fails, try to clean up common issues
            # Remove trailing commas before closing braces/brackets
            json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
            return json.loads(json_str)
    
    raise ValueError("No valid JSON found in vision response")


def normalize_coordinates(points: List[List[float]], 
                         source_width: int, 
                         source_height: int,
                         target_width: int = 800, 
                         target_height: int = 600) -> List[List[int]]:
    """Normalize coordinates from source canvas to target canvas."""
    scale_x = target_width / source_width
    scale_y = target_height / source_height
    
    normalized = []
    for point in points:
        x, y = point[0], point[1]
        new_x = int(x * scale_x)
        new_y = int(y * scale_y)
        normalized.append([new_x, new_y])
    
    return normalized


def create_ellipse_stroke_approximation(center: List[float], 
                                        width: float, 
                                        height: float, 
                                        num_points: int = 36) -> List[List[int]]:
    """Create a stroke that approximates an ellipse using points."""
    import math
    
    cx, cy = center
    rx = width / 2
    ry = height / 2
    
    points = []
    for i in range(num_points + 1):  # +1 to close the ellipse
        angle = (2 * math.pi * i) / num_points
        x = int(cx + rx * math.cos(angle))
        y = int(cy + ry * math.sin(angle))
        points.append([x, y])
    
    return points


def create_rectangle_stroke(top_left: List[float], 
                            width: float, 
                            height: float) -> List[List[int]]:
    """Create a stroke that draws a rectangle."""
    x, y = top_left
    return [
        [int(x), int(y)],
        [int(x + width), int(y)],
        [int(x + width), int(y + height)],
        [int(x), int(y + height)],
        [int(x), int(y)]  # Close the rectangle
    ]


def convert_element_to_stroke(element: Dict[str, Any], 
                              source_width: int, 
                              source_height: int,
                              target_width: int = 800, 
                              target_height: int = 600) -> Dict[str, Any]:
    """Convert a single vision element to a Krita stroke."""
    element_type = element.get("type", "stroke")
    
    if element_type == "ellipse":
        center = element.get("center", [400, 300])
        width = element.get("width", 100)
        height = element.get("height", 100)
        points = create_ellipse_stroke_approximation(center, width, height)
        points = normalize_coordinates(points, source_width, source_height, target_width, target_height)
    
    elif element_type == "rectangle":
        # Can have either top_left + width/height or points
        if "top_left" in element:
            top_left = element.get("top_left", [0, 0])
            width = element.get("width", 100)
            height = element.get("height", 100)
            points = create_rectangle_stroke(top_left, width, height)
            points = normalize_coordinates(points, source_width, source_height, target_width, target_height)
        else:
            points = element.get("points", [[0, 0], [100, 100]])
            points = normalize_coordinates(points, source_width, source_height, target_width, target_height)
    
    else:  # stroke or any other type
        points = element.get("points", [[0, 0], [100, 100]])
        points = normalize_coordinates(points, source_width, source_height, target_width, target_height)
    
    return {
        "points": points,
        "description": element.get("description", ""),
    }


def vision_plan_to_drawing_batches(vision_response: str, 
                                   target_width: int = 800, 
                                   target_height: int = 600) -> List[Dict[str, Any]]:
    """Convert vision analysis JSON into batched drawing commands grouped by color.
    
    Returns a list of batch objects, each containing:
    - color: hex color code
    - brush_size: integer
    - strokes: list of stroke objects with points
    - complete: boolean (true only for the last batch)
    """
    # Extract JSON from response
    plan = extract_json_from_response(vision_response)
    
    canvas = plan.get("canvas", {"width": 800, "height": 600})
    source_width = canvas.get("width", 800)
    source_height = canvas.get("height", 600)
    
    elements = plan.get("elements", [])
    
    if not elements:
        print("Warning: No elements found in vision analysis")
        return []
    
    # Sort elements by order if specified
    elements_sorted = sorted(elements, key=lambda e: e.get("order", 999))
    
    # Group elements by color and brush_size
    color_groups: Dict[tuple, List[Dict]] = {}
    
    for element in elements_sorted:
        # Determine which color to use (prefer outline_color for shapes, regular color for strokes)
        element_type = element.get("type", "stroke")
        if element_type in ("ellipse", "rectangle") and "outline_color" in element:
            color = element.get("outline_color", "#000000")
        else:
            color = element.get("color", "#000000")
        
        brush_size = element.get("brush_size", 3)
        
        # Convert element to stroke
        stroke = convert_element_to_stroke(element, source_width, source_height, target_width, target_height)
        
        # Group by (color, brush_size)
        key = (color, brush_size)
        if key not in color_groups:
            color_groups[key] = []
        color_groups[key].append(stroke)
    
    # Convert groups to batches
    batches = []
    group_items = list(color_groups.items())
    
    for idx, ((color, brush_size), strokes) in enumerate(group_items):
        is_last = (idx == len(group_items) - 1)
        
        batch = {
            "color": color,
            "brush_size": brush_size,
            "strokes": strokes,
            "complete": is_last
        }
        batches.append(batch)
    
    print(f"Created {len(batches)} drawing batches from {len(elements)} elements")
    for i, batch in enumerate(batches):
        print(f"  Batch {i+1}: color={batch['color']}, brush_size={batch['brush_size']}, strokes={len(batch['strokes'])}")
    
    return batches


def create_drawing_plan_prompt(user_prompt: str) -> str:
    """Create enhanced prompt for drawing from reference image."""
    return f"""{user_prompt}

Analyze the reference image and create an accurate reproduction using the available drawing tools.
Focus on capturing:
- Overall composition and layout
- Character/object proportions and positioning
- Facial features and expressions (if present)
- Colors and shading
- Line quality and curves
- Important details

Create a complete, accurate drawing that preserves the visual characteristics of the reference."""
