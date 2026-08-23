"""
Quick Character Detection Test

Fast verification that detection is working.
"""

from mcp_client import KritaMCPClient
from canvas_detector import detect_canvas_state


def main():
    print("="*60)
    print("QUICK CHARACTER DETECTION TEST")
    print("="*60)
    
    print("\nConnecting to Krita...")
    mcp = KritaMCPClient()
    
    print("\nRunning detection...")
    canvas_state = detect_canvas_state(mcp, require_drawing=True)
    
    print("\n" + "="*60)
    print("DETECTION RESULT")
    print("="*60)
    print(f"\nReady for animation: {canvas_state['ready']}")
    print(f"Has layer: {canvas_state['has_layer']}")
    print(f"Has drawing: {canvas_state['has_drawing']}")
    print(f"\nReason: {canvas_state['reason']}")
    
    print("\n" + "="*60)
    if canvas_state['ready']:
        print("✓ CHARACTER DETECTED")
        print("="*60)
        print("\nAnimation would be ALLOWED to proceed.")
        print("The canvas has a drawable character.")
    else:
        print("✗ NO CHARACTER DETECTED")
        print("="*60)
        print("\nAnimation would be BLOCKED.")
        print("The canvas does not have sufficient drawable content.")
    
    print("\n" + "="*60)
    print("WHAT TO VERIFY:")
    print("="*60)
    print("\nIf canvas is EMPTY:")
    print("  → Detection should show 'NO CHARACTER DETECTED'")
    print("  → Non-blank pixels should be 0-4 out of 25")
    print("\nIf canvas HAS CHARACTER:")
    print("  → Detection should show 'CHARACTER DETECTED'")
    print("  → Non-blank pixels should be 5+ out of 25")
    print("\n" + "="*60)


if __name__ == "__main__":
    main()
