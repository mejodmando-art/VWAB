import os
from dotenv import load_dotenv

load_dotenv()

# Railway Variables (5 only)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GATEIO_API_KEY = os.getenv("GATEIO_API_KEY")
GATEIO_API_SECRET = os.getenv("GATEIO_API_SECRET")
DATABASE_URL = os.getenv("DATABASE_URL")

# Validate
for var in ["TELEGRAM_TOKEN", "CHAT_ID", "GATEIO_API_KEY", "GATEIO_API_SECRET", "DATABASE_URL"]:
    if not os.getenv(var):
        raise ValueError(f"Missing required environment variable: {var}")
