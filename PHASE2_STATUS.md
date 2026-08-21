# Phase 2: Generic Timeline + Key Pose Planning - Status

## Status: COMPLETE ✓

Phase 2 (Generic Timeline and Key Pose Planning) has been successfully implemented and tested.

**NO DRAWING. NO GROQ. NO KRITA. NO MCP. Pure planning/data layer.**

---

## Purpose

Build the deterministic planning foundation for arbitrary-length animations:

```
USER REQUEST
    ↓
AnimationRequest
    ↓
AnimationPlan
    ↓
Timeline + Segments + KeyPoses
    ↓
LATER: Motion Engine → Interpolation → All Frames
```

**Critical Architecture Decision:**

The AI does NOT independently generate every frame. Instead:

```
ACTION (e.g., "walk 240 frames")
    ↓
Timeline Allocation
    ↓
Key Poses (20-30 important moments)
    ↓
Future: Interpolation
    ↓
All 240 Poses
```

---

## Core Classes Implemented

### 1. AnimationRequest
Generic animation request supporting any action.

**Fields:**
- `action`: str (e.g., "walk", "run", "wave", "sit", "jump")
- `frame_count`: int (20, 100, 240, 250, arbitrary)
- `loop`: bool (default True)
- `direction`: str (default "forward")
- `speed`: str (default "normal")
- `style`: str (default "natural")
- `metadata`: Dict[str, Any]

**Examples:**
```python
AnimationRequest(action="walk", frame_count=240, loop=True)
AnimationRequest(action="wave", frame_count=40, loop=False)
AnimationRequest(action="run", frame_count=120)
```

### 2. TimelineSegment
Represents a meaningful action phase.

**Fields:**
- `name`: str (e.g., "walk_cycle", "stop", "transition")
- `action`: str (e.g., "walk", "stop", "wave")
- `start_frame`: int
- `end_frame`: int
- `metadata`: Dict[str, Any]

**Methods:**
- `duration()`: Returns frame count
- `contains_frame(frame)`: Checks if frame is in segment

**Example:**
```python
TimelineSegment(
    name="walk_cycle",
    action="walk",
    start_frame=1,
    end_frame=120
)
```

### 3. KeyPose
Important pose at a specific frame.

**Fields:**
- `frame`: int
- `pose`: Pose (Dict[str, Tuple[float, float]])
- `label`: str (e.g., "contact", "passing", "extreme")
- `segment`: Optional[str] (associated segment name)
- `metadata`: Dict[str, Any]

**Key Principle:**
Key poses represent IMPORTANT moments, NOT every frame.

**Example:**
```python
KeyPose(
    frame=20,
    pose=neutral_pose,
    label="contact"
)
```

### 4. Timeline
Complete animation timeline structure.

**Fields:**
- `total_frames`: int
- `segments`: List[TimelineSegment]
- `metadata`: Dict[str, Any]

**Methods:**
- `add_segment(segment)`: Add segment with bounds validation
- `get_segment_at_frame(frame)`: Find segment containing frame

**Example:**
```python
Timeline(total_frames=240)
```

### 5. AnimationPlan
Complete animation plan.

**Fields:**
- `request`: AnimationRequest
- `timeline`: Timeline
- `key_poses`: List[KeyPose]
- `validated`: bool
- `validation_errors`: List[str]
- `metadata`: Dict[str, Any]

**Methods:**
- `add_key_pose(kp)`: Add key pose with validation
- `get_key_poses_sorted()`: Get poses sorted by frame
- `get_key_pose_at_frame(frame)`: Find pose at frame

**Example:**
```python
AnimationPlan(
    request=AnimationRequest(action="walk", frame_count=240),
    timeline=Timeline(total_frames=240),
    key_poses=[...]
)
```

### 6. TimelineAllocator
Deterministic timeline segment allocator.

**Methods:**

**`allocate_simple(request)`**
- Single action, full timeline
- Example: "walk for 240 frames" → one segment [1-240]

**`allocate_compound(request, phases)`**
- Multiple actions with proportional weights
- Example: `[("walk", 0.6), ("stop", 0.1), ("wave", 0.3)]` for 240 frames
  - walk: 144 frames
  - stop: 24 frames  
  - wave: 72 frames

**`allocate_uniform(request, actions)`**
- Equal distribution across actions
- Example: `["walk", "stop", "wave"]` → each gets 1/3 of frames

