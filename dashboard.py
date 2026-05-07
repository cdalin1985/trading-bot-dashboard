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
                                   index=0 if settings["mode"] == "Full Auto" else 1)

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
    # Get logs for specific bot
    tag_map = {
        "Trailing Stop Bot v1": "[TRAILING-STOP]",
        "Politician Tracker": "[POLITICIAN-TRACKER]",
        "The Wheel (Income)": "[THE-WHEEL]"
    }
    selected_tag = tag_map[active_bot]
    
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
            bot_lines = [l.strip() for l in lines if selected_tag in l][-10:]
            if bot_lines:
                st.code("\n".join(bot_lines[::-1]), language="text")
            else:
                st.info("No recent log entries for this bot.")
    else:
        st.info("Log file not found.")

with settings_col:
    st.write("**Local Settings**")
    if active_bot == "Trailing Stop Bot v1":
        new_val = st.slider("Trailing Stop %", 1.0, 20.0, float(settings.get("trailing_stop_pct", 5.0)))
        if new_val != settings.get("trailing_stop_pct"):
            settings["trailing_stop_pct"] = new_val
            save_settings(settings)
            st.success("Updated!")
            
    elif active_bot == "Politician Tracker":
        new_val = st.text_input("Whale Symbols", settings.get("whale_symbols", "NVDA,AAPL"))
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
    else:
        st.info("No active positions.")

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
                        with open(PENDING_TRADES_FILE, "w") as f:
                            json.dump(pending, f)
                        st.rerun()
                    if st.button("Reject", key=f"rej_{i}"):
                        pending.pop(i)
                        with open(PENDING_TRADES_FILE, "w") as f:
                            json.dump(pending, f)
                        st.rerun()
        else: st.write("None.")
    else: st.write("None.")

st.subheader("🕹️ Manual Order")
with st.form("manual_trade_form"):
    c1, c2, c3 = st.columns(3)
    t_symbol = c1.text_input("Symbol", value="TSLA").upper()
    t_qty = c2.number_input("Qty", min_value=1, value=1)
    t_side = c3.selectbox("Action", ["buy", "sell"])
    if st.form_submit_button("Execute Manual Trade"):
        api.submit_order(symbol=t_symbol, qty=t_qty, side=t_side, type='market', time_in_force='gtc')
        st.success(f"Sent: {t_side.upper()} {t_qty} {t_symbol}")
