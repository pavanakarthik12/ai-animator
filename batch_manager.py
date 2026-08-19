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
        
        self.metrics = {
            "total_strokes": 0,
            "total_points": 0,
            "total_batches_planned": 0,
            "successful_batches": 0,
            "failed_batches": 0,
            "retry_count": 0,
            "mcp_requests": 0,
            "execution_time": 0.0
        }

    def _count_points(self, stroke: Any) -> int:
        points = _extract_points(stroke)
        return len(points)

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
        """
        start_time = time.time()
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

        self.metrics["execution_time"] = time.time() - start_time
        
        print("\n" + "="*60)
        print("DRAWING METRICS")
        print("="*60)
        print(f"Total strokes:      {self.metrics['total_strokes']}")
        print(f"Total points:       {self.metrics['total_points']}")
        print(f"Batches planned:    {self.metrics['total_batches_planned']}")
        print(f"Successful batches: {self.metrics['successful_batches']}")
        print(f"Failed batches:     {self.metrics['failed_batches']}")
        print(f"Retries used:       {self.metrics['retry_count']}")
        print(f"MCP requests:       {self.metrics['mcp_requests']}")
        print(f"Execution time:     {self.metrics['execution_time']:.2f}s")
        print("="*60 + "\n")
        
        return self.metrics
