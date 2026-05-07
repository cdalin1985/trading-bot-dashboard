import streamlit as st
import pandas as pd
from alpaca_trade_api.rest import REST
import os
import json

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
PENDING_TRADES_FILE = "pending_trades.json"

# --- UI HEADER ---
st.set_page_config(page_title="Gemini Trading Mission Control", layout="wide")
st.title("🚀 Gemini Trading Mission Control")
st.markdown("---")

# --- SIDEBAR: CONTROLS ---
st.sidebar.header("Bot Fleet Management")
automation_mode = st.sidebar.radio("Bot Authority", ["Full Auto", "Manual Approval Required"])

# Save mode to shared settings file
SETTINGS_FILE = "settings.json"
with open(SETTINGS_FILE, "w") as f:
    json.dump({"mode": automation_mode}, f)

active_bot = st.sidebar.selectbox("Select Active Bot", ["Trailing Stop Bot v1", "Politician Tracker", "The Wheel (Income)"])

# --- TOP LEVEL METRICS ---
try:
    account = api.get_account()
    col1, col2, col3 = st.columns(3)
    col1.metric("Buying Power", f"${float(account.buying_power):,.2f}")
    col2.metric("Portfolio Value", f"${float(account.portfolio_value):,.2f}")
    col3.metric("Daily P/L", f"${float(account.equity) - float(account.last_equity):,.2f}")
except:
    st.error("Could not connect to Alpaca. Check your API keys.")

# --- POSITIONS TABLE ---
st.subheader("📊 Active Positions")
positions = api.list_positions()
if positions:
    pos_data = [[p.symbol, p.qty, p.current_price, f"{float(p.unrealized_pl):.2f}"] for p in positions]
    df = pd.DataFrame(pos_data, columns=['Symbol', 'Qty', 'Price', 'Unrealized P/L'])
    st.dataframe(df, use_container_width=True)
else:
    st.info("No active positions.")

st.markdown("---")
col_left, col_right = st.columns(2)

# --- MANUAL TRADING TERMINAL ---
with col_left:
    st.subheader("🕹️ Manual Trading")
    with st.form("manual_trade_form"):
        t_symbol = st.text_input("Symbol (e.g. AAPL)", value="TSLA").upper()
        t_qty = st.number_input("Quantity", min_value=1, value=1)
        t_side = st.selectbox("Action", ["buy", "sell"])
        
        submit_trade = st.form_submit_button("Submit Order")
        if submit_trade:
            try:
                api.submit_order(symbol=t_symbol, qty=t_qty, side=t_side, type='market', time_in_force='gtc')
                st.success(f"Order Sent: {t_side.upper()} {t_qty} {t_symbol}")
            except Exception as e:
                st.error(f"Trade Failed: {e}")

# --- BOT APPROVAL QUEUE ---
with col_right:
    st.subheader("💡 Bot Suggestions")
    if os.path.exists(PENDING_TRADES_FILE):
        with open(PENDING_TRADES_FILE, "r") as f:
            pending = json.load(f)
        
        if pending:
            for i, trade in enumerate(pending):
                with st.expander(f"{trade['bot'].upper()}: {trade['side'].upper()} {trade['symbol']}"):
                    st.write(f"**Reason**: {trade.get('reason', 'Strategy trigger')}")
                    if st.button("Approve Trade", key=f"app_{i}"):
                        try:
                            api.submit_order(symbol=trade['symbol'], qty=trade['qty'], side=trade['side'], type='market', time_in_force='gtc')
                            st.success("Trade Approved!")
                            # Remove from list
                            pending.pop(i)
                            with open(PENDING_TRADES_FILE, "w") as f:
                                json.dump(pending, f)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Approval failed: {e}")
                    
                    if st.button("Reject", key=f"rej_{i}"):
                        pending.pop(i)
                        with open(PENDING_TRADES_FILE, "w") as f:
                            json.dump(pending, f)
                        st.rerun()
        else:
            st.write("No pending suggestions.")
    else:
        st.write("No pending suggestions.")
