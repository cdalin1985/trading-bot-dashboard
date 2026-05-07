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
if 'order_review_mode' not in st.session_state:
    st.session_state.order_review_mode = False
if 'pending_order_params' not in st.session_state:
    st.session_state.pending_order_params = None

def get_ai_advice(params):
    order_type = params['type'].replace('_', ' ').title()
    side = params['side'].upper()
    qty = params['qty']
    symbol = params['symbol']
    
    # Validation Logic
    if params.get('order_class') == 'bracket':
        tp = float(params['take_profit']['limit_price'])
        sl = float(params['stop_loss']['stop_price'])
        limit = float(params.get('limit_price', 0))
        if side == "BUY" and tp <= limit: return "❌ **ERROR**: Your Profit Target must be higher than your Entry Price."
        if side == "SELL" and tp >= limit: return "❌ **ERROR**: Your Profit Target must be lower than your Entry Price."
    
    # "Wash Trade" check helper
    if params['type'] in ["stop", "stop_limit"] and side == "buy":
        return "⚠️ **WASH TRADE WARNING**: You are trying to BUY when the price is falling. This often triggers 'Wash Trade' rules in automated systems. Try a standard Market or Limit order, or use a Bracket order to define your full exit plan."

    details = [f"at **${v}**" for k,v in params.items() if 'price' in k]
    detail_str = " ".join(details)
    
    advice = f"### 🛡️ Risk Analyst Report: {order_type} {side}\n\n"
    advice += f"**Trade**: {side} {qty} {symbol} {detail_str}.\n\n"
    
    explanation = {
        "market": "Buying at the best available price right now. Simple and fast.",
        "limit": "Buying only if the price hits your target. Protects you from overpaying.",
        "stop": "Buying when the price rises to a trigger level. Often used for 'breakouts'.",
        "stop_limit": "A stop order that turns into a limit order. Very precise.",
        "trailing_stop": "A 'smart' stop that follows the stock price up as it climbs.",
        "bracket": "A professional plan: Buy + Take Profit + Stop Loss."
    }
    advice += f"**What this means**: {explanation.get(params['type'], 'This order will execute based on your specified price logic.')}"
    
    return advice

# --- UI HEADER ---
st.set_page_config(page_title="Gemini Trading Mission Control", layout="wide")
st.title("🚀 Gemini Trading Mission Control")
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
        t_limit = r2c1.number_input("Entry/Limit Price ($)", min_value=0.01, step=0.01, value=300.0) if t_type in ["limit", "stop_limit", "bracket"] else None
        t_stop = r2c2.number_input("Trigger Price ($)", min_value=0.01, step=0.01, value=300.0) if t_type in ["stop", "stop_limit"] else None
        t_trail = r2c3.number_input("Trailing %", min_value=0.1, max_value=25.0, value=5.0) if t_type == "trailing_stop" else None
        
        t_tp, t_sl = None, None
        if t_type == "bracket":
            t_tp = r2c3.number_input("Profit Target ($)", min_value=0.01, step=0.01, value=350.0)
            t_sl = r2c4.number_input("Stop Loss ($)", min_value=0.01, step=0.01, value=250.0)

        if st.form_submit_button("🛡️ Review Order with AI Advisor"):
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
    st.warning("⚠️ **TRADE ON HOLD.**")
    st.markdown(get_ai_advice(params))
    
    if st.button("🔥 Confirm & Execute Trade", type="primary"):
        try:
            api.submit_order(time_in_force='gtc', **params)
            st.success("ORDER SENT!")
            st.session_state.order_review_mode = False
            st.rerun()
        except Exception as e:
            st.error(f"Execution Error: {e}. If this is a 'Wash Trade', try using a Bracket order to define clear Exit and Entry points.")
            
    if st.button("⬅️ Cancel"):
        st.session_state.order_review_mode = False
        st.rerun()
