# Groq + Krita Drawing Agent - Usage Guide

## Interactive Mode (Default)

Simply run:
```powershell
python main.py
```

The application will wait for your input and guide you through the process:

### Text-Only Drawing Example:
```
============================================================
AI KRITA DRAWING AGENT
============================================================

Waiting for user input...

What do you want to draw?
> Draw a red circle.

User request received.

Do you want to use a reference image? (y/n)
> n

Reference mode: NO

[Groq processes request → MCP draws in Krita]
```

### Reference Image Drawing Example:
```
============================================================
AI KRITA DRAWING AGENT
============================================================

Waiting for user input...

What do you want to draw?
> Recreate this character

User request received.

Do you want to use a reference image? (y/n)
> y

Reference mode: YES

Waiting for reference image...
Enter the reference image path:
> C:\Users\YourName\Pictures\character.png

Reference image loaded: C:\Users\YourName\Pictures\character.png

Waiting for reference instructions...
What do you want me to do with this reference?
Examples:
  - Recreate this character accurately, preserving all details.
  - Use this character but raise the right arm.
  - Create two frames with this character waving.
> Recreate this character accurately, preserving all visible details.

Instructions received.

[Computer vision extracts geometry → Groq organizes → MCP draws in Krita]
```

## Automation Mode (Testing/Scripting)

For automated testing or scripting, you can use environment variables to bypass interactive prompts:

### Text-Only Drawing (Automation):
```powershell
$env:AUTOMATION_PROMPT="Draw a red circle."
python main.py
```

### Reference Image Drawing (Automation):
```powershell
$env:REFERENCE_IMAGE="C:\path\to\image.png"
$env:AUTOMATION_PROMPT="Recreate this accurately"
python main.py
```

## Supported Image Formats

- PNG (.png)
- JPEG (.jpg, .jpeg)
- WebP (.webp)

## Features

1. **Text-Based Drawing**: Describe what you want, AI draws it
2. **Reference Image Drawing**: Upload an image, AI recreates it using computer vision geometry extraction
3. **Reference + Instructions**: Upload image + provide custom instructions (e.g., "raise the arm")
4. **Animation**: Create multiple frames with the same or modified character
5. **Fast Batched Drawing**: Efficient MCP batching for speed
6. **Actual Krita Integration**: Real drawing operations in Krita, not image generation

## Important Notes

- The application WAITS for user input - it does NOT draw automatically on startup
- Each request = ONE drawing operation
- No automatic repeating or test generation in normal mode
- Reference images use computer vision to extract actual geometry (not AI hallucination)
- All drawing happens via MCP tools in actual Krita canvas
