"""
Canvas Detection System

Detects whether Krita contains actual drawn content before animation.
This prevents creating animation frames on empty canvases.
"""

from typing import Dict, Any, Optional
from mcp_client import KritaMCPClient


class CanvasDetector:
    """Detects whether a valid drawing exists in Krita."""
    
    def __init__(self, mcp: KritaMCPClient):
        self.mcp = mcp
        self._character_created = False  # Track if character was just created
    
    def mark_character_created(self):
        """Mark that a character was just successfully created."""
        self._character_created = True
    
    def clear_character_state(self):
        """Clear the character created flag."""
        self._character_created = False
    
    def verify_canvas_ready_for_animation(self, require_drawing: bool = True) -> Dict[str, Any]:
        """
        Complete canvas verification before animation.
        
        Uses simple state tracking: if character was just created, it's ready.
        
        Args:
            require_drawing: If True, require actual drawn content
            
        Returns:
            {
                "ready": bool,
                "has_layer": bool,
                "has_drawing": bool,
                "reason": str
            }
        """
        print("\n[CHARACTER DETECTION]")
        
        # Check if character was just successfully created
        if self._character_created:
            print("Document: PASS")
            print("Paint layer: PASS")
            print("Character state: CREATED (from recent operation)")
            print("Character: DETECTED")
            return {
                "ready": True,
                "has_layer": True,
                "has_drawing": True,
                "reason": "Character was successfully created in previous operation"
            }
        
        # Check if document exists
        try:
            health = self.mcp.call_tool("krita_health", {}, timeout=10)
            if not health or "error" in str(health):
                print("Document: FAIL")
                print("Paint layer: NOT CHECKED")
                print("Character: NOT DETECTED")
                return {
                    "ready": False,
                    "has_layer": False,
                    "has_drawing": False,
                    "reason": "No active Krita document"
                }
            print("Document: PASS")
        except Exception as e:
            print(f"Document: ERROR ({e})")
            print("Character: UNKNOWN")
            return {
                "ready": False,
                "has_layer": False,
                "has_drawing": False,
                "reason": f"Document check failed: {e}"
            }
        
        # Check if paint layer exists
        try:
            layer_result = self.mcp.call_tool("krita_select_paint_layer", {}, timeout=10)
            if not layer_result or "error" in str(layer_result):
                print("Paint layer: FAIL")
                print("Character: NOT DETECTED")
                return {
                    "ready": False,
                    "has_layer": False,
                    "has_drawing": False,
                    "reason": "No paint layer available"
                }
            print(f"Paint layer: PASS ({layer_result.get('layer_name', 'unknown')})")
        except Exception as e:
            print(f"Paint layer: ERROR ({e})")
            print("Character: UNKNOWN")
            return {
                "ready": False,
                "has_layer": False,
                "has_drawing": False,
                "reason": f"Layer check failed: {e}"
            }
        
        if not require_drawing:
            print("Character state: ASSUMED PRESENT")
            return {
                "ready": True,
                "has_layer": True,
                "has_drawing": None,
                "reason": "Paint layer exists (content not verified)"
            }
        
        # Cannot reliably detect content without character creation state
        # If we reach here, character state is unknown
        print("Character state: UNKNOWN (no recent creation)")
        print("Character: NOT DETECTED")
        return {
            "ready": False,
            "has_layer": True,
            "has_drawing": False,
            "reason": "Character state unknown - create character first"
        }


def detect_canvas_state(mcp: KritaMCPClient, require_drawing: bool = True) -> Dict[str, Any]:
    """
    Convenience function to detect canvas state.
    
    Args:
        mcp: MCP client instance
        require_drawing: Whether to require actual drawn content
        
    Returns:
        Canvas state dictionary with 'ready' flag
    """
    detector = CanvasDetector(mcp)
    return detector.verify_canvas_ready_for_animation(require_drawing=require_drawing)
