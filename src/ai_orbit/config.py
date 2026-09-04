import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

    MAX_CONCURRENCY = 5
    REQUEST_TIMEOUT = 30
    DATA_DIR = os.path.join(os.getcwd(), "data")
    RAW_DIR = os.path.join(DATA_DIR, "raw")
    PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
    OUTPUT_DIR = os.path.join(DATA_DIR, "output")

    @classmethod
    def setup_dirs(cls):
        os.makedirs(cls.RAW_DIR, exist_ok=True)
        os.makedirs(cls.PROCESSED_DIR, exist_ok=True)
        os.makedirs(cls.OUTPUT_DIR, exist_ok=True)

Config.setup_dirs()
