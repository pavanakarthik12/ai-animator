"""
Diagnostic Script - Inspect Actual Krita State

This script shows EXACTLY what Krita contains right now.
Does NOT modify anything.
"""

from mcp_client import KritaMCPClient
from canvas_detector import CanvasDetector


def main():
    print("="*60)
    print("KRITA STATE DIAGNOSTIC")
    print("="*60)
    print("\nThis script inspects the ACTUAL Krita state.")
    print("It does NOT modify the canvas.")
    print("\nMake sure:")
    print("1. Krita is running")
    print("2. A document is open")
    print("3. The character you want to animate is visible")
    
    input("\nPress Enter to inspect Krita state...")
    
    mcp = KritaMCPClient()
    detector = CanvasDetector(mcp)
    
    # Run diagnostic
    state = detector.inspect_character_state()
    
    # Print summary
    print("\n" + "="*60)
    print("DIAGNOSTIC SUMMARY")
    print("="*60)
    
    print(f"\nDocument found: {state['document_found']}")
    if state['document_found']:
        print(f"  Name: {state['document_name']}")
        print(f"  Size: {state['document_width']}x{state['document_height']}")
    
    print(f"\nActive layer: {state['active_layer']}")
    if state['active_layer']:
        print(f"  Type: {state['active_layer_type']}")
    
    print(f"\nCurrent frame: {state['current_frame']}")
    
    print(f"\nNon-empty layers: {len(state['non_empty_layers'])}")
    for layer in state['non_empty_layers']:
        bbox = state['bounding_boxes'].get(layer, {})
        print(f"  {layer}:")
        print(f"    Non-blank pixels: {bbox.get('non_blank_pixels', 0)}")
        print(f"    Total sampled: {bbox.get('total_sampled', 0)}")
        print(f"    Percentage: {bbox.get('percentage', 0):.1f}%")
    
    print(f"\n" + "="*60)
    print(f"CHARACTER DETECTED: {state['character_detected']}")
    print("="*60)
    
    if not state['character_detected']:
        print(f"\nFailure reason: {state['failure_reason']}")
        print("\n" + "="*60)
        print("TROUBLESHOOTING")
        print("="*60)
        print("\nPossible issues:")
        print("1. Canvas is actually empty - draw something visible")
        print("2. Drawing is on wrong layer - check active paint layer")
        print("3. Drawing is pure white - use a different color")
        print("4. Drawing is on different frame - check current frame")
        print("5. Document not saved/committed - try Ctrl+S")
    else:
        print("\n✓ Character is detected and ready for animation")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main()
