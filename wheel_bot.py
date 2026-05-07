import os
import time
import json
from datetime import datetime
from alpaca_trade_api.rest import REST

# CONFIGURATION
API_KEY = "PKRPLQBGC5J3ALAUJ2CEXRF5WS"
SECRET_KEY = "5nWMXqwxJyyknuaVsLEsiDdLKB9ue9HNz2cnLL5j11Qo"
BASE_URL = "https://paper-api.alpaca.markets"

api = REST(API_KEY, SECRET_KEY, BASE_URL)
SYMBOL = "TSLA"
SETTINGS_FILE = "settings.json"
PENDING_TRADES_FILE = "pending_trades.json"

def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [THE-WHEEL] {message}\n"
    log_file = r"C:\Users\chase\Documents\trading-bot\bot_log.txt"
    for _ in range(5):
        try:
            with open(log_file, "a") as f:
                f.write(log_entry)
            break
        except PermissionError:
            time.sleep(1)
    print(log_entry.strip())

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

def run_wheel_logic():
    try:
        # Check if we own the stock
        position = api.get_position(SYMBOL)
        qty = int(position.qty)
        log_message(f"Owned: {qty} shares of {SYMBOL}. Strategy: Selling Covered Calls (Income).")
        
        # Calculate a conservative Strike Price (5% above current)
        target_strike = float(position.current_price) * 1.05
        log_message(f"Optimal Strike for Friday: ${target_strike:.2f}")
        
    except Exception as e:
        if "position does not exist" in str(e):
            log_message(f"No {SYMBOL} shares held. Strategy: Selling Cash-Secured Puts (Entry).")
            # Get latest price to find entry point
            last_quote = api.get_latest_quote(SYMBOL)
            entry_price = float(last_quote.ask) * 0.97
            log_message(f"Target Entry (Sell Put): ${entry_price:.2f}")
            
            mode = get_automation_mode()
            if mode == "Full Auto":
                try:
                    api.submit_order(symbol=SYMBOL, qty=10, side='buy', type='market', time_in_force='gtc')
                    log_message(f"ORDER SENT: Entry initiated for {SYMBOL} (10 shares).")
                except Exception as order_err:
                    log_message(f"ORDER FAILED: {order_err}")
            else:
                log_message(f"STRATEGY TRIGGER: Entry for {SYMBOL}. Queuing for Manual Approval.")
                queue_trade("The Wheel", SYMBOL, 10, "buy", f"Entry logic: No position in {SYMBOL}")
        else:
            log_message(f"Error: {e}")

if __name__ == "__main__":
    log_message("Wheel strategy active. Scanning for premiums...")
    while True:
        run_wheel_logic()
        time.sleep(600) # Check every 10 minutes