**Key Properties:**
- ✅ Deterministic (no randomness)
- ✅ No Groq/LLM calls
- ✅ Complete coverage (no gaps)
- ✅ No overlaps
- ✅ Respects frame budget

### 7. TimelineValidator
Validates animation plans for correctness.

**Validation Checks:**

1. **Coverage** - No gaps in timeline
2. **Overlap** - No segments overlap
3. **Bounds** - All segments within timeline
4. **Key Pose Bounds** - All poses within timeline
5. **Duplicate Frames** - No two poses at same frame

**Method:**
```python
validator.validate_plan(plan) -> (is_valid, errors)
```

---

## Validation Rules

### Segment Rules
1. `start_frame >= 1`
2. `end_frame <= total_frames`
3. `start_frame <= end_frame`
4. No gaps between segments
5. No overlaps between segments

### Key Pose Rules
1. `frame >= 1`
2. `frame <= total_frames`
3. No duplicate frames
4. Associated with valid segment (if specified)

### Timeline Rules
1. `total_frames >= 1`
2. Complete coverage (1 → total_frames)
3. No silent frame budget changes
4. Deterministic ordering

---

## Frame Budget Support

**Arbitrary frame counts supported:**
- ✅ 20 frames (testing)
- ✅ 30 frames
- ✅ 50 frames
- ✅ 100 frames
- ✅ 120 frames
- ✅ 200 frames
- ✅ 240 frames
- ✅ 250 frames
- ✅ Any positive integer

**NOT hard-coded to 20 frames.**

---

## Action Support

**Generic architecture supports any action:**
- walk
- run
- wave
- point
- sit
- stand
- jump
- turn
- look
- gesture
- compound actions (walk → stop → wave)

**NOT walking-specific.**

---

## Compound Actions

Timeline can represent multi-action sequences:

```python
request = AnimationRequest(action="compound", frame_count=200)
phases = [
    ("walk", 0.5),    # 100 frames
    ("stop", 0.15),   # 30 frames
    ("wave", 0.35)    # 70 frames
]
plan = create_compound_plan(request, phases)
```

Result: walk [1-100] → stop [101-130] → wave [131-200]

---

## Tests - All Passing

### Basic Validation (13 tests)
- ✅ Valid requests
- ✅ Invalid frame counts rejected
- ✅ Empty actions rejected
- ✅ Segment validation
- ✅ Key pose validation
- ✅ Timeline validation

### Required Test Cases

**TEST 1:** 20-frame request → valid timeline [1-20]
**TEST 2:** 100-frame request → valid timeline [1-100]
**TEST 3:** 240-frame request → valid timeline [1-240]
**TEST 4:** 250-frame request → valid timeline [1-250]
**TEST 5:** Multiple segments, complete coverage → PASS
**TEST 6:** Segments with gap → FAIL (detected)
**TEST 7:** Segments with overlap → FAIL (detected)
**TEST 8:** Segment outside budget → FAIL (detected)
**TEST 9:** Key pose inside timeline → PASS
**TEST 10:** Key pose outside timeline → FAIL (detected)
**TEST 11:** Duplicate key pose frame → FAIL (detected)
**TEST 12:** Compound action (walk → stop → wave) → PASS
**TEST 13:** Same input twice → identical output (deterministic)

### 240-Frame Specific Test
- ✅ 240-frame walk request
- ✅ Valid deterministic plan
- ✅ No gaps, no overlaps
- ✅ Frames [1-240] covered
- ✅ **NO DRAWINGS CREATED**

### Total: 37 tests - all passing

---

## Overall Test Results

```
Phase 1 tests:     17 passed
Phase 1.5 tests:   17 passed
Phase 1.6 tests:   24 passed
Phase 2 tests:     37 passed
Total:             95 passed
Failures:          0
Errors:            0
```

---

## Files Created

### Phase 2
- `animation_timeline.py` - Timeline and planning (443 lines)
- `test_animation_timeline.py` - Unit tests (448 lines)

**Total: 2 files, 891 lines**

---

## Files Modified

**None** - Zero modifications to existing code

---

## Verification

### Functionality Preserved
- ✅ All Phase 1 tests pass
- ✅ All Phase 1.5/1.6 tests pass
- ✅ All Phase 2 tests pass
- ✅ Existing imports work
- ✅ No circular dependencies
- ✅ `CharacterModel` unchanged
- ✅ `CharacterRig` unchanged
- ✅ `BONE_HIERARCHY` unchanged
- ✅ `PoseTransformer` unchanged
- ✅ Renderer unchanged
- ✅ Frame creation unchanged
- ✅ Drawing logic unchanged
- ✅ **Existing walking implementation unchanged**

