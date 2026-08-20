"""Test frame creation system independently.

This tests ONLY frame creation and selection, no drawing.
"""
import sys
import os
from config import config
from mcp_client import KritaMCPClient
import time


def test_create_20_frames():
    """Create 20 empty frames and verify they exist."""
    print("="*60)
    print("FRAME SYSTEM TEST - Creating 20 Empty Frames")
    print("="*60)
    print()
    
    krita_server = config.krita_mcp_server
    if not krita_server:
        print("ERROR: KRITA_MCP_SERVER not set in .env")
        return False
    
    # Start MCP
    mcp = KritaMCPClient(krita_server)
    print("[TEST] Starting MCP client...")
    mcp.start()
    print("[TEST] MCP started successfully")
    print()
    
    # Select paint layer first
    try:
        result = mcp.call_tool("krita_select_paint_layer", {}, timeout=10)
        print(f"[TEST] Selected paint layer: {result}")
    except Exception as e:
        print(f"[TEST] ERROR selecting paint layer: {e}")
        return False
    
    print()
    print("[TEST] Creating 20 frames...")
    print()
    
    created_frames = []
    
    for frame_num in range(1, 21):
        print(f"[FRAME {frame_num}/20]")
        print(f"  Creating frame {frame_num}...")
        
        # Create keyframe
        try:
            result = mcp.call_tool("krita_create_keyframe", {"frame": frame_num}, timeout=10)
            print(f"  Create result: {result}")
        except Exception as e:
            print(f"  ERROR creating frame: {e}")
            continue
        
        # Set current frame
        try:
            result = mcp.call_tool("krita_set_current_frame", {"frame": frame_num}, timeout=10)
            print(f"  Set frame result: {result}")
        except Exception as e:
            print(f"  ERROR setting frame: {e}")
            continue
        
        # Verify current frame
        try:
            result = mcp.call_tool("krita_get_current_frame", {}, timeout=10)
            actual_frame = result.get("current_frame", -1) if isinstance(result, dict) else -1
            print(f"  Krita current frame = {actual_frame}")
            
            if actual_frame == frame_num:
                print(f"  ✓ Frame {frame_num} verified")
                created_frames.append(frame_num)
            else:
                print(f"  ✗ Frame verification FAILED (expected {frame_num}, got {actual_frame})")
        except Exception as e:
            print(f"  ERROR verifying frame: {e}")
        
        print()
        time.sleep(0.1)  # Small delay between frames
    
    # Final verification - list all keyframes
    print("="*60)
    print("FINAL VERIFICATION")
    print("="*60)
    print()
    
    try:
        result = mcp.call_tool("krita_list_keyframes", {}, timeout=10)
        print(f"Krita keyframes list: {result}")
        
        if isinstance(result, dict) and "keyframes" in result:
            keyframes = result["keyframes"]
            print(f"\nTotal keyframes in Krita: {len(keyframes)}")
            print(f"Keyframes: {keyframes}")
            print()
            
            if len(keyframes) == 20:
                print("✓ SUCCESS: All 20 frames created")
                return True
            else:
                print(f"✗ FAILED: Expected 20 frames, got {len(keyframes)}")
                return False
        else:
            print("✗ FAILED: Could not retrieve keyframes list")
            return False
    except Exception as e:
        print(f"ERROR listing keyframes: {e}")
        return False


if __name__ == "__main__":
    success = test_create_20_frames()
    print()
    print("="*60)
    if success:
        print("FRAME SYSTEM TEST: PASSED ✓")
    else:
        print("FRAME SYSTEM TEST: FAILED ✗")
    print("="*60)
    sys.exit(0 if success else 1)
