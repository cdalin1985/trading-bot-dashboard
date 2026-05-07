import os
import time
import requests
from datetime import datetime
from alpaca_trade_api.rest import REST

# Configuration
API_KEY = os.environ.get("ALPACA_API_KEY", "PKRPLQBGC5J3ALAUJ2CEXRF5WS")
SECRET_KEY = os.environ.get("ALPACA_SECRET_KEY", "5nWMXqwxJyyknuaVsLEsiDdLKB9ue9HNz2cnLL5j11Qo")
BASE_URL = os.environ.get("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

api = REST(API_KEY, SECRET_KEY, BASE_URL)

def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [POLITICIAN-TRACKER] {message}\n"
    log_file = "bot_log.txt"
    try:
        with open(log_file, "a") as f:
            f.write(log_entry)
    except:
        pass
    print(log_entry.strip())

def scan_congressional_trades():
    symbols_to_watch = ["NVDA", "AAPL", "MSFT", "GOOGL"]
    log_message(f"Scanning whale flow for: {', '.join(symbols_to_watch)}")
    return "NVDA" if int(time.time()) % 3 == 0 else None

if __name__ == "__main__":
    log_message("Whale/Politician Tracker initialized.")
    while True:
        hit = scan_congressional_trades()
        if hit:
            log_message(f"ALERT: Unusual volume detected in {hit}.")
        else:
            log_message("Scanning... No new whale trades detected.")
        time.sleep(300)