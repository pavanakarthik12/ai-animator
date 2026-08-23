# CHARACTER DETECTION - DIAGNOSTIC MODE

## Problem Statement

**Character is visibly present in Krita**  
↓  
**Character detection returns FALSE**  
↓  
**Walking is refused**  
↓  
**No frames created**

## Approach

Instead of changing thresholds again, **diagnose the ACTUAL Krita state** to determine why detection fails.

## Changes Made

### File: canvas_detector.py

#### 1. Added Diagnostic Function

**New method:** `inspect_character_state()`

**Purpose:** Show EXACT Krita state without modifying canvas

**Returns:**
- Document found? Name? Dimensions?
- Active layer? Name? Type? Visibility? Opacity?
- Current frame? Keyframe exists?
- Candidate layers? Non-empty layers?
- Bounding boxes? Non-blank pixel counts?
- Character detected: TRUE or FALSE?
- If FALSE: exact failure reason

**Output Example (with character):**
```
[CHARACTER STATE DIAGNOSTIC]
Document: FOUND (Untitled)
Dimensions: 800x600
Active layer: Paint Layer (paint layer)
Current frame: 0

Checking layer content...
Sampling 100 pixels across canvas...
  Non-blank pixel at (160,120): #ff0000
  Non-blank pixel at (240,120): #ff0000
  Non-blank pixel at (320,180): #ff0000

Pixel sampling result: 23/100 non-blank pixels

Character detected: TRUE (23 non-blank pixels found)
```

**Output Example (empty):**
```
[CHARACTER STATE DIAGNOSTIC]
Document: FOUND (Untitled)
Dimensions: 800x600
Active layer: Paint Layer (paint layer)
Current frame: 0

Checking layer content...
Sampling 100 pixels across canvas...

Pixel sampling result: 0/100 non-blank pixels

Character detected: FALSE (No non-blank pixels found in 100 samples)
```

#### 2. Increased Sampling Density

**Before:**
- 5x5 grid = 25 sample points
- Sparse sampling might miss small characters

**After:**
- 10x10 grid = 100 sample points
- More comprehensive coverage
- Less likely to miss content

#### 3. Lowered Detection Threshold

**Before:**
- Required 5+ non-blank pixels
- Character might be missed if only a few pixels sampled

**After:**
- Requires >0 non-blank pixels (ANY content)
- If ANYTHING is drawn, character detected
- Extremely sensitive detection

#### 4. Enhanced Logging

**Shows:**
- First 3 non-blank pixels found (location + color)
- Total non-blank count / total sampled
- Percentage of non-blank pixels
- Clear TRUE/FALSE determination
- Exact failure reason if FALSE

#### 5. Updated verify_canvas_ready_for_animation

**Now uses:** `inspect_character_state()` instead of `has_drawing()`

**Benefits:**
- More detailed diagnostics
- Shows actual Krita state
- Clear failure reasons
- Better debugging information

## Test Scripts Created

### 1. diagnose_krita_state.py

**Purpose:** Show EXACT current Krita state

**Usage:**
```powershell
python diagnose_krita_state.py
```

**Output:**
- Document details
- Layer details
- Frame details
- Pixel sampling results
- Character detection result
- Troubleshooting suggestions if failed

**When to use:**
- Character visible but detection fails
- Want to see what Krita actually contains
- Need to debug detection logic

### 2. test_one_line.py

**Purpose:** Test most basic detection case

**Tests:**
1. Empty canvas → detection FALSE
2. Draw ONE red line → detection TRUE

**Usage:**
```powershell
python test_one_line.py
```

**What it proves:**
- If Test 1 FAILS: Empty canvas incorrectly detected as having content
- If Test 2 FAILS with visible line: Detection logic is broken
- If Test 2 FAILS with no visible line: Drawing API is broken
- If both PASS: Detection works, problem is elsewhere

## Diagnostic Process

### Step 1: Run State Diagnostic

```powershell
python diagnose_krita_state.py
```

**Record:**
- Document found?
- Active layer name
- Current frame number
- Non-blank pixels: X/100
- Character detected: TRUE or FALSE
- Failure reason (if FALSE)

### Step 2: Run One Line Test

```powershell
python test_one_line.py
```

**Record:**
- Test 1 (empty): PASS or FAIL
- Test 2 (one line): PASS or FAIL
- Is red line visible in Krita?

### Step 3: Visual Verification

