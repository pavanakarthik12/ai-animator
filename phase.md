The existing drawing system works, but the new animation-frame system is NOT being invoked.

Current test:

User:
create two frames of a stick man waving

Output:

Sending request to Groq (step 1)...
Groq request: 2.642s
Model response:
Final assistant response:

There are NO MCP tool calls.

This means Groq is returning a normal final response instead of calling the animation tools.

FIX THIS.

==================================================
GOAL
==================================================

For:

"create two frames of a stick man waving"

Groq MUST use the actual Krita animation MCP tools.

The expected tool sequence is conceptually:

create/select frame 0
        ↓
draw stick man with arm down
        ↓
create/select frame 1
        ↓
draw stick man with arm raised
        ↓
final response

Do not allow Groq to simply respond with text saying that it created the frames.

The frames must actually be created inside Krita.

==================================================
1. INSPECT MCP TOOL DISCOVERY
==================================================

Inspect the MCP client implementation.

Print ALL tools discovered from the Krita MCP server, including:

- tool name
- description
- input schema

I need to see whether the animation tools are actually being discovered.

For example:

Discovered MCP tools:

krita_set_color
krita_stroke
krita_draw_shape
...
krita_create_keyframe
krita_set_current_frame
...

If the animation tools are NOT in the discovered list, fix the MCP server/plugin first.

Do not assume they exist.

==================================================
2. MAKE SURE ANIMATION TOOLS ARE SENT TO GROQ
==================================================

The discovered MCP tools must be converted into Groq-compatible function/tool definitions.

The Groq request must contain the animation tools in its `tools` parameter.

Do NOT only expose the drawing tools.

The model must receive the actual animation tools.

Verify this by logging:

Groq tools available:
- ...
- create_keyframe
- set_current_frame
- ...
- krita_stroke
...

Use the actual names returned by MCP.

Do NOT invent names.

==================================================
3. FORCE TOOL USE WHEN THE USER REQUESTS ANIMATION
==================================================

Update the system prompt.

Use instructions similar to:

"You are controlling Krita through MCP.

When the user asks you to create, modify, or animate artwork inside Krita, you MUST perform the requested operation using the available Krita MCP tools.

Never claim that a frame, keyframe, or drawing was created unless the corresponding MCP tool was actually executed successfully.

For animation requests, you MUST use the animation/keyframe tools and drawing tools.

A normal text response is NOT sufficient."

Do NOT force a specific tool for every request.

The model should choose the appropriate available tool.

==================================================
4. TOOL-CALLING MODE
==================================================

Inspect the Groq request.

If supported by the current Groq API/model, configure tool calling correctly.

The request should effectively contain:

tools=[...]

and allow the model to make tool calls.

Do not parse tool calls only from normal text.

Use the actual structured tool-call field returned by the Groq SDK.

For example, inspect:

response.choices[0].message.tool_calls

If `tool_calls` is empty, log that clearly.

==================================================
5. DO NOT ACCEPT A FINAL RESPONSE TOO EARLY
==================================================

Current behavior:

Groq returns:

Final assistant response

and the program stops.

For an animation request this is wrong.

Before accepting a final response, determine whether the requested operation has actually been performed.

For:

"create two frames of a stick man waving"

the agent should not finish until:

- frame 0 exists
- drawing exists on frame 0
- frame 1 exists
- drawing exists on frame 1

If Groq returns a final text response before doing the work, send a follow-up message telling it that the requested Krita operation has not been completed and it must use the available tools.

Do not fake completion.

==================================================
6. DO NOT USE FALLBACK HARDCODED DRAWING
==================================================

Do NOT hard-code:

if "stick man" in prompt:
    ...

Do not create fake frames in Python.

The AI must decide what tools to use.

==================================================
7. VERIFY ACTUAL FRAME STATE
==================================================

The animation tools must eventually allow us to verify:

Current frame: 0
Keyframes: [0]

then:

Current frame: 1
Keyframes: [0, 1]

The drawing must happen after selecting the appropriate frame.

Do not treat changing a variable in Python as changing Krita's animation frame.

==================================================
8. FIRST DEBUG TEST
==================================================

Before testing the stick man, run a simpler request:

"Create two animation frames."

The terminal should show something like:

Groq → animation/keyframe tool
MCP → success

Groq → animation/keyframe tool
MCP → success

Final assistant response

If Groq still returns no tool calls, print:

1. The complete list of MCP tools discovered.
2. The names of the tools passed to Groq.
3. Whether `response.choices[0].message.tool_calls` is None or empty.
4. The model name being used.

DO NOT print the API key.

==================================================
9. SECOND TEST
==================================================

After the first test works:

"Create two frames. Draw a red circle on the left in frame 0 and a red circle on the right in frame 1."

Expected:

Groq → create/select frame 0
MCP → success

Groq → drawing tool
MCP → success

Groq → create/select frame 1
MCP → success

Groq → drawing tool
MCP → success

Final response

Then verify the actual Krita timeline.

==================================================
10. NO IMAGE GENERATION
==================================================

Absolutely no:

- image generation
- PNG/JPEG generation
- external images
- generated frames
- importing images

The only drawing mechanism is:

Groq
 ↓
MCP
 ↓
Krita
 ↓
actual timeline/keyframe
 ↓
actual drawing

==================================================

Do not modify the already-working drawing functionality unnecessarily.

First diagnose why the animation MCP tools are not being passed to or selected by Groq.

Then fix it.

After the fix, show the discovered animation tools and test the two-frame circle example.