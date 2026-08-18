"""Convert detailed vision analysis JSON into Krita MCP drawing commands."""
import json
import re
from typing import Dict, List, Any, Tuple


def extract_json_from_response(response: str) -> Dict[str, Any]:
    """Extract JSON from vision model response, handling markdown code blocks and thinking tags."""
    # Remove <think> tags if present (Qwen thinking mode)
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


def denormalize_points(normalized_points: List[List[float]], 
                       target_width: int, 
                       target_height: int) -> List[List[int]]:
    """Convert normalized coordinates (0.0-1.0) to actual canvas coordinates."""
    denormalized = []
    for point in normalized_points:
        x_norm, y_norm = point[0], point[1]
        x = int(x_norm * target_width)
        y = int(y_norm * target_height)
        # Clamp to canvas bounds
        x = max(0, min(target_width - 1, x))
        y = max(0, min(target_height - 1, y))
        denormalized.append([x, y])
    
    return denormalized


def smooth_stroke_points(points: List[List[int]], smoothing_factor: float = 0.3) -> List[List[int]]:
    """Apply light smoothing to stroke points to reduce jitter."""
    if len(points) < 3:
        return points
    
    smoothed = [points[0]]  # Keep first point
    
    for i in range(1, len(points) - 1):
        prev_p = points[i - 1]
        curr_p = points[i]
        next_p = points[i + 1]
        
        # Weighted average with neighbors
        smooth_x = int(prev_p[0] * smoothing_factor/2 + curr_p[0] * (1 - smoothing_factor) + next_p[0] * smoothing_factor/2)
        smooth_y = int(prev_p[1] * smoothing_factor/2 + curr_p[1] * (1 - smoothing_factor) + next_p[1] * smoothing_factor/2)
        
        smoothed.append([smooth_x, smooth_y])
    
    smoothed.append(points[-1])  # Keep last point
    
    return smoothed


