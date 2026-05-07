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
    API_KEY = "PKRPLQBGC5J3ALAUJ2CEXRF5WS"
    SECRET_KEY = "5nWMXqwxJyyknuaVsLEsiDdLKB9ue9HNz2cnLL5j11Qo"
    BASE_URL = "https://paper-api.alpaca.markets"
    GEMINI_API_KEY = None # Local development fallback

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
    """
    Calls Gemini API if available, otherwise uses a robust template logic.
    """
    order_type = params['type'].replace('_', ' ').title()
    side = params['side'].upper()
    qty = params['qty']
    symbol = params['symbol']
    
    details = ""
    if params['type'] == "limit": details = f"at a maximum price of ${params['limit_price']}"
    if params['type'] == "stop": details = f"once the price hits ${params['stop_price']}"
    if params['type'] == "trailing_stop": details = f"with a {params['trail_percent']}% floor following the price"

    # Default robust explanation (The "Internal Analyst")
    advice = f"### 🛡️ Risk Analyst Report\n\n"
    advice += f"You are preparing to **{side} {qty} shares of {symbol}** using a **{order_type}** order {details}.\n\n"
    
    if params['type'] == "market":
        advice += "**Advice**: This order executes immediately at the current price. It's the fastest way to trade but offers no protection if the price spikes or dips suddenly."
    elif params['type'] == "limit":
        advice += f"**Advice**: You are protected! If {symbol} is currently higher than ${params['limit_price']}, this order will wait. You will never pay more than your limit."
    elif params['type'] == "stop":
        advice += f"**Advice**: This is a 'trigger' order. Your trade stays hidden until {symbol} hits ${params['stop_price']}, then it becomes a market order. Used to limit losses or enter a breakout."
    elif params['type'] == "trailing_stop":
        advice += f"**Advice**: This is your bot's favorite! It protects your profits by moving a 'sell floor' up as {symbol} climbs. If the stock drops {params['trail_percent']}% from its highest point, it triggers a sell automatically."

    # Attempt to enhance with Gemini if key exists
    if GEMINI_API_KEY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
            prompt = f"Act as a professional financial advisor. Explain the risks and benefits of this specific order: {side} {qty} {symbol} {order_type} {details}. Keep it concise and dummy-proof."
            resp = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
            if resp.status_code == 200:
                ai_text = resp.json()['candidates'][0]['content']['parts'][0]['text']
                advice += f"\n\n---\n### ✨ AI Market Perspective\n{ai_text}"
        except:
            pass
            
    return advice

# --- UI HEADER ---
st.set_page_config(page_title="Gemini Trading Mission Control", layout="wide")
st.title("🚀 Gemini Trading Mission Control")
st.markdown("---")

# --- SIDEBAR: CONTROLS ---
if not os.path.exists(SETTINGS_FILE):
    with open(SETTINGS_FILE, "w") as f:
        json.dump({"mode": "Full Auto", "trailing_stop_pct": 5.0, "whale_symbols": "NVDA,AAPL", "wheel_symbol": "TSLA"}, f)

with open(SETTINGS_FILE, "r") as f:
    settings = json.load(f)

st.sidebar.header("Bot Fleet Management")
automation_mode = st.sidebar.radio("Bot Authority", ["Full Auto", "Manual Approval Required"], 
                                   index=0 if settings["mode"] == "Full Auto" else 1)

if automation_mode != settings["mode"]:
    settings["mode"] = automation_mode
    with open(SETTINGS_FILE, "w") as f: json.dump(settings, f)

active_bot = st.sidebar.selectbox("Select Active Bot", ["Trailing Stop Bot v1", "Politician Tracker", "The Wheel (Income)"])

# --- TOP LEVEL METRICS ---
try:
    account = api.get_account()
    col1, col2, col3 = st.columns(3)
    col1.metric("Buying Power", f"${float(account.buying_power):,.2f}")
    col2.metric("Portfolio Value", f"${float(account.portfolio_value):,.2f}")
    col3.metric("Daily P/L", f"${float(account.equity) - float(account.last_equity):,.2f}")
except:
    st.error("Connection Error.")

# --- BOT SPECIFIC VIEW ---
st.subheader(f"🤖 Bot Insight: {active_bot}")
insight_col, settings_col = st.columns([2, 1])

