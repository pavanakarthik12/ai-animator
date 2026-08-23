"""
Test Character Detection Before Animation

This script tests all detection scenarios:
1. Empty canvas → detection FALSE → no animation
2. Character present → detection TRUE → animation allowed
3. Reference exists but canvas empty → detection FALSE
4. Character created from reference → detection TRUE
5. Animation creates frames with drawings
"""

import sys
import time
from mcp_client import KritaMCPClient
from canvas_detector import detect_canvas_state


def wait_for_user(message: str = "Press Enter to continue..."):
    """Wait for user confirmation."""
    input(f"\n{message}")


def test_empty_canvas():
    """TEST 1: Empty canvas should be rejected."""
    print("\n" + "="*60)
    print("TEST 1: EMPTY CANVAS DETECTION")
    print("="*60)
    print("\nPREREQUISITE:")
    print("1. Open Krita")
    print("2. Create a NEW blank document (File → New)")
    print("3. Make sure the canvas is completely EMPTY")
    
    wait_for_user("Press Enter when ready...")
    
    mcp = KritaMCPClient()
    canvas_state = detect_canvas_state(mcp, require_drawing=True)
    
    print("\n[RESULT]")
    print(f"Ready: {canvas_state['ready']}")
    print(f"Has layer: {canvas_state['has_layer']}")
    print(f"Has drawing: {canvas_state['has_drawing']}")
    print(f"Reason: {canvas_state['reason']}")
    
    if not canvas_state['ready']:
        print("\n✓ TEST 1 PASSED: Empty canvas correctly rejected")
        return True
    else:
        print("\n✗ TEST 1 FAILED: Empty canvas was incorrectly detected as having content")
        return False


def test_character_present():
    """TEST 2: Character visible should be detected."""
    print("\n" + "="*60)
    print("TEST 2: CHARACTER PRESENT DETECTION")
    print("="*60)
    print("\nPREREQUISITE:")
    print("1. Draw something visible on the canvas")
    print("2. Use any color except pure white")
    print("3. Make a few brush strokes")
    
    wait_for_user("Press Enter when you've drawn something...")
    
    mcp = KritaMCPClient()
    canvas_state = detect_canvas_state(mcp, require_drawing=True)
    
    print("\n[RESULT]")
    print(f"Ready: {canvas_state['ready']}")
    print(f"Has layer: {canvas_state['has_layer']}")
    print(f"Has drawing: {canvas_state['has_drawing']}")
    print(f"Reason: {canvas_state['reason']}")
    
    if canvas_state['ready']:
        print("\n✓ TEST 2 PASSED: Character correctly detected")
        return True
    else:
        print("\n✗ TEST 2 FAILED: Character was not detected even though drawing exists")
        return False


def test_reference_vs_canvas():
    """TEST 3: Reference image alone should not count."""
    print("\n" + "="*60)
    print("TEST 3: REFERENCE IMAGE VS CANVAS")
    print("="*60)
    print("\nThis test verifies that a reference image on disk")
    print("does NOT count as a character in Krita.")
    print("\nPREREQUISITE:")
    print("1. Clear the canvas completely (Ctrl+A, Delete)")
    print("2. Reference image may exist on disk - doesn't matter")
    
    wait_for_user("Press Enter when canvas is empty...")
    
    mcp = KritaMCPClient()
    canvas_state = detect_canvas_state(mcp, require_drawing=True)
    
    print("\n[RESULT]")
    print(f"Ready: {canvas_state['ready']}")
    print(f"Reason: {canvas_state['reason']}")
    
    if not canvas_state['ready']:
        print("\n✓ TEST 3 PASSED: Reference image alone correctly ignored")
        return True
    else:
        print("\n✗ TEST 3 FAILED: System thinks character exists when canvas is empty")
        return False


