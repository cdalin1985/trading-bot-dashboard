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
SETTINGS_FILE = "settings.json"
PENDING_TRADES_FILE = "pending_trades.json"

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

def get_full_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"mode": "Full Auto", "whale_symbols": "NVDA,AAPL,MSFT,GOOGL"}

def scan_congressional_trades():
    url = "https://www.capitoltrades.com/trades"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        settings = get_full_settings()
        watch_list = settings.get("whale_symbols", "NVDA,AAPL,MSFT,GOOGL").upper().split(",")
        watch_list = [s.strip() for s in watch_list if s.strip()]

        log_message(f"Scanning Capitol Trades (Watch: {', '.join(watch_list)})")
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return None
        
        tickers = re.findall(r'([A-Z]+):US', response.text)
        valid_tickers = [t for t in tickers if t in watch_list]
        
        if valid_tickers:
            return valid_tickers[0]
    except Exception as e:
        log_message(f"Scrape Error: {e}")
    return None

def queue_trade(bot_name, symbol, qty, side, reason):
    pending = []
    if os.path.exists(PENDING_TRADES_FILE):
        try:
            with open(PENDING_TRADES_FILE, "r") as f:
                pending = json.load(f)
        except: pass
    if any(t['symbol'] == symbol and t['bot'] == bot_name for t in pending):
        return
    pending.append({"bot": bot_name, "symbol": symbol, "qty": qty, "side": side, "reason": reason, "timestamp": datetime.now().isoformat()})
    with open(PENDING_TRADES_FILE, "w") as f:
        json.dump(pending, f)

def get_last_ticker():
    if os.path.exists(LAST_TICKER_FILE):
        with open(LAST_TICKER_FILE, "r") as f:
            return f.read().strip()
    return ""

def set_last_ticker(ticker):
    with open(LAST_TICKER_FILE, "w") as f:
        f.write(ticker)

if __name__ == "__main__":
    log_message("Whale/Politician Tracker ONLINE.")
    while True:
        current_ticker = scan_congressional_trades()
        last_ticker = get_last_ticker()
        
        if current_ticker and current_ticker != last_ticker:
            settings = get_full_settings()
            mode = settings.get("mode", "Full Auto")
            
            if mode == "Full Auto":
                log_message(f"AUTO-BUY: {current_ticker}.")
                try:
                    api.submit_order(symbol=current_ticker, qty=1, side='buy', type='market', time_in_force='gtc')
                    set_last_ticker(current_ticker)
                except Exception as e:
                    log_message(f"Order Failed: {e}")
            else:
                log_message(f"QUEUED: {current_ticker}.")
                queue_trade("Politician Tracker", current_ticker, 1, "buy", "Whale Trade Disclosure")
                set_last_ticker(current_ticker)
        else:
            log_message("No new trades found.")
        time.sleep(900)
