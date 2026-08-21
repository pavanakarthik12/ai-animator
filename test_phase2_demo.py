"""Phase 2 Standalone Test/Demo Command

Simple tests for AnimationRequest, Timeline, TimelineSegment, 
KeyPose, AnimationPlan, and TimelineAllocator.

NO GROQ. NO KRITA. NO MCP. NO RENDERER. NO FRAME CREATION.

Usage:
    python test_phase2_demo.py
"""

from animation_timeline import (
    AnimationRequest,
    Timeline,
    TimelineSegment,
    KeyPose,
    AnimationPlan,
    TimelineAllocator,
    TimelineValidator,
    create_simple_plan,
    create_compound_plan
)


def print_separator():
    """Print simple separator."""
    print("-" * 60)


def test_1_20_frame_walk():
    """Test 1: 20-frame walk."""
    print("\nTest 1: 20-frame walk")
    print_separator()
    
    try:
        request = AnimationRequest(action="walk", frame_count=20)
        print(f"Request: {request.action}, {request.frame_count} frames")
        
        plan = create_simple_plan(request)
        print(f"Timeline: 1-{plan.timeline.total_frames}")
        print(f"Segments: {len(plan.timeline.segments)}")
        
        for seg in plan.timeline.segments:
            print(f"  - {seg.action}: frames {seg.start_frame}-{seg.end_frame}")
        
        print(f"Validated: {plan.validated}")
        
        if plan.validated and plan.timeline.total_frames == 20:
            print("\nResult: PASS")
            return True
        else:
            print(f"\nResult: FAIL - {plan.validation_errors}")
            return False
    except Exception as e:
        print(f"\nResult: FAIL - {e}")
        return False


def test_2_100_frame_walk():
    """Test 2: 100-frame walk."""
    print("\nTest 2: 100-frame walk")
    print_separator()
    
    try:
        request = AnimationRequest(action="walk", frame_count=100)
        print(f"Request: {request.action}, {request.frame_count} frames")
        
        plan = create_simple_plan(request)
        print(f"Timeline: 1-{plan.timeline.total_frames}")
        print(f"Segments: {len(plan.timeline.segments)}")
        
        for seg in plan.timeline.segments:
            print(f"  - {seg.action}: frames {seg.start_frame}-{seg.end_frame}")
        
        print(f"Validated: {plan.validated}")
        
        if plan.validated and plan.timeline.total_frames == 100:
            print("\nResult: PASS")
            return True
        else:
            print(f"\nResult: FAIL - {plan.validation_errors}")
            return False
    except Exception as e:
        print(f"\nResult: FAIL - {e}")
        return False


def test_3_240_frame_walk():
    """Test 3: 240-frame walk."""
    print("\nTest 3: 240-frame walk")
    print_separator()
    
    try:
        request = AnimationRequest(action="walk", frame_count=240)
        print(f"Request: {request.action}, {request.frame_count} frames")
        
        plan = create_simple_plan(request)
        print(f"Timeline: 1-{plan.timeline.total_frames}")
        print(f"Segments: {len(plan.timeline.segments)}")
        
        for seg in plan.timeline.segments:
            print(f"  - {seg.action}: frames {seg.start_frame}-{seg.end_frame}")
        
        print(f"Validated: {plan.validated}")
        print(f"No gaps: {len([e for e in plan.validation_errors if 'gap' in e.lower()]) == 0}")
        print(f"No overlaps: {len([e for e in plan.validation_errors if 'overlap' in e.lower()]) == 0}")
        
        if plan.validated and plan.timeline.total_frames == 240:
            print("\nResult: PASS")
            return True
        else:
            print(f"\nResult: FAIL - {plan.validation_errors}")
            return False
    except Exception as e:
        print(f"\nResult: FAIL - {e}")
        return False


def test_4_250_frame_walk():
    """Test 4: 250-frame walk."""
    print("\nTest 4: 250-frame walk")
    print_separator()
    
    try:
        request = AnimationRequest(action="walk", frame_count=250)
        print(f"Request: {request.action}, {request.frame_count} frames")
        
        plan = create_simple_plan(request)
        print(f"Timeline: 1-{plan.timeline.total_frames}")
        print(f"Segments: {len(plan.timeline.segments)}")
        
        for seg in plan.timeline.segments:
            print(f"  - {seg.action}: frames {seg.start_frame}-{seg.end_frame}")
        
        print(f"Validated: {plan.validated}")
        
        if plan.validated and plan.timeline.total_frames == 250:
            print("\nResult: PASS")
            return True
        else:
            print(f"\nResult: FAIL - {plan.validation_errors}")
            return False
    except Exception as e:
        print(f"\nResult: FAIL - {e}")
        return False


def test_5_240_frame_compound():
    """Test 5: 240-frame compound animation (walk → stop → wave → hold)."""
    print("\nTest 5: 240-frame compound (walk → stop → wave → hold)")
    print_separator()
    
    try:
        request = AnimationRequest(action="compound", frame_count=240)
        print(f"Request: {request.action}, {request.frame_count} frames")
        
        # Define phases with weights
        phases = [
            ("walk", 0.5),   # 50% = 120 frames
            ("stop", 0.1),   # 10% = 24 frames
            ("wave", 0.25),  # 25% = 60 frames
            ("hold", 0.15)   # 15% = 36 frames
        ]
        
        plan = create_compound_plan(request, phases)
        print(f"Timeline: 1-{plan.timeline.total_frames}")
        print(f"Segments: {len(plan.timeline.segments)}")
        
        for seg in plan.timeline.segments:
            duration = seg.duration()
            print(f"  - {seg.action}: frames {seg.start_frame}-{seg.end_frame} ({duration} frames)")
        
        print(f"Validated: {plan.validated}")
        
        # Verify we have all 4 actions
        actions = [seg.action for seg in plan.timeline.segments]
        has_all_actions = all(action in actions for action in ["walk", "stop", "wave", "hold"])
        
        if plan.validated and plan.timeline.total_frames == 240 and has_all_actions:
            print("\nResult: PASS")
            return True
        else:
            print(f"\nResult: FAIL - {plan.validation_errors}")
            return False
    except Exception as e:
        print(f"\nResult: FAIL - {e}")
        return False


