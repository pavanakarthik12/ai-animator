# ROOT CAUSE FOUND AND FIXED

## The Problem

**Error:** `{'error': 'Unknown action: bulk_strokes'}`

**Root Cause:** Krita was loading the OLD plugin from a DIFFERENT location than where we were editing.

## File Locations

### Development Location (Where We Edited)
```
Path: C:\Users\pavan\OneDrive\Desktop\krita-mcp\krita-plugin\kritamcp\__init__.py
Modified: 23-08-2026 13:25:23
Size: 58,361 bytes
Has bulk_strokes: YES ✓
```

### ACTUAL Running Location (Where Krita Loads From)
```
Path: C:\Users\pavan\AppData\Roaming\krita\pykrita\kritamcp\__init__.py
Modified: 15-08-2026 16:41:39 (8 days old!)
Size: 49,066 bytes
Has bulk_strokes: NO ✗
```

## Why This Happened

Krita loads Python plugins from:
```
%APPDATA%\krita\pykrita\
```

NOT from the development directory in:
```
C:\Users\pavan\OneDrive\Desktop\krita-mcp\krita-plugin\
```

All our edits were going to the development copy, but Krita was running the old installed copy.

## The Fix

Copied the updated plugin to the location Krita actually uses:

```powershell
Copy-Item "C:\Users\pavan\OneDrive\Desktop\krita-mcp\krita-plugin\kritamcp\__init__.py" `
          -Destination "C:\Users\pavan\AppData\Roaming\krita\pykrita\kritamcp\__init__.py" `
          -Force
```

**Status:** ✓ File copied successfully
**Verification:** ✓ cmd_bulk_strokes now exists at line 1315 in running plugin

## Next Step

**Restart Krita** to load the updated plugin.

```
1. Close Krita completely
2. Wait 3 seconds
3. Reopen Krita
4. The bulk API will now work
```

## Verification After Restart

Run this test:
```powershell
cd C:\Users\pavan\OneDrive\Desktop\groq-krita-agent
python test_bulk_api_simple.py
```

Expected result:
- ✓ Using BULK API mode (no fallback message)
- ✓ Red line appears in Krita
- ✓ No "Unknown action" error

## Summary

**Running server path:** MCP server was correct all along
**Dispatcher location:** Line 242 in __init__.py (both copies)
**Accepted action name:** "bulk_strokes" (correct)
**Registration mechanism:** @mcp.tool() decorator (correct)
**Why it failed:** Wrong file was being loaded by Krita
**Minimal fix:** Copy development file to AppData location + restart Krita

**Status:** FIXED ✓ (pending Krita restart)
