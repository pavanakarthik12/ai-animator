"""Frame Count Integration Test

Verifies that frame counts propagate correctly through the system.

Tests frame counts without rendering:
- 20 frames
- 50 frames
- 100 frames
- 200 frames
- 240 frames
- 250 frames

NO GROQ. NO KRITA. NO MCP. NO RENDERING.
"""

from animation_timeline import (
    AnimationRequest,
    Timeline,
    AnimationPlan,
    TimelineAllocator,
    TimelineValidator,
    create_simple_plan
)


def test_frame_count(count: int) -> bool:
    """Test that frame count propagates correctly."""
    print(f"\nTesting {count}-frame animation")
    print("-" * 60)
    
    try:
        # Create request
        request = AnimationRequest(action="walk", frame_count=count)
        print(f"AnimationRequest.frame_count: {request.frame_count}")
        
        # Create plan
        plan = create_simple_plan(request)
        print(f"AnimationPlan.timeline.total_frames: {plan.timeline.total_frames}")
        
        # Verify timeline
        timeline = plan.timeline
        print(f"Timeline start: {timeline.segments[0].start_frame}")
        print(f"Timeline end: {timeline.segments[0].end_frame}")
        
        # Validate
        validator = TimelineValidator()
        is_valid, errors = validator.validate_plan(plan)
        print(f"Validated: {is_valid}")
        
        if errors:
            print("Errors:")
            for err in errors:
                print(f"  - {err}")
            return False
        
        # Verify all values match
        if request.frame_count != count:
            print(f"FAIL: Request frame_count mismatch: {request.frame_count} != {count}")
            return False
        
        if plan.timeline.total_frames != count:
            print(f"FAIL: Timeline total_frames mismatch: {plan.timeline.total_frames} != {count}")
            return False
        
        if timeline.segments[0].start_frame != 1:
            print(f"FAIL: Timeline doesn't start at 1: {timeline.segments[0].start_frame}")
            return False
        
        if timeline.segments[0].end_frame != count:
            print(f"FAIL: Timeline doesn't end at {count}: {timeline.segments[0].end_frame}")
            return False
        
        print(f"Result: PASS")
        return True
        
    except Exception as e:
        print(f"Result: FAIL - {e}")
        return False


def run_all_tests():
    """Run all frame count integration tests."""
    print("=" * 60)
    print("FRAME COUNT INTEGRATION TEST")
    print("=" * 60)
    print("\nVerifying frame counts propagate through:")
    print("  AnimationRequest → AnimationPlan → Timeline")
    print("\nNO GROQ. NO KRITA. NO MCP. NO RENDERING.")
    print("=" * 60)
    
    test_counts = [20, 50, 100, 200, 240, 250]
    results = {}
    
    for count in test_counts:
        results[count] = test_frame_count(count)
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for count, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"{count:3d} frames: {status}")
    
    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    
    print("=" * 60)
    print(f"Total: {passed_count}/{total_count} tests passed")
    print("=" * 60)
    
    if passed_count == total_count:
        print("\nAll frame count integration tests PASSED")
        print("\nHard-coded 20-frame production limit: REMOVED")
        print("Frame counts now support arbitrary positive integers")
    else:
        print(f"\n{total_count - passed_count} test(s) FAILED")
    
    return passed_count == total_count


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
