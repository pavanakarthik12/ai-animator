# Image Reference Drawing Feature Guide

## Overview

The Image Reference Drawing feature allows you to upload a reference image and have the AI analyze it using Groq Vision, then recreate it in Krita using actual drawing operations (strokes, shapes, colors).

**IMPORTANT:** The reference image is NOT imported into Krita. The AI analyzes the image and recreates it using drawing commands.

## How It Works

```
Reference Image
      ↓
Groq Vision Analysis
      ↓
Structured Drawing Plan (JSON)
      ↓
Convert to Drawing Primitives
      ↓
Batch MCP Drawing Commands
      ↓
Krita Canvas (Actual Strokes)
```

## Setup

1. Install dependencies (if not already done):
```bash
pip install -r requirements.txt
```

2. Ensure your `.env` file contains:
```bash
GROQ_API_KEY=your_key_here
GROQ_MODEL=openai/gpt-oss-120b
GROQ_VISION_MODEL=qwen/qwen3.6-27b
KRITA_MCP_SERVER=path/to/krita-mcp/server.py
```

## Usage

### Method 1: Interactive Mode

```bash
python main.py
```

When prompted:
1. Enter the path to your reference image (PNG, JPG, JPEG, or WEBP)
2. Enter what you want to draw (or press Enter for default prompt)

Example:
```
Image path (or press Enter to skip): my_character.png
What should I draw based on this reference?
> Recreate this character in Krita as accurately as possible.
```

### Method 2: Test Script

```bash
python test_reference_drawing.py <image_path> [prompt]
```

Examples:
```bash
python test_reference_drawing.py reference.png
python test_reference_drawing.py character.jpg "Draw this character"
python test_reference_drawing.py scene.png "Recreate this scene with accurate colors and proportions"
```

### Method 3: Environment Variables

```bash
set REFERENCE_IMAGE=path/to/image.png
set AUTOMATION_PROMPT="Draw this accurately"
python main.py
```

## Supported Image Formats

- PNG (.png)
- JPEG (.jpg, .jpeg)
- WebP (.webp)

## What Gets Analyzed

The Groq Vision model analyzes:

- **Composition**: Overall layout and structure
- **Shapes**: Circles, ellipses, rectangles, curves
- **Proportions**: Relative sizes and positions
- **Colors**: Hex color codes for all elements
- **Details**: Facial features, clothing, objects
- **Layer Order**: Background to foreground elements

## Drawing Process

1. **Vision Analysis**: Image is sent to Groq Vision model with detailed prompt
2. **Structured Plan**: AI returns JSON with canvas size and drawable elements:
   ```json
   {
     "canvas": {"width": 800, "height": 600},
     "elements": [
       {
         "type": "ellipse",
         "center": [400, 300],
         "width": 150,
         "height": 180,
         "color": "#f5d7b8",
         "brush_size": 3
       }
     ]
   }
   ```
3. **Coordinate Normalization**: Positions scaled to Krita canvas (800x600 default)
4. **Batching**: Elements grouped by color for efficient drawing
5. **Execution**: MCP commands sent to Krita in batches

## Accuracy Tips

For best results:

1. **Use clear, well-lit reference images**
2. **Avoid overly complex backgrounds** (or they'll be simplified)
3. **Simple cartoon-style images work best** initially
4. **Provide descriptive prompts** like:
   - "Recreate this character with accurate proportions and colors"
   - "Draw this scene focusing on the main subject"
   - "Reproduce this with attention to facial features"

## Testing

Create test images:
```bash
python create_test_image.py
```

This generates:
- `test_simple_character.png` - Basic stick figure
- `test_detailed_character.png` - More detailed character

Test with:
```bash
python test_reference_drawing.py test_simple_character.png
python test_reference_drawing.py test_detailed_character.png
```

## Troubleshooting

### "No valid JSON found in vision response"
- The vision model didn't return structured JSON
- Try a clearer image or more specific prompt
- Check that GROQ_VISION_MODEL is correctly set

### "Image file not found"
- Verify the image path is correct
- Use absolute path or path relative to project root
- On Windows, use `\\` or `/` in paths, not single `\`

### "Unsupported image format"
- Only PNG, JPG, JPEG, WEBP are supported
- Convert image to supported format

### Drawing looks wrong
- Vision model interpretation may differ from reference
- Try more descriptive prompt
- Use simpler reference images initially
- Check that colors and proportions are clearly visible

## Limitations

1. **Complexity**: Very detailed images may be simplified
2. **Accuracy**: AI interpretation, not pixel-perfect reproduction
3. **Style**: Best with cartoon/illustration style, not photorealistic
4. **Elements**: Limited to strokes, ellipses, rectangles (no fill patterns, gradients, etc.)
5. **Text**: Text in images will be drawn as shapes, not as text

## Comparison with Text Mode

### Text Mode (Original)
```bash
python main.py
> Draw a red circle in the center
```
- AI imagines what to draw
- Simple, direct commands
- Good for geometric shapes and simple scenes

### Image Reference Mode (New)
```bash
python test_reference_drawing.py character.png "Draw this"
```
- AI sees actual reference
- Accurate proportions and colors
- Good for recreating existing artwork

**Both modes use the same underlying MCP drawing tools**, so quality depends on the drawing commands generated, not on the input method.

## Advanced: Correction Passes (Future)

The `MAX_CORRECTION_PASSES` config (default: 2) is reserved for future enhancement where:
1. Initial drawing is created
2. Vision model compares result to reference
3. Corrections generated if needed
4. Process repeats up to max passes

Currently, drawing executes once without correction loops.

## Architecture

```python
# Vision Analysis
vision_response = agent.analyze_image(image_path, prompt)

# Convert to Drawing Batches
batches = vision_plan_to_drawing_batches(vision_response)

# Each batch contains:
{
  "color": "#ff0000",
  "brush_size": 3,
  "strokes": [{"points": [[x1,y1], [x2,y2], ...]}, ...],
  "complete": True/False
}

# Execute via MCP
for batch in batches:
    mcp.call_tool("krita_set_color", {"color": batch["color"]})
    mcp.call_tool("krita_set_brush", {"size": batch["brush_size"]})
    for stroke in batch["strokes"]:
        mcp.call_tool("krita_stroke", {"points": stroke["points"]})
```

## See Also

- README.md - General project documentation
- test_reference_drawing.py - Example usage script
- vision_to_drawing.py - Implementation details