def test_6_invalid_gap():
    """Test 6: Invalid timeline with gap."""
    print("\nTest 6: Invalid timeline with gap")
    print_separator()
    
    try:
        request = AnimationRequest(action="test", frame_count=100)
        timeline = Timeline(total_frames=100)
        
        # Create segments with gap (1-40, then 45-100, missing 41-44)
        seg1 = TimelineSegment(name="part1", action="action1", start_frame=1, end_frame=40)
        seg2 = TimelineSegment(name="part2", action="action2", start_frame=45, end_frame=100)
        
        timeline.add_segment(seg1)
        timeline.add_segment(seg2)
        
        print(f"Timeline: 1-{timeline.total_frames}")
        print(f"Segments:")
        print(f"  - {seg1.action}: frames {seg1.start_frame}-{seg1.end_frame}")
        print(f"  - {seg2.action}: frames {seg2.start_frame}-{seg2.end_frame}")
        print(f"Gap: frames 41-44")
        
        plan = AnimationPlan(request=request, timeline=timeline)
        validator = TimelineValidator()
        is_valid, errors = validator.validate_plan(plan)
        
        print(f"Validated: {is_valid}")
        if errors:
            print(f"Errors:")
            for err in errors:
                print(f"  - {err}")
        
        # Should FAIL with gap detected
        if not is_valid and any("gap" in err.lower() for err in errors):
            print("\nResult: PASS (gap correctly detected)")
            return True
        else:
            print("\nResult: FAIL (gap not detected)")
            return False
    except Exception as e:
        print(f"\nResult: FAIL - {e}")
        return False


def test_7_invalid_overlap():
    """Test 7: Invalid timeline with overlap."""
    print("\nTest 7: Invalid timeline with overlap")
    print_separator()
    
    try:
        request = AnimationRequest(action="test", frame_count=100)
        timeline = Timeline(total_frames=100)
        
        # Create overlapping segments (1-50, then 40-100, overlap 40-50)
        seg1 = TimelineSegment(name="part1", action="action1", start_frame=1, end_frame=50)
        seg2 = TimelineSegment(name="part2", action="action2", start_frame=40, end_frame=100)
        
        timeline.add_segment(seg1)
        timeline.add_segment(seg2)
        
        print(f"Timeline: 1-{timeline.total_frames}")
        print(f"Segments:")
        print(f"  - {seg1.action}: frames {seg1.start_frame}-{seg1.end_frame}")
        print(f"  - {seg2.action}: frames {seg2.start_frame}-{seg2.end_frame}")
        print(f"Overlap: frames 40-50")
        
        plan = AnimationPlan(request=request, timeline=timeline)
        validator = TimelineValidator()
        is_valid, errors = validator.validate_plan(plan)
        
        print(f"Validated: {is_valid}")
        if errors:
            print(f"Errors:")
            for err in errors:
                print(f"  - {err}")
        
        # Should FAIL with overlap detected
        if not is_valid and any("overlap" in err.lower() for err in errors):
            print("\nResult: PASS (overlap correctly detected)")
            return True
        else:
            print("\nResult: FAIL (overlap not detected)")
            return False
    except Exception as e:
        print(f"\nResult: FAIL - {e}")
        return False


def test_8_invalid_frame_count():
    """Test 8: Invalid frame count."""
    print("\nTest 8: Invalid frame count")
    print_separator()
    
    try:
        # Try to create request with invalid frame count
        print("Attempting to create request with frame_count=0")
        request = AnimationRequest(action="walk", frame_count=0)
        
        print("\nResult: FAIL (should have raised ValueError)")
        return False
    except ValueError as e:
        print(f"ValueError raised: {e}")
        print("\nResult: PASS (invalid frame count correctly rejected)")
        return True
    except Exception as e:
        print(f"\nResult: FAIL - Unexpected error: {e}")
        return False


def run_all_tests():
    """Run all Phase 2 tests."""
    print("=" * 60)
    print("PHASE 2 STANDALONE TEST/DEMO")
    print("=" * 60)
    print("\nTesting: AnimationRequest, Timeline, TimelineSegment,")
    print("         KeyPose, AnimationPlan, TimelineAllocator")
    print("\nNO GROQ. NO KRITA. NO MCP. NO RENDERER. NO FRAMES.")
    print("=" * 60)
    
    results = []
    
    # Run all tests
    results.append(("Test 1: 20-frame walk", test_1_20_frame_walk()))
    results.append(("Test 2: 100-frame walk", test_2_100_frame_walk()))
    results.append(("Test 3: 240-frame walk", test_3_240_frame_walk()))
    results.append(("Test 4: 250-frame walk", test_4_250_frame_walk()))
    results.append(("Test 5: 240-frame compound", test_5_240_frame_compound()))
    results.append(("Test 6: Invalid gap", test_6_invalid_gap()))
    results.append(("Test 7: Invalid overlap", test_7_invalid_overlap()))
    results.append(("Test 8: Invalid frame count", test_8_invalid_frame_count()))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print("=" * 60)
    print(f"Total: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("\nAll Phase 2 tests PASSED")
    else:
        print(f"\n{total - passed} test(s) FAILED")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
