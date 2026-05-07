import streamlit as st
import pandas as pd
from alpaca_trade_api.rest import REST
import os
import json
from datetime import datetime

# --- CONFIGURATION (Streamlit Secrets or Local) ---
if "ALPACA_API_KEY" in st.secrets:
    API_KEY = st.secrets["ALPACA_API_KEY"]
    SECRET_KEY = st.secrets["ALPACA_SECRET_KEY"]
    BASE_URL = st.secrets.get("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
else:
    API_KEY = "PKRPLQBGC5J3ALAUJ2CEXRF5WS"
    SECRET_KEY = "5nWMXqwxJyyknuaVsLEsiDdLKB9ue9HNz2cnLL5j11Qo"
    BASE_URL = "https://paper-api.alpaca.markets"

api = REST(API_KEY, SECRET_KEY, BASE_URL)
SETTINGS_FILE = "settings.json"
PENDING_TRADES_FILE = "pending_trades.json"
LOG_FILE = "bot_log.txt"

# Initialize settings if missing
if not os.path.exists(SETTINGS_FILE):
    with open(SETTINGS_FILE, "w") as f:
        json.dump({
            "mode": "Full Auto",
            "trailing_stop_pct": 5.0,
            "whale_symbols": "NVDA,AAPL,MSFT,GOOGL",
            "wheel_symbol": "TSLA"
        }, f)

def load_settings():
    with open(SETTINGS_FILE, "r") as f:
        return json.load(f)

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)

# --- UI HEADER ---
st.set_page_config(page_title="Gemini Trading Mission Control", layout="wide")
st.title("🚀 Gemini Trading Mission Control")
st.markdown("---")

# --- SIDEBAR: CONTROLS ---
settings = load_settings()
st.sidebar.header("Bot Fleet Management")
automation_mode = st.sidebar.radio("Bot Authority", ["Full Auto", "Manual Approval Required"], 
                                   index=0 if settings["mode"] == "Full Auto" else 1,
                                   help="Full Auto: Bots trade immediately. Manual: Bots wait for your 'Approve' click.")

# Update mode if changed
if automation_mode != settings["mode"]:
    settings["mode"] = automation_mode
    save_settings(settings)

active_bot = st.sidebar.selectbox("Select Active Bot", ["Trailing Stop Bot v1", "Politician Tracker", "The Wheel (Income)"])

# --- TOP LEVEL METRICS ---
try:
    account = api.get_account()
    col1, col2, col3 = st.columns(3)
    col1.metric("Buying Power", f"${float(account.buying_power):,.2f}")
    col2.metric("Portfolio Value", f"${float(account.portfolio_value):,.2f}")
    col3.metric("Daily P/L", f"${float(account.equity) - float(account.last_equity):,.2f}")
except:
    st.error("Could not connect to Alpaca.")

# --- BOT SPECIFIC VIEW ---
st.subheader(f"🤖 Bot Insight: {active_bot}")
insight_col, settings_col = st.columns([2, 1])

with insight_col:
    tag_map = {"Trailing Stop Bot v1": "[TRAILING-STOP]", "Politician Tracker": "[POLITICIAN-TRACKER]", "The Wheel (Income)": "[THE-WHEEL]"}
    selected_tag = tag_map[active_bot]
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
            bot_lines = [l.strip() for l in lines if selected_tag in l][-10:]
            if bot_lines: st.code("\n".join(bot_lines[::-1]), language="text")
            else: st.info("No recent activity.")
    else: st.info("Logs initializing...")

with settings_col:
    st.write("**Local Settings**")
    if active_bot == "Trailing Stop Bot v1":
        new_val = st.slider("Trailing Stop %", 1.0, 20.0, float(settings.get("trailing_stop_pct", 5.0)), help="The 'floor' that follows the price up.")
        if new_val != settings.get("trailing_stop_pct"):
            settings["trailing_stop_pct"] = new_val
            save_settings(settings)
            st.success("Updated!")
    elif active_bot == "Politician Tracker":
        new_val = st.text_input("Whale Symbols", settings.get("whale_symbols", "NVDA,AAPL"), help="Comma-separated symbols to watch.")
        if new_val != settings.get("whale_symbols"):
            settings["whale_symbols"] = new_val
            save_settings(settings)
            st.success("Updated!")
    elif active_bot == "The Wheel (Income)":
        new_val = st.text_input("Target Ticker", settings.get("wheel_symbol", "TSLA"))
        if new_val != settings.get("wheel_symbol"):
            settings["wheel_symbol"] = new_val
            save_settings(settings)
            st.success("Updated!")

