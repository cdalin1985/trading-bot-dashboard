import streamlit as st
import pandas as pd
from alpaca_trade_api.rest import REST
import os
import json
from datetime import datetime
import requests

# --- CONFIGURATION ---
if "ALPACA_API_KEY" in st.secrets:
    API_KEY = st.secrets["ALPACA_API_KEY"]
    SECRET_KEY = st.secrets["ALPACA_SECRET_KEY"]
    BASE_URL = st.secrets.get("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", None)
else:
    API_KEY = st.secrets.get("ALPACA_API_KEY", "PKRPLQBGC5J3ALAUJ2CEXRF5WS")
    SECRET_KEY = st.secrets.get("ALPACA_SECRET_KEY", "5nWMXqwxJyyknuaVsLEsiDdLKB9ue9HNz2cnLL5j11Qo")
    BASE_URL = st.secrets.get("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", None)

api = REST(API_KEY, SECRET_KEY, BASE_URL)
SETTINGS_FILE = "settings.json"
PENDING_TRADES_FILE = "pending_trades.json"
LOG_FILE = "bot_log.txt"

# Initialize Session States
if 'order_review_mode' not in st.session_state: st.session_state.order_review_mode = False
if 'pending_order_params' not in st.session_state: st.session_state.pending_order_params = None

def get_ai_advice(params):
    order_type = params['type'].replace('_', ' ').title()
    side = params['side'].upper()
    qty = params['qty']
    symbol = params['symbol']
    
    details = [f"at **${v}**" for k,v in params.items() if 'price' in k]
    if 'trail_percent' in params: details.append(f"trailing by **{params['trail_percent']}%**")
    
    if params.get('order_class') == 'bracket':
        tp = float(params['take_profit']['limit_price'])
        sl = float(params['stop_loss']['stop_price'])
        limit = float(params.get('limit_price', 0))
        if side == "BUY" and tp <= limit: return "❌ **Error**: Your Profit Target must be higher than your Entry Price."
        if side == "SELL" and tp >= limit: return "❌ **Error**: Your Profit Target must be lower than your Entry Price."
    
    detail_str = " ".join(details)
    advice = f"### 🛡️ Risk Analyst Report: {order_type} {side}\n\n"
    advice += f"**Trade**: {side} {qty} {symbol} {detail_str}.\n\n"
    
    if GEMINI_API_KEY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
            resp = requests.post(url, json={"contents": [{"parts": [{"text": f"Explain the risk of a {order_type} {side} order for {symbol}"}]}]})
            if resp.status_code == 200:
                advice += f"### ✨ AI Advisor\n{resp.json()['candidates'][0]['content']['parts'][0]['text']}"
        except: pass
    return advice

# --- UI HEADER ---
st.set_page_config(page_title="Mission Control", layout="wide")
st.title("🚀 Gemini Trading Mission Control")

# --- SIDEBAR & TOP METRICS ---
if not os.path.exists(SETTINGS_FILE):
    with open(SETTINGS_FILE, "w") as f:
        json.dump({"mode": "Full Auto", "trailing_stop_pct": 5.0, "whale_symbols": "NVDA,AAPL", "wheel_symbol": "TSLA"}, f)

with open(SETTINGS_FILE, "r") as f: settings = json.load(f)

st.sidebar.header("Bot Fleet Management")
automation_mode = st.sidebar.radio("Bot Authority", ["Full Auto", "Manual Approval Required"], index=0 if settings["mode"] == "Full Auto" else 1)
if automation_mode != settings["mode"]:
    settings["mode"] = automation_mode
    with open(SETTINGS_FILE, "w") as f: json.dump(settings, f)

active_bot = st.sidebar.selectbox("Select Active Bot", ["Trailing Stop Bot v1", "Politician Tracker", "The Wheel (Income)"])

try:
    account = api.get_account()
    c1, c2, c3 = st.columns(3)
    c1.metric("Buying Power", f"${float(account.buying_power):,.2f}")
    c2.metric("Portfolio Value", f"${float(account.portfolio_value):,.2f}")
    c3.metric("Daily P/L", f"${float(account.equity) - float(account.last_equity):,.2f}")
except: st.error("Account Offline.")

st.markdown("---")
# --- MANUAL ORDER SECTION ---
st.header("🕹️ Pro Manual Terminal")

if not st.session_state.order_review_mode:
    with st.form("pro_order_form"):
        r1c1, r1c2, r1c3, r1c4 = st.columns(4)
        t_symbol = r1c1.text_input("Ticker Symbol", value="TSLA").upper()
        t_qty = r1c2.number_input("Shares", min_value=1, value=1)
        t_side = r1c3.selectbox("Action", ["buy", "sell"])
        t_type = r1c4.selectbox("Order Type", ["market", "limit", "stop", "stop_limit", "trailing_stop", "bracket"])

        r2c1, r2c2, r2c3, r2c4 = st.columns(4)
        t_limit = r2c1.number_input("Entry Price ($)", min_value=0.01, step=0.01, value=300.0) if t_type in ["limit", "stop_limit", "bracket"] else None
        t_stop = r2c2.number_input("Trigger Price ($)", min_value=0.01, step=0.01, value=290.0) if t_type in ["stop", "stop_limit"] else None
        t_trail = r2c3.number_input("Trailing %", min_value=0.1, max_value=25.0, value=5.0) if t_type == "trailing_stop" else None
        t_tp, t_sl = None, None
        if t_type == "bracket":
            t_tp = r2c3.number_input("Profit Target ($)", min_value=0.01, step=0.01, value=350.0)
            t_sl = r2c4.number_input("Stop Loss ($)", min_value=0.01, step=0.01, value=250.0)

        if st.form_submit_button("🛡️ Review Order"):
            params = {"symbol": t_symbol, "qty": t_qty, "side": t_side, "type": t_type if t_type != "bracket" else "limit"}
            if t_limit: params["limit_price"] = t_limit
            if t_stop: params["stop_price"] = t_stop
            if t_trail: params["trail_percent"] = t_trail
            if t_type == "bracket":
                params["order_class"] = "bracket"
                params["take_profit"] = {"limit_price": t_tp}
                params["stop_loss"] = {"stop_price": t_sl}
            st.session_state.pending_order_params = params
            st.session_state.order_review_mode = True
            st.rerun()
else:
    params = st.session_state.pending_order_params
    st.markdown(get_ai_advice(params))
    if st.button("🔥 Confirm & Execute"):
        api.submit_order(time_in_force='gtc', **params)
        st.session_state.order_review_mode = False; st.rerun()
    if st.button("⬅️ Cancel"): st.session_state.order_review_mode = False; st.rerun()
