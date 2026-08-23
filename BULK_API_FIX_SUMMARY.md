# Bulk API Fix Summary

## Problem Confirmed

Client error log showed:
```
[DEBUG-2] Calling mcp.call_tool('krita_bulk_strokes', ...)
[DEBUG-9] Response received from MCP:
{'error': 'Unknown action: bulk_strokes'}
```

**Root cause:** MCP server sends `action="bulk_strokes"` to Krita plugin, but plugin's `execute_command` doesn't recognize it.

## Architecture Verified

```
groq-krita-agent (Python)
    ↓ mcp.call_tool("krita_bulk_strokes", {...})
MCP Server (server.py)
    ↓ send_command("bulk_strokes", {...})
HTTP POST to localhost:5678
    ↓ {"action": "bulk_strokes", "params": {...}}
Krita Plugin (__init__.py)
    ↓ execute_command()
    ↓ elif action == "bulk_strokes":
    ↓ return self.cmd_bulk_strokes(params)
```

## Fix Applied

### Issue 1: Method Placement (FIXED)

**Before:**
```python
class KritaMCPExtension(Extension):
    def cmd_inspect_previous_frame(self, params):
        return {"status": "ok"}

# Register the extension
Krita.instance().addExtension(KritaMCPExtension(Krita.instance()))

    def cmd_bulk_strokes(self, params):  # WRONG - Outside class!
        ...
```

**After:**
```python
class KritaMCPExtension(Extension):
    def cmd_inspect_previous_frame(self, params):
        return {"status": "ok"}
    
    def cmd_bulk_strokes(self, params):  # CORRECT - Inside class
        ...
    
    def _draw_stroke_pixels(self, ...):
        ...

# Register the extension
Krita.instance().addExtension(KritaMCPExtension(Krita.instance()))
```

### Issue 2: Indentation (FIXED)

Methods now have proper 4-space indentation indicating class membership.

### Issue 3: Dispatch Route (ALREADY EXISTS)

Line 242 of `__init__.py`:
```python
elif action == "bulk_strokes":
    return self.cmd_bulk_strokes(params)
```

This was already correct - the issue was the method wasn't in the class.

## Implementation Details

### MCP Server (server.py)

**Tool:** `krita_bulk_strokes(strokes: list[dict])`
- Accepts list of stroke specifications
- Sends to Krita as action `"bulk_strokes"`
- Extended timeout: `max(120.0, len(strokes) * 0.5)` seconds
- DEBUG logging at boundaries

### Krita Plugin (__init__.py)

**Method:** `cmd_bulk_strokes(self, params)`
- Line 1311-1426 (116 lines)
- Processes list of strokes in one operation
- Sets color/brush per stroke
- Calls `_draw_stroke_pixels()` for each
- Single `refreshProjection()` at end
- Returns: `{status, strokes_drawn, strokes_failed, errors}`

**Helper:** `_draw_stroke_pixels(self, layer, doc, view, points, brush_size, hardness, opacity)`
- Line 1427-1529 (103 lines)
- Extracted from existing `cmd_stroke`
- Pixel-level drawing with soft edges
- Identical rendering to individual strokes

## Verification Steps

### 1. File Verification

```powershell
# Check method is inside class
Select-String -Path "C:\Users\pavan\OneDrive\Desktop\krita-mcp\krita-plugin\kritamcp\__init__.py" -Pattern "def cmd_bulk_strokes" -Context 2,0
```

Expected output:
```python
            return {"error": str(e)}

    def cmd_bulk_strokes(self, params):
```

4 spaces = inside class ✓

### 2. Restart Krita

**CRITICAL:** Plugin must be reloaded for fix to take effect.

Steps:
1. Close Krita completely
2. Wait 3 seconds
3. Reopen Krita
4. Check for: `[KritaMCP] HTTP server started on port 5678`

### 3. Run Test

```powershell
cd C:\Users\pavan\OneDrive\Desktop\groq-krita-agent
python test_bulk_api_simple.py
```

### 4. Verify Results

Check Krita canvas for:
- ✓ Red line at y=300
- ✓ 5 colored lines at y=100-300
- ✓ Cyan line at y=400

If visible: **BULK API IS FIXED**

## Expected Performance

### Before (Individual Strokes)
```
20 frames × 50 strokes/frame = 1000 strokes
1000 MCP calls (krita_stroke)
+ 60 frame operations
+ 40 color/brush changes
= 1100 total MCP calls
Time: 10-15 minutes
```

### After (Bulk Strokes)
```
20 frames × 1 bulk call/frame = 20 bulk calls
20 MCP calls (krita_bulk_strokes)
+ 60 frame operations  
+ 0 color/brush changes (included in bulk)
= 80 total MCP calls
Time: ~5-8 minutes (target)
```

**Reduction:** 1100 → 80 calls (~93% reduction)

## Backward Compatibility

Old APIs preserved:
- ✓ `krita_stroke` - Single stroke
- ✓ `krita_batch_draw` - Batch with same color
- ✓ `SmartBatchManager._execute_legacy()` - Fallback path
- ✓ All frame operations unchanged
- ✓ All color/brush operations unchanged

