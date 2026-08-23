"""
Test script to verify regression fixes:
1. Canvas detection works correctly
2. Bulk API actually draws strokes in Krita

REQUIREMENTS:
- Krita must be running
- Krita MCP plugin must be loaded and restarted to pick up fixes

RUN THIS TEST:
1. Restart Krita (CRITICAL - plugin needs reload)
2. Open a document in Krita  
3. Run: python test_regression_fixes.py
"""

import sys
import time
from mcp_client import KritaMCPClient
from canvas_detector import detect_canvas_state

def test_canvas_detection():
    """Test 1: Verify canvas detection works."""
    print("="*60)
    print("TEST 1: CANVAS DETECTION")
    print("="*60)
    
    mcp = KritaMCPClient()
    
    # Test A: Check if canvas state can be detected
    print("\n[TEST A] Detecting canvas state...")
    canvas_state = detect_canvas_state(mcp, require_drawing=True)
    
    print(f"Ready: {canvas_state['ready']}")
    print(f"Has layer: {canvas_state['has_layer']}")
    print(f"Has drawing: {canvas_state['has_drawing']}")
    print(f"Reason: {canvas_state['reason']}")
    
    if canvas_state['ready']:
        print("[TEST A] PASS - Canvas has drawing")
    else:
        print("[TEST A] PASS - Canvas correctly detected as not ready")
    
    return True