st.markdown("---")
# --- SHARED DASHBOARD ELEMENTS ---
col_pos, col_trade = st.columns([2, 1])

with col_pos:
    st.subheader("📊 Active Positions")
    positions = api.list_positions()
    if positions:
        pos_data = [[p.symbol, p.qty, p.current_price, f"{float(p.unrealized_pl):.2f}"] for p in positions]
        df = pd.DataFrame(pos_data, columns=['Symbol', 'Qty', 'Price', 'Unrealized P/L'])
        st.dataframe(df, use_container_width=True)
    else: st.info("No active positions.")

with col_trade:
    st.subheader("💡 Bot Suggestions")
    if os.path.exists(PENDING_TRADES_FILE):
        with open(PENDING_TRADES_FILE, "r") as f:
            pending = json.load(f)
        if pending:
            for i, trade in enumerate(pending):
                with st.expander(f"{trade['bot'].upper()}: {trade['side'].upper()} {trade['symbol']}"):
                    st.write(f"Reason: {trade.get('reason', 'Strategy trigger')}")
                    if st.button("Approve", key=f"app_{i}"):
                        api.submit_order(symbol=trade['symbol'], qty=trade['qty'], side=trade['side'], type='market', time_in_force='gtc')
                        pending.pop(i)
                        with open(PENDING_TRADES_FILE, "w") as f: json.dump(pending, f)
                        st.rerun()
                    if st.button("Reject", key=f"rej_{i}"):
                        pending.pop(i)
                        with open(PENDING_TRADES_FILE, "w") as f: json.dump(pending, f)
                        st.rerun()
        else: st.write("None.")
    else: st.write("None.")

# --- ENHANCED MANUAL ORDERING ---
st.subheader("🕹️ Advanced Manual Order")
with st.form("advanced_manual_trade"):
    row1_c1, row1_c2, row1_c3, row1_c4 = st.columns(4)
    t_symbol = row1_c1.text_input("Symbol", value="TSLA", help="Ticker symbol (e.g., TSLA, NVDA)").upper()
    t_qty = row1_c2.number_input("Quantity", min_value=1, value=1, help="Number of shares to buy or sell")
    t_side = row1_c3.selectbox("Action", ["buy", "sell"], help="Buy to open a position, Sell to close it")
    t_type = row1_c4.selectbox("Order Type", ["market", "limit", "stop", "trailing_stop"], 
                                help="Market: Buy/Sell now. Limit: Buy low/Sell high. Stop: Trigger at a price. Trailing Stop: Floor that follows the price up.")

    row2_c1, row2_c2, row2_c3 = st.columns(3)
    t_limit_price = None
    t_stop_price = None
    t_trail_percent = None

    if t_type == "limit":
        t_limit_price = row2_c1.number_input("Limit Price ($)", min_value=0.01, step=0.01, help="The MAXIMUM price you are willing to pay, or MINIMUM you will sell for.")
    elif t_type == "stop":
        t_stop_price = row2_c1.number_input("Trigger Price ($)", min_value=0.01, step=0.01, help="When the stock hits this price, your order becomes active.")
    elif t_type == "trailing_stop":
        t_trail_percent = row2_c1.number_input("Trail Percent (%)", min_value=0.1, max_value=20.0, value=5.0, step=0.1, help="The distance the stop follows the price. If it drops this much from the high, it sells.")

    if st.form_submit_button("🔥 Execute Advanced Order"):
        try:
            order_params = {
                "symbol": t_symbol,
                "qty": t_qty,
                "side": t_side,
                "type": t_type,
                "time_in_force": 'gtc'
            }
            if t_type == "limit": order_params["limit_price"] = t_limit_price
            if t_type == "stop": order_params["stop_price"] = t_stop_price
            if t_type == "trailing_stop": order_params["trail_percent"] = t_trail_percent
            
            api.submit_order(**order_params)
            st.success(f"Successfully placed {t_type.upper()} {t_side.upper()} order for {t_qty} {t_symbol}")
        except Exception as e:
            st.error(f"Order failed: {e}")