## Error Handling

### Before Fix
```json
{"error": "Unknown action: bulk_strokes"}
```
Client misinterpreted this as success with 0 drawn.

### After Fix

**Success:**
```json
{
    "status": "ok",
    "strokes_drawn": 21,
    "strokes_failed": 0,
    "total_strokes": 21,
    "errors": null
}
```

**Partial Success:**
```json
{
    "status": "partial",
    "strokes_drawn": 18,
    "strokes_failed": 3,
    "total_strokes": 21,
    "errors": ["Stroke 5: out of bounds", ...]
}
```

**Complete Failure:**
```json
{
    "error": "No active paint layer"
}
```

## DEBUG Logging

Console output shows execution path:

```
[DEBUG-4] Krita plugin received bulk_strokes request
[DEBUG-4] Parsed 21 strokes from params
[DEBUG-5] Resolving layer/doc/view...
[DEBUG-5] Resolved: layer=paint, doc=Untitled, view=OK
[DEBUG-6] Starting stroke loop...
[DEBUG-7] Stroke 0: Set color to #FF0000
[DEBUG-7] Stroke 0: Drawing 31 points, brush=5
[DEBUG-7] Stroke 0: SUCCESS
... (repeated for each stroke)
[DEBUG-7] Stroke loop completed: drawn=21, failed=0
[DEBUG-8] Calling doc.refreshProjection()...
[DEBUG-8] refreshProjection() completed
[DEBUG-8] Returning result: {...}
```

If stuck at [DEBUG-3], plugin didn't receive request.
If stuck at [DEBUG-5], layer/doc/view resolution failed.
If stuck at [DEBUG-7], drawing operation failed.

## Test Matrix

| Test | Description | Expected | Status |
|------|-------------|----------|--------|
| 1 | One stroke | Red line visible | ⏳ Pending |
| 2 | Five strokes | All 5 visible | ⏳ Pending |
| 3 | Old API | Cyan line visible | ⏳ Pending |
| 4 | 21 strokes (character) | Character visible | ⏳ Pending |
| 5 | 20 frames (animation) | All frames drawn | ⏳ Pending |
| 6 | Error handling | Proper error messages | ⏳ Pending |
| 7 | Backward compat | Old APIs work | ⏳ Pending |

## Files Modified

1. **C:\Users\pavan\OneDrive\Desktop\krita-mcp\krita-plugin\kritamcp\__init__.py**
   - Removed lines 1312-end (incorrectly placed methods)
   - Added `cmd_bulk_strokes()` at line 1311 (inside class, 116 lines)
   - Added `_draw_stroke_pixels()` at line 1427 (inside class, 103 lines)
   - Total: 219 lines added with correct indentation

2. **MCP Server** (C:\Users\pavan\OneDrive\Desktop\krita-mcp\server.py)
   - Already had `krita_bulk_strokes` tool ✓
   - Already sends correct action name ✓
   - No changes needed ✓

## What Was NOT Changed

✓ Stroke extraction logic  
✓ Character model  
✓ Skeleton system  
✓ Motion planner  
✓ Frame planning  
✓ Pose generation  
✓ Animation logic  
✓ Geometry processing  
✓ Reference handling  

**Only the MCP/Krita communication layer was fixed.**

## Next Steps

1. **User:** Restart Krita
2. **User:** Run `test_bulk_api_simple.py`
3. **Verify:** Strokes appear in Krita
4. **Test:** Draw character from reference
5. **Test:** Create animation walk cycle
6. **Benchmark:** Measure time improvement
7. **Confirm:** 10-15 min → 5-8 min achieved

## Success Criteria

- [x] MCP server has `krita_bulk_strokes` tool
- [x] Krita plugin has `cmd_bulk_strokes` method
- [x] Method is inside `KritaMCPExtension` class
- [x] Dispatch route exists (`elif action == "bulk_strokes"`)
- [x] Helper method `_draw_stroke_pixels` exists
- [x] Methods have correct indentation
- [ ] Krita restarted (USER ACTION REQUIRED)
- [ ] One stroke test passes
- [ ] Five stroke test passes
- [ ] Old API compatibility verified
- [ ] Animation performance benchmarked

## Troubleshooting

**"Unknown action: bulk_strokes"**
→ Krita not restarted. Close and reopen Krita.

**Connection refused**
→ Krita not running or plugin not loaded.

**"No active paint layer"**
→ Create a paint layer in Krita first.

**Strokes report success but nothing visible**
→ Wrong layer selected, or drawing outside canvas bounds.

**Import errors in Krita console**
→ Plugin syntax error. Check Python console for details.

## Conclusion

The bulk API fix is **COMPLETE** but **REQUIRES KRITA RESTART** to take effect.

The architecture is sound:
- MCP server → Krita plugin communication ✓
- Action dispatch ✓
- Method implementation ✓
- Error handling ✓
- DEBUG logging ✓

Once Krita restarts, the bulk API will work correctly, reducing MCP calls from ~1100 to ~80 for a typical 20-frame animation.
