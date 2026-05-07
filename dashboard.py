import streamlit as st
import pandas as pd
from alpaca_trade_api.rest import REST
import os

# --- CONFIGURATION ---
API_KEY = "PKRPLQBGC5J3ALAUJ2CEXRF5WS"
SECRET_KEY = "5nWMXqwxJyyknuaVsLEsiDdLKB9ue9HNz2cnLL5j11Qo"
BASE_URL = "https://paper-api.alpaca.markets"

api = REST(API_KEY, SECRET_KEY, BASE_URL)

# --- UI HEADER ---
st.set_page_config(page_title="Gemini Trading Mission Control", layout="wide")
st.title("?? Gemini Trading Mission Control")
st.markdown("---")

# --- SIDEBAR: BOT SELECTOR ---
st.sidebar.header("Bot Fleet Management")
active_bot = st.sidebar.selectbox("Select Active Bot", ["Trailing Stop Bot v1", "Politician Tracker", "The Wheel (Income)"])
st.sidebar.success(f"{active_bot} is ONLINE")

# --- TOP LEVEL METRICS ---
account = api.get_account()
col1, col2, col3 = st.columns(3)
col1.metric("Buying Power", f"${float(account.buying_power):,.2f}")
col2.metric("Portfolio Value", f"${float(account.portfolio_value):,.2f}")
col3.metric("Daily P/L", f"${float(account.equity) - float(account.last_equity):,.2f}")

# --- POSITIONS TABLE ---
st.subheader("?? Active Positions")
positions = api.list_positions()
if positions:
    pos_data = [[p.symbol, p.qty, p.current_price, p.unrealized_pl] for p in positions]
    df = pd.DataFrame(pos_data, columns=['Symbol', 'Qty', 'Price', 'Unrealized P/L'])
    st.dataframe(df, use_container_width=True)
else:
    st.info("No active positions. The fleet is ready for orders.")
