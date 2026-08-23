# CRITICAL NEXT STEP - Krita Plugin Reload Required

## The Bug Was Fixed

The Krita plugin had a **critical indentation bug**:
- `cmd_bulk_strokes()` method was placed OUTSIDE the `KritaMCPExtension` class
- When `execute_command` tried to call `self.cmd_bulk_strokes()`, Python couldn't find it
- This caused the error: `"Unknown action: bulk_strokes"`

**The fix is complete** - methods are now properly placed INSIDE the class.

## But Krita Hasn't Reloaded the Plugin Yet!

**YOU MUST RESTART KRITA** for the fixed plugin to take effect.

## Step-by-Step Instructions

### 1. Close Krita Completely
- Close all Krita windows
- Wait 3 seconds

### 2. Restart Krita
- Open Krita
- Wait for it to fully load
- The plugin should auto-start

### 3. Check Plugin Loaded
Look for this message in Krita's Scripting Console (Settings → Dockers → Scripting Console):
```
[KritaMCP] HTTP server started on port 5678
```

If you see this message: **Plugin is loaded**

If you don't see it:
- Plugin may not be installed correctly
- Check: `~/.local/share/krita/pykrita/kritamcp/`
- Or on Windows: `%APPDATA%\krita\pykrita\kritamcp\`

### 4. Create or Open a Document
- Create new (File → New) or open existing
- Canvas size: 800x600 recommended for testing
- Make sure you have a paint layer selected

### 5. Run the Test

```powershell
cd C:\Users\pavan\OneDrive\Desktop\groq-krita-agent
python test_bulk_api_simple.py
```

## What the Test Does

**Test 1: ONE Red Stroke**
- Draws a single horizontal red line at y=300
- Expected: You should SEE the red line in Krita

**Test 2: FIVE Colored Strokes**
- Draws 5 horizontal lines in different colors
- Expected: You should SEE all 5 lines in Krita

**Test 3: Old API Still Works**
- Tests backward compatibility
- Expected: Cyan line appears

## Success Criteria

After running the test, check your Krita canvas:

✓ Red horizontal line at (300,300) to (500,300)  
✓ 5 colored lines (red, green, blue, yellow, magenta)  
✓ Cyan line at (400,400) to (600,400)

If you see these lines: **BULK API IS FIXED AND WORKING**

## If Test Still Fails

### Symptom: "Unknown action: bulk_strokes"
**Cause:** Plugin not reloaded

**Fix:**
1. Verify Krita was actually closed and restarted
2. Check Krita scripting console for plugin load message
3. Try manually reloading: Settings → Configure Krita → Python Plugin Manager → Untick/Tick kritamcp

### Symptom: Connection errors
**Cause:** Plugin not running

**Fix:**
1. Check if plugin is in correct directory
2. Check Python console for errors  
3. Verify no firewall blocking localhost:5678

### Symptom: "No active paint layer"
**Cause:** No paint layer selected

**Fix:**
1. Create a paint layer (Layer → New → Paint Layer)
2. Make sure it's selected (highlighted in Layers docker)
3. Run test again

## After Tests Pass

Once all 3 tests pass and you see the strokes in Krita:

1. The bulk API is working correctly
2. You can proceed to test with real character drawing
3. Animation with bulk API should now work

## Technical Verification

If you want to verify the fix was applied correctly:

```powershell
# Check the plugin file has the methods in the right place
Select-String -Path "C:\Users\pavan\OneDrive\Desktop\krita-mcp\krita-plugin\kritamcp\__init__.py" -Pattern "def cmd_bulk_strokes" -Context 5,0
```

You should see:
```python
    def cmd_bulk_strokes(self, params):
```

With 4 spaces indentation (indicating it's inside the class), and appearing BEFORE the `Krita.instance().addExtension()` line.

## Next Steps After Verification

Once bulk API is confirmed working:

1. Test with reference image drawing
2. Test with animation (walk cycle)
3. Benchmark performance improvement
4. Compare before/after MCP call counts

**Expected improvement:**
- Before: 1000 MCP calls for 20 frames
- After: ~100 MCP calls for 20 frames  
- Time: 10-15 min → ~5-8 min (target)

## File Locations Reference

**MCP Server:** `C:\Users\pavan\OneDrive\Desktop\krita-mcp\server.py`
- Has `@mcp.tool() krita_bulk_strokes()` ✓

**Krita Plugin:** `C:\Users\pavan\OneDrive\Desktop\krita-mcp\krita-plugin\kritamcp\__init__.py`
- Line 242: `elif action == "bulk_strokes":` dispatch ✓
- Line 1311: `def cmd_bulk_strokes(self, params):` implementation ✓
- Line 1420: `def _draw_stroke_pixels(...)` helper ✓

**Test Script:** `c:\Users\pavan\OneDrive\Desktop\groq-krita-agent\test_bulk_api_simple.py`
- Ready to run after Krita restart

## The Root Cause (For Reference)

The original bulk API code was added with `fs_append` which:
1. Appended to the END of the file
2. This placed it AFTER the `Krita.instance().addExtension()` call
3. Methods were at module level, not class level
4. Python couldn't find `self.cmd_bulk_strokes()` when called

The fix:
1. Truncated file before the registration line
2. Added methods with proper 4-space indentation
3. Then added registration line
4. Methods are now INSIDE the class, BEFORE registration

**But the fix only takes effect after Krita restarts!**
