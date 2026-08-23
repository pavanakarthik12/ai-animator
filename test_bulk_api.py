"""
Test script to verify krita_bulk_strokes functionality.
Tests with a single simple stroke first.
"""

import sys
import time
from config import config
from mcp_client import KritaMCPClient

def test_bulk_api():
    print("="*60)
    print("BULK API DEBUG TEST")
    print("="*60)
    
    # Start MCP client
    krita_server = config.krita_mcp_server
    if not krita_server:
        print("ERROR: KRITA_MCP_SERVER not set in .env")
        return
    
    print(f"MCP Server: {krita_server}")
    
    mcp = KritaMCPClient(krita_server)
    print("Starting MCP client...")
    mcp.start()
    
    # List available tools
    print("\n" + "="*60)
    print("AVAILABLE MCP TOOLS:")
    print("="*60)
    tools = mcp.list_tools()
    for tool in tools:
        print(f"  - {tool}")
    
    # Check if bulk API exists
    has_bulk = "krita_bulk_strokes" in tools
    print(f"\nkrita_bulk_strokes available: {has_bulk}")
    
    if not has_bulk:
        print("ERROR: krita_bulk_strokes not found in MCP tools!")
        print("The bulk API is not registered.")
        return
    
    # Test 1: Single stroke with krita_stroke (baseline)
    print("\n" + "="*60)
    print("TEST 1: Single stroke via krita_stroke (baseline)")
    print("="*60)
    
    test_points = [[300, 200], [500, 200]]  # Horizontal line
    
    try:
        # Set color first
        mcp.call_tool("krita_set_color", {"color": "#ff0000"}, timeout=10)
        mcp.call_tool("krita_set_brush", {"size": 5}, timeout=10)
        
        result = mcp.call_tool("krita_stroke", {
            "points": test_points,
            "pressure": 1.0
        }, timeout=30)
        
        print(f"Result: {result}")
        print("✓ krita_stroke completed")
        print("\nCheck Krita canvas - you should see a RED horizontal line")
        input("Press Enter after verifying the line appears...")
        
    except Exception as e:
        print(f"✗ krita_stroke failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 2: Single stroke with krita_bulk_strokes
    print("\n" + "="*60)
    print("TEST 2: Single stroke via krita_bulk_strokes")
    print("="*60)
    
    test_stroke = {
        "points": [[300, 250], [500, 250]],  # Horizontal line below first
        "color": "#00ff00",  # Green
        "brush_size": 5,
        "pressure": 1.0
    }
    
    try:
        print("[TEST] Calling krita_bulk_strokes with 1 stroke...")
        print(f"[TEST] Stroke data: {test_stroke}")
        
        result = mcp.call_tool("krita_bulk_strokes", {
            "strokes": [test_stroke]
        }, timeout=30)
        
        print(f"\n[TEST] Result: {result}")
        
        if isinstance(result, dict):
            drawn = result.get("strokes_drawn", 0)
            failed = result.get("strokes_failed", 0)
            errors = result.get("errors")
            
            print(f"\nStrokes drawn: {drawn}")
            print(f"Strokes failed: {failed}")
            if errors:
                print(f"Errors: {errors}")
            
            if drawn == 1:
                print("✓ krita_bulk_strokes reported success")
                print("\nCheck Krita canvas - you should see a GREEN horizontal line below the red one")
                input("Press Enter after verifying...")
            else:
                print("✗ krita_bulk_strokes did not draw the stroke")
        else:
            print(f"✗ Unexpected result type: {type(result)}")
            print(f"Result: {result}")
        
    except Exception as e:
        print(f"✗ krita_bulk_strokes failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Multiple strokes
    print("\n" + "="*60)
    print("TEST 3: Multiple strokes via krita_bulk_strokes")
    print("="*60)
    
    multi_strokes = [
        {
            "points": [[300, 300], [400, 300]],
            "color": "#ff00ff",  # Magenta
            "brush_size": 3
        },
        {
            "points": [[400, 300], [500, 350]],
            "color": "#00ffff",  # Cyan
            "brush_size": 3
        },
        {
            "points": [[500, 350], [500, 400]],
            "color": "#ffff00",  # Yellow
            "brush_size": 3
        }
    ]
    
    try:
        print(f"[TEST] Calling krita_bulk_strokes with {len(multi_strokes)} strokes...")
        
        result = mcp.call_tool("krita_bulk_strokes", {
            "strokes": multi_strokes
        }, timeout=30)
        
        print(f"\n[TEST] Result: {result}")
        
        if isinstance(result, dict):
            drawn = result.get("strokes_drawn", 0)
            failed = result.get("strokes_failed", 0)
            
            print(f"\nStrokes drawn: {drawn}/{len(multi_strokes)}")
            print(f"Strokes failed: {failed}")
            
            if drawn == len(multi_strokes):
                print("✓ All strokes drawn successfully")
                print("\nCheck Krita canvas - you should see a 3-segment colored path")
                input("Press Enter after verifying...")
            else:
                print(f"✗ Only {drawn}/{len(multi_strokes)} strokes drawn")
        
    except Exception as e:
        print(f"✗ krita_bulk_strokes multi-stroke test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    test_bulk_api()
