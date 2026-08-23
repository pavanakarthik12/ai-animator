# Testing Instructions - Regression Fixes

## CRITICAL: Restart Krita First

**The Krita plugin MUST be reloaded for the bulk API fix to work.**

Steps:
1. Close Krita completely
2. Reopen Krita
3. Verify plugin loaded (check status bar or scripting console)
4. Open or create a document (800x600 recommended)

## Quick Test

### Test 1: One Stroke (Most Important)

```powershell
cd C:\Users\pavan\OneDrive\Desktop\groq-krita-agent
python test_regression_fixes.py
```

This will:
1. Test canvas detection
2. Draw ONE red line in Krita
3. Draw FIVE colored lines
4. Test old API still works

**Expected Result:**
- You should SEE strokes appear in Krita
- Not just "success" messages - ACTUAL visible lines

### Test 2: Manual Verification

After running the test, check your Krita canvas for:
- ✓ Red horizontal line at y=300
- ✓ 5 colored lines (red, green, blue, yellow, magenta) at y=100-300
- ✓ Cyan line at y=400

If you see these lines: **BULK API IS FIXED**

If you don't see lines but test reports "success": **BUG STILL EXISTS**

## Troubleshooting

### Plugin Not Reloaded
**Symptom:** Test reports success but nothing appears in Krita

**Fix:**
1. Close Krita
2. Check if kritamcp plugin is in: `~/.local/share/krita/pykrita/`
3. Restart Krita
4. Check Python console in Krita for errors
5. Run test again

### Connection Failed
**Symptom:** "Connection refused" or timeout errors

**Fix:**
1. Verify Krita is running
2. Check plugin started: Should see "[KritaMCP] HTTP server started on port 5678"
3. Check firewall isn't blocking localhost:5678
4. Try health check: Run `python -c "from mcp_client import KritaMCPClient; print(KritaMCPClient().call_tool('krita_health', {}))"`

### Canvas Detection Always Fails
**Symptom:** "No character detected" even with drawing

**Fix:**
1. Check if you're drawing on a paint layer (not group layer)
2. Try drawing larger/darker strokes
3. Adjust threshold in canvas_detector.py (line 84: `min_non_blank_pixels`)

## Expected Output

### Successful Test Run

```
==========================================================
REGRESSION FIX VERIFICATION
==========================================================

TEST 1: CANVAS DETECTION
[TEST A] PASS - Canvas correctly detected as not ready

TEST 2: BULK API - ONE STROKE  
[TEST 2] Result: {'status': 'ok', 'strokes_drawn': 1, ...}
[TEST 2] PASS - Bulk API reports success
[TEST 2] CHECK KRITA MANUALLY: Do you see a RED horizontal line?

TEST 3: BULK API - FIVE STROKES
[TEST 3] Result: {'status': 'ok', 'strokes_drawn': 5, ...}
[TEST 3] PASS - Bulk API reports all strokes drawn
[TEST 3] CHECK KRITA MANUALLY: Do you see 5 colored lines?

TEST 4: OLD API - BACKWARD COMPATIBILITY
[TEST 4] PASS - Old API still works

==========================================================
FINAL REPORT
==========================================================
Canvas Detection              : PASS
Bulk API - 1 Stroke           : PASS
Bulk API - 5 Strokes          : PASS
Old API Compatibility         : PASS
----------------------------------------------------------
Total: 4/4 tests passed
==========================================================

ALL TESTS PASSED!
Canvas detection: WORKING
Bulk API drawing: WORKING
Backward compatibility: WORKING
```

### Failed Test (Before Fix)

```
TEST 2: BULK API - ONE STROKE
[TEST 2] Result: {'status': 'ok', 'strokes_drawn': 1, ...}
[TEST 2] PASS - Bulk API reports success
[TEST 2] CHECK KRITA MANUALLY: Do you see a RED horizontal line?

# User checks Krita - NO LINE VISIBLE
# This means bulk API still broken
```

## Animation Test (After Basic Tests Pass)

Once the basic tests pass, test animation:

```powershell
python main.py
# Choose option 1 (Load reference)
# Choose option 2 (Draw character)
# Choose option 3 (Create walk cycle)
```

**Expected:**
1. System detects no character → blocks animation
2. After drawing character → allows animation
3. Frames are created with actual strokes visible

## Debug Logging

If tests fail, check Krita's scripting console for DEBUG messages:

```
[DEBUG-4] Krita plugin received bulk_strokes request
[DEBUG-5] Resolved: layer=paint, doc=Untitled, view=OK
[DEBUG-6] Starting stroke loop...
[DEBUG-7] Stroke 0: Drawing 2 points, brush=10
[DEBUG-7] Stroke 0: SUCCESS
[DEBUG-8] Calling doc.refreshProjection()...
[DEBUG-8] refreshProjection() completed
[DEBUG-8] Returning result: {'status': 'ok', 'strokes_drawn': 1}
```

If you see these messages, the plugin is working.

If you don't see [DEBUG-4], the plugin wasn't reloaded properly.

## Success Criteria

| Check | Status |
|-------|--------|
| Krita restarted | ☐ |
| Plugin loaded | ☐ |
| Test script runs without errors | ☐ |
| Red line visible in Krita | ☐ |
| 5 colored lines visible | ☐ |
| Cyan line visible | ☐ |
| Canvas detection works | ☐ |
| Animation blocks on empty canvas | ☐ |

If all checked: **REGRESSIONS FIXED**

## Contact

If tests still fail after:
1. Restarting Krita
2. Verifying plugin loaded
3. Running test script

Check REGRESSION_FIX_REPORT.md for technical details.
