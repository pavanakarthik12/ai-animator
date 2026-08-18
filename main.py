import sys
import traceback
import time
import os
import json
from pathlib import Path
from config import config
from mcp_client import KritaMCPClient
from groq_agent import GroqAgent
from vision_to_drawing import vision_plan_to_drawing_batches, create_drawing_plan_prompt

# Windows consoles may use cp1252; force UTF-8 with lossless replacement so
# printing tool results (which may contain unicode) never crashes.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def _extract_points(stroke):
    """Coerce a batch stroke argument into a list of [x, y] integer pairs.

    Accepts {"points": [[x, y], ...]}, [[x, y], ...], or a flat
    [x1, y1, x2, y2, ...] list, so slightly malformed model output still
    executes instead of failing the whole batch.
    """
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


def _create_batches_from_extracted_geometry(extracted_geometry, target_width=800, target_height=600):
    """Convert extracted computer vision geometry directly to drawing batches.
    
    This bypasses Groq coordinate generation and uses actual extracted contours.
    """
    strokes_data = extracted_geometry.get("strokes", [])
    regions_data = extracted_geometry.get("regions", [])
    
    if not strokes_data and not regions_data:
        return []
    
    # Group strokes by (color, thickness) for efficient batching
    from collections import defaultdict
    stroke_groups = defaultdict(list)
    
    # Process extracted strokes
    for stroke_data in strokes_data:
        normalized_points = stroke_data.get("points", [])
        if len(normalized_points) < 2:
            continue
        
        # Denormalize points to target canvas
        canvas_points = []
        for norm_x, norm_y in normalized_points:
            x = int(norm_x * target_width)
            y = int(norm_y * target_height)
            # Clamp to canvas
            x = max(0, min(target_width - 1, x))
            y = max(0, min(target_height - 1, y))
            canvas_points.append([x, y])
        
        color = stroke_data.get("color", "#000000")
        thickness = stroke_data.get("thickness", 3)
        
        # Group by (color, thickness)
        key = (color, thickness)
        stroke_groups[key].append({
            "points": canvas_points,
            "closed": stroke_data.get("closed", False)
        })
    
    # Process extracted regions (filled areas)
    for region_data in regions_data:
        normalized_points = region_data.get("points", [])
        if len(normalized_points) < 3:
            continue
        
        # Denormalize points
        canvas_points = []
        for norm_x, norm_y in normalized_points:
            x = int(norm_x * target_width)
            y = int(norm_y * target_height)
            x = max(0, min(target_width - 1, x))
            y = max(0, min(target_height - 1, y))
            canvas_points.append([x, y])
        
        color = region_data.get("color", "#808080")
        thickness = 2  # Thin outline for filled regions
        
        key = (color, thickness)
        stroke_groups[key].append({
            "points": canvas_points,
            "closed": True
        })
    
    # Create batches
    batches = []
    group_items = list(stroke_groups.items())
    
    for idx, ((color, thickness), strokes) in enumerate(group_items):
        is_last = (idx == len(group_items) - 1)
        
        batch = {
            "color": color,
            "brush_size": thickness,
            "strokes": strokes,
            "complete": is_last
        }
        batches.append(batch)
    
    return batches


