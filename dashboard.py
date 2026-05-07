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

# --- HELPER: AI ADVISOR ---
def get_ai_advice(params):
    order_type = params['type'].replace('_', ' ').title()
    side = params['side'].upper()
    qty = params['qty']
    symbol = params['symbol']
    
    details = [f"at **${v}**" for k,v in params.items() if 'price' in k]
    if 'trail_percent' in params: details.append(f"trailing by **{params['trail_percent']}%**")
    
    # Logic Checks
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

# --- UI APP ---
st.set_page_config(page_title="Mission Control", layout="wide")
st.title("🚀 Gemini Trading Mission Control")

# Session management
if 'review_mode' not in st.session_state: st.session_state.review_mode = False
if 'params' not in st.session_state: st.session_state.params = None

# Sidebar
if not os.path.exists(SETTINGS_FILE): with open(SETTINGS_FILE, "w") as f: json.dump({"mode": "Full Auto"}, f)
with open(SETTINGS_FILE, "r") as f: settings = json.load(f)

st.sidebar.header("Bot Fleet")
mode = st.sidebar.radio("Mode", ["Full Auto", "Manual"], index=0 if settings["mode"]=="Full Auto" else 1)
if mode != settings["mode"]:
    settings["mode"] = mode
    with open(SETTINGS_FILE, "w") as f: json.dump(settings, f)

bot = st.sidebar.selectbox("Active Bot", ["Trailing Stop Bot v1", "Politician Tracker", "The Wheel (Income)"])

# Stats & Tables
try:
    acc = api.get_account()
    c1, c2, c3 = st.columns(3)
    c1.metric("Buying Power", f"${float(acc.buying_power):,.2f}")
    c2.metric("Positions", str(len(api.list_positions())))
    c3.metric("Open Orders", str(len(api.list_orders())))
except: st.error("Alpaca Offline.")

st.markdown("---")
col_pos, col_ord = st.columns(2)

with col_pos:
    st.subheader("📊 Open Positions")
    pos = api.list_positions()
    if pos: st.dataframe(pd.DataFrame([[p.symbol, p.qty, p.current_price, p.unrealized_pl] for p in pos], columns=['Symbol', 'Qty', 'Price', 'P/L']))
    else: st.info("No open positions.")

with col_ord:
    st.subheader("⏳ Pending/Open Orders")
    orders = api.list_orders(status='open')
    if orders: st.dataframe(pd.DataFrame([[o.symbol, o.qty, o.type, o.status] for o in orders], columns=['Symbol', 'Qty', 'Type', 'Status']))
    else: st.info("No open orders.")

# --- MANUAL TRADING ---
if not st.session_state.review_mode:
    st.header("🕹️ Pro Manual Terminal")
    with st.form("manual"):
        c1, c2, c3, c4 = st.columns(4)
        sym = c1.text_input("Ticker", "TSLA").upper()
        qty = c2.number_input("Qty", 1, 1000, 1)
        side = c3.selectbox("Action", ["buy", "sell"])
        otype = c4.selectbox("Type", ["market", "limit", "stop", "bracket"])
        
        limit = st.number_input("Limit Price", 0.01, 10000.0, 300.0) if otype in ["limit", "bracket"] else None
        tp = st.number_input("Profit Target", 0.01, 10000.0, 350.0) if otype == "bracket" else None
        sl = st.number_input("Stop Loss", 0.01, 10000.0, 250.0) if otype == "bracket" else None
        
        if st.form_submit_button("Review Trade"):
            params = {"symbol": sym, "qty": qty, "side": side, "type": otype if otype != "bracket" else "limit"}
            if limit: params["limit_price"] = limit
            if otype == "bracket": params["order_class"] = "bracket"; params["take_profit"] = {"limit_price": tp}; params["stop_loss"] = {"stop_price": sl}
            st.session_state.params = params
            st.session_state.review_mode = True
            st.rerun()
else:
    st.warning("⚠️ Review Trade")
    st.markdown(get_ai_advice(st.session_state.params))
    if st.button("🔥 Execute"):
        api.submit_order(time_in_force='gtc', **st.session_state.params)
        st.session_state.review_mode = False; st.rerun()
    if st.button("Cancel"): st.session_state.review_mode = False; st.rerun()
