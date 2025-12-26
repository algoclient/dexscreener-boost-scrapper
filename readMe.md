# DexScreener Boost Scrapper

A lightweight Python bot that scrapes DexScreener for trading signals and sends them to a Telegram chat.

---

## Overview

- **Language:** Python 3.11+
- **Dependencies:** Listed in `requirements.txt`
- **Configuration:** Environment variables stored in a `.env` file
- **Execution:** Run with `python bot.py`

---

## Prerequisites

1. **Python 3.11+**  
   Install from the official site: https://www.python.org/downloads/  
   Verify installation:

   ```bash
   python --version   # Should output: Python 3.11.x
   ```

2. **pip** (Python package installer)  
   Usually comes bundled with Python. Check:

   ```bash
   pip --version
   ```

3. **Git** (optional, for cloning the repository)  
   https://git-scm.com/downloads

---

## Installation

```bash
# 1. Clone the repo (or download the ZIP)
git clone https://github.com/devpetrate/dexscreener-boost-scrapper.git
cd dexscreener-boost-scrapper

# 2. (Optional but recommended) Create a virtual environment
python -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Configuration

Create a `.env` file in the project root with the following keys:

```dotenv
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
```

- **`TELEGRAM_BOT_TOKEN`** – The token you receive from @BotFather.
- **`TELEGRAM_CHAT_ID`** – The numeric ID of the chat/group where messages will be posted.

> **Tip:** Use `python -m telegram_bot_finder` (if installed) to retrieve the chat ID.

---

## Running the Bot

```bash
# Ensure you are inside the project directory and the virtual environment is active
python bot.py
```

The bot will start, scrape DexScreener, and forward any detected boosts to the specified Telegram chat.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError` | Make sure the virtual environment is activated and `pip install -r requirements.txt` ran successfully. |
| No messages in Telegram | Verify the `.env` file contains correct `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. |
| `ConnectionError` | Check your internet connection or proxy settings. |

---

## License

MIT © 2025 Your Name

---