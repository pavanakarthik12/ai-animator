import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "")
    groq_vision_model: str = os.getenv("GROQ_VISION_MODEL", "qwen/qwen3.6-27b")
    krita_mcp_server: str = os.getenv("KRITA_MCP_SERVER", "")
    max_correction_passes: int = int(os.getenv("MAX_CORRECTION_PASSES", "2"))


config = Config()
