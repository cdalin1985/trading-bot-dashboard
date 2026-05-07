import os
import time
import requests
import re
import json
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

SETTINGS_FILE = "settings.json"
PENDING_TRADES_FILE = "pending_trades.json"

def get_automation_mode():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f).get("mode", "Full Auto")
        except:
            return "Full Auto"
    return "Full Auto"

def queue_trade(bot_name, symbol, qty, side, reason):
    pending = []
    if os.path.exists(PENDING_TRADES_FILE):
        try:
            with open(PENDING_TRADES_FILE, "r") as f:
                pending = json.load(f)
        except:
            pass
    
    # Check if this exact trade is already queued to avoid spam
    if any(t['symbol'] == symbol and t['bot'] == bot_name for t in pending):
        return

    pending.append({
        "bot": bot_name,
        "symbol": symbol,
        "qty": qty,
        "side": side,
        "reason": reason,
        "timestamp": datetime.now().isoformat()
    })
    with open(PENDING_TRADES_FILE, "w") as f:
        json.dump(pending, f)

if __name__ == "__main__":
    log_message("Whale/Politician Tracker ONLINE. Monitoring Capitol Trades.")
    
    while True:
        current_ticker = scan_congressional_trades()
        last_ticker = get_last_ticker()
        
        if current_ticker and current_ticker != last_ticker:
            mode = get_automation_mode()
            reason = f"New whale disclosure for {current_ticker}"
            
            if mode == "Full Auto":
                log_message(f"NEW WHALE TRADE DETECTED: {current_ticker}. Executing Market Buy (AUTO).")
                try:
                    api.submit_order(symbol=current_ticker, qty=1, side='buy', type='market', time_in_force='gtc')
                    log_message(f"ORDER SUCCESS: Bought 1 share of {current_ticker}.")
                    set_last_ticker(current_ticker)
                except Exception as e:
                    log_message(f"ORDER FAILED: {e}")
            else:
                log_message(f"STRATEGY TRIGGER: {current_ticker}. Queuing for Manual Approval.")
                queue_trade("Politician Tracker", current_ticker, 1, "buy", reason)
                set_last_ticker(current_ticker)
        else:
            log_message("No new whale trades since last scan.")
            
        time.sleep(900)