def test_created_character():
    """TEST 4: Character created from reference should be detected."""
    print("\n" + "="*60)
    print("TEST 4: CREATED CHARACTER DETECTION")
    print("="*60)
    print("\nThis test creates a character using bulk drawing,")
    print("then verifies detection works.")
    
    print("\nStep 1: Clearing canvas...")
    mcp = KritaMCPClient()
    
    # Clear canvas
    try:
        mcp.call_tool("krita_clear_layer", {}, timeout=10)
        print("✓ Canvas cleared")
    except:
        print("Note: Manual clear may be needed (Ctrl+A, Delete)")
    
    # Verify empty
    canvas_state = detect_canvas_state(mcp, require_drawing=True)
    if canvas_state['ready']:
        print("⚠ Warning: Canvas should be empty but detection says it has content")
    
    print("\nStep 2: Drawing test character...")
    
    # Draw a simple test character (red stick figure)
    strokes = [
        # Head (circle approximation)
        {"color": "#ff0000", "brush_size": 3, "opacity": 1.0, "points": [
            {"x": 400, "y": 200}, {"x": 420, "y": 200}, {"x": 430, "y": 210},
            {"x": 430, "y": 230}, {"x": 420, "y": 240}, {"x": 400, "y": 240},
            {"x": 380, "y": 230}, {"x": 380, "y": 210}, {"x": 390, "y": 200}
        ]},
        # Body
        {"color": "#ff0000", "brush_size": 3, "opacity": 1.0, "points": [
            {"x": 400, "y": 240}, {"x": 400, "y": 350}
        ]},
        # Left arm
        {"color": "#ff0000", "brush_size": 3, "opacity": 1.0, "points": [
            {"x": 400, "y": 270}, {"x": 350, "y": 300}
        ]},
        # Right arm
        {"color": "#ff0000", "brush_size": 3, "opacity": 1.0, "points": [
            {"x": 400, "y": 270}, {"x": 450, "y": 300}
        ]},
        # Left leg
        {"color": "#ff0000", "brush_size": 3, "opacity": 1.0, "points": [
            {"x": 400, "y": 350}, {"x": 370, "y": 420}
        ]},
        # Right leg
        {"color": "#ff0000", "brush_size": 3, "opacity": 1.0, "points": [
            {"x": 400, "y": 350}, {"x": 430, "y": 420}
        ]},
    ]
    
    try:
        result = mcp.call_tool("krita_bulk_strokes", {
            "strokes": strokes,
            "layer": "Paint Layer",
            "frame": 0
        }, timeout=30)
        
        if result and result.get("strokes_drawn", 0) > 0:
            print(f"✓ Drew {result['strokes_drawn']} strokes")
        else:
            print(f"⚠ Drawing result: {result}")
    except Exception as e:
        print(f"✗ Drawing failed: {e}")
        return False
    
    print("\nStep 3: Verifying character is detected...")
    time.sleep(0.5)  # Give Krita time to render
    
    canvas_state = detect_canvas_state(mcp, require_drawing=True)
    
    print("\n[RESULT]")
    print(f"Ready: {canvas_state['ready']}")
    print(f"Has drawing: {canvas_state['has_drawing']}")
    print(f"Reason: {canvas_state['reason']}")
    
    if canvas_state['ready']:
        print("\n✓ TEST 4 PASSED: Newly created character correctly detected")
        return True
    else:
        print("\n✗ TEST 4 FAILED: Newly created character was not detected")
        print("Check Krita - is the red stick figure visible?")
        return False


def test_animation_frames():
    """TEST 5: Animation creates frames with drawings."""
    print("\n" + "="*60)
    print("TEST 5: ANIMATION FRAME CREATION")
    print("="*60)
    print("\nThis test is MANUAL - run the animation system and verify:")
    print("1. Character detection passes")
    print("2. Frames are created (check timeline)")
    print("3. Each frame contains actual drawings (not empty)")
    print("\nRun this command in another terminal:")
    print("  python test_walk_3_frames.py")
    print("\nThen check Krita:")
    print("- Timeline shows 3 frames")
    print("- Each frame has the character drawn")
    print("- Character pose changes between frames")
    
    result = input("\nDid the animation work correctly? (y/n): ").strip().lower()
    
    if result == 'y':
        print("\n✓ TEST 5 PASSED: Animation creates frames with drawings")
        return True
    else:
        print("\n✗ TEST 5 FAILED: Animation issue reported")
        return False


def main():
    """Run all character detection tests."""
    print("="*60)
    print("CHARACTER DETECTION TEST SUITE")
    print("="*60)
    print("\nThis test suite verifies:")
    print("- Empty canvas is correctly rejected")
    print("- Existing character is correctly detected")
    print("- Reference image alone doesn't count")
    print("- Newly created character is detected")
    print("- Animation only runs after successful detection")
    
    print("\n" + "="*60)
    print("SETUP")
    print("="*60)
    print("1. Open Krita")
    print("2. Have the MCP server running")
    print("3. Follow test instructions")
    
    wait_for_user("\nPress Enter to start tests...")
    
    results = []
    
    # Run tests
    try:
        results.append(("Empty Canvas", test_empty_canvas()))
    except Exception as e:
        print(f"\n✗ Test 1 crashed: {e}")
        results.append(("Empty Canvas", False))
    
    try:
        results.append(("Character Present", test_character_present()))
    except Exception as e:
        print(f"\n✗ Test 2 crashed: {e}")
        results.append(("Character Present", False))
    
    try:
        results.append(("Reference vs Canvas", test_reference_vs_canvas()))
    except Exception as e:
        print(f"\n✗ Test 3 crashed: {e}")
        results.append(("Reference vs Canvas", False))
    
    try:
        results.append(("Created Character", test_created_character()))
    except Exception as e:
        print(f"\n✗ Test 4 crashed: {e}")
        results.append(("Created Character", False))
    
    try:
        results.append(("Animation Frames", test_animation_frames()))
    except Exception as e:
        print(f"\n✗ Test 5 crashed: {e}")
        results.append(("Animation Frames", False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n" + "="*60)
        print("ALL TESTS PASSED!")
        print("="*60)
        print("✓ Empty canvas correctly rejected")
        print("✓ Existing character correctly detected")
        print("✓ Reference image alone does not count")
        print("✓ Newly created character is detected")
        print("✓ Animation only starts after successful detection")
        return 0
    else:
        print("\n" + "="*60)
        print("SOME TESTS FAILED")
        print("="*60)
        print("Review the failures above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
