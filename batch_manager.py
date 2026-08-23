import time
import json
import traceback
from typing import List, Dict, Any
from config import config

def _extract_points(stroke):
    """Coerce a batch stroke argument into a list of [x, y] integer pairs."""
    if isinstance(stroke, dict):
        points = stroke.get("points")
    else:
        points = stroke
    if not isinstance(points, list) or not points:
        return []
    if all(isinstance(p, (list, tuple)) for p in points):
        out = []
        for p in points:
            if len(p) >= 2:
                try:
                    out.append([int(p[0]), int(p[1])])
                except Exception:
                    pass
        return out
    flat = []
    for v in points:
        try:
            flat.append(int(v))
        except Exception:
            pass
    return [[flat[i], flat[i + 1]] for i in range(0, len(flat) - 1, 2)]

class SmartBatchManager:
    def __init__(self, mcp_client):
        self.mcp = mcp_client
        self.max_strokes = config.max_strokes_per_batch
        self.max_points = config.max_points_per_batch
        self.max_payload = config.max_payload_bytes
        self.retry_count = config.batch_retry_count
        self._bulk_api_available = None  # Cache bulk API availability
        
        self.metrics = {
            "total_strokes": 0,
            "total_points": 0,
            "total_batches_planned": 0,
            "successful_batches": 0,
            "failed_batches": 0,
            "retry_count": 0,
            "mcp_requests": 0,
            "execution_time": 0.0,
            "bulk_mode": False
        }

    def _count_points(self, stroke: Any) -> int:
        points = _extract_points(stroke)
        return len(points)
    
    def _has_bulk_api(self) -> bool:
        """Check if krita_bulk_strokes MCP tool is available."""
        if self._bulk_api_available is not None:
            return self._bulk_api_available
        
        try:
            tools = self.mcp.list_tools()
            self._bulk_api_available = "krita_bulk_strokes" in tools
        except Exception:
            self._bulk_api_available = False
        
        return self._bulk_api_available

    def plan_batches(self, original_batches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Takes the complete drawing plan and safely splits it into smaller execution batches
        based on configuration constraints (max strokes, max points).
        """
        planned_batches = []
        batch_id_counter = 1
        
        for ob in original_batches:
            color = ob.get("color")
            brush_size = ob.get("brush_size")
            strokes = ob.get("strokes", [])
            
            if not strokes:
                continue
                
            current_chunk_strokes = []
            current_points = 0
            
            for stroke in strokes:
                stroke_points_count = self._count_points(stroke)
                
                if current_chunk_strokes and (
                    len(current_chunk_strokes) >= self.max_strokes or 
                    current_points + stroke_points_count > self.max_points
                ):
                    planned_batches.append({
                        "batch_id": f"batch_{batch_id_counter}",
                        "color": color,
                        "brush_size": brush_size,
                        "strokes": current_chunk_strokes,
                        "status": "PENDING"
                    })
                    batch_id_counter += 1
                    current_chunk_strokes = []
                    current_points = 0
                
                current_chunk_strokes.append(stroke)
                current_points += stroke_points_count
                self.metrics["total_strokes"] += 1
                self.metrics["total_points"] += stroke_points_count
            
            if current_chunk_strokes:
                planned_batches.append({
                    "batch_id": f"batch_{batch_id_counter}",
                    "color": color,
                    "brush_size": brush_size,
                    "strokes": current_chunk_strokes,
                    "status": "PENDING"
                })
                batch_id_counter += 1

        self.metrics["total_batches_planned"] = len(planned_batches)
        return planned_batches

    def execute_plan(self, original_batches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Plans and executes the batches, tracking idempotency and handling retries/failures.
        
        Uses bulk API if available (significantly faster), falls back to legacy mode if not.
        """
        start_time = time.time()
        
        # Check if bulk API is available
        if self._has_bulk_api():
            print(f"\n[SmartBatchManager] Using BULK API mode (krita_bulk_strokes)")
            result = self._execute_bulk(original_batches)
        else:
            print(f"\n[SmartBatchManager] Using LEGACY mode (individual krita_stroke calls)")
            result = self._execute_legacy(original_batches)
        
        self.metrics["execution_time"] = time.time() - start_time
        return result
    
    def _execute_bulk(self, original_batches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute using bulk API - send all strokes in one MCP call.
        
        This reduces 1000 strokes from 1000 MCP calls to 1 MCP call.
        """
        self.metrics["bulk_mode"] = True
        
        # Collect all strokes with their properties
        all_strokes = []
        for batch in original_batches:
            color = batch.get("color")
            brush_size = batch.get("brush_size")
            
            for stroke in batch.get("strokes", []):
                points = _extract_points(stroke)
                if len(points) < 2:
                    continue
                
                stroke_data = {
                    "points": points,
                    "pressure": 1.0
                }
                
                # Include color and brush size in each stroke
                if color:
                    stroke_data["color"] = color
                if brush_size is not None:
                    stroke_data["brush_size"] = int(brush_size)
                
                all_strokes.append(stroke_data)
                self.metrics["total_strokes"] += 1
                self.metrics["total_points"] += len(points)
        
        if not all_strokes:
            return self.metrics
        
        print(f"[SmartBatchManager] Sending {len(all_strokes)} strokes in ONE bulk call")
        print(f"[DEBUG-1] Python bulk request created: {len(all_strokes)} strokes")
        print(f"[DEBUG-1] First stroke sample: points={len(all_strokes[0]['points'])}, color={all_strokes[0].get('color')}, brush={all_strokes[0].get('brush_size')}")
        
        try:
            # Single MCP call for all strokes
            print(f"[DEBUG-2] Calling mcp.call_tool('krita_bulk_strokes', ...)")
            result = self.mcp.call_tool("krita_bulk_strokes", {
                "strokes": all_strokes
            }, timeout=max(120, len(all_strokes) * 0.5))
            
            print(f"[DEBUG-9] Response received from MCP: {result}")
            
            self.metrics["mcp_requests"] += 1
            
            # CRITICAL: Check for error FIRST before trying to parse success
            if isinstance(result, dict) and "error" in result:
                error_msg = result["error"]
                print(f"[DEBUG-ERROR] Bulk API returned error: {error_msg}")
                
                # Check if bulk API is unavailable (not registered)
                if "Unknown action" in error_msg or "bulk_strokes" in error_msg.lower():
                    print(f"\n✗ Bulk API unavailable: {error_msg}")
                    print(f"[SmartBatchManager] FALLBACK: Switching to legacy mode")
                    print(f"[SmartBatchManager] This will be slower but functional")
                    
                    # Mark bulk API as unavailable for future calls
                    self._bulk_api_available = False
                    
                    # FALLBACK to legacy mode
                    return self._execute_legacy(original_batches)
                else:
                    # Other error - report failure
                    print(f"✗ Bulk operation FAILED: {error_msg}")
                    self.metrics["failed_batches"] += 1
                    print(f"\nDRAWING FAILED")
                    print(f"Requested: {len(all_strokes)} strokes")
                    print(f"Drawn: 0 strokes")
                    print(f"Failed: {len(all_strokes)} strokes")
                    print(f"Error: {error_msg}")
                    self._print_metrics()
                    return self.metrics
            
            # Parse success result
            if isinstance(result, dict):
                strokes_drawn = result.get("strokes_drawn", 0)
                strokes_failed = result.get("strokes_failed", 0)
                total_requested = len(all_strokes)
                
                print(f"[DEBUG-10] Parsed result: drawn={strokes_drawn}, failed={strokes_failed}")
                
                if strokes_drawn > 0:
                    self.metrics["successful_batches"] += 1
                    print(f"✓ Bulk operation completed: {strokes_drawn}/{total_requested} strokes drawn")
                
                if strokes_failed > 0:
                    self.metrics["failed_batches"] += 1
                    errors = result.get("errors", [])
                    print(f"✗ Bulk operation partial failure: {strokes_failed} strokes failed")
                    if errors:
                        for error in errors[:5]:  # Show first 5 errors
                            print(f"  - {error}")
                
                # Verify we drew what we requested
                if strokes_drawn != total_requested:
                    print(f"\n⚠ WARNING: Incomplete drawing")
                    print(f"Requested: {total_requested}")
                    print(f"Drawn: {strokes_drawn}")
                    print(f"Missing: {total_requested - strokes_drawn}")
            else:
                # Unexpected result type
                print(f"✗ Unexpected result type: {type(result)}")
                print(f"Result: {result}")
                self.metrics["failed_batches"] += 1
            
        except Exception as e:
            print(f"✗ Bulk operation EXCEPTION: {e}")
            print(f"[DEBUG-ERROR] Exception details: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            self.metrics["failed_batches"] += 1
            print(f"\nDRAWING FAILED")
            print(f"Requested: {len(all_strokes)} strokes")
            print(f"Drawn: 0 strokes")
            print(f"Failed: {len(all_strokes)} strokes")
        
        self._print_metrics()
        return self.metrics
    
    def _execute_legacy(self, original_batches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute using legacy mode - one MCP call per stroke.
        
        This is the original implementation, kept as fallback.
        """
        self.metrics["bulk_mode"] = False
        planned_batches = self.plan_batches(original_batches)
        
        print(f"\n[SmartBatchManager] Planned {len(planned_batches)} optimal batches from complete plan.")
        print(f"[SmartBatchManager] Total strokes: {self.metrics['total_strokes']}, Total points: {self.metrics['total_points']}")
        
        last_color = None
        last_brush = None
        
        for i, batch in enumerate(planned_batches):
            print(f"\nExecuting Batch {i+1}/{len(planned_batches)} (ID: {batch['batch_id']})")
            print(f"  Color: {batch.get('color')}, Brush: {batch.get('brush_size')}, Strokes: {len(batch.get('strokes', []))}")
            
            retries = 0
            success = False
            
            while retries <= self.retry_count and not success:
                try:
                    if retries > 0:
                        print(f"  Retry {retries}/{self.retry_count} for batch {batch['batch_id']}...")
                        self.metrics["retry_count"] += 1
                        
                    batch["status"] = "RUNNING"
                    
                    color = batch.get("color")
                    if color and color != last_color:
                        r = self.mcp.call_tool("krita_set_color", {"color": color}, timeout=10)
                        self.metrics["mcp_requests"] += 1
                        last_color = color
                        
                    brush_size = batch.get("brush_size")
                    if brush_size is not None and brush_size != last_brush:
                        r = self.mcp.call_tool("krita_set_brush", {"size": int(brush_size)}, timeout=10)
                        self.metrics["mcp_requests"] += 1
                        last_brush = brush_size
                        
                    strokes = batch.get("strokes", [])
                    strokes_drawn = 0
                    
                    for stroke_item in strokes:
                        if isinstance(stroke_item, dict):
                            points = stroke_item.get("points", [])
                            sid = stroke_item.get("stroke_id", "unknown")
                        else:
                            points = stroke_item
                            sid = "unknown"
                            
                        if len(points) < 2:
                            continue
                            
                        print(f"MCP draw:")
                        print(f"stroke_id={sid}")
                        print(f"width={brush_size}")
                        print(f"points={len(points)}")
                        
                        res = self.mcp.call_tool("krita_stroke", {"points": points, "pressure": 1.0}, timeout=30)
                        self.metrics["mcp_requests"] += 1
                        
                        if "error" in str(res).lower():
                            raise Exception(f"MCP Error: {res}")
                        strokes_drawn += 1
                            
                    success = True
                    batch["status"] = "SUCCESS"
                    self.metrics["successful_batches"] += 1
                    print(f"  ✓ Batch {batch['batch_id']} completed successfully ({strokes_drawn} merged strokes drawn).")
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    print(f"  ✗ Error in batch {batch['batch_id']}: {e}")
                    
                    # Do not retry permanent errors
                    if "unknown action" in error_msg or "invalid" in error_msg:
                        print(f"  ! Permanent error detected. Skipping retries.")
                        break
                        
                    retries += 1
                    
            if not success:
                batch["status"] = "FAILED"
                self.metrics["failed_batches"] += 1
                print(f"  ! Batch {batch['batch_id']} failed permanently after {self.retry_count} retries.")
                # We do NOT exit. We continue to next batch (Partial Failure Handling)

        self._print_metrics()
        return self.metrics
    
    def _print_metrics(self):
        """Print drawing metrics summary."""
        print("\n" + "="*60)
        print("DRAWING METRICS")
        print("="*60)
        print(f"Mode:               {'BULK API' if self.metrics['bulk_mode'] else 'LEGACY'}")
        print(f"Total strokes:      {self.metrics['total_strokes']}")
        print(f"Total points:       {self.metrics['total_points']}")
        if not self.metrics['bulk_mode']:
            print(f"Batches planned:    {self.metrics['total_batches_planned']}")
            print(f"Successful batches: {self.metrics['successful_batches']}")
            print(f"Failed batches:     {self.metrics['failed_batches']}")
            print(f"Retries used:       {self.metrics['retry_count']}")
        print(f"MCP requests:       {self.metrics['mcp_requests']}")
        print(f"Execution time:     {self.metrics['execution_time']:.2f}s")
        print("="*60 + "\n")
