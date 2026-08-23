"""
Test: One Simple Line Detection

This tests the most basic case:
1. Clear canvas → detection FALSE
2. Draw ONE red line → detection TRUE
"""

import time
from mcp_client import KritaMCPClient
from canvas_detector import detect_canvas_state


def main():
    print("="*60)
    print("TEST: ONE LINE DETECTION")
    print("="*60)
    
    mcp = KritaMCPClient()
    
    # Test 1: Empty canvas
    print("\n[TEST 1] EMPTY CANVAS")
    print("-"*60)
    print("Setup: Please clear the canvas completely")
    print("       (Select All → Delete, or Ctrl+A then Delete)")
    input("\nPress Enter when canvas is empty...")
    
    print("\nRunning detection...")
    state = detect_canvas_state(mcp, require_drawing=True)
    
    if not state['ready']:
        print("✓ TEST 1 PASSED: Empty canvas correctly rejected")
    else:
        print("✗ TEST 1 FAILED: Empty canvas incorrectly detected as having content")
        print(f"   Reason: {state['reason']}")
    
    # Test 2: One line
    print("\n[TEST 2] ONE RED LINE")
    print("-"*60)
    print("Step 1: Drawing one red horizontal line...")
    
    try:
        # Draw one simple red line
        result = mcp.call_tool("krita_stroke", {
            "color": "#ff0000",
            "brush_size": 5,
            "opacity": 1.0,
            "points": [
                {"x": 200, "y": 300, "pressure": 1.0},
                {"x": 600, "y": 300, "pressure": 1.0}
            ]
        }, timeout=30)
        
        if result and "error" not in str(result):
            print("✓ Line drawn")
        else:
            print(f"✗ Drawing failed: {result}")
            return
    
    except Exception as e:
        print(f"✗ Drawing error: {e}")
        return
    
    print("\nStep 2: Waiting for Krita to render...")
    time.sleep(1)
    
    print("\nStep 3: Running detection...")
    state = detect_canvas_state(mcp, require_drawing=True)
    
    print("\n" + "="*60)
    print("RESULT")
    print("="*60)
    print(f"Ready: {state['ready']}")
    print(f"Has layer: {state['has_layer']}")
    print(f"Has drawing: {state['has_drawing']}")
    print(f"Reason: {state['reason']}")
    
    if state['ready']:
        print("\n✓ TEST 2 PASSED: One line correctly detected")
    else:
        print("\n✗ TEST 2 FAILED: One line was NOT detected")
        print("\nDEBUG INFO:")
        print("- Check Krita - is the red line visible?")
        print("- If visible but not detected, there's a detection bug")
        print("- Run: python diagnose_krita_state.py for details")
    
    print("\n" + "="*60)
    print("VERIFICATION")
    print("="*60)
    print("Check Krita canvas:")
    print("- You should see ONE red horizontal line")
    print("- If yes but detection failed, there's a detection bug")
    print("- If no line visible, there's a drawing bug")
    print("\n" + "="*60)


if __name__ == "__main__":
    main()
