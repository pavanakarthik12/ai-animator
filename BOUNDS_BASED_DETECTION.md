# CHARACTER DETECTION - BOUNDS-BASED FIX

## Root Cause

**Pixel sampling is unreliable for small characters on large canvases.**

Example from screenshot:
- Canvas: 800x600
- Character: Small, positioned right side
- Pixel sampling: 2/25 or 0/100 non-blank pixels
- Result: FALSE NEGATIVE (character exists but not detected)

**Problem:** Random pixel sampling can miss small or off-center characters.

## Solution

**Use Krita's actual content bounds API instead of pixel sampling.**

Krita's `node.bounds()` returns the actual bounding rectangle of non-empty content,  
regardless of character size or position.

## Changes Made

### 1. Krita Plugin - New Command

**File:** `C:\Users\pavan\AppData\Roaming\krita\pykrita\kritamcp\__init__.py`

**Added:** `cmd_get_layer_bounds()` method

**Location:** After line 589 (after cmd_select_paint_layer)

**What it does:**
- Calls `layer.bounds()` on active paint layer
- Returns actual content bounds from Krita
- Returns `has_content: false` if bounds.isEmpty()
- Returns `has_content: true` with x, y, width, height if content exists

**Dispatch added:** Line 222
```python
elif action == "get_layer_bounds":
    return self.cmd_get_layer_bounds(params)
```

**Implementation:**
```python
def cmd_get_layer_bounds(self, params):
    """Get the actual content bounds of the active paint layer."""
    doc = self.get_active_document()
    if not doc:
        return {"error": "No active document"}

    layer = self._get_active_paint_layer()
    if not layer:
        return {"error": "No paint layer found"}

    try:
        bounds = layer.bounds()
        
        if bounds.isEmpty():
            return {
                "status": "ok",
                "has_content": False,
                "x": 0,
                "y": 0,
                "width": 0,
                "height": 0,
                "layer_name": layer.name()
            }
        
        return {
            "status": "ok",
            "has_content": True,
            "x": bounds.x(),
            "y": bounds.y(),
            "width": bounds.width(),
            "height": bounds.height(),
            "layer_name": layer.name()
        }
    except Exception as e:
        return {"error": f"Failed to get bounds: {str(e)}"}
```

### 2. Canvas Detector - Bounds-Based Detection

**File:** `canvas_detector.py`

**Removed:** Pixel sampling logic (100-point grid, color checking)

**Added:** `get_layer_content_bounds()` method

**What it does:**
- Calls `krita_send_command` with action "get_layer_bounds"
- Returns bounds from Krita
- No pixel sampling, no threshold tuning

**Updated:** `inspect_character_state()` 
- Now uses content bounds instead of pixel sampling
- Shows actual bounds: position (x,y) and size (width x height)
- Character detected if bounds.has_content == true

**Updated:** `verify_canvas_ready_for_animation()`
- Uses bounds-based detection
- Logs content bounds details
- Reports actual position and size

### 3. Logging Output

**New format:**
```
[CHARACTER STATE DIAGNOSTIC]
Document: FOUND (Untitled)
Dimensions: 800x600
Active layer: Paint Layer (paint layer)

Checking layer content bounds...
Content bounds found:
  Position: (520, 180)
  Size: 150x300
  Layer: Paint Layer

Character detected: TRUE (content bounds: 150x300)

[CHARACTER DETECTION]
Document: PASS
Paint layer: PASS (Paint Layer)
Content bounds:
  x: 520
  y: 180
  width: 150
  height: 300
Non-empty content: TRUE
Character candidate: TRUE
```

**Empty canvas:**
```
[CHARACTER STATE DIAGNOSTIC]
Document: FOUND (Untitled)
Dimensions: 800x600
Active layer: Paint Layer (paint layer)

Checking layer content bounds...
Content bounds: EMPTY
  Reason: No content bounds

Character detected: FALSE (No content bounds)

[CHARACTER DETECTION]
Document: PASS
Paint layer: PASS (Paint Layer)
Content bounds: EMPTY
Non-empty content: FALSE
Character candidate: FALSE
```

## Why This Works

### Old Approach (Pixel Sampling)
- Sample 25 or 100 fixed points across canvas
- Count non-white pixels
- Threshold: need X pixels
- **Problem:** Small character can be between sample points → missed

