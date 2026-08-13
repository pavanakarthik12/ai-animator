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
            "When invoking a tool, output ONLY a JSON object with keys 'tool' (string) and 'args' (object).\n"
            "When finished, return a plain natural-language message (not JSON).\n"
            "Example tool call: {\"tool\": \"krita_draw_shape\", \"args\": {\"shape\": \"ellipse\", \"x\": 400, \"y\": 300, \"width\": 200, \"height\": 200, \"fill\": true}}"
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

        import json

        max_steps = 20
        executed_drawing = False
        for step in range(max_steps):
            print("Sending request to Groq (step", step + 1, ")...")
            try:
                resp = agent.call_model(messages, tools_for_model)
            except Exception as e:
                print("Fatal error calling Groq:", e)
                return

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
                for tc in tool_calls:
                    tc_id = getattr(tc, "id", None)
                    fn = getattr(tc, "function", None)
                    fn_name = getattr(fn, "name", None) if fn else None
                    fn_args = getattr(fn, "arguments", None) if fn else None

                    print("Groq tool call:")
                    print("  id:", tc_id)
                    print("  name:", fn_name)

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
