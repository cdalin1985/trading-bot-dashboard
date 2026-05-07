import os
import time
from datetime import datetime
from alpaca_trade_api.rest import REST

# Configuration
API_KEY = os.environ.get("ALPACA_API_KEY", "PKRPLQBGC5J3ALAUJ2CEXRF5WS")
SECRET_KEY = os.environ.get("ALPACA_SECRET_KEY", "5nWMXqwxJyyknuaVsLEsiDdLKB9ue9HNz2cnLL5j11Qo")
BASE_URL = os.environ.get("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

api = REST(API_KEY, SECRET_KEY, BASE_URL)
SYMBOL = "TSLA"

def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [THE-WHEEL] {message}\n"
    log_file = "bot_log.txt"
    try:
        with open(log_file, "a") as f:
            f.write(log_entry)
    except:
        pass
    print(log_entry.strip())

def run_wheel_logic():
    try:
        position = api.get_position(SYMBOL)
        qty = int(position.qty)
        log_message(f"Owned: {qty} shares of {SYMBOL}.")
        target_strike = float(position.current_price) * 1.05
        log_message(f"Optimal Strike: ${target_strike:.2f}")
    except Exception as e:
        if "position does not exist" in str(e):
            log_message(f"No {SYMBOL} shares held. Targeting entry.")
            last_quote = api.get_latest_quote(SYMBOL)
            entry_price = float(last_quote.ask) * 0.97
            log_message(f"Target Entry: ${entry_price:.2f}")
        else:
            log_message(f"Error: {e}")

if __name__ == "__main__":
    log_message("Wheel strategy active.")
    while True:
        run_wheel_logic()
        time.sleep(600)