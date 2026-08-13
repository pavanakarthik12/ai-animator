# Groq → Krita MCP Agent

This project connects a Groq model to the Krita MCP server to let the model control Krita directly via MCP tools.

Quick start:

1. Copy your Groq API key to `.env` as `GROQ_API_KEY` and set `GROQ_MODEL` and `KRITA_MCP_SERVER`.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run:

```bash
python main.py
```

Type a request like: `Draw a simple circle in the center of the canvas.`

The agent will ask Groq for a tool call and execute the discovered MCP tool.
