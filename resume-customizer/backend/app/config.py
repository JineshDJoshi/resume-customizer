"""Central configuration, read once from environment variables / .env."""
import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self) -> None:
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.llm_timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "90"))
        self.llm_retries = int(os.getenv("LLM_MAX_RETRIES", "3"))
        self.max_upload_bytes = int(os.getenv("MAX_UPLOAD_MB", "5")) * 1024 * 1024
        self.cors_origins = [
            o.strip()
            for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
            if o.strip()
        ]
        self.rate_limit_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))


settings = Settings()
