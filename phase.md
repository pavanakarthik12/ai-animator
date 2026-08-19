I need you to fix the EXISTING Groq + MCP + Krita project.

DO NOT redesign the project.
DO NOT change the architecture.
DO NOT add image generation.
DO NOT invent tools.
DO NOT hallucinate Krita APIs.
DO NOT implement fake animation.
DO NOT create external image files.
DO NOT give me documentation.

The existing drawing functionality already works.

CURRENT WORKING PIPELINE:

User
↓
Groq
↓
MCP client
↓
krita-mcp server
↓
Krita MCP Bridge
↓
Krita
↓
AI can already draw actual strokes on the Krita canvas.

That part MUST NOT be broken.

==================================================
CURRENT PROBLEM
==================================================

When I send Groq:

"create two frames of a stick man waving"

the program sends the request to Groq, but Groq returns no useful tool call and the program does not create frames or draw anything.

I need you to FIX THIS SPECIFIC PROBLEM.

The final goal of this task is:

FRAME 0:
draw stick man with arm down

FRAME 1:
draw the same stick man with arm raised

Both must be REAL animation frames/keyframes inside Krita.

==================================================
FIRST: INSPECT THE EXISTING CODE
==================================================

Before changing anything, inspect:

1. The Groq agent code.
2. The MCP client code.
3. The discovered MCP tool list.
4. The Krita MCP server.
5. The Krita Python plugin/bridge.
6. The existing working drawing implementation.

Find exactly where animation/frame functionality currently fails.

DO NOT assume that a tool exists.

DO NOT assume that a Krita API exists.

DO NOT invent:

create_frame()
set_frame()
create_keyframe()
etc.

unless those functions/tools actually exist in the code or are implemented correctly.

==================================================
CRITICAL REQUIREMENT: MCP TOOL DISCOVERY
==================================================

Print the COMPLETE list of tools actually discovered from the running MCP server.

For every tool print:

- name
- description
- input schema

I specifically need to know whether there are currently REAL animation-related tools.

For example, determine whether tools for:

- current frame
- animation frame
- keyframe creation
- frame selection
- keyframe listing

actually exist.

If they do not exist, say so in the terminal output.

DO NOT pretend they exist.

==================================================
CRITICAL REQUIREMENT: GROQ RESPONSE
==================================================

When the user sends:

"create two frames of a stick man waving"

log the COMPLETE structured response received from Groq, excluding the API key.

I need to know whether:

1. Groq returned tool_calls.
2. Groq returned normal text.
3. Groq returned an empty response.
4. Groq returned an invalid tool call.

Do NOT convert an empty response into a fake action.

Do NOT invent an action.

Do NOT silently continue.

==================================================
IF GROQ RETURNS NO TOOL CALL
==================================================

If Groq returns:

tool_calls = None

or:

tool_calls = []

then DO NOT hallucinate that the AI requested an animation operation.

Instead, inspect why.

Check:

1. Are the animation tools actually included in the Groq `tools` parameter?
2. Are their schemas valid?
3. Are the tool names valid?
4. Is the current Groq model capable of tool calling?
5. Is the message structure valid?
6. Is the system prompt correctly telling the model to use tools?
7. Is the MCP tool definition being converted correctly into Groq's function/tool schema?

Fix the actual problem.

==================================================
DO NOT USE FALLBACK ACTIONS
==================================================

Remove/disable any fallback such as:

"If Groq doesn't return a tool call, manually create a frame."

Do NOT do that.

The goal is to make the AI correctly call the real tools.

Never do:

if "stick man" in prompt:
    create_frame()

Never hard-code animation behavior based on the user's text.

==================================================
ANIMATION MUST BE REAL
==================================================

A frame means a REAL Krita animation keyframe.

Do NOT simulate frames using:

- Python lists
- separate layers
- separate canvases
- external files
- PNG/JPEG files
- clearing and redrawing the same frame
- fake frame counters

The result must exist in Krita's actual animation timeline.

==================================================
IF ANIMATION TOOLS ARE MISSING
==================================================

If the existing Krita MCP plugin does not expose the required animation operations, implement ONLY the minimum required functionality in the existing Krita plugin.

Required capabilities:

1. Get current animation frame.
2. Set current animation frame.
3. Create a real animation keyframe.
4. Verify whether a keyframe exists.

Use Krita's actual internal document/layer/keyframe functionality.

Inspect the installed Krita API and the existing plugin code before implementing it.

Do NOT guess API method names.

==================================================
FIRST TEST — NO AI DRAWING YET
==================================================

Before testing the stick man, make this work:

User:

"Create two animation frames."

The AI must use the actual animation tools.

Expected terminal behavior:

Groq → animation tool
MCP → success

Groq → animation tool
MCP → success

Then verify:

Current frame: 0
Keyframes: [0, 1]

If this does not work, STOP THERE and fix it.

Do not proceed to drawing.

==================================================
SECOND TEST
==================================================

After the two real frames exist, test:

"Draw a red circle on the left side of frame 0."

Expected:

Groq → select frame 0
MCP → success

Groq → drawing tool
MCP → success

Then:

"Draw a red circle on the right side of frame 1."

Expected:

Groq → select frame 1
MCP → success

Groq → drawing tool
MCP → success

When I click frame 0 in Krita:

LEFT circle must appear.

When I click frame 1:

RIGHT circle must appear.

==================================================
ONLY AFTER THAT
==================================================

Test:

"Create two frames of a stick man waving."

Expected:

FRAME 0:
stick man with arm down

FRAME 1:
same stick man with arm raised

Both drawings must exist as separate Krita animation frames.

==================================================
NO IMAGE GENERATION
==================================================

Absolutely no:

- image generation
- image models
- generated images
- PNG/JPEG frames
- image importing
- external animation generation

The AI must literally draw using Krita MCP drawing tools.

==================================================
DO NOT CHANGE WORKING DRAWING
==================================================

The existing drawing pipeline is already working.

Do not rewrite:

- Groq authentication
- working drawing tools
- MCP transport
- Krita MCP Bridge
- batch stroke functionality

unless the change is directly required to fix animation tool calling.

==================================================
IMPORTANT
==================================================

Do not give me a long explanation.

Do not write documentation.

Do not tell me what "could" be wrong.

Inspect the actual code, identify the exact failure, fix it, and test it.

At the end, report ONLY:

1. What was actually broken.
2. What files were changed.
3. What was fixed.
4. The exact test result.

The final success condition is:

REAL Krita animation timeline:

FRAME 0 | FRAME 1

with different drawings actually present on each frame.

Do not claim success unless you can verify that the drawings exist on separate Krita keyframes