# Quick Start Guide - Image Reference Drawing

## Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Verify configuration in .env:**
   ```
   GROQ_API_KEY=your_key_here
   GROQ_MODEL=openai/gpt-oss-120b
   GROQ_VISION_MODEL=qwen/qwen3.6-27b
   KRITA_MCP_SERVER=C:\path\to\krita-mcp\server.py
   KRITA_URL=http://127.0.0.1:5678
   ```

3. **Make sure Krita is running** with the MCP server active

## Usage

### Option 1: Interactive Mode

```bash
python main.py
```

**For text-only drawing:**
- Press Enter when asked for image path
- Type your drawing request

**For image reference:**
- Enter path to your image file
- Describe what you want drawn

### Option 2: Quick Test with Sample Images

```bash
# Generate test images
python create_test_image.py

# Test with simple character
python test_reference_drawing.py test_simple_character.png

# Test with detailed character
python test_reference_drawing.py test_detailed_character.png "Draw this accurately"
```

### Option 3: Your Own Images

```bash
python test_reference_drawing.py path/to/your/image.png "Your prompt here"
```

## What to Expect

### Text Mode (Original)
```
> Draw a red circle in the center

Groq → Plans drawing → Executes in Krita
Time: ~2-5 seconds
```

### Image Reference Mode (New)
```
Image: character.png
> Recreate this character

Loading image → Groq Vision analyzes → Creates drawing plan → Executes in Krita
Time: ~10-20 seconds

Progress output:
========== IMAGE REFERENCE MODE ==========
Reference image: character.png
Sending image to Groq Vision...
Vision analysis complete.
Converting vision analysis to drawing commands...
Created 5 drawing batches from 23 elements
  Batch 1: color=#000000, brush_size=3, strokes=8
  Batch 2: color=#f5d7b8, brush_size=3, strokes=4
  ...

========== EXECUTING DRAWING FROM REFERENCE ==========
Executing batch 1/5...
  Color: #000000
  Brush size: 3
  Strokes: 8
  Progress: 8/8 strokes
  Batch complete: 8/8 strokes drawn
...

========== DRAWING COMPLETE ==========
Total batches: 5
Total MCP calls: 47
Execution time: 12.34s

The reference image has been recreated in Krita using actual drawing operations.
Check your Krita canvas to see the result.
```

## Troubleshooting

### "KRITA_MCP_SERVER not set in .env"
- Edit `.env` and set the path to your Krita MCP server.py

### "Missing GROQ_API_KEY"
- Add your Groq API key to `.env`

### "Image file not found"
- Check the path is correct
- Use absolute path or path relative to project directory
- On Windows, use forward slashes: `C:/path/to/image.png`

### "No valid JSON found in vision response"
- The vision model might not support structured output
- Try a different image (simpler, clearer)
- Check that GROQ_VISION_MODEL is set correctly

### "Connection refused" / "MCP client not started"
- Make sure Krita is running
- Check that Krita MCP server is active
- Verify KRITA_URL in .env matches Krita's server

## Testing Without Groq API

To verify the code without API calls:

```bash
# Test the vision conversion module
python test_vision_module.py

# Test image creation
python create_test_image.py
```

## File Reference

**Core Files:**
- `main.py` - Main application entry point
- `groq_agent.py` - Groq API integration with vision support
- `vision_to_drawing.py` - Vision analysis to drawing conversion
- `mcp_client.py` - Krita MCP client wrapper
- `config.py` - Configuration management

**Test/Example Files:**
- `test_reference_drawing.py` - Image reference test script
- `create_test_image.py` - Generate test images
- `test_vision_module.py` - Unit tests for vision module

**Documentation:**
- `README.md` - Project overview
- `IMAGE_REFERENCE_GUIDE.md` - Detailed feature guide
- `IMPLEMENTATION_SUMMARY.md` - Technical implementation details
- `VERIFICATION_CHECKLIST.md` - Implementation verification
- `QUICK_START.md` - This file

**Configuration:**
- `.env` - Environment variables (API keys, model names)
- `requirements.txt` - Python dependencies

## Next Steps

1. Try the simple test image first to verify setup
2. Try your own reference images (PNG, JPG, WEBP)
3. Experiment with different prompts for better accuracy
4. For animation: Use the existing frame/keyframe tools (unchanged)

## Support

For issues or questions:
1. Check the troubleshooting sections
2. Review IMAGE_REFERENCE_GUIDE.md for detailed documentation
3. Verify all dependencies are installed
4. Ensure Krita and MCP server are running
