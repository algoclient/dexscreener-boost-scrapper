import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Scan Configuration
SCAN_INTERVAL = 10  # seconds between scans
BOOST_AMOUNTS = [500, 100]
TARGET_CHAIN = "solana"

# DexScreener API URLs
BOOST_API_URL = "https://api.dexscreener.com/token-boosts/latest/v1"
TOKEN_API_URL = "https://api.dexscreener.com/latest/dex"
SEARCH_API_URL = "https://api.dexscreener.com/latest/dex/search"

# Cache Settings
MAX_CACHED_BOOSTS = 500
CACHE_CLEANUP_INTERVAL = 10  # scans