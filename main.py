import sys
import traceback
from config import config
from mcp_client import KritaMCPClient
from groq_agent import GroqAgent

# Windows consoles may use cp1252; force UTF-8 with lossless replacement so
# printing tool results (which may contain unicode) never crashes.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main():
    try:
        krita_server = config.krita_mcp_server
        if not krita_server:
            print("KRITA_MCP_SERVER not set in .env")
            return

        # Start MCP client and discover tools
        mcp = KritaMCPClient(krita_server)
        print("Starting MCP client and launching server.py...")
        mcp.start()

        tools = mcp.list_tools()
        tools_detailed = mcp.list_tools_detailed()
        print("Discovered MCP tools:")
        for t in tools_detailed:
            name = t.get("name")
            print("  -", name)
            if t.get("input_schema"):
                print("     schema:", t.get("input_schema"))

        # Start Groq agent
        if not config.groq_api_key:
            print("Missing GROQ_API_KEY in environment (.env). Exiting.")
            return

        agent = GroqAgent(config.groq_api_key, config.groq_model)

        import os
        # Allow non-interactive testing via AUTOMATION_PROMPT env var
        prompt = os.environ.get("AUTOMATION_PROMPT")
        if not prompt:
            prompt = input("What should I draw in Krita?\n> ")

        # System prompt: be explicit about completing the user's drawing by using MCP tools.
        # Include discovered tool schemas to help the model choose correct arguments.
        tool_summaries = []
        for t in tools_detailed:
            summary = t.get("name")
            schema = t.get("input_schema")
            if schema:
                summary += f" schema={schema}"
            tool_summaries.append(summary)

        system_message = (
            "You are controlling Krita through MCP. Complete the user's requested artwork inside Krita by CALLING the available tools. "
            "Never describe performing an operation in text — invoke the tool. "
            "Changing a setting such as color or brush is only an intermediate step. "
            "Continue making tool calls until the requested artwork has actually been created in Krita, then return a plain natural-language summary.\n"
            f"Available tools: {', '.join(tool_summaries)}.\n"
            "If the user requests a multi-stroke drawing, prefer returning a single `krita_batch_draw` tool_call containing the color, "
            "brush_size, and an array of strokes (each with points). This lets the agent send many strokes in one MCP batch.\n"
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
            "krita_batch_draw / krita_stroke -> krita_create_keyframe(frame=1) -> krita_set_current_frame(frame=1) -> draw -> "
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

        # Only expose tools relevant to drawing/animation tasks. This keeps the
        # Groq `tools` payload small enough to stay under the TPM rate limit
        # across the many requests a two-frame animation requires.
        tool_subset = {
            "krita_new_canvas", "krita_set_color", "krita_set_brush",
            "krita_stroke", "krita_fill", "krita_draw_shape", "krita_get_canvas",
            "krita_select_paint_layer", "krita_create_frame", "krita_select_frame",
            "krita_get_current_frame", "krita_set_current_frame",
            "krita_create_keyframe", "krita_delete_keyframe",
            "krita_list_keyframes", "krita_has_keyframe",
        }

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
                            "points": {"type": "array", "description": "List of [x,y] pairs", "items": {"type": "array", "items": {"type": "integer"}}},
                            "pressure": {"type": "number", "description": "Optional pressure for stroke", "default": 1.0}
                        },
                        "required": ["points"]
                    }
                }
            },
            "required": ["strokes"]
        }

        tools_for_model.append({
            "type": "function",
            "function": {
                "name": "krita_batch_draw",
                "description": "Batch drawing: set color, brush, and multiple strokes in one call.",
                "parameters": batch_schema,
            },
        })

        print("Groq tools available (passed in `tools`):")
        for tf in tools_for_model:
            fn = tf.get("function", {})
            print("  -", fn.get("name"))
        print("Model name:", config.groq_model)

        import json

        # Classify the request so we can gate the final response on actual tool use.
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
        follow_ups = 0
        for step in range(max_steps):
            print("Sending request to Groq (step", step + 1, ")...")
            import time
            t0 = time.time()
            try:
                resp = agent.call_model(messages, tools_for_model)
            except Exception as e:
                t1 = time.time()
                model_duration = t1 - t0
                print(f"Groq request: {model_duration:.3f}s")
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
            except Exception:
                print("Malformed model response:", resp)
                return

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
                import time
                mcp_start = time.time()
                for tc in tool_calls:
                    tc_id = getattr(tc, "id", None)
                    fn = getattr(tc, "function", None)
                    fn_name = getattr(fn, "name", None) if fn else None
                    fn_args = getattr(fn, "arguments", None) if fn else None

                    print("Groq tool call:")
                    print("  id:", tc_id)
                    print("  name:", fn_name)

                    # Special handling: agent-side batch wrapper
                    if fn_name == "krita_batch_draw":
                        # fn_args expected to be an object with color, brush_size, strokes
                        args_obj = fn_args
                        try:
                            if isinstance(fn_args, str):
                                args_obj = json.loads(fn_args)
                        except Exception:
                            args_obj = fn_args

                        batch_results = []
                        # set color
                        color = args_obj.get("color") if isinstance(args_obj, dict) else None
                        if color:
                            try:
                                r = mcp.call_tool("krita_set_color", {"color": color}, timeout=60)
                                batch_results.append({"action": "krita_set_color", "result": r})
                                print("MCP →", r)
                            except Exception as e:
                                print("MCP call failed:", e)
                                traceback.print_exc()
                                return

                        # set brush size if provided
                        brush_size = args_obj.get("brush_size") if isinstance(args_obj, dict) else None
                        if brush_size is not None:
                            try:
                                r = mcp.call_tool("krita_set_brush", {"size": brush_size}, timeout=60)
                                batch_results.append({"action": "krita_set_brush", "result": r})
                                print("MCP →", r)
                            except Exception as e:
                                print("MCP call failed:", e)
                                traceback.print_exc()
                                return

                        # strokes
                        strokes = args_obj.get("strokes") if isinstance(args_obj, dict) else None
                        if strokes:
                            for s in strokes:
                                points = s.get("points")
                                pressure = s.get("pressure", 1.0)
                                try:
                                    r = mcp.call_tool("krita_stroke", {"points": points, "pressure": pressure}, timeout=60)
                                    batch_results.append({"action": "krita_stroke", "result": r})
                                    if "error" not in str(r).lower():
                                        executed_drawing = True
                                except Exception as e:
                                    print("MCP call failed:", e)
                                    traceback.print_exc()
                                    return

                        # Append a single tool result summarizing batch actions
                        messages.append({"role": "tool", "tool_call_id": tc_id, "content": str(batch_results)})
                        # mark executed drawing if any strokes present
                        if strokes:
                            executed_drawing = True
                            last_draw_step = step
                        continue

                    # Parse arguments if they're a JSON string
                    args = fn_args
                    try:
                        if isinstance(fn_args, str):
                            args = json.loads(fn_args)
                    except Exception:
                        pass

                    try:
                        res = mcp.call_tool(fn_name, args or {}, timeout=60)
                        print("MCP →", res)
                    except Exception as e:
                        print("MCP call failed:", e)
                        traceback.print_exc()
                        return

                    # Only count operations as performed if the tool actually succeeded
                    res_ok = "error" not in str(res).lower()

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
                    followup = (
                        "You returned a natural-language response, but the user's animation request has not been completed: "
                        "no animation/frame tools were actually executed" + (" and no drawing was performed" if wants_drawing and not executed_drawing else "") + ". "
                        "You MUST use the Krita MCP tools to perform the work: "
                        "`krita_select_paint_layer`, `krita_create_keyframe(frame=...)`, `krita_set_current_frame(frame=...)`, "
                        "verify with `krita_get_current_frame`/`krita_list_keyframes`, and draw with `krita_batch_draw`/`krita_stroke`/`krita_draw_shape`. "
                        "If the frames already exist but the last-created frame has nothing drawn on it, switch to it with "
                        "`krita_set_current_frame(frame=N)` and draw there before summarizing. "
                        "Only after the tools have succeeded, summarize what was created."
                    )
                else:
                    followup = (
                        "You returned a natural-language response but the user's drawing request has not been completed because no drawing tool was used. "
                        "Please invoke a drawing tool call (krita_batch_draw, krita_stroke or krita_draw_shape) to perform the actual drawing."
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

    except Exception as e:
        print("Fatal error:", e)
        traceback.print_exc()


if __name__ == "__main__":
    main()
