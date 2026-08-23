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
    
    def has_drawing(self, sample_points: int = 25, min_non_blank_pixels: int = 100) -> Dict[str, Any]:
        """
        Detect if Krita canvas contains actual drawn content.
        
        Strategy:
        1. Sample pixels across the canvas
        2. Count non-blank (non-transparent, non-white) pixels
        3. Require minimum threshold of content pixels
        
        Args:
            sample_points: Number of points to sample across canvas
            min_non_blank_pixels: Minimum non-blank pixels required
            
        Returns:
            {
                "has_drawing": bool,
                "non_blank_pixels": int,
                "total_sampled": int,
                "reason": str
            }
        """
        try:
            # Get canvas dimensions
            result = self.mcp.call_tool("krita_health", {}, timeout=10)
            if not result or "error" in str(result):
                return {
                    "has_drawing": False,
                    "non_blank_pixels": 0,
                    "total_sampled": 0,
                    "reason": "No active Krita document"
                }
            
            # Sample pixels in a grid pattern across canvas
            # Assuming 800x600 default canvas
            canvas_width = 800
            canvas_height = 600
            
            # Sample in a 5x5 grid pattern
            rows = 5
            cols = 5
            step_x = canvas_width // (cols + 1)
            step_y = canvas_height // (rows + 1)
            
            non_blank_count = 0
            total_sampled = 0
            
            for row in range(1, rows + 1):
                for col in range(1, cols + 1):
                    x = col * step_x
                    y = row * step_y
                    
                    try:
                        color_result = self.mcp.call_tool("krita_get_color_at", {
                            "x": x,
                            "y": y
                        }, timeout=5)
                        
                        total_sampled += 1
                        
                        if isinstance(color_result, dict):
                            color = color_result.get("color", "#ffffff")
                            
                            # Check if pixel is non-blank
                            # Blank = white (#ffffff) or transparent
                            if color and color.lower() not in ("#ffffff", "#fff", "white"):
                                # Additional check: not fully transparent
                                # Color format may include alpha
                                if not color.lower().endswith("00"):  # Not transparent
                                    non_blank_count += 1
                    
                    except Exception as e:
                        # Individual pixel sample failure doesn't fail entire check
                        pass
            
            has_content = non_blank_count >= min_non_blank_pixels
            
            return {
                "has_drawing": has_content,
                "non_blank_pixels": non_blank_count,
                "total_sampled": total_sampled,
                "reason": f"Found {non_blank_count}/{total_sampled} non-blank pixels" if has_content else f"Only {non_blank_count}/{total_sampled} non-blank pixels (minimum: {min_non_blank_pixels})"
            }
            
        except Exception as e:
            return {
                "has_drawing": False,
                "non_blank_pixels": 0,
                "total_sampled": 0,
                "reason": f"Canvas detection failed: {str(e)}"
            }
    
    def has_paint_layer_with_content(self) -> Dict[str, Any]:
        """
        Verify active paint layer exists and appears to have content.
        
        This is a lighter check than full pixel sampling.
        
        Returns:
            {
                "has_layer": bool,
                "layer_name": str,
                "reason": str
            }
        """
        try:
            result = self.mcp.call_tool("krita_select_paint_layer", {}, timeout=10)
            
            if isinstance(result, dict):
                if "error" in result:
                    return {
                        "has_layer": False,
                        "layer_name": None,
                        "reason": result["error"]
                    }
                
                layer_name = result.get("layer_name", "unknown")
                return {
                    "has_layer": True,
                    "layer_name": layer_name,
                    "reason": f"Paint layer '{layer_name}' is active"
                }
            
            return {
                "has_layer": False,
                "layer_name": None,
                "reason": "Could not verify paint layer"
            }
            
        except Exception as e:
            return {
                "has_layer": False,
                "layer_name": None,
                "reason": f"Paint layer check failed: {str(e)}"
            }
    
    def verify_canvas_ready_for_animation(self, require_drawing: bool = True) -> Dict[str, Any]:
        """
        Complete canvas verification before animation.
        
        Checks:
        1. Paint layer exists
        2. Canvas has drawn content (if require_drawing=True)
        
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
        # Check paint layer
        layer_check = self.has_paint_layer_with_content()
        
        if not layer_check["has_layer"]:
            return {
                "ready": False,
                "has_layer": False,
                "has_drawing": False,
                "reason": f"No paint layer available: {layer_check['reason']}"
            }
        
        # Check for drawn content if required
        if require_drawing:
            drawing_check = self.has_drawing()
            
            if not drawing_check["has_drawing"]:
                return {
                    "ready": False,
                    "has_layer": True,
                    "has_drawing": False,
                    "reason": f"No character/drawing detected: {drawing_check['reason']}"
                }
            
            return {
                "ready": True,
                "has_layer": True,
                "has_drawing": True,
                "reason": f"Canvas ready: {drawing_check['non_blank_pixels']} non-blank pixels detected"
            }
        else:
            # Don't require drawing content
            return {
                "ready": True,
                "has_layer": True,
                "has_drawing": None,  # Not checked
                "reason": "Paint layer exists (drawing content not verified)"
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
