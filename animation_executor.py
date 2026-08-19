import time
from typing import Dict, Any
from animation_planner import CharacterRig, LinearBlendSkinning, PoseInterpolator
from groq_animation import analyze_character_rig, plan_walk_cycle
from batch_manager import SmartBatchManager

def run_walk_cycle_animation(agent, mcp, extracted_geometry: Dict[str, Any], ref_path: str, target_width=800, target_height=600, fit_mode="contain"):
    print("\n" + "="*60)
    print("WALK CYCLE ANIMATION PIPELINE STARTED")
    print("="*60)
    
    # 1. Analyze character to get rest pose joints
    rest_joints_norm = analyze_character_rig(agent, ref_path)
    
    # 2. De-normalize joints to match canvas scaling
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
        
    print(f"\n[ANIM] Extracted {len(rest_joints)} joints for rest pose.")
    
    # 3. Plan Walk Cycle Keyframes
    keyframes = plan_walk_cycle(agent, rest_joints_norm)
    
    # 4. Interpolate 20 frames
    frames_angles = PoseInterpolator.interpolate(keyframes, 20)
    print(f"\n[ANIM] Interpolated {len(frames_angles)} frames of animation.")
    
    # 5. Extract rest pose strokes (already normalized in extracted_geometry)
    from main import _create_batches_from_extracted_geometry
    # We use _create_batches_from_extracted_geometry to get the base canvas coordinates
    # We don't batch them yet, we just want the flattened list of strokes
    # Actually, _create_batches_from_extracted_geometry returns batches.
    # We can unwrap them.
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
            
    print(f"\n[ANIM] Found {len(all_strokes)} strokes to bind to rig.")
    
    # 6. Bind strokes to rig
    rig = CharacterRig(rest_joints)
    skinning = LinearBlendSkinning(rig, all_strokes)
    print("[ANIM] LBS Binding complete.")
    
    # 7. Execute 20 frames in Krita
    batch_manager = SmartBatchManager(mcp)
    
    # Select paint layer
    try:
        mcp.call_tool("krita_select_paint_layer", {}, timeout=10)
    except Exception as e:
        print(f"Warning: select paint layer failed: {e}")
    
    # Enable onion skin
    try:
        mcp.call_tool("krita_enable_onion", {"enabled": True}, timeout=10)
    except Exception as e:
        print(f"Warning: enable onion skin failed: {e}")
        
    for frame_idx, angles in enumerate(frames_angles):
        krita_frame = frame_idx + 1
        print(f"\n--- Drawing Frame {krita_frame}/20 ---")
        
        # Create keyframe and select frame with validation
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
                # Parse current frame from dict
                actual_frame = current_frame_result.get("current_frame", -1) if isinstance(current_frame_result, dict) else -1
                
                print(f"[FRAME {krita_frame}/20] Target frame: {krita_frame}")
                print(f"[FRAME {krita_frame}/20] Krita current frame: {actual_frame}")
                
                if actual_frame == krita_frame:
                    frame_ready = True
                    break
                else:
                    print(f"Frame validation failed (expected {krita_frame}, got {actual_frame}). Retrying...")
                    time.sleep(1)
            except Exception as e:
                print(f"Warning: get current frame failed: {e}")
                time.sleep(1)
                
        if not frame_ready:
            print(f"Fatal: Could not select/verify frame {krita_frame}. Stopping animation.")
            break
            
        print(f"[FRAME {krita_frame}/20] Clearing frame...")
        try:
            # Clear canvas so we don't draw over the duplicated keyframe
            mcp.call_tool("krita_clear", {"color": "#ffffff"}, timeout=10)
        except Exception as e:
            print(f"Warning: failed to clear frame: {e}")
            
        print(f"[FRAME {krita_frame}/20] Drawing...")
        
        # Deform geometry
        # Fix vertical bouncing: root_y is absolute addition, we want it scaled
        if "root_y" in angles:
            angles["root_y"] = angles["root_y"] * ref_h * scale
        if "root_x" in angles:
            angles["root_x"] = angles["root_x"] * ref_w * scale
            
        rig.set_pose(angles)
        deformed_strokes = skinning.deform()
        
        # Group back into batches
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
            
        # Draw!
        batch_manager.execute_plan(frame_batches)
        
    print("\n" + "="*60)
    print("WALK CYCLE ANIMATION COMPLETE")
    print("="*60)
