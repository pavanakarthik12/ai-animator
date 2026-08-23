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
    print(f"Performance profiling: ENABLED")
    
    # CRITICAL: Verify canvas has character before creating animation frames
    print("\n[CANVAS CHECK] Verifying character exists in Krita...")
    from canvas_detector import detect_canvas_state
    
    # If extracted_geometry is provided with content, character was just created
    character_just_created = (extracted_geometry and 
                               isinstance(extracted_geometry, dict) and 
                               extracted_geometry.get("total_elements", 0) > 0)
    
    if character_just_created:
        print("[CANVAS CHECK] Character was just created in previous operation")
        print("[CANVAS CHECK] Canvas ready for animation")
    else:
        # Check if character exists
        canvas_state = detect_canvas_state(mcp, require_drawing=True)
        
        if not canvas_state["ready"]:
            print("\n" + "="*60)
            print("ANIMATION BLOCKED - NO CHARACTER DETECTED")
            print("="*60)
            print(f"Reason: {canvas_state['reason']}")
            print("\nThe canvas must contain a drawn character before animation can begin.")
            print("Please draw the character first, then try animation again.")
            print("="*60)
            return
        
        print(f"[CANVAS CHECK] {canvas_state['reason']}")
        print("[CANVAS CHECK] Canvas ready for animation")
    
    # 1. Analyze character to get rest pose joints
    profiler.start("1_Groq_character_analysis")
    rest_joints_norm = analyze_character_rig(agent, ref_path)
    profiler.end()
    
    # 2. De-normalize joints to match canvas scaling
    profiler.start("2_Geometry_scaling")
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
    profiler.start("3_Groq_walk_planning")
    keyframes = plan_walk_cycle(agent, rest_joints_norm)
    profiler.end()
    
    # Instantiate rig early for procedural walk cycle generation
    profiler.start("4_Rig_initialization")
    rig = CharacterRig(rest_joints)
    profiler.end()
    
    # 4. Interpolate frames using IK / procedural generator
    profiler.start("5_Pose_interpolation")
    frames_angles = PoseInterpolator.interpolate(keyframes, frame_count, rig)
    profiler.end()
    print(f"\n[ANIM] Generated {len(frames_angles)} frames of procedural animation.")
    
    # 5. Extract rest pose strokes (already normalized in extracted_geometry)
    profiler.start("6_Batch_preparation")
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
    profiler.start("7_LBS_binding")
    skinning = LinearBlendSkinning(rig, all_strokes)
    profiler.end()
    print("[ANIM] LBS Binding complete.")
    
    # 7. Execute frames in Krita
    batch_manager = SmartBatchManager(mcp)
    
    # Select paint layer
    profiler.start("8_MCP_setup")
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
    
    # Per-frame timing accumulators
    total_frame_creation_time = 0.0
    total_deformation_time = 0.0
    total_batch_grouping_time = 0.0
    total_mcp_drawing_time = 0.0
        
    total_frames = len(frames_angles)
    for frame_idx, angles in enumerate(frames_angles):
        krita_frame = frame_idx + 1
        print(f"\n[FRAME {krita_frame}/{total_frames}]")
        print(f"Creating/selecting frame {krita_frame}")
        
        # Create keyframe and select frame with validation
        frame_creation_start = time.time()
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
        
        frame_creation_end = time.time()
        total_frame_creation_time += (frame_creation_end - frame_creation_start)
                
        if not frame_ready:
            print(f"Fatal: requested frame != actual Krita frame. DO NOT DRAW.")
            break
            
        print(f"Drawing frame {krita_frame}")
        
        # Deform geometry
        deformation_start = time.time()
        rig.set_pose(angles)
        deformed_strokes = skinning.deform()
        deformation_end = time.time()
        total_deformation_time += (deformation_end - deformation_start)
        
        # Group back into batches
        batch_grouping_start = time.time()
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
        batch_grouping_end = time.time()
        total_batch_grouping_time += (batch_grouping_end - batch_grouping_start)
            
        # Draw!
        mcp_drawing_start = time.time()
        batch_manager.execute_plan(frame_batches)
        mcp_drawing_end = time.time()
        total_mcp_drawing_time += (mcp_drawing_end - mcp_drawing_start)
        print(f"Frame {krita_frame} drawing complete")
    
    # Record per-frame totals
    profiler.timings["9_Frame_creation_per_frame"] = total_frame_creation_time
    profiler.timings["10_Geometry_deformation_per_frame"] = total_deformation_time
    profiler.timings["11_Batch_grouping_per_frame"] = total_batch_grouping_time
    profiler.timings["12_MCP_drawing_per_frame"] = total_mcp_drawing_time
    
    pipeline_total = time.time() - pipeline_start
    
    print("\n" + "="*60)
    print("WALK CYCLE ANIMATION COMPLETE")
    print("="*60)
    print(f"Total pipeline time: {pipeline_total:.2f}s")
    
    profiler.print_report()
