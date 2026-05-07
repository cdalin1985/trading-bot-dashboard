import os
import time
import requests
import re
from datetime import datetime
from alpaca_trade_api.rest import REST

# CONFIGURATION
API_KEY = "PKRPLQBGC5J3ALAUJ2CEXRF5WS"
SECRET_KEY = "5nWMXqwxJyyknuaVsLEsiDdLKB9ue9HNz2cnLL5j11Qo"
BASE_URL = "https://paper-api.alpaca.markets"

api = REST(API_KEY, SECRET_KEY, BASE_URL)
LAST_TICKER_FILE = "last_whale_ticker.txt"

def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [POLITICIAN-TRACKER] {message}\n"
    log_file = r"C:\Users\chase\Documents\trading-bot\bot_log.txt"
    # Thread-safe-ish appending for multiple bots
    for _ in range(5):
        try:
            with open(log_file, "a") as f:
                f.write(log_entry)
            break
        except PermissionError:
            time.sleep(1)
    print(log_entry.strip())

def scan_congressional_trades():
    """
    Scrapes real-time ticker data from Capitol Trades.
    """
    url = "https://www.capitoltrades.com/trades"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        log_message("Scraping latest Capitol Trades data...")
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            log_message(f"Scrape failed (Status: {response.status_code})")
            return None
        
        # Regex to find tickers like 'PLTR:US'
        tickers = re.findall(r'([A-Z]+):US', response.text)
        valid_tickers = [t for t in tickers if t not in ["USD", "US", "GT"]]
        
        if valid_tickers:
            return valid_tickers[0] # Return the most recent one
            
    except Exception as e:
        log_message(f"Scrape Error: {e}")
        
    return None

def get_last_ticker():
    if os.path.exists(LAST_TICKER_FILE):
        with open(LAST_TICKER_FILE, "r") as f:
            return f.read().strip()
    return ""

def set_last_ticker(ticker):
    with open(LAST_TICKER_FILE, "w") as f:
        f.write(ticker)

if __name__ == "__main__":
    log_message("Whale/Politician Tracker ONLINE. Monitoring Capitol Trades.")
    
    while True:
        current_ticker = scan_congressional_trades()
        last_ticker = get_last_ticker()
        
        if current_ticker and current_ticker != last_ticker:
            log_message(f"NEW WHALE TRADE DETECTED: {current_ticker}. Executing Market Buy.")
            try:
                # Execute Paper Trade
                api.submit_order(
                    symbol=current_ticker,
                    qty=1,
                    side='buy',
                    type='market',
                    time_in_force='gtc'
                )
                log_message(f"ORDER SUCCESS: Bought 1 share of {current_ticker}.")
                set_last_ticker(current_ticker)
            except Exception as e:
                log_message(f"ORDER FAILED for {current_ticker}: {e}")
                # Don't set last_ticker so we try again next cycle
        else:
            log_message("No new whale trades since last scan.")
            
        time.sleep(900) # Scan every 15 minutes to avoid being blocked