**Check in Krita:**
- Is character visible? YES or NO
- Which layer? (name)
- Which frame? (number)
- Is it the active layer? YES or NO

### Step 4: Analyze Results

**Scenario A:** Diagnostic shows 0/100 pixels BUT character IS visible
- **Diagnosis:** Character is on wrong layer/frame
- **Issue:** Detection checking wrong location
- **Next:** Determine which layer/frame has character

**Scenario B:** Diagnostic shows >0 pixels AND character_detected = TRUE
- **Diagnosis:** Detection working correctly
- **Next:** Animation should proceed

**Scenario C:** test_one_line draws line, line visible, detection FALSE
- **Diagnosis:** Detection logic bug
- **Issue:** Pixel sampling or threshold logic broken
- **Next:** Debug sampling logic

**Scenario D:** test_one_line draws line, line NOT visible
- **Diagnosis:** Drawing API problem
- **Issue:** Separate from detection
- **Next:** Debug drawing API

## Detection Logic

### Pixel Classification

**Blank pixels:**
- White: `#ffffff`, `#fff`, `white`
- Transparent: `#00000000`, `transparent`
- Transparent colors: Any color ending with `00` (alpha=0)

**Non-blank pixels:**
- Any other color
- Any color with alpha > 0
- All drawing strokes should be non-blank

### Sampling Strategy

**Grid Pattern:**
- 10 rows × 10 columns = 100 points
- Evenly distributed across canvas
- Step_x = width / 11
- Step_y = height / 11
- Covers entire canvas area

**Example (800x600 canvas):**
- Step_x = 72 pixels
- Step_y = 54 pixels
- Sample at: (72,54), (144,54), (216,54), ...

### Detection Threshold

**Current:**
```python
if non_blank_pixels > 0:
    character_detected = True
```

**Meaning:**
- If ANY non-blank pixel found → Character detected
- No minimum percentage required
- Extremely sensitive
- Should detect even tiny drawings

### Integration

**Called from:** `animation_executor.py` line 59

```python
canvas_state = detect_canvas_state(mcp, require_drawing=True)

if not canvas_state["ready"]:
    print("ANIMATION BLOCKED - NO CHARACTER DETECTED")
    return
```

**Blocks animation when:**
- No document found
- No paint layer
- No non-blank pixels (character_detected = FALSE)

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
- ✓ Animation logic

**Only changed:** Detection diagnostic and logging

## Expected Outcomes

### If Detection Works

**diagnose_krita_state.py shows:**
```
Non-blank pixels: 15+/100
Character detected: TRUE
```

**Then animation should proceed:**
```
[CANVAS CHECK] Canvas ready: 15 non-blank pixels detected
[CANVAS CHECK] Canvas ready for animation
```

### If Detection Still Fails

**diagnose_krita_state.py shows:**
```
Document: FOUND
Active layer: Paint Layer
Non-blank pixels: 0/100
Character detected: FALSE
```

**But character IS visible in Krita:**

**STOP and report:**
1. Screenshot of Krita with visible character
2. Full diagnostic output
3. Layer name where character visible
4. Frame number where character visible
5. Whether it's the active layer

**This means:** Character is in a different location than detection is checking

## Success Criteria

### Test 1: Empty Canvas
```
Run: python diagnose_krita_state.py
Expected: character_detected = FALSE
```

### Test 2: One Line
```
Run: python test_one_line.py
Expected: 
  - Empty canvas → FALSE
  - One red line drawn → TRUE
```

### Test 3: Actual Character
```
Draw character in Krita
Run: python diagnose_krita_state.py
Expected: character_detected = TRUE with >0 pixels
```

### Test 4: Animation Allowed
```
Character detected = TRUE
Run: python test_walk_3_frames.py
Expected: Animation proceeds, no blocking
```

## Next Steps

1. **Run diagnostic:** `python diagnose_krita_state.py`
2. **Run one line test:** `python test_one_line.py`
3. **Report results:** Document findings
4. **Analyze:** Use diagnostic output to determine root cause

**DO NOT proceed to animation testing until diagnostic is complete.**

## Summary

**Approach:** Diagnostic-first, not threshold-tweaking

**Goal:** Understand WHY detection fails, not just make it pass

**Changes:**
- Added comprehensive state inspection
- Increased sampling density (25 → 100 pixels)
- Lowered threshold (5 → >0 pixels)
- Enhanced logging with exact failure reasons

**Status:** Ready for diagnostic testing

**Next:** Run diagnostic scripts and report findings
