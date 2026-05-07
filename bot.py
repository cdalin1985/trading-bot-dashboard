import os
import time
from datetime import datetime
from alpaca_trade_api.rest import REST

API_KEY = "PKRPLQBGC5J3ALAUJ2CEXRF5WS"
SECRET_KEY = "5nWMXqwxJyyknuaVsLEsiDdLKB9ue9HNz2cnLL5j11Qo"
BASE_URL = "https://paper-api.alpaca.markets"

api = REST(API_KEY, SECRET_KEY, BASE_URL)
SYMBOL = "TSLA"
STOP_LOSS_PCT = 0.05

def log_message(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [TRAILING-STOP] {message}\n"
    log_file = r"C:\Users\chase\Documents\trading-bot\bot_log.txt"
    for _ in range(5):
        try:
            with open(log_file, "a") as f:
                f.write(log_entry)
            break
        except PermissionError:
            time.sleep(1)
    print(log_entry.strip())

def run_bot():
    log_message("Bot started. Monitoring TSLA.")
    while True:
        try:
            position = api.get_position(SYMBOL)
            current_price = float(position.current_price)
            stop_price = current_price * (1 - STOP_LOSS_PCT)
            log_message(f"Price: ${current_price} | Floor: ${stop_price:.2f}")
            time.sleep(60)
        except Exception as e:
            if "position does not exist" in str(e):
                log_message("Waiting for TSLA order to fill (Market opens 7:30 AM MDT)...")
            else:
                log_message(f"Error: {e}")
            time.sleep(30)

if __name__ == "__main__":
    run_bot()