### Not Called/Used (Phase 2 is pure data)
- ✅ Krita - not called
- ✅ MCP - not called  
- ✅ Groq - not called
- ✅ Renderer - not called
- ✅ Image generation - not used
- ✅ LLM - not used
- ✅ Drawing - not performed
- ✅ Frame creation - not performed

---

## Architecture

```
Phase 1: CharacterModel + Skeleton + Dimensions
    ↓
Phase 1.5: ConsistencyValidator
    ↓
Phase 1.6: MasterGeometry + PoseTransformer
    ↓
Phase 2: AnimationRequest + Timeline + KeyPose
    ↓
        AnimationRequest
            ↓
        TimelineAllocator
            ↓
        Timeline + Segments
            ↓
        KeyPoses (important moments)
            ↓
        AnimationPlan (validated)
            ↓
    FUTURE: Motion Engine
            ↓
    FUTURE: Interpolation (key poses → all poses)
            ↓
    FUTURE: PoseTransformer (existing)
            ↓
    FUTURE: Renderer (existing)
```

---

## Data Flow

```
User: "Create 240-frame walk animation"
    ↓
AnimationRequest(action="walk", frame_count=240)
    ↓
TimelineAllocator.allocate_simple()
    ↓
Timeline(total_frames=240)
    └── TimelineSegment("walk_main", 1-240)
    ↓
AnimationPlan
    ├── request
    ├── timeline
    └── key_poses: []  (to be added by future motion planner)
    ↓
TimelineValidator.validate_plan()
    ↓
AnimationPlan(validated=True, errors=[])
    ↓
FUTURE: Motion planner adds key poses
FUTURE: Interpolator generates all poses
FUTURE: Transformer applies poses to geometry
FUTURE: Renderer draws frames
```

---

## Key Design Decisions

### 1. Generic Architecture
- NOT walking-specific
- Supports any action type
- Supports compound actions
- Supports arbitrary frame counts

### 2. Deterministic Planning
- No randomness
- No Groq/LLM in Phase 2
- Same input → same output
- Predictable validation

### 3. Pure Data Layer
- No drawing
- No rendering
- No Krita/MCP calls
- Clean separation of concerns

### 4. Frame Budget Authority
- Requested `frame_count` is authoritative
- No silent changes
- Validation enforces bounds
- No exceeding budget

### 5. Key Pose Philosophy
- Key poses mark important moments
- NOT every frame needs a key pose
- Future interpolation fills gaps
- Efficient for long animations

### 6. Extensible Allocation
- Simple single-action
- Compound multi-action
- Uniform distribution
- Easy to extend with new strategies

### 7. Fail-Fast Validation
- Gaps detected
- Overlaps detected
- Out-of-bounds detected
- Duplicate frames detected

---

## Future Compatibility

Phase 2 architecture supports future phases:

**Phase 3 (Future):** Motion planning
- AI suggests key poses
- Deterministic interpolation
- Action-specific motion profiles

**Phase 4 (Future):** Motion library
- Walk cycles
- Run cycles
- Gestures
- Compound actions

**Phase 5 (Future):** Integration
- Motion Engine → PoseTransformer → Renderer
- Full animation pipeline

---

## Example Usage

### Simple Single Action
```python
from animation_timeline import AnimationRequest, create_simple_plan

request = AnimationRequest(action="walk", frame_count=240)
plan = create_simple_plan(request)

print(plan)
# AnimationPlan(walk, 240 frames, 1 segments, 0 key poses, VALID)
```

### Compound Action
```python
from animation_timeline import create_compound_plan

request = AnimationRequest(action="compound", frame_count=180)
phases = [
    ("walk", 0.5),
    ("stop", 0.2),
    ("wave", 0.3)
]
plan = create_compound_plan(request, phases)

print(plan)
# AnimationPlan(compound, 180 frames, 3 segments, 0 key poses, VALID)
```

### With Key Poses (Future)
```python
from animation_timeline import KeyPose

# Add key poses for important moments
plan.add_key_pose(KeyPose(
    frame=1,
    pose=neutral_pose,
    label="start"
))

plan.add_key_pose(KeyPose(
    frame=20,
    pose=contact_pose,
    label="contact"
))

plan.add_key_pose(KeyPose(
    frame=240,
    pose=neutral_pose,
    label="end"
))
```

