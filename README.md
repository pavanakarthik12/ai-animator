# Groq → Krita MCP Agent

This project connects a Groq model to the Krita MCP server to let the model control Krita directly via MCP tools.

## Features

- **Text-to-Drawing**: Natural language drawing commands → Krita artwork
- **Image Reference Drawing**: Upload reference image → AI analyzes → Reproduces in Krita using actual drawing operations
- **Animation Support**: Create multi-frame animations with keyframes
- **Batched Operations**: Efficient drawing with minimal API calls

## Quick Start

1. Copy your Groq API key to `.env` as `GROQ_API_KEY` and set `GROQ_MODEL` and `KRITA_MCP_SERVER`.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run:

```bash
python main.py
```

## Usage Modes

### Mode 1: Text-Only Drawing

Type a request like: `Draw a simple circle in the center of the canvas.`

The agent will ask Groq for a tool call and execute the discovered MCP tool.

### Mode 2: Image Reference Drawing (NEW!)

Provide a reference image and the AI will analyze it and recreate it in Krita:

**Interactive:**
```bash
python main.py
# When prompted, enter the path to your reference image
# Then describe what you want drawn
```

**Programmatic:**
```bash
python test_reference_drawing.py path/to/reference.png "Recreate this character"
```

**How it works:**
1. Reference image is sent to Groq Vision model
2. AI analyzes composition, colors, shapes, proportions, details
3. Creates structured drawing plan with primitives (strokes, ellipses, rectangles)
4. Executes plan using existing Krita MCP drawing tools
5. Result: Actual Krita strokes/shapes on canvas (NOT imported image)

**Supported formats:** PNG, JPG, JPEG, WEBP

## Configuration

Edit `.env`:

```bash
GROQ_API_KEY=your_api_key_here
GROQ_MODEL=openai/gpt-oss-120b              # Model for text-to-drawing
GROQ_VISION_MODEL=qwen/qwen3.6-27b          # Model for image analysis (Qwen 3.6 27B multimodal)
KRITA_MCP_SERVER=path/to/krita-mcp/server.py
KRITA_URL=http://127.0.0.1:5678
MAX_CORRECTION_PASSES=2                      # Optional: vision-based refinement passes
```

## Architecture

```
TEXT MODE:
  User prompt → Groq → Drawing plan → MCP batch → Krita

IMAGE REFERENCE MODE:
  Reference image → Groq Vision → Structured analysis → Drawing plan → MCP batch → Krita
```

The image is NEVER imported into Krita. It's only used as visual reference for the AI to analyze and recreate using actual drawing operations.
