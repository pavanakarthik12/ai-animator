import time
from typing import Dict, Any
from animation_planner import CharacterRig, LinearBlendSkinning, PoseInterpolator
from groq_animation import analyze_character_rig, plan_walk_cycle
from batch_manager import SmartBatchManager


class PerformanceProfiler:
    """Track timing for each stage of the animation pipeline."""
    def __init__(self):
        self.timings = {}
        self.current_stage = None
        self.stage_start = None
    
    def start(self, stage_name):
        if self.current_stage:
            self.end()
        self.current_stage = stage_name
        self.stage_start = time.time()
    
    def end(self):
        if self.current_stage and self.stage_start:
            elapsed = time.time() - self.stage_start
            if self.current_stage in self.timings:
                self.timings[self.current_stage] += elapsed
            else:
                self.timings[self.current_stage] = elapsed
            self.current_stage = None
            self.stage_start = None
    
    def print_report(self):
        self.end()  # End any active stage
        print("\n" + "="*60)
        print("[PERF] PERFORMANCE BREAKDOWN")
        print("="*60)
        total = sum(self.timings.values())
        for stage, duration in sorted(self.timings.items(), key=lambda x: -x[1]):
            pct = (duration / total * 100) if total > 0 else 0
            print(f"{stage:25s}: {duration:6.2f}s ({pct:5.1f}%)")
        print("-"*60)
        print(f"{'TOTAL':25s}: {total:6.2f}s")
        print("="*60)


