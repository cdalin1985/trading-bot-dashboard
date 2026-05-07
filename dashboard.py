import streamlit as st
import pandas as pd
from alpaca_trade_api.rest import REST
import os
import json
from datetime import datetime
import requests

# --- CONFIGURATION (Streamlit Secrets or Local) ---
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
    
    details = []
    if 'limit_price' in params: details.append(f"at **${params['limit_price']}**")
    if 'stop_price' in params: details.append(f"triggered at **${params['stop_price']}**")
    if 'trail_percent' in params: details.append(f"trailing by **{params['trail_percent']}%**")
    
    if params.get('order_class') == 'bracket':
        tp = params['take_profit']['limit_price']
        sl = params['stop_loss']['stop_price']
        details.append(f"with Profit Goal at **${tp}** and Emergency Stop at **${sl}**")
        
        # Immediate logic check to help the user
        if side == "BUY" and float(tp) <= float(sl):
            return "❌ **ERROR**: For a BUY order, your 'Profit Goal' must be HIGHER than your 'Stop Loss'. Please adjust the numbers below."
        if side == "SELL" and float(tp) >= float(sl):
            return "❌ **ERROR**: For a SELL order, your 'Profit Goal' must be LOWER than your 'Stop Loss'. Please adjust the numbers below."
    
    detail_str = " ".join(details)
    advice = f"### 🛡️ Risk Analyst Report: {order_type} {side}\n\n"
    advice += f"Action: **{side} {qty} shares of {symbol}** {detail_str}.\n\n"
    
    if params['type'] == "market":
        advice += "**Advice**: This executes immediately. You are at the mercy of the current market price."
    elif params['type'] == "limit":
        advice += "**Advice**: You've set a maximum price. The trade will only happen if the stock is at or below this value."
    elif params.get('order_class') == 'bracket':
        advice += "**Advice**: This is a complete trade plan. It will automatically try to sell for a profit or exit for a small loss once the buy is finished."

    if GEMINI_API_KEY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
            prompt = f"Act as a professional financial advisor. Analyze this specific order: {side} {qty} {symbol} {order_type} {detail_str}. Briefly explain the strategy."
            resp = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
            if resp.status_code == 200:
                ai_text = resp.json()['candidates'][0]['content']['parts'][0]['text']
                advice += f"\n\n---\n### ✨ AI Context\n{ai_text}"
        except: pass
            
    return advice

# --- UI HEADER ---
st.set_page_config(page_title="Gemini Trading Mission Control", layout="wide")
st.title("🚀 Gemini Trading Mission Control")
st.markdown("---")

# --- SIDEBAR & TOP METRICS ---
if not os.path.exists(SETTINGS_FILE):
    with open(SETTINGS_FILE, "w") as f: json.dump({"mode": "Full Auto", "trailing_stop_pct": 5.0, "wheel_symbol": "TSLA"}, f)

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
    # --- STEP 1: INPUT ---
    with st.form("pro_order_form"):
        r1c1, r1c2, r1c3, r1c4 = st.columns(4)
        t_symbol = r1c1.text_input("Ticker Symbol", value="TSLA").upper()
        t_qty = r1c2.number_input("Shares", min_value=1, value=1)
        t_side = r1c3.selectbox("Action", ["buy", "sell"])
        t_type = r1c4.selectbox("Order Type", ["market", "limit", "stop", "stop_limit", "trailing_stop", "bracket"])

        r2c1, r2c2, r2c3, r2c4 = st.columns(4)
        t_limit = r2c1.number_input("Entry Price ($)", min_value=0.01, step=0.01, value=400.0) if t_type in ["limit", "stop_limit", "bracket"] else None
        t_stop = r2c2.number_input("Trigger Price ($)", min_value=0.01, step=0.01, value=390.0) if t_type in ["stop", "stop_limit"] else None
        t_trail = r2c3.number_input("Trailing %", min_value=0.1, max_value=25.0, value=5.0) if t_type == "trailing_stop" else None
        
        t_tp = None
        t_sl = None
        if t_type == "bracket":
            t_tp = r2c3.number_input("Profit Target ($)", min_value=0.01, step=0.01, value=450.0)
            t_sl = r2c4.number_input("Stop Loss ($)", min_value=0.01, step=0.01, value=380.0)

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
    # --- STEP 2: REVIEW & QUICK ADJUST ---
    params = st.session_state.pending_order_params
    st.warning("⚠️ **TRADE ON HOLD.** Review and adjust parameters below.")
    
    with st.container(border=True):
        st.markdown(get_ai_advice(params))

    # --- QUICK ADJUSTMENT PANEL ---
    with st.expander("🛠️ Adjust Order Parameters (Fix Errors Here)"):
        adj_col1, adj_col2 = st.columns(2)
        params['qty'] = adj_col1.number_input("Adjust Shares", min_value=1, value=int(params['qty']))
        
        if 'limit_price' in params:
            params['limit_price'] = adj_col2.number_input("Adjust Entry Price ($)", value=float(params['limit_price']), step=0.01)
        
        if params.get('order_class') == 'bracket':
            adj_col3, adj_col4 = st.columns(2)
            params['take_profit']['limit_price'] = adj_col3.number_input("Adjust Profit Target ($)", value=float(params['take_profit']['limit_price']), step=0.01)
            params['stop_loss']['stop_price'] = adj_col4.number_input("Adjust Stop Loss ($)", value=float(params['stop_loss']['stop_price']), step=0.01)
            
        st.session_state.pending_order_params = params

    btn_col1, btn_col2 = st.columns(2)
    
    # Validation for the 'Execute' button
    can_execute = True
    if params.get('order_class') == 'bracket':
        if params['side'] == 'buy' and params['take_profit']['limit_price'] <= params['stop_loss']['stop_price']:
            can_execute = False
    
    if btn_col1.button("🔥 Confirm & Execute Trade", type="primary", use_container_width=True, disabled=not can_execute):
        try:
            api.submit_order(time_in_force='gtc', **params)
            st.success("ORDER SENT!")
            st.session_state.order_review_mode = False
            st.rerun()
        except Exception as e:
            st.error(f"Execution Error: {e}")
            
    if btn_col2.button("⬅️ Cancel / Clear All", use_container_width=True):
        st.session_state.order_review_mode = False
        st.rerun()

st.markdown("---")
# --- PORTFOLIO & LOGS ---
col_pos, col_log = st.columns([2, 1])
with col_pos:
    st.subheader("📊 Active Positions")
    positions = api.list_positions()
    if positions:
        st.dataframe(pd.DataFrame([[p.symbol, p.qty, p.current_price, f"{float(p.unrealized_pl):.2f}"] for p in positions], 
                                 columns=['Symbol', 'Qty', 'Price', 'P/L']), use_container_width=True)
    else: st.info("No active trades.")

with col_log:
    st.subheader("🤖 Bot Activity")
    tag_map = {"Trailing Stop Bot v1": "[TRAILING-STOP]", "Politician Tracker": "[POLITICIAN-TRACKER]", "The Wheel (Income)": "[THE-WHEEL]"}
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            bot_lines = [l.strip() for l in f.readlines() if tag_map[active_bot] in l][-5:]
            if bot_lines: st.code("\n".join(bot_lines[::-1]))