def interpolate_points(points: List[List[int]], target_density: int = 20) -> List[List[int]]:
    """Increase point density for smoother curves by linear interpolation."""
    if len(points) < 2 or len(points) >= target_density:
        return points
    
    interpolated = []
    total_segments = len(points) - 1
    points_per_segment = max(2, target_density // total_segments)
    
    for i in range(len(points) - 1):
        p1 = points[i]
        p2 = points[i + 1]
        
        interpolated.append(p1)
        
        # Add intermediate points
        for j in range(1, points_per_segment):
            t = j / points_per_segment
            interp_x = int(p1[0] + t * (p2[0] - p1[0]))
            interp_y = int(p1[1] + t * (p2[1] - p1[1]))
            interpolated.append([interp_x, interp_y])
    
    interpolated.append(points[-1])
    
    return interpolated


def process_component_strokes(component: Dict[str, Any], 
                              target_width: int, 
                              target_height: int) -> List[Dict[str, Any]]:
    """Process all strokes in a component, converting normalized coords to canvas coords."""
    processed_strokes = []
    
    strokes = component.get("strokes", [])
    component_name = component.get("name", "unknown")
    
    for stroke_idx, stroke in enumerate(strokes):
        normalized_points = stroke.get("normalized_points", [])
        
        if len(normalized_points) < 2:
            continue
        
        # Convert normalized coordinates to canvas coordinates
        canvas_points = denormalize_points(normalized_points, target_width, target_height)
        
        # Interpolate if needed for smoother curves
        if len(canvas_points) < 15:
            canvas_points = interpolate_points(canvas_points, target_density=20)
        
        # Apply light smoothing
        canvas_points = smooth_stroke_points(canvas_points, smoothing_factor=0.2)
        
        processed_stroke = {
            "points": canvas_points,
            "color": stroke.get("color", "#000000"),
            "brush_size": stroke.get("brush_size", 3),
            "closed": stroke.get("closed", False),
            "component": component_name,
            "order": component.get("order", 999)
        }
        
        processed_strokes.append(processed_stroke)
    
    return processed_strokes


def vision_plan_to_drawing_batches(vision_response: str, 
                                   target_width: int = 800, 
                                   target_height: int = 600) -> List[Dict[str, Any]]:
    """Convert detailed vision analysis JSON into batched drawing commands.
    
    New format: component-based with normalized coordinates.
    
    Returns a list of batch objects, each containing:
    - color: hex color code
    - brush_size: integer
    - strokes: list of stroke objects with points
    - complete: boolean (true only for the last batch)
    """
    # Extract JSON from response
    plan = extract_json_from_response(vision_response)
    
    # Check for new component-based format
    if "components" in plan:
        return _process_component_based_plan(plan, target_width, target_height)
    
    # Fallback to old element-based format for backward compatibility
    return _process_legacy_element_plan(plan, target_width, target_height)


def _process_component_based_plan(plan: Dict[str, Any], 
                                   target_width: int, 
                                   target_height: int) -> List[Dict[str, Any]]:
    """Process new component-based vision plan with normalized coordinates."""
    canvas = plan.get("canvas", {"width": target_width, "height": target_height})
    components = plan.get("components", [])
    
    if not components:
        print("Warning: No components found in vision analysis")
        return []
    
    print(f"Processing {len(components)} components from vision analysis...")
    
    # Sort components by order
    components_sorted = sorted(components, key=lambda c: c.get("order", 999))
    
    # Process all strokes from all components
    all_strokes = []
    for component in components_sorted:
        component_strokes = process_component_strokes(component, target_width, target_height)
        all_strokes.extend(component_strokes)
        
        component_name = component.get("name", "unknown")
        print(f"  Component '{component_name}': {len(component_strokes)} strokes")
    
    # Group strokes by (color, brush_size) for efficient batching
    stroke_groups: Dict[Tuple[str, int], List[Dict]] = {}
    
    for stroke in all_strokes:
        color = stroke.get("color", "#000000")
        brush_size = stroke.get("brush_size", 3)
        key = (color, brush_size)
        
        if key not in stroke_groups:
            stroke_groups[key] = []
        
        stroke_groups[key].append(stroke)
    
    # Create batches
    batches = []
    group_items = list(stroke_groups.items())
    
    for idx, ((color, brush_size), strokes) in enumerate(group_items):
        is_last = (idx == len(group_items) - 1)
        
        batch = {
            "color": color,
            "brush_size": brush_size,
            "strokes": strokes,
            "complete": is_last
        }
        batches.append(batch)
    
    print(f"Created {len(batches)} drawing batches from {len(all_strokes)} total strokes")
    for i, batch in enumerate(batches):
        print(f"  Batch {i+1}: color={batch['color']}, brush_size={batch['brush_size']}, strokes={len(batch['strokes'])}")
    
    return batches


def _process_legacy_element_plan(plan: Dict[str, Any], 
                                  target_width: int, 
                                  target_height: int) -> List[Dict[str, Any]]:
    """Process old element-based plan format for backward compatibility."""
    import math
    
    canvas = plan.get("canvas", {"width": 800, "height": 600})
    source_width = canvas.get("width", 800)
    source_height = canvas.get("height", 600)
    
    elements = plan.get("elements", [])
    
    if not elements:
        print("Warning: No elements found in vision analysis")
        return []
    
    print(f"Processing {len(elements)} elements (legacy format)...")
    
    # Sort elements by order if specified
    elements_sorted = sorted(elements, key=lambda e: e.get("order", 999))
    
    # Group elements by color and brush_size
    color_groups: Dict[tuple, List[Dict]] = {}
    
    for element in elements_sorted:
        element_type = element.get("type", "stroke")
        if element_type in ("ellipse", "rectangle") and "outline_color" in element:
            color = element.get("outline_color", "#000000")
        else:
            color = element.get("color", "#000000")
        
        brush_size = element.get("brush_size", 3)
        
        # Convert element to stroke
        stroke = _convert_legacy_element(element, source_width, source_height, target_width, target_height)
        
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
    
    print(f"Created {len(batches)} drawing batches from {len(elements)} elements (legacy format)")
    
    return batches


def _convert_legacy_element(element: Dict[str, Any], 
                            source_width: int, 
                            source_height: int,
                            target_width: int, 
                            target_height: int) -> Dict[str, Any]:
    """Convert old element format to stroke (for backward compatibility)."""
    import math
    
    element_type = element.get("type", "stroke")
    
    if element_type == "ellipse":
        center = element.get("center", [400, 300])
        width = element.get("width", 100)
        height = element.get("height", 100)
        
        # Create ellipse as polyline
        cx, cy = center
        rx = width / 2
        ry = height / 2
        points = []
        num_points = 36
        for i in range(num_points + 1):
            angle = (2 * math.pi * i) / num_points
            x = int(cx + rx * math.cos(angle))
            y = int(cy + ry * math.sin(angle))
            points.append([x, y])
        
        # Normalize to target
        scale_x = target_width / source_width
        scale_y = target_height / source_height
        points = [[int(p[0] * scale_x), int(p[1] * scale_y)] for p in points]
    
    elif element_type == "rectangle":
        if "top_left" in element:
            top_left = element.get("top_left", [0, 0])
            width = element.get("width", 100)
            height = element.get("height", 100)
            x, y = top_left
            points = [
                [int(x), int(y)],
                [int(x + width), int(y)],
                [int(x + width), int(y + height)],
                [int(x), int(y + height)],
                [int(x), int(y)]
            ]
        else:
            points = element.get("points", [[0, 0], [100, 100]])
        
        # Normalize to target
        scale_x = target_width / source_width
        scale_y = target_height / source_height
        points = [[int(p[0] * scale_x), int(p[1] * scale_y)] for p in points]
    
    else:  # stroke
        points = element.get("points", [[0, 0], [100, 100]])
        
        # Normalize to target
        scale_x = target_width / source_width
        scale_y = target_height / source_height
        points = [[int(p[0] * scale_x), int(p[1] * scale_y)] for p in points]
    
    return {
        "points": points,
        "description": element.get("description", ""),
    }


def create_drawing_plan_prompt(user_prompt: str) -> str:
    """Create enhanced prompt for detailed drawing from reference image."""
    return f"""{user_prompt}

CRITICAL: Analyze the reference image in DETAIL and capture ACTUAL VISUAL GEOMETRY, not just object descriptions.

Focus on:
- Tracing actual contours as polylines (not simplifying to ellipses/rectangles)
- Using normalized coordinates (0.0-1.0) for precision
- Capturing facial features separately (eyebrows, eyes, nose, mouth)
- Preserving line weight variations
- Including ALL visible details (hair strands, fingers, clothing folds)
- Extracting actual colors from the image
- Using high point density for smooth curves (20-30+ points)

The goal is to recreate the reference's ACTUAL APPEARANCE, not a generic interpretation."""
