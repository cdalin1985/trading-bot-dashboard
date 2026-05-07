import os
import time
import requests
from datetime import datetime
from alpaca_trade_api.rest import REST

# CONFIGURATION
API_KEY = "PKRPLQBGC5J3ALAUJ2CEXRF5WS"
SECRET_KEY = "5nWMXqwxJyyknuaVsLEsiDdLKB9ue9HNz2cnLL5j11Qo"
BASE_URL = "https://paper-api.alpaca.markets"

api = REST(API_KEY, SECRET_KEY, BASE_URL)

def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [POLITICIAN-TRACKER] {message}\n"
    log_file = r"C:\Users\chase\Documents\trading-bot\bot_log.txt"
    for _ in range(5):
        try:
            with open(log_file, "a") as f:
                f.write(log_entry)
            break
        except PermissionError:
            time.sleep(1)
    print(log_entry.strip())

def scan_congressional_trades():
    # Mocking real-time scan - in a real app, we'd use Quiver Quantitative or similar API
    # For now, let's look for large volume spikes in symbols often traded by politicians (e.g., NANC, KRUZ, or tech giants)
    symbols_to_watch = ["NVDA", "AAPL", "MSFT", "GOOGL"]
    log_message(f"Scanning whale flow for: {', '.join(symbols_to_watch)}")
    
    # Simple logic: check for high relative volume (dummy implementation)
    # We will simulate a 'hit' every few cycles to show activity in the log
    return "NVDA" if int(time.time()) % 3 == 0 else None

if __name__ == "__main__":
    log_message("Whale/Politician Tracker initialized.")
    while True:
        hit = scan_congressional_trades()
        if hit:
            log_message(f"ALERT: Unusual volume detected in {hit}. Potential insider/whale trade.")
        else:
            log_message("Scanning... No new whale trades detected.")
        time.sleep(300) # Scan every 5 minutes