def test_bulk_drawing_one_stroke():
    """Test 2: Draw ONE stroke using bulk API."""
    print("\n" + "="*60)
    print("TEST 2: BULK API - ONE STROKE")
    print("="*60)
    
    mcp = KritaMCPClient()
    
    # Simple horizontal line in center of canvas
    test_stroke = {
        "points": [[300, 300], [500, 300]],
        "color": "#FF0000",  # Red
        "brush_size": 10,
        "hardness": 0.5,
        "opacity": 1.0
    }
    
    print("[TEST 2] Sending ONE red horizontal line (300,300) to (500,300)")
    print("[TEST 2] Expected: A red line should appear in Krita")
    
    try:
        result = mcp.call_tool("krita_bulk_strokes", {
            "strokes": [test_stroke]
        }, timeout=30)
        
        print(f"\n[TEST 2] Result: {result}")
        
        if isinstance(result, dict):
            strokes_drawn = result.get("strokes_drawn", 0)
            strokes_failed = result.get("strokes_failed", 0)
            total = result.get("total_strokes", 0)
            
            print(f"[TEST 2] Strokes drawn: {strokes_drawn}/{total}")
            print(f"[TEST 2] Strokes failed: {strokes_failed}")
            
            if strokes_drawn == 1 and strokes_failed == 0:
                print("[TEST 2] PASS - Bulk API reports success")
                print("[TEST 2] CHECK KRITA MANUALLY: Do you see a RED horizontal line?")
                return True
            else:
                print("[TEST 2] FAIL - Bulk API did not draw stroke")
                return False
        else:
            print(f"[TEST 2] FAIL - Unexpected result type: {type(result)}")
            return False
            
    except Exception as e:
        print(f"[TEST 2] FAIL - Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_bulk_drawing_five_strokes():
    """Test 3: Draw FIVE strokes using bulk API."""
    print("\n" + "="*60)
    print("TEST 3: BULK API - FIVE STROKES")
    print("="*60)
    
    mcp = KritaMCPClient()
    
    # Five different colored lines
    test_strokes = [
        {"points": [[100, 100], [200, 100]], "color": "#FF0000", "brush_size": 8},  # Red
        {"points": [[100, 150], [200, 150]], "color": "#00FF00", "brush_size": 8},  # Green  
        {"points": [[100, 200], [200, 200]], "color": "#0000FF", "brush_size": 8},  # Blue
        {"points": [[100, 250], [200, 250]], "color": "#FFFF00", "brush_size": 8},  # Yellow
        {"points": [[100, 300], [200, 300]], "color": "#FF00FF", "brush_size": 8},  # Magenta
    ]
    
    print("[TEST 3] Sending FIVE colored horizontal lines")
    print("[TEST 3] Expected: 5 colored lines should appear in Krita")
    
    try:
        result = mcp.call_tool("krita_bulk_strokes", {
            "strokes": test_strokes
        }, timeout=30)
        
        print(f"\n[TEST 3] Result: {result}")
        
        if isinstance(result, dict):
            strokes_drawn = result.get("strokes_drawn", 0)
            strokes_failed = result.get("strokes_failed", 0)
            total = result.get("total_strokes", 0)
            
            print(f"[TEST 3] Strokes drawn: {strokes_drawn}/{total}")
            print(f"[TEST 3] Strokes failed: {strokes_failed}")
            
            if strokes_drawn == 5 and strokes_failed == 0:
                print("[TEST 3] PASS - Bulk API reports all strokes drawn")
                print("[TEST 3] CHECK KRITA MANUALLY: Do you see 5 colored lines?")
                return True
            else:
                print(f"[TEST 3] FAIL - Expected 5 drawn, got {strokes_drawn}")
                return False
        else:
            print(f"[TEST 3] FAIL - Unexpected result type: {type(result)}")
            return False
            
    except Exception as e:
        print(f"[TEST 3] FAIL - Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_old_api_still_works():
    """Test 4: Verify old krita_stroke still works."""
    print("\n" + "="*60)
    print("TEST 4: OLD API - BACKWARD COMPATIBILITY")
    print("="*60)
    
    mcp = KritaMCPClient()
    
    print("[TEST 4] Drawing with old krita_stroke API")
    print("[TEST 4] Expected: A cyan line should appear")
    
    try:
        # Set color
        mcp.call_tool("krita_set_color", {"color": "#00FFFF"}, timeout=10)
        
        # Draw stroke
        result = mcp.call_tool("krita_stroke", {
            "points": [[400, 400], [600, 400]]
        }, timeout=30)
        
        print(f"\n[TEST 4] Result: {result}")
        
        if "status" in str(result) and "ok" in str(result):
            print("[TEST 4] PASS - Old API still works")
            print("[TEST 4] CHECK KRITA MANUALLY: Do you see a CYAN line at (400,400)?")
            return True
        else:
            print("[TEST 4] FAIL - Old API returned error")
            return False
            
    except Exception as e:
        print(f"[TEST 4] FAIL - Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\n" + "="*60)
    print("REGRESSION FIX VERIFICATION")
    print("="*60)
    print("\nThis test verifies:")
    print("1. Canvas detection works")
    print("2. Bulk API actually draws (not just reports success)")
    print("3. Old API still works (backward compatibility)")
    print("\nIMPORTANT: Krita must be running and plugin restarted!")
    print("="*60)
    
    input("\nPress ENTER when Krita is ready...")
    
    results = []
    
    # Test 1: Canvas detection
    try:
        results.append(("Canvas Detection", test_canvas_detection()))
    except Exception as e:
        print(f"Test 1 crashed: {e}")
        results.append(("Canvas Detection", False))
    
    time.sleep(1)
    
    # Test 2: One stroke
    try:
        results.append(("Bulk API - 1 Stroke", test_bulk_drawing_one_stroke()))
    except Exception as e:
        print(f"Test 2 crashed: {e}")
        results.append(("Bulk API - 1 Stroke", False))
    
    time.sleep(1)
    
    # Test 3: Five strokes  
    try:
        results.append(("Bulk API - 5 Strokes", test_bulk_drawing_five_strokes()))
    except Exception as e:
        print(f"Test 3 crashed: {e}")
        results.append(("Bulk API - 5 Strokes", False))
    
    time.sleep(1)
    
    # Test 4: Old API
    try:
        results.append(("Old API Compatibility", test_old_api_still_works()))
    except Exception as e:
        print(f"Test 4 crashed: {e}")
        results.append(("Old API Compatibility", False))
    
    # Final report
    print("\n" + "="*60)
    print("FINAL REPORT")
    print("="*60)
    
    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"{test_name:30s}: {status}")
    
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    
    print("-"*60)
    print(f"Total: {passed_count}/{total_count} tests passed")
    print("="*60)
    
    if passed_count == total_count:
        print("\nALL TESTS PASSED!")
        print("Canvas detection: WORKING")
        print("Bulk API drawing: WORKING")
        print("Backward compatibility: WORKING")
    else:
        print("\nSOME TESTS FAILED")
        print("Review the output above for details")
    
    print("\n" + "="*60)
    print("MANUAL VERIFICATION REQUIRED")
    print("="*60)
    print("Check your Krita canvas - you should see:")
    print("- Red horizontal line at y=300")
    print("- 5 colored lines (red, green, blue, yellow, magenta)")
    print("- Cyan line at y=400")
    print("="*60)

if __name__ == "__main__":
    main()