with insight_col:
    tag_map = {"Trailing Stop Bot v1": "[TRAILING-STOP]", "Politician Tracker": "[POLITICIAN-TRACKER]", "The Wheel (Income)": "[THE-WHEEL]"}
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            bot_lines = [l.strip() for l in f.readlines() if tag_map[active_bot] in l][-5:]
            if bot_lines: st.code("\n".join(bot_lines[::-1]), language="text")
            else: st.info("No recent activity.")

with settings_col:
    st.write("**Bot Config**")
    if active_bot == "Trailing Stop Bot v1":
        new_val = st.slider("Stop %", 1.0, 20.0, float(settings.get("trailing_stop_pct", 5.0)))
        if new_val != settings.get("trailing_stop_pct"):
            settings["trailing_stop_pct"] = new_val
            with open(SETTINGS_FILE, "w") as f: json.dump(settings, f)
            st.success("Saved")

st.markdown("---")
# --- MAIN AREA ---
col_pos, col_trade = st.columns([2, 1])

with col_pos:
    st.subheader("📊 Active Positions")
    positions = api.list_positions()
    if positions:
        df = pd.DataFrame([[p.symbol, p.qty, p.current_price, f"{float(p.unrealized_pl):.2f}"] for p in positions], 
                          columns=['Symbol', 'Qty', 'Price', 'Unrealized P/L'])
        st.dataframe(df, use_container_width=True)
    else: st.info("Empty portfolio.")

with col_trade:
    st.subheader("💡 Suggestions")
    if os.path.exists(PENDING_TRADES_FILE):
        with open(PENDING_TRADES_FILE, "r") as f: pending = json.load(f)
        for i, t in enumerate(pending):
            with st.expander(f"{t['bot']}: {t['side']} {t['symbol']}"):
                if st.button("Approve", key=f"a_{i}"):
                    api.submit_order(symbol=t['symbol'], qty=t['qty'], side=t['side'], type='market', time_in_force='gtc')
                    pending.pop(i)
                    with open(PENDING_TRADES_FILE, "w") as f: json.dump(pending, f)
                    st.rerun()

# --- ENHANCED MANUAL ORDERING WITH AI CONFIRMATION ---
st.subheader("🕹️ Advanced Manual Order")

if not st.session_state.order_review_mode:
    # --- INPUT MODE ---
    with st.form("order_entry_form"):
        r1c1, r1c2, r1c3, r1c4 = st.columns(4)
        t_symbol = r1c1.text_input("Symbol", value="TSLA").upper()
        t_qty = r1c2.number_input("Qty", min_value=1, value=1)
        t_side = r1c3.selectbox("Action", ["buy", "sell"])
        t_type = r1c4.selectbox("Type", ["market", "limit", "stop", "trailing_stop"])

        r2c1, r2c2, r2c3 = st.columns(3)
        t_limit = r2c1.number_input("Limit ($)", min_value=0.01) if t_type == "limit" else None
        t_stop = r2c1.number_input("Stop ($)", min_value=0.01) if t_type == "stop" else None
        t_trail = r2c1.number_input("Trail (%)", min_value=0.1, max_value=20.0, value=5.0) if t_type == "trailing_stop" else None

        if st.form_submit_button("🛡️ Review Order with AI Advisor"):
            params = {"symbol": t_symbol, "qty": t_qty, "side": t_side, "type": t_type}
            if t_limit: params["limit_price"] = t_limit
            if t_stop: params["stop_price"] = t_stop
            if t_trail: params["trail_percent"] = t_trail
            
            st.session_state.pending_order_params = params
            st.session_state.order_review_mode = True
            st.rerun()
else:
    # --- REVIEW MODE ---
    params = st.session_state.pending_order_params
    st.info("💡 **Your Order is on Hold.** Please review the analyst's advice below.")
    
    with st.container(border=True):
        st.markdown(get_ai_advice(params))
    
    btn_col1, btn_col2 = st.columns(2)
    if btn_col1.button("🔥 Confirm & Execute Trade", type="primary", use_container_width=True):
        try:
            api.submit_order(time_in_force='gtc', **params)
            st.success("ORDER EXECUTED!")
            st.session_state.order_review_mode = False
            st.session_state.pending_order_params = None
            st.rerun()
        except Exception as e:
            st.error(f"Execution Error: {e}")
            
    if btn_col2.button("⬅️ Go Back & Edit", use_container_width=True):
        st.session_state.order_review_mode = False
        st.rerun()