---

## Logging Example

Simple, non-flashy output:

```
Phase 1 tests: PASS
Phase 1.5 tests: PASS
Phase 1.6 tests: PASS
Phase 2 tests: PASS

20-frame timeline: PASS
100-frame timeline: PASS
240-frame timeline: PASS
250-frame timeline: PASS

Gaps detected: PASS
Overlaps detected: PASS
Out-of-bounds detected: PASS
Duplicate frames detected: PASS

Existing imports: PASS
Existing walking: unchanged

Phase 2: COMPLETE
```

---

## Success Criteria - All Met ✓

✅ AnimationRequest exists
✅ Timeline exists
✅ TimelineSegment exists
✅ KeyPose exists
✅ AnimationPlan exists
✅ TimelineAllocator exists
✅ TimelineValidator exists
✅ 20-frame plans work
✅ 100-frame plans work
✅ 200-frame plans work
✅ 240-frame plans work
✅ 250-frame plans work
✅ Gaps detected
✅ Overlaps detected
✅ Invalid frame ranges detected
✅ Invalid key poses detected
✅ Compound actions represented
✅ Behavior is deterministic
✅ No drawing occurs
✅ No Krita calls
✅ No MCP calls
✅ No Groq calls
✅ Existing walking unchanged
✅ All 95 tests pass
✅ No import errors
✅ No circular dependencies
✅ No regressions

**PHASE 2 COMPLETE**

---

## Next Phases (Not Implemented)

**Phase 3:** Motion planning and interpolation
- Generate key poses from timeline
- Interpolate between key poses
- Action-specific motion profiles
- Integration with Phase 1.6 PoseTransformer

**Phase 4:** Motion library
- Walk cycles
- Run cycles  
- Gesture library
- Compound action sequencing

**Phase 5:** AI planning layer
- Groq action planning
- Natural language → AnimationPlan
- Intelligent key pose suggestions

**Phase 6:** Full integration
- AnimationPlan → Motion Engine → Poses → Rendering
- Complete animation pipeline
- Krita frame generation

---

## Core Principles

1. **Generic, not action-specific**
2. **Deterministic, not AI-based**
3. **Planning, not drawing**
4. **Validated, not assumed**
5. **Extensible, not hard-coded**
6. **Arbitrary lengths, not fixed to 20 frames**

The foundation is ready for future motion planning and generation.


---

## Standalone Demo Command

A simple standalone test/demo command is available:

### Usage

```bash
python test_phase2_demo.py
```

### What It Tests

1. **20-frame walk** - Simple single-action timeline
2. **100-frame walk** - Medium-length timeline
3. **240-frame walk** - Long timeline (target use case)
4. **250-frame walk** - Extended timeline
5. **240-frame compound** - Multi-action sequence (walk → stop → wave → hold)
6. **Invalid gap** - Gap detection in timeline
7. **Invalid overlap** - Overlap detection in timeline
8. **Invalid frame count** - Frame count validation

### Sample Output

```
============================================================
PHASE 2 STANDALONE TEST/DEMO
============================================================

Testing: AnimationRequest, Timeline, TimelineSegment,
         KeyPose, AnimationPlan, TimelineAllocator

NO GROQ. NO KRITA. NO MCP. NO RENDERER. NO FRAMES.
============================================================

Test 1: 20-frame walk
------------------------------------------------------------
Request: walk, 20 frames
Timeline: 1-20
Segments: 1
  - walk: frames 1-20
Validated: True

Result: PASS

...

============================================================
SUMMARY
============================================================
Test 1: 20-frame walk: PASS
Test 2: 100-frame walk: PASS
Test 3: 240-frame walk: PASS
Test 4: 250-frame walk: PASS
Test 5: 240-frame compound: PASS
Test 6: Invalid gap: PASS
Test 7: Invalid overlap: PASS
Test 8: Invalid frame count: PASS
============================================================
Total: 8/8 tests passed
============================================================

All Phase 2 tests PASSED
```

### Verification

- ✅ No Groq calls
- ✅ No Krita calls
- ✅ No MCP calls
- ✅ No rendering
- ✅ No frame creation
- ✅ Simple readable text output
- ✅ Clear PASS/FAIL status
- ✅ Existing code unchanged
