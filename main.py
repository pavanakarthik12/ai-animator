import sys
import traceback
from config import config
from mcp_client import KritaMCPClient
from groq_agent import GroqAgent


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
            "You are controlling Krita through MCP. Complete the user's requested drawing using the available Krita tools. "
            "Changing a setting such as color or brush is only an intermediate step. Continue making tool calls until the requested artwork has actually been drawn. "
            "After each tool result, reassess whether the user's request is complete. Never stop merely because an intermediate tool succeeded.\n"
            f"Available tools: {', '.join(tool_summaries)}.\n"
            "If the user requests a multi-stroke drawing, prefer returning a single `krita_batch_draw` tool_call containing the color, brush_size, and an array of strokes (each with points). This lets the agent send many strokes in one MCP batch.\n"
            "For simple frame-by-frame animation tasks, you may use these animation helpers: `krita_create_frame(name)`, `krita_select_frame(index)`, `krita_get_current_frame()`, `krita_enable_onion(enabled)`, and `krita_inspect_previous_frame(downscale)`.\n"
            "Typical animation sequence: call `krita_create_frame` then `krita_select_frame` to work on frame N, draw using `krita_batch_draw`, then `krita_create_frame`/`krita_select_frame` for next frame, enable onion skin with `krita_enable_onion(true)`, inspect previous frame with `krita_inspect_previous_frame`, then draw on the new frame.\n"
            "When invoking a tool, output ONLY a JSON object with keys 'tool' (string) and 'args' (object).\n"
            "When finished, return a plain natural-language message (not JSON).\n"
            "Example tool call: {\"tool\": \"krita_batch_draw\", \"args\": {\"color\": \"#ff0000\", \"brush_size\": 6, \"strokes\": [{\"points\": [[100,100],[120,120]]}]}}"
        )

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ]

        # Convert MCP tools into Groq `tools` function definitions so the model
        # can call them with structured inputs.
        tools_for_model = []
        for t in tools_detailed:
            name = t.get("name")
            desc = t.get("description") or f"MCP tool {name}"
            params_schema = t.get("input_schema") or {"type": "object", "properties": {}}
            func = {"name": name, "description": desc, "parameters": params_schema}
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

        import json

        max_steps = 20
        executed_drawing = False
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
                                except Exception as e:
                                    print("MCP call failed:", e)
                                    traceback.print_exc()
                                    return

                        # Append a single tool result summarizing batch actions
                        messages.append({"role": "tool", "tool_call_id": tc_id, "content": str(batch_results)})
                        # mark executed drawing if any strokes present
                        if strokes:
                            executed_drawing = True
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

                    # Mark drawing executed if applicable
                    if fn_name in ("krita_draw_shape", "krita_stroke", "krita_fill"):
                        executed_drawing = True

                    # Append the tool result with matching tool_call_id
                    messages.append({"role": "tool", "tool_call_id": tc_id, "content": str(res)})

                mcp_end = time.time()
                mcp_duration = mcp_end - mcp_start
                print(f"MCP execution: {mcp_duration:.3f}s")

                # After executing all tool calls, continue loop so model can respond
                continue

            # No tool calls — treat as final natural-language reply
            # If the user requested a drawing but no drawing tools were executed, prompt the model to continue (no fallback drawing)
            user_requested_draw = any(k in prompt.lower() for k in ("draw", "circle", "ellipse", "paint", "stroke"))
            if user_requested_draw and not executed_drawing:
                print("Model returned final text but no drawing performed. Prompting model to finish the drawing.")
                followup = (
                    "You returned a natural-language response but the user's drawing request has not been completed because no drawing tool was used. "
                    "Please respond with a JSON tool call to perform the actual drawing (use krita_draw_shape or krita_stroke)."
                )
                messages.append({"role": "user", "content": followup})
                continue

            print("Final assistant response:")
            if isinstance(model_text, dict):
                print(json.dumps(model_text))
            else:
                print(model_text)
            break

    except Exception as e:
        print("Fatal error:", e)
        traceback.print_exc()


if __name__ == "__main__":
    main()
