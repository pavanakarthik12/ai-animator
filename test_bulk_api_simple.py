"""
Simple Bulk API Test

Tests the fixed bulk_strokes implementation with minimal strokes.

REQUIREMENTS:
1. Krita must be running
2. Krita must have been RESTARTED after the plugin fix
3. A document must be open with a paint layer

RUN: python test_bulk_api_simple.py
"""

import sys
import time
from mcp_client import KritaMCPClient

def test_one_stroke():
    """Test 1: Draw ONE stroke."""
    print("="*60)
    print("TEST 1: ONE STROKE")
    print("="*60)
    
    mcp = KritaMCPClient()
    
    stroke = {
        "points": [[300, 300], [500, 300]],
        "color": "#FF0000",
        "brush_size": 10,
        "hardness": 0.5,
        "opacity": 1.0
    }
    
    print("Sending ONE red horizontal line from (300,300) to (500,300)")
    print("Expected: Red line should appear in Krita")
    
    try:
        result = mcp.call_tool("krita_bulk_strokes", {"strokes": [stroke]}, timeout=30)
        
        print(f"\nResult: {result}")
        
        if isinstance(result, dict):
            if "error" in result:
                print(f"\nFAIL: {result['error']}")
                if "Unknown action" in result["error"]:
                    print("\nKrita plugin was NOT reloaded!")
                    print("You MUST restart Krita for the fix to take effect.")
                return False
            
            drawn = result.get("strokes_drawn", 0)
            failed = result.get("strokes_failed", 0)
            
            if drawn == 1 and failed == 0:
                print("\nPASS: Bulk API reports success")
                print("CHECK KRITA: Do you see a RED line at y=300?")
                return True
            else:
                print(f"\nFAIL: drawn={drawn}, failed={failed}")
                return False
        else:
            print(f"\nFAIL: Unexpected result type: {type(result)}")
            return False
            
    except Exception as e:
        print(f"\nFAIL: Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_five_strokes():
    """Test 2: Draw FIVE strokes."""
    print("\n" + "="*60)
    print("TEST 2: FIVE STROKES")
    print("="*60)
    
    mcp = KritaMCPClient()
    
    strokes = [
        {"points": [[100, 100], [200, 100]], "color": "#FF0000", "brush_size": 8},
        {"points": [[100, 150], [200, 150]], "color": "#00FF00", "brush_size": 8},
        {"points": [[100, 200], [200, 200]], "color": "#0000FF", "brush_size": 8},
        {"points": [[100, 250], [200, 250]], "color": "#FFFF00", "brush_size": 8},
        {"points": [[100, 300], [200, 300]], "color": "#FF00FF", "brush_size": 8},
    ]
    
    print("Sending FIVE colored lines")
    print("Expected: 5 lines (red, green, blue, yellow, magenta) should appear")
    
    try:
        result = mcp.call_tool("krita_bulk_strokes", {"strokes": strokes}, timeout=30)
        
        print(f"\nResult: {result}")
        
        if isinstance(result, dict):
            if "error" in result:
                print(f"\nFAIL: {result['error']}")
                return False
            
            drawn = result.get("strokes_drawn", 0)
            failed = result.get("strokes_failed", 0)
            
            if drawn == 5 and failed == 0:
                print("\nPASS: All 5 strokes drawn")
                print("CHECK KRITA: Do you see 5 colored lines?")
                return True
            else:
                print(f"\nFAIL: drawn={drawn}/5, failed={failed}")
                return False
        else:
            print(f"\nFAIL: Unexpected result type")
            return False
            
    except Exception as e:
        print(f"\nFAIL: Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_old_api():
    """Test 3: Verify old API still works."""
    print("\n" + "="*60)
    print("TEST 3: OLD API COMPATIBILITY")
    print("="*60)
    
    mcp = KritaMCPClient()
    
    print("Testing old krita_stroke API")
    print("Expected: Cyan line should appear at y=400")
    
    try:
        # Set color
        mcp.call_tool("krita_set_color", {"color": "#00FFFF"}, timeout=10)
        
        # Draw stroke
        result = mcp.call_tool("krita_stroke", {"points": [[400, 400], [600, 400]]}, timeout=30)
        
        print(f"\nResult: {result}")
        
        if "status" in str(result) and "ok" in str(result):
            print("\nPASS: Old API still works")
            print("CHECK KRITA: Do you see a CYAN line at y=400?")
            return True
        else:
            print("\nFAIL: Old API returned error")
            return False
            
    except Exception as e:
        print(f"\nFAIL: Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\n" + "="*60)
    print("BULK API TEST - SIMPLE VERSION")
    print("="*60)
    print("\nThis tests the fixed bulk_strokes implementation.")
    print("\nCRITICAL: Krita must be RESTARTED after the plugin fix!")
    print("\nIf you haven't restarted Krita yet, do it now.")
    print("="*60)
    
    input("\nPress ENTER when Krita is ready (with document open)...")
    
    results = []
    
    # Test 1
    print("\nRunning Test 1...")
    time.sleep(0.5)
    results.append(("One Stroke", test_one_stroke()))
    
    # Test 2
    print("\nRunning Test 2...")
    time.sleep(1)
    results.append(("Five Strokes", test_five_strokes()))
    
    # Test 3
    print("\nRunning Test 3...")
    time.sleep(1)
    results.append(("Old API", test_old_api()))
    
    # Report
    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        symbol = "✓" if passed else "✗"
        print(f"{symbol} {name:20s}: {status}")
    
    passed_count = sum(1 for _, p in results if p)
    total = len(results)
    
    print("-"*60)
    print(f"Total: {passed_count}/{total} tests passed")
    print("="*60)
    
    if passed_count == total:
        print("\nSUCCESS! All tests passed.")
        print("\nBulk API is working correctly.")
        print("You should see these lines in Krita:")
        print("  - Red line at y=300")
        print("  - 5 colored lines at y=100-300")
        print("  - Cyan line at y=400")
    else:
        print("\nSOME TESTS FAILED")
        print("\nCommon issues:")
        print("  - 'Unknown action': Krita not restarted")
        print("  - Connection error: Krita not running")
        print("  - 'No paint layer': Create a paint layer first")
    
    print("="*60)

if __name__ == "__main__":
    main()
