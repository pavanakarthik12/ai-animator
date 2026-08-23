"""
Debug MCP Server - Find out what's actually happening

This script will:
1. Show the server path being used
2. List all available MCP tools
3. Try calling krita_bulk_strokes
4. Show the exact error
"""

import sys
import os
from pathlib import Path

print("="*60)
print("DEBUG MCP SERVER")
print("="*60)

# Load environment
from dotenv import load_dotenv
load_dotenv()

server_path = os.getenv("KRITA_MCP_SERVER")
krita_url = os.getenv("KRITA_URL")

print(f"\n1. ENVIRONMENT:")
print(f"   KRITA_MCP_SERVER: {server_path}")
print(f"   KRITA_URL: {krita_url}")
print(f"   Server exists: {Path(server_path).exists() if server_path else 'N/A'}")

# Start MCP client
print(f"\n2. STARTING MCP CLIENT:")
print(f"   Launching: {server_path}")

try:
    from mcp_client import KritaMCPClient
    
    mcp = KritaMCPClient(server_path)
    mcp.start(wait=10.0)
    print(f"   ✓ MCP client started")
    
except Exception as e:
    print(f"   ✗ Failed to start MCP client: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# List tools
print(f"\n3. AVAILABLE TOOLS:")
try:
    tools = mcp.list_tools()
    print(f"   Total tools: {len(tools)}")
    
    # Check for bulk_strokes related tools
    bulk_tools = [t for t in tools if 'bulk' in t.lower()]
    stroke_tools = [t for t in tools if 'stroke' in t.lower()]
    
    print(f"\n   Tools with 'bulk' in name:")
    if bulk_tools:
        for t in bulk_tools:
            print(f"     - {t}")
    else:
        print(f"     (none found)")
    
    print(f"\n   Tools with 'stroke' in name:")
    if stroke_tools:
        for t in stroke_tools:
            print(f"     - {t}")
    else:
        print(f"     (none found)")
    
    print(f"\n   All tools:")
    for i, tool in enumerate(sorted(tools), 1):
        print(f"     {i:2d}. {tool}")
    
except Exception as e:
    print(f"   ✗ Failed to list tools: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Check if krita_bulk_strokes exists
print(f"\n4. BULK API CHECK:")
if 'krita_bulk_strokes' in tools:
    print(f"   ✓ krita_bulk_strokes IS registered")
else:
    print(f"   ✗ krita_bulk_strokes NOT registered")
    print(f"   This explains the 'Unknown action' error!")

# Test krita_health
print(f"\n5. TESTING KRITA CONNECTION:")
try:
    result = mcp.call_tool("krita_health", {}, timeout=5)
    print(f"   Result: {result}")
except Exception as e:
    print(f"   ✗ Failed: {e}")

# Try bulk API if it exists
if 'krita_bulk_strokes' in tools:
    print(f"\n6. TESTING BULK API (1 stroke):")
    test_stroke = {
        "points": [[100, 100], [200, 100]],
        "color": "#FF0000",
        "brush_size": 10
    }
    
    try:
        print(f"   Calling krita_bulk_strokes with 1 stroke...")
        result = mcp.call_tool("krita_bulk_strokes", {
            "strokes": [test_stroke]
        }, timeout=30)
        
        print(f"   Result: {result}")
        
        if isinstance(result, dict):
            if "error" in result:
                print(f"   ✗ ERROR: {result['error']}")
            else:
                drawn = result.get("strokes_drawn", 0)
                failed = result.get("strokes_failed", 0)
                print(f"   Drawn: {drawn}, Failed: {failed}")
                
                if drawn == 1:
                    print(f"   ✓ BULK API WORKING!")
                else:
                    print(f"   ✗ Bulk API failed to draw")
    
    except Exception as e:
        print(f"   ✗ Exception: {e}")
        import traceback
        traceback.print_exc()
else:
    print(f"\n6. SKIPPING BULK API TEST (not registered)")

# Final diagnosis
print(f"\n" + "="*60)
print("DIAGNOSIS")
print("="*60)

if 'krita_bulk_strokes' not in tools:
    print("""
✗ PROBLEM FOUND: krita_bulk_strokes is NOT registered in the MCP server

This means:
  1. The @mcp.tool() decorator for krita_bulk_strokes is missing
  2. OR the function is defined but not decorated
  3. OR the server.py file being used is different from the one we edited

NEXT STEPS:
  1. Check C:\\Users\\pavan\\OneDrive\\Desktop\\krita-mcp\\server.py
  2. Verify the krita_bulk_strokes function has @mcp.tool() decorator
  3. The MCP client will need to restart to pick up changes
""")
else:
    if result and isinstance(result, dict) and "error" in result:
        print(f"""
✗ PROBLEM: krita_bulk_strokes IS registered but returned error:
  {result['error']}

This could mean:
  1. Krita plugin hasn't been restarted
  2. Krita plugin dispatch is broken
  3. Communication issue

NEXT STEPS:
  1. Restart Krita to reload the plugin
  2. Verify dispatch in Krita plugin __init__.py
""")
    else:
        print("""
✓ BULK API IS WORKING!

The tool is registered and responding correctly.
""")

print("="*60)