def run_walk_cycle_animation(agent, mcp, extracted_geometry: Dict[str, Any], ref_path: str, frame_count: int = 240, target_width=800, target_height=600, fit_mode="contain"):
    profiler = PerformanceProfiler()
    pipeline_start = time.time()
    
    print("\n" + "="*60)
    print("WALK CYCLE ANIMATION PIPELINE STARTED")
    print("="*60)
    print(f"Requested frame count: {frame_count}")
    
    # 1. Analyze character to get rest pose joints
    profiler.start("Groq character analysis")
    rest_joints_norm = analyze_character_rig(agent, ref_path)
    profiler.end()
    
    # 2. De-normalize joints to match canvas scaling
    profiler.start("Geometry scaling")
    ref_w = extracted_geometry.get("width", target_width)
    ref_h = extracted_geometry.get("height", target_height)
    
    scale_x = target_width / ref_w
    scale_y = target_height / ref_h
    scale = min(scale_x, scale_y) if fit_mode == "contain" else max(scale_x, scale_y)
    offset_x = (target_width - ref_w * scale) / 2
    offset_y = (target_height - ref_h * scale) / 2
    
    rest_joints = {}
    for j, (nx, ny) in rest_joints_norm.items():
        x = nx * ref_w * scale + offset_x
        y = ny * ref_h * scale + offset_y
        rest_joints[j] = (x, y)
    profiler.end()
        
    print(f"\n[ANIM] Extracted {len(rest_joints)} joints for rest pose.")
    
    # 3. Plan Walk Cycle Keyframes
    profiler.start("Groq walk planning")
    keyframes = plan_walk_cycle(agent, rest_joints_norm)
    profiler.end()
    
    # Instantiate rig early for procedural walk cycle generation
    profiler.start("Rig initialization")
    rig = CharacterRig(rest_joints)
    profiler.end()
    
    # 4. Interpolate frames using IK / procedural generator
    profiler.start("Pose interpolation")
    frames_angles = PoseInterpolator.interpolate(keyframes, frame_count, rig)
    profiler.end()
    print(f"\n[ANIM] Generated {len(frames_angles)} frames of procedural animation.")
    
    # 5. Extract rest pose strokes (already normalized in extracted_geometry)
    profiler.start("Batch preparation")
    from main import _create_batches_from_extracted_geometry
    batches = _create_batches_from_extracted_geometry(extracted_geometry, target_width, target_height, fit_mode)
    
    all_strokes = []
    for b in batches:
        for s in b.get("strokes", []):
            stroke_obj = {
                "points": s["points"],
                "color": b["color"],
                "brush_size": b["brush_size"],
                "stroke_id": s.get("stroke_id", "unknown"),
                "closed": s.get("closed", False)
            }
            all_strokes.append(stroke_obj)
    profiler.end()
            
    print(f"\n[ANIM] Found {len(all_strokes)} strokes to bind to rig.")
    
    # 6. Bind strokes to rig
    profiler.start("LBS binding")
    skinning = LinearBlendSkinning(rig, all_strokes)
    profiler.end()
    print("[ANIM] LBS Binding complete.")
    
    # 7. Execute frames in Krita
    batch_manager = SmartBatchManager(mcp)
    
    # Select paint layer
    profiler.start("MCP setup")
    try:
        mcp.call_tool("krita_select_paint_layer", {}, timeout=10)
    except Exception as e:
        print(f"Warning: select paint layer failed: {e}")
    
    # Enable onion skin
    try:
        mcp.call_tool("krita_enable_onion", {"enabled": True}, timeout=10)
    except Exception as e:
        print(f"Warning: enable onion skin failed: {e}")
    profiler.end()
        
    total_frames = len(frames_angles)
    for frame_idx, angles in enumerate(frames_angles):
        krita_frame = frame_idx + 1
        print(f"\n[FRAME {krita_frame}/{total_frames}]")
        print(f"Creating/selecting frame {krita_frame}")
        
        # Create keyframe and select frame with validation
        profiler.start("Frame creation")
        max_retries = 3
        frame_ready = False
        
        for attempt in range(max_retries):
            # 1. Create keyframe at N
            try:
                mcp.call_tool("krita_create_keyframe", {"frame": krita_frame}, timeout=10)
            except Exception as e:
                print(f"Warning: create keyframe failed on attempt {attempt+1}: {e}")
                
            # 2. Set current frame to N
            try:
                mcp.call_tool("krita_set_current_frame", {"frame": krita_frame}, timeout=10)
            except Exception as e:
                print(f"Warning: set current frame failed on attempt {attempt+1}: {e}")
                
            # 3. Verify current frame
            try:
                current_frame_result = mcp.call_tool("krita_get_current_frame", {}, timeout=10)
                actual_frame = current_frame_result.get("current_frame", -1) if isinstance(current_frame_result, dict) else -1
                
                print(f"Krita current frame = {actual_frame}")
                
                if actual_frame == krita_frame:
                    frame_ready = True
                    break
                else:
                    print(f"Frame validation failed. Retrying...")
                    time.sleep(1)
            except Exception as e:
                print(f"Warning: get current frame failed: {e}")
                time.sleep(1)
        profiler.end()
                
        if not frame_ready:
            print(f"Fatal: requested frame != actual Krita frame. DO NOT DRAW.")
            break
            
        print(f"Drawing frame {krita_frame}")
        
        # Deform geometry
        profiler.start("Geometry deformation")
        rig.set_pose(angles)
        deformed_strokes = skinning.deform()
        profiler.end()
        
        # Group back into batches
        profiler.start("Batch grouping")
        from collections import defaultdict
        grouped = defaultdict(list)
        for s in deformed_strokes:
            key = (s["color"], s["brush_size"])
            grouped[key].append({
                "stroke_id": s["stroke_id"],
                "points": s["points"],
                "closed": s["closed"]
            })
            
        frame_batches = []
        for (color, brush), strokes in grouped.items():
            frame_batches.append({
                "color": color,
                "brush_size": brush,
                "strokes": strokes,
                "complete": False
            })
        if frame_batches:
            frame_batches[-1]["complete"] = True
        profiler.end()
            
        # Draw!
        profiler.start("MCP drawing")
        batch_manager.execute_plan(frame_batches)
        profiler.end()
        print(f"Frame {krita_frame} drawing complete")
    
    pipeline_total = time.time() - pipeline_start
    
    print("\n" + "="*60)
    print("WALK CYCLE ANIMATION COMPLETE")
    print("="*60)
    print(f"Total pipeline time: {pipeline_total:.2f}s")
    
    profiler.print_report()