def main():
    # STARTUP VERIFICATION - Do NOT remove
    print()
    print("="*60)
    print("AI KRITA AGENT STARTED")
    print("RUNNING FILE:", __file__)
    print("PID:", os.getpid())
    print("="*60)
    print()
    
    try:
        krita_server = config.krita_mcp_server
        if not krita_server:
            print("KRITA_MCP_SERVER not set in .env")
            return

        # Start MCP client and discover tools
        mcp = KritaMCPClient(krita_server)
        print("[STARTUP] Starting MCP client and launching server.py...")
        mcp.start()

        tools = mcp.list_tools()
        tools_detailed = mcp.list_tools_detailed()
        print("[STARTUP] Discovered MCP tools:")
        for t in tools_detailed:
            name = t.get("name")
            print("  -", name)

        # Start Groq agent
        if not config.groq_api_key:
            print("Missing GROQ_API_KEY in environment (.env). Exiting.")
            return

        print("[STARTUP] Initializing Groq agent...")
        agent = GroqAgent(config.groq_api_key, config.groq_model, config.groq_vision_model)
        print("[STARTUP] Application initialized successfully.")
        print()

        # Check for automation mode (environment variables)
        reference_image_path = os.environ.get("REFERENCE_IMAGE")
        prompt = os.environ.get("AUTOMATION_PROMPT")
        
        # Interactive mode: proper user input flow
        if not prompt:
            print("="*60)
            print("AI KRITA DRAWING AGENT")
            print("="*60)
            print()
            print("[INPUT] Waiting for drawing request...")
            print()
            
            # Ask what to draw
            prompt = input("What do you want to draw?\n> ").strip()
            if not prompt:
                print("No drawing request provided.")
                return
            
            print(f"[INPUT] Drawing request received: {prompt}")
            print()
            
            # Ask if user wants a reference image
            print("[INPUT] Waiting for reference choice...")
            use_reference = input("Do you want to use a reference image? (y/n)\n> ").strip().lower()
            print(f"[INPUT] Reference choice: {use_reference}")
            print()
            
            if use_reference in ['y', 'yes']:
                print("[INPUT] Reference mode: YES")
                print()
                
                # Ask for reference image path
                while True:
                    print("[INPUT] Waiting for reference path...")
                    reference_input = input("Enter the reference image path:\n> ").strip()
                    
                    if not reference_input:
                        print("Reference image path is required.")
                        retry = input("Try again? (y/n)\n> ").strip().lower()
                        if retry not in ['y', 'yes']:
                            print("Exiting.")
                            return
                        continue
                    
                    # Validate file exists
                    if not os.path.exists(reference_input):
                        print(f"Error: File not found: {reference_input}")
                        retry = input("Try again? (y/n)\n> ").strip().lower()
                        if retry not in ['y', 'yes']:
                            print("Exiting.")
                            return
                        continue
                    
                    # Validate file extension
                    ext = os.path.splitext(reference_input)[1].lower()
                    if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
                        print(f"Error: Unsupported image format: {ext}")
                        print("Supported formats: .png, .jpg, .jpeg, .webp")
                        retry = input("Try again? (y/n)\n> ").strip().lower()
                        if retry not in ['y', 'yes']:
                            print("Exiting.")
                            return
                        continue
                    
                    # File is valid
                    reference_image_path = reference_input
                    print(f"[INPUT] Reference path received: {reference_image_path}")
                    print(f"Reference image loaded successfully: {reference_image_path}")
                    break
                
                # Ask what to do with the reference
                print()
                print("[INPUT] Waiting for reference instructions...")
                print("What do you want me to do with this reference?")
                print("Examples:")
                print("  - Recreate this character accurately, preserving all details.")
                print("  - Use this character but raise the right arm.")
                print("  - Create two frames with this character waving.")
                instruction = input("> ").strip()
                
                if instruction:
                    print(f"[INPUT] Reference instructions received: {instruction}")
                    # Combine original prompt with instruction
                    prompt = instruction
                else:
                    # Use default instruction
                    prompt = f"{prompt} - Recreate the reference image accurately, preserving all visible details."
                    print(f"[INPUT] Using default instruction.")
            else:
                print("[INPUT] Reference mode: NO")
                print()

        # Expose only planning-level tools to the model. The per-stroke MCP
        # tools (krita_set_color, krita_set_brush, krita_stroke, krita_fill,
        # krita_draw_shape) are NOT passed to Groq — they are still executed
        # via MCP, but only through the agent-side `krita_batch_draw` wrapper,
        # so the model cannot fall back to one request per stroke.
        tool_subset = {
            "krita_new_canvas",
            "krita_select_paint_layer",
            "krita_create_frame", "krita_select_frame",
            "krita_get_current_frame", "krita_set_current_frame",
            "krita_create_keyframe", "krita_delete_keyframe",
            "krita_list_keyframes", "krita_has_keyframe",
        }

        # System prompt: be explicit about completing the user's drawing by using MCP tools.
        # Only summarize the tools actually exposed to the model (names + one-line
        # descriptions). Dumping full MCP schemas here inflates the Groq request
        # past the org TPM limit.
        tool_summaries = []
        for t in tools_detailed:
            name = t.get("name")
            if name not in tool_subset:
                continue
            desc = (t.get("description") or "").strip().split("\n")[0]
            tool_summaries.append(f"{name} — {desc}")
        tool_summaries.append(
            "krita_batch_draw — draw a COMPLETE drawing in one call (color, brush_size, strokes array of point lists)"
        )

        system_message = (
            "You are controlling Krita through MCP. Complete the user's requested artwork inside Krita by CALLING the available tools. "
            "Never describe performing an operation in text — invoke the tool. "
            "Changing a setting such as color or brush is only an intermediate step.\n"
            "PLANNING RULE (most important): Plan the COMPLETE drawing before executing anything. "
            "For any drawing request, your FIRST tool-calling response must contain the entire drawing as ONE `krita_batch_draw` "
            "call with the color, brush_size, and an array of strokes (each stroke is an object with a `points` array of [x, y] pairs). "
            "Do NOT draw stroke by stroke with separate requests — the whole drawing must be planned and emitted in a single response. "
            "If the drawing needs more than one color, emit one `krita_batch_draw` call per color IN THE SAME response; do not wait "
            "for a reply between colors. "
            "Every `krita_batch_draw` call MUST include `complete`: set it to `true` ONLY in the LAST batch, once the ENTIRE requested "
            "drawing (all colors, all parts) has been drawn in that response; set it to `false` when more drawing will follow. "
            "The request is considered finished when a `krita_batch_draw` with `complete=true` executes successfully.\n"
            "The Krita canvas is 800x600 pixels by default: x ranges 0-799, y ranges 0-599.\n"
            f"Available tools: {', '.join(tool_summaries)}.\n"
            "ANIMATION RULES:\n"
            "- When the user asks you to create, modify, or animate frames, you MUST use the animation/keyframe tools "
            "(krita_select_paint_layer, krita_create_keyframe, krita_set_current_frame, krita_get_current_frame, "
            "krita_list_keyframes, krita_has_keyframe, krita_delete_keyframe) together with the drawing tools.\n"
            "- A frame is a REAL timeline keyframe on the active paint layer. Do not fake frames with layers, files, or text claims.\n"
            "- Never claim that a frame, keyframe, or drawing was created unless the corresponding MCP tool was actually executed and "
            "returned success.\n"
            "- For a two-frame task, use this strict order: `krita_select_paint_layer` -> `krita_create_keyframe(frame=0)` -> "
            "`krita_set_current_frame(frame=0)` -> verify with `krita_get_current_frame` / `krita_has_keyframe` / `krita_list_keyframes` "
            "-> draw frame 0; then `krita_create_keyframe(frame=1)` -> `krita_set_current_frame(frame=1)` -> verify keyframes include "
            "both 0 and 1 -> draw frame 1.\n"
            "- After each frame operation, verify the state and include that evidence (current frame and keyframe list) in your final response.\n"
            "Example animation flow: krita_select_paint_layer -> krita_create_keyframe(frame=0) -> krita_set_current_frame(frame=0) -> "
            "krita_batch_draw -> krita_create_keyframe(frame=1) -> krita_set_current_frame(frame=1) -> draw -> "
            "krita_list_keyframes to verify.\n"
        )

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ]

        # Convert MCP tools into Groq `tools` function definitions so the model
        # can call them with structured inputs.
        #
        # Schema compression: MCP schemas contain bloated constructs (nullable
        # `anyOf` variants, `additionalProperties`) that inflate the Groq
        # request to thousands of tokens and trigger 429 TPM rate limits on
        # multi-step runs. Strip them before sending to Groq.
        def sanitize_schema(schema):
            if isinstance(schema, dict):
                out = {}
                for k, v in schema.items():
                    if k == "additionalProperties":
                        continue
                    if k == "anyOf" and isinstance(v, list):
                        non_null = [x for x in v if not (isinstance(x, dict) and x.get("type") == "null")]
                        if len(non_null) == 1:
                            out.update(sanitize_schema(non_null[0]))
                            continue
                        out[k] = [sanitize_schema(x) for x in non_null]
                        continue
                    if k == "properties" and isinstance(v, dict):
                        out[k] = {pk: sanitize_schema(pv) for pk, pv in v.items()}
                        continue
                    if k == "items" and isinstance(v, dict):
                        out[k] = sanitize_schema(v)
                        continue
                    out[k] = v
                return out
            return schema

        tools_for_model = []
        for t in tools_detailed:
            name = t.get("name")
            if name not in tool_subset:
                continue
            desc = t.get("description") or f"MCP tool {name}"
            params_schema = t.get("input_schema") or {"type": "object", "properties": {}}
            func = {"name": name, "description": desc, "parameters": sanitize_schema(params_schema)}
            tools_for_model.append({"type": "function", "function": func})

        # Add an agent-side batch drawing helper so the model can return one tool call
        # describing many strokes. This wrapper uses existing MCP tools under the hood.
        batch_schema = {
            "type": "object",
            "properties": {
                "color": {"type": "string", "description": "Hex color code, e.g. '#ff0000'"},
                "brush_size": {"type": "integer", "description": "Brush size in pixels"},
                "strokes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "points": {"type": "array", "description": "List of [x, y] coordinate pairs", "items": {"type": "array", "items": {"type": "number"}}},
                            "pressure": {"type": "number", "description": "Optional pressure for stroke", "default": 1.0}
                        },
                        "required": ["points"]
                    }
                },
                "complete": {"type": "boolean", "description": "Set to true ONLY when this batch finishes the ENTIRE requested drawing (every color, every part). Set to false when more drawing is still to come."}
            },
            "required": ["strokes", "complete"]
        }

        tools_for_model.append({
            "type": "function",
            "function": {
                "name": "krita_batch_draw",
                "description": "Draw a complete drawing in ONE call: sets the color and brush, then paints ALL strokes. "
                               "For every drawing request, plan the entire drawing and include every stroke in a single "
                               "krita_batch_draw call. If multiple colors are needed, use one krita_batch_draw call per color "
                               "in the SAME response, and set complete=true only in the LAST batch once the whole drawing is done.",
                "parameters": batch_schema,
            },
        })

        print("Groq tools available (passed in `tools`):")
        for tf in tools_for_model:
            fn = tf.get("function", {})
            print("  -", fn.get("name"))
        print("Model name:", config.groq_model)
        print()

        # IMAGE REFERENCE MODE: Extract actual geometry using computer vision, then use vision for interpretation
        vision_drawing_batches = None
        if reference_image_path:
            print()
            print("[REFERENCE] Processing reference image...")
            print(f"Reference image: {reference_image_path}")
            
            # Verify image exists and has valid extension
            if not os.path.exists(reference_image_path):
                print(f"Error: Image file not found: {reference_image_path}")
                return
            
            ext = os.path.splitext(reference_image_path)[1].lower()
            if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
                print(f"Error: Unsupported image format: {ext}")
                print("Supported formats: .png, .jpg, .jpeg, .webp")
                return
            
            try:
                # STEP 1: Extract actual geometry from image using computer vision
                print("\n--- Extracting Geometry Using Computer Vision ---")
                from image_processor import extract_contours_from_image
                
                extracted_geometry = extract_contours_from_image(
                    reference_image_path,
                    min_contour_points=10,
                    epsilon_factor=0.002  # Minimal simplification - preserve details
                )
                
                print(f"Extracted geometry:")
                print(f"  Image size: {extracted_geometry['width']}x{extracted_geometry['height']}")
                print(f"  Type: {'line art' if extracted_geometry['is_line_art'] else 'colored'}")
                print(f"  Strokes: {len(extracted_geometry['strokes'])}")
                print(f"  Filled regions: {len(extracted_geometry['regions'])}")
                print(f"  Total elements: {extracted_geometry['total_elements']}")
                
                if extracted_geometry['total_elements'] == 0:
                    print("\nError: No visual geometry could be extracted from the reference image.")
                    print("The image may be blank, very low contrast, or in an unsupported format.")
                    return
                
                # STEP 2: Use Groq Vision to interpret and organize the extracted geometry
                print("\n--- Using Groq Vision for Interpretation ---")
                print("Sending extracted geometry + reference image to Groq for organization...")
                
                # Create prompt that emphasizes Groq's role as interpreter, not generator
                interpretation_prompt = f"""{prompt}

IMPORTANT: The actual visual geometry has already been extracted from the reference image using computer vision.

Extracted data:
- {len(extracted_geometry['strokes'])} strokes with actual point coordinates
- {len(extracted_geometry['regions'])} filled regions
- Image type: {'line art' if extracted_geometry['is_line_art'] else 'colored image'}

Your role is to INTERPRET and ORGANIZE this extracted geometry, NOT to generate new coordinates.

Please provide:
1. Drawing order (which strokes should be drawn first)
2. Semantic grouping (which strokes represent the same feature)
3. Color assignments (based on the reference image colors)
4. Brush sizes appropriate for each stroke type
5. Any user-requested modifications to pose/style

Output format: JSON with components list, each containing:
- name: component description (e.g., "head_outline", "left_eye")
- order: drawing order number
- strokes: use the EXTRACTED NORMALIZED POINTS from the geometry data
- color: hex color code
- brush_size: integer

DO NOT invent new coordinates. Use the extracted geometry as the source of truth."""

                vision_response = agent.analyze_image(reference_image_path, interpretation_prompt)
                
                print("\n--- Groq Interpretation (preview) ---")
                preview = vision_response[:500] + "..." if len(vision_response) > 500 else vision_response
                print(preview)
                print()
                
                # STEP 3: Merge extracted geometry with Groq interpretation
                print("\n--- Merging Extracted Geometry with Interpretation ---")
                
                # Convert extracted geometry directly to drawing batches
                # Use Groq interpretation for organization hints if available
                vision_drawing_batches = _create_batches_from_extracted_geometry(
                    extracted_geometry,
                    target_width=800,
                    target_height=600
                )
                
                if not vision_drawing_batches:
                    print("Error: Could not create drawing batches from extracted geometry.")
                    return
                
                print(f"\nDrawing plan created from extracted geometry:")
                print(f"  Total batches: {len(vision_drawing_batches)}")
                total_strokes = sum(len(b["strokes"]) for b in vision_drawing_batches)
                print(f"  Total strokes: {total_strokes}")
                
                # Show detailed breakdown
                for i, batch in enumerate(vision_drawing_batches):
                    print(f"  Batch {i+1}: {len(batch['strokes'])} strokes, color={batch['color']}, brush={batch['brush_size']}")
                print()
                
            except ImportError as e:
                print(f"Error: Could not import image processing module: {e}")
                print("\nMissing dependencies. Please install:")
                print("  pip install opencv-python numpy")
                return
            except ValueError as e:
                # JSON parsing errors
                print(f"Error: Vision model did not return valid JSON: {e}")
                if 'vision_response' in locals():
                    print("Response was:", vision_response[:500])
                return
            except Exception as e:
                print(f"Error during reference processing: {e}")
                error_msg = str(e).lower()
                if "decommissioned" in error_msg or "deprecated" in error_msg:
                    print("\nThe vision model is no longer available.")
                    print("Please update GROQ_VISION_MODEL in .env to a supported model.")
                    print("Current supported vision model: qwen/qwen3.6-27b")
                    print("\nTo fix: Edit .env and set:")
                    print("  GROQ_VISION_MODEL=qwen/qwen3.6-27b")
                traceback.print_exc()
                return

        import json

        # Execution statistics: actual Groq requests, MCP calls, and batches.
        stats = {"groq_requests": 0, "mcp_calls": 0, "batches": 0}
        t_start = time.time()

        def mcp_call(name, arguments):
            stats["mcp_calls"] += 1
            return mcp.call_tool(name, arguments, timeout=60)

        # IMAGE REFERENCE MODE: Execute vision-based drawing batches directly
        if vision_drawing_batches:
            print()
            print("[MCP] Executing drawing from reference...")
            print()
            for batch_idx, batch in enumerate(vision_drawing_batches):
                batch_num = batch_idx + 1
                print(f"\nExecuting batch {batch_num}/{len(vision_drawing_batches)}...")
                print(f"  Color: {batch['color']}")
                print(f"  Brush size: {batch['brush_size']}")
                print(f"  Strokes: {len(batch['strokes'])}")
                
                stats["batches"] += 1
                batch_results = []
                
                # Set color
                color = batch.get("color")
                if color:
                    try:
                        r = mcp_call("krita_set_color", {"color": color})
                        batch_results.append({"action": "krita_set_color", "result": r})
                        print(f"    Set color: {color}")
                    except Exception as e:
                        batch_results.append({"action": "krita_set_color", "error": str(e)})
                        print(f"    Error setting color: {e}")
                        traceback.print_exc()
                
                # Set brush size
                brush_size = batch.get("brush_size")
                if brush_size is not None:
                    try:
                        r = mcp_call("krita_set_brush", {"size": int(brush_size)})
                        batch_results.append({"action": "krita_set_brush", "result": r})
                        print(f"    Set brush size: {brush_size}")
                    except Exception as e:
                        batch_results.append({"action": "krita_set_brush", "error": str(e)})
                        print(f"    Error setting brush: {e}")
                        traceback.print_exc()
                
                # Draw all strokes
                strokes = batch.get("strokes", [])
                strokes_drawn = 0
                for stroke_idx, stroke in enumerate(strokes):
                    points = stroke.get("points", [])
                    if len(points) < 2:
                        batch_results.append({"action": "krita_stroke", "error": "Invalid points"})
                        continue
                    
                    try:
                        r = mcp_call("krita_stroke", {"points": points, "pressure": 1.0})
                        batch_results.append({"action": "krita_stroke", "result": r})
                        if "error" not in str(r).lower():
                            strokes_drawn += 1
                        
                        # Progress indicator for large batches
                        if (stroke_idx + 1) % 10 == 0 or stroke_idx == len(strokes) - 1:
                            print(f"    Progress: {stroke_idx + 1}/{len(strokes)} strokes")
                    except Exception as e:
                        batch_results.append({"action": "krita_stroke", "error": str(e)})
                        print(f"    Error drawing stroke {stroke_idx + 1}: {e}")
                        traceback.print_exc()
                
                print(f"  Batch complete: {strokes_drawn}/{len(strokes)} strokes drawn")
            
            print()
            print("[KRITA] Drawing operation completed.")
            print()
            print("="*60)
            print("DRAWING COMPLETE")
            print("="*60)
            print(f"Total batches: {stats['batches']}")
            print(f"Total MCP calls: {stats['mcp_calls']}")
            print(f"Execution time: {time.time() - t_start:.2f}s")
            print("\nThe reference image has been recreated in Krita using actual drawing operations.")
            print("Check your Krita canvas to see the result.")
            return

        # Classify the request so we can gate the final response on actual tool use.
        print()
        print("[GROQ] Sending request to Groq for text-based drawing...")
        print()
        
        prompt_lower = prompt.lower()
        wants_drawing = any(k in prompt_lower for k in (
            "draw", "circle", "ellipse", "paint", "stroke", "shape", "stick", "man", "scene", "art",
        ))
        wants_animation = any(k in prompt_lower for k in (
            "frame", "frames", "animation", "animate", "animating", "keyframe", "keyframes",
            "wave", "waving", "timeline",
        ))
        wants_multiple_frames = any(k in prompt_lower for k in (
            "two", " 2 ", "2 frames", "second frame", "frame 0", "frame 1", "each frame", "both frames",
        ))

        max_steps = 20
        executed_drawing = False
        executed_frame_ops = False
        create_keyframe_count = 0
        last_draw_step = -1
        last_keyframe_step = -1
        last_keyframes = None
        tool_error_retries = 0
        follow_ups = 0
        for step in range(max_steps):
            stats["groq_requests"] += 1
            print("Sending request to Groq (step", step + 1, ")...")
            t0 = time.time()
            try:
                resp = agent.call_model(messages, tools_for_model)
            except Exception as e:
                t1 = time.time()
                model_duration = t1 - t0
                print(f"Groq request: {model_duration:.3f}s")
                emsg = str(e).lower()
                if ("tool call" in emsg or "tool_use_failed" in emsg or "did not match" in emsg
                        or "failed to parse" in emsg or "arguments" in emsg) and tool_error_retries < 3:
                    tool_error_retries += 1
                    print(f"Groq rejected a tool call ({tool_error_retries}/3); asking the model to fix it...")
                    messages.append({
                        "role": "user",
                        "content": "Your previous tool call was rejected: the tool arguments were not valid JSON "
                                   "(no // comments, no trailing commas, quoted keys, valid values only). "
                                   "Re-issue the same tool call with corrected arguments.",
                    })
                    continue
                print("Fatal error calling Groq:", e)
                return
            else:
                t1 = time.time()
                model_duration = t1 - t0
                print(f"Groq request: {model_duration:.3f}s")

            # Extract assistant message and preserve tool_calls (if any)
            try:
                choice = resp.choices[0]
                assistant_message = getattr(choice, "message", None)
                finish_reason = getattr(choice, "finish_reason", None)
            except Exception:
                print("Malformed model response:", resp)
                return

            # If the response was cut off at the token limit, the plan may be
            # incomplete — do NOT fast-exit; let the model continue.
            truncated = finish_reason == "length"

            model_text = assistant_message.content if hasattr(assistant_message, "content") else str(assistant_message)
            print("Model response:", model_text)

            # Preserve the assistant message including any tool_calls metadata
            assistant_entry = {"role": "assistant", "content": model_text}
            tool_calls = getattr(assistant_message, "tool_calls", None) or []
            if tool_calls:
                assistant_entry["tool_calls"] = []
                for tc in tool_calls:
                    fn = getattr(tc, "function", None)
                    fn_name = getattr(fn, "name", None) if fn else None
                    fn_args = getattr(fn, "arguments", None) if fn else None
                    assistant_entry["tool_calls"].append({
                        "id": getattr(tc, "id", None),
                        "type": getattr(tc, "type", None),
                        "function": {"name": fn_name, "arguments": fn_args},
                    })

            # Append assistant message BEFORE executing tools
            messages.append(assistant_entry)

            # If the assistant invoked tool_calls, execute each and append matching tool results
            if tool_calls:
                # measure MCP execution time for all tool_calls in this assistant message
                mcp_start = time.time()
                batch_done = False
                batch_strokes_drawn = 0
                batch_color = None
                batch_brush = None
                batch_complete = False
                pending_work_calls = 0
                for tc in tool_calls:
                    tc_id = getattr(tc, "id", None)
                    fn = getattr(tc, "function", None)
                    fn_name = getattr(fn, "name", None) if fn else None
                    fn_args = getattr(fn, "arguments", None) if fn else None

                    print("Groq tool call:")
                    print("  id:", tc_id)
                    print("  name:", fn_name)

                    # Special handling: agent-side batch wrapper — executes the
                    # complete drawing plan without any further Groq round trip.
                    if fn_name == "krita_batch_draw":
                        # fn_args expected to be an object with color, brush_size, strokes
                        args_obj = fn_args
                        try:
                            if isinstance(fn_args, str):
                                args_obj = json.loads(fn_args)
                        except Exception:
                            args_obj = fn_args

                        stats["batches"] += 1
                        batch_results = []
                        color = None
                        brush_size = None
                        strokes_drawn = 0
                        if isinstance(args_obj, dict):
                            color = args_obj.get("color")
                            if color:
                                try:
                                    r = mcp_call("krita_set_color", {"color": color})
                                    batch_results.append({"action": "krita_set_color", "result": r})
                                    print("MCP →", r)
                                except Exception as e:
                                    batch_results.append({"action": "krita_set_color", "error": str(e)})
                                    traceback.print_exc()

                            brush_size = args_obj.get("brush_size")
                            if brush_size is not None:
                                try:
                                    r = mcp_call("krita_set_brush", {"size": int(brush_size)})
                                    batch_results.append({"action": "krita_set_brush", "result": r})
                                    print("MCP →", r)
                                except Exception as e:
                                    batch_results.append({"action": "krita_set_brush", "error": str(e)})
                                    traceback.print_exc()

                            strokes = args_obj.get("strokes") or []
                            # Merge strokes that share an endpoint into a single
                            # MCP call (identical pixels; the plugin blends with
                            # max-alpha, so redrawing a joint is a no-op).
                            merged = []
                            for s in strokes:
                                points = _extract_points(s)
                                if len(points) < 2:
                                    batch_results.append({"action": "krita_stroke", "error": "Invalid points"})
                                    continue
                                if merged and merged[-1][-1] == points[0]:
                                    merged[-1].extend(points[1:])
                                else:
                                    merged.append(list(points))
                            for points in merged:
                                try:
                                    r = mcp_call("krita_stroke", {"points": points, "pressure": 1.0})
                                    batch_results.append({"action": "krita_stroke", "result": r})
                                    print("MCP →", r)
                                    if "error" not in str(r).lower():
                                        strokes_drawn += 1
                                except Exception as e:
                                    batch_results.append({"action": "krita_stroke", "error": str(e)})
                                    traceback.print_exc()

                        # Append a single tool result summarizing batch actions
                        messages.append({"role": "tool", "tool_call_id": tc_id, "content": str(batch_results)})
                        # Mark drawing executed if any strokes actually painted
                        if strokes_drawn > 0:
                            executed_drawing = True
                            last_draw_step = step
                            batch_done = True
                            batch_strokes_drawn = strokes_drawn
                            batch_color = color
                            batch_brush = brush_size
                            batch_complete = bool(args_obj.get("complete"))
                        continue

                    # Parse arguments if they're a JSON string
                    args = fn_args
                    try:
                        if isinstance(fn_args, str):
                            args = json.loads(fn_args)
                    except Exception:
                        pass

                    # Canvas/layer setup tools are part of planning and do not
                    # block the fast path; anything else may mean more work.
                    if fn_name not in ("krita_new_canvas", "krita_select_paint_layer"):
                        pending_work_calls += 1

                    try:
                        res = mcp_call(fn_name, args or {})
                        # The plugin creates real keyframes by driving Krita's
                        # timeline UI, which is racy: it occasionally reports
                        # "Failed to create keyframe" even though the state is
                        # healthy. Retry a few times before giving up.
                        if fn_name in ("krita_create_keyframe", "krita_create_frame") and "error" in str(res).lower():
                            for attempt in range(1, 4):
                                time.sleep(1.0)
                                print(f"Retrying {fn_name} (attempt {attempt + 1}/4)...")
                                res = mcp_call(fn_name, args or {})
                                print("MCP →", res)
                                if "error" not in str(res).lower():
                                    break
                        print("MCP →", res)
                    except Exception as e:
                        print("MCP call failed:", e)
                        traceback.print_exc()
                        return

                    # Only count operations as performed if the tool actually succeeded
                    res_ok = "error" not in str(res).lower()

                    # Remember the keyframe list when a result reports it
                    if res_ok and isinstance(res, dict) and res.get("keyframes") is not None:
                        last_keyframes = res["keyframes"]

                    # Mark drawing executed if applicable
                    if fn_name in ("krita_draw_shape", "krita_stroke", "krita_fill") and res_ok:
                        executed_drawing = True
                        last_draw_step = step

                    # Mark animation/frame operations executed
                    if fn_name in (
                        "krita_create_keyframe", "krita_set_current_frame", "krita_select_frame",
                        "krita_create_frame", "krita_get_current_frame", "krita_list_keyframes",
                        "krita_has_keyframe", "krita_delete_keyframe",
                    ) and res_ok:
                        executed_frame_ops = True
                        if fn_name in ("krita_create_keyframe", "krita_create_frame"):
                            create_keyframe_count += 1
                            last_keyframe_step = step

                    # Append the tool result with matching tool_call_id
                    messages.append({"role": "tool", "tool_call_id": tc_id, "content": str(res)})

                mcp_end = time.time()
                mcp_duration = mcp_end - mcp_start
                print(f"MCP execution: {mcp_duration:.3f}s")

                # Fast path: the model planned the complete drawing in one batch
                # and it executed successfully. For a plain drawing request there
                # is nothing left to reason about — skip the summary round trip.
                if (
                    batch_done
                    and batch_complete
                    and batch_strokes_drawn > 0
                    and not wants_animation
                    and not truncated
                    and pending_work_calls == 0
                ):
                    print("\nDrawing complete (no summary round trip needed):")
                    print(f"  strokes drawn: {batch_strokes_drawn}")
                    if batch_color:
                        print(f"  color: {batch_color}")
                    if batch_brush is not None:
                        print(f"  brush size: {batch_brush}")
                    print("Final assistant response:")
                    summary = f"Drew {batch_strokes_drawn} stroke(s) on the Krita canvas."
                    if batch_color:
                        summary += f" Color: {batch_color}."
                    if batch_brush is not None:
                        summary += f" Brush size: {batch_brush}."
                    print(summary)
                    break

                # After executing all tool calls, continue loop so model can respond
                continue

            # No tool calls — the model produced plain text.
            print("message.tool_calls:", "EMPTY/None" if not tool_calls else f"{len(tool_calls)} call(s)")

            # Determine whether the requested operation has actually been performed
            # using tools. Do NOT accept a final text response for animation/drawing
            # requests unless the required tools were executed (phase.md §5).
            missing_work = False
            if wants_animation:
                if not executed_frame_ops:
                    missing_work = True
                if wants_multiple_frames and create_keyframe_count < 2:
                    missing_work = True
                if wants_drawing and not executed_drawing:
                    missing_work = True
                # A multi-frame drawing must have actual drawing AFTER the last
                # keyframe was created; drawing only on earlier frames is not
                # enough (the model often stops right after create_keyframe).
                if wants_multiple_frames and not missing_work and last_keyframe_step > last_draw_step:
                    missing_work = True
            elif wants_drawing and not executed_drawing:
                missing_work = True

            # An empty final response is never acceptable for a work request.
            if not missing_work and (wants_drawing or wants_animation):
                if not (model_text and str(model_text).strip()):
                    missing_work = True

            if missing_work and follow_ups < 5:
                follow_ups += 1
                print("Model returned final text but the requested operation was not performed with tools. Prompting the model to use the tools.")
                if wants_animation:
                    kf_info = f" Keyframes currently on the paint layer: {last_keyframes}." if last_keyframes is not None else ""
                    followup = (
                        "You returned a natural-language response, but the user's animation request has not been completed: "
                        "no animation/frame tools were actually executed" + (" and no drawing was performed" if wants_drawing and not executed_drawing else "") + ". "
                        "You MUST use the Krita MCP tools to perform the work: "
                        "`krita_select_paint_layer`, `krita_create_keyframe(frame=...)`, `krita_set_current_frame(frame=...)`, "
                        "verify with `krita_get_current_frame`/`krita_list_keyframes`, and draw with `krita_batch_draw`/`krita_stroke`/`krita_draw_shape`."
                        + kf_info +
                        " If a keyframe exists but has nothing drawn on it, switch to it with `krita_set_current_frame(frame=N)` "
                        "and draw there before summarizing. "
                        "Only after the tools have succeeded, summarize what was created."
                    )
                else:
                    followup = (
                        "You returned a natural-language response but the user's drawing request has not been completed because no drawing tool was used. "
                        "Please invoke the `krita_batch_draw` tool with the complete drawing in a single call: color, brush_size, all strokes, and complete=true."
                    )
                messages.append({"role": "user", "content": followup})
                continue

            if follow_ups >= 5:
                print("Too many follow-ups without tool use; accepting response.")

            print("Final assistant response:")
            if isinstance(model_text, dict):
                print(json.dumps(model_text))
            else:
                print(model_text)
            break

        else:
            print("Max steps reached without completion.")

        print()
        print("[KRITA] Drawing operation completed.")
        print()
        print("="*60)
        print("DRAWING COMPLETE")
        print("="*60)
        print(f"Total Groq requests: {stats['groq_requests']}")
        print(f"Total MCP calls: {stats['mcp_calls']}")
        print(f"Total batch drawing operations: {stats['batches']}")
        print(f"Total execution time: {time.time() - t_start:.2f}s")

    except Exception as e:
        print("Fatal error:", e)
        traceback.print_exc()


if __name__ == "__main__":
    main()