### New Approach (Content Bounds)
- Ask Krita: "What is the bounding rectangle of actual content?"
- Krita scans the layer and returns exact bounds
- If bounds exist → content exists
- **Benefit:** Finds content regardless of size or position

## Test Cases

### TEST 1: Empty Canvas
```
Setup: Blank paint layer
Expected:
  Content bounds: EMPTY
  has_content: FALSE
  Character detected: FALSE
  Animation: BLOCKED
```

### TEST 2: Small Character (Right Side)
```
Setup: Character from screenshot (small, right-aligned)
Expected:
  Content bounds: NON-EMPTY (e.g., 150x300 at position 520,180)
  has_content: TRUE
  Character detected: TRUE
  Animation: ALLOWED
```

### TEST 3: Small Line (Any Position)
```
Setup: Draw one line anywhere on canvas
Expected:
  Content bounds: NON-EMPTY
  has_content: TRUE
  Character detected: TRUE
```

### TEST 4: Character Created from Reference
```
Setup: Reference → bulk drawing → character in Krita
Expected:
  Content bounds: NON-EMPTY
  Character detected: TRUE
  Animation: ALLOWED
```

### TEST 5: Animation (3 Frames)
```
Setup: Character detected → run animation
Expected:
  Frame 1: Character drawn
  Frame 2: Character drawn
  Frame 3: Character drawn
```

## What Was NOT Changed

- ✓ Bulk drawing API
- ✓ krita_bulk_strokes
- ✓ SmartBatchManager
- ✓ Stroke extraction
- ✓ CharacterModel
- ✓ Skeleton
- ✓ MotionPlanner
- ✓ Walk mechanics
- ✓ Frame planning
- ✓ Animation timing

**Only changed:** Character detection mechanism (pixel sampling → content bounds)

## Next Steps

### 1. Restart Krita

**CRITICAL:** Must restart Krita to load updated plugin

```
1. Close Krita completely
2. Wait 3 seconds
3. Reopen Krita
4. Open document with character
```

### 2. Run Diagnostic

```powershell
python diagnose_krita_state.py
```

**Expected with character:**
```
Content bounds found:
  Position: (X, Y)
  Size: WxH
Character detected: TRUE
```

**Expected empty canvas:**
```
Content bounds: EMPTY
Character detected: FALSE
```

### 3. Test Animation

```powershell
python test_walk_3_frames.py
```

**Expected with character:**
```
[CHARACTER DETECTION]
Document: PASS
Paint layer: PASS
Content bounds: NON-EMPTY
Character: DETECTED

(Animation proceeds)
```

**Expected empty canvas:**
```
[CHARACTER DETECTION]
Document: PASS
Paint layer: PASS
Content bounds: EMPTY
Character: NOT DETECTED

ANIMATION BLOCKED - NO CHARACTER DETECTED
```

## Success Criteria

| Test | Status | Requirement |
|------|--------|-------------|
| Empty canvas → detection FALSE | ✓ READY | Content bounds empty |
| Small character (screenshot) → detection TRUE | ✓ READY | Content bounds found |
| Small line anywhere → detection TRUE | ✓ READY | Position doesn't matter |
| Character from reference → detection TRUE | ✓ READY | Bulk drawing → bounds exist |
| Animation creates 3 frames | ✓ READY | Existing animation logic |

## Technical Details

### Krita API Used

**node.bounds()** - QRect
- Returns bounding rectangle of layer content
- x(), y() → top-left position
- width(), height() → dimensions
- isEmpty() → true if no content

**Benefits:**
- Native Krita functionality
- Reliable regardless of content size
- Finds content anywhere on canvas
- No arbitrary thresholds
- No sampling misses

### Client-Side Integration

**MCP Call:**
```python
result = mcp.call_tool("krita_send_command", {
    "action": "get_layer_bounds"
}, timeout=10)
```

**Response:**
```python
{
    "status": "ok",
    "has_content": True/False,
    "x": int,
    "y": int,
    "width": int,
    "height": int,
    "layer_name": str
}
```

## Summary

**Problem:** Pixel sampling missed small characters  
**Solution:** Use Krita's actual content bounds API  
**Status:** IMPLEMENTED - awaiting Krita restart and testing

**Key Changes:**
1. Added `cmd_get_layer_bounds()` to Krita plugin
2. Added `get_layer_content_bounds()` to canvas_detector
3. Replaced pixel sampling with bounds checking
4. Updated logging to show actual bounds

**Next:** Restart Krita and test
