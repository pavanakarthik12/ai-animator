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
    
    # Smart Batching Configuration
    max_strokes_per_batch: int = int(os.getenv("MAX_STROKES_PER_BATCH", "50"))
    max_points_per_batch: int = int(os.getenv("MAX_POINTS_PER_BATCH", "2000"))
    max_payload_bytes: int = int(os.getenv("MAX_PAYLOAD_BYTES", "102400"))
    max_batch_execution_time: int = int(os.getenv("MAX_BATCH_EXECUTION_TIME", "60"))
    batch_retry_count: int = int(os.getenv("BATCH_RETRY_COUNT", "3"))
    enable_batch_verification: bool = os.getenv("ENABLE_BATCH_VERIFICATION", "false").lower() == "true"

config = Config()
