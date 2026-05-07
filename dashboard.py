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
    # Local fallback for your computer (using the hidden secrets file if it exists)
    try:
        # Streamlit reads from .streamlit/secrets.toml automatically if running via 'streamlit run'
        # But we'll try to explicitly grab them for safety in some environments
        API_KEY = st.secrets.get("ALPACA_API_KEY", "PKRPLQBGC5J3ALAUJ2CEXRF5WS")
        SECRET_KEY = st.secrets.get("ALPACA_SECRET_KEY", "5nWMXqwxJyyknuaVsLEsiDdLKB9ue9HNz2cnLL5j11Qo")
        BASE_URL = st.secrets.get("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
        GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", None)
    except:
        API_KEY = "PKRPLQBGC5J3ALAUJ2CEXRF5WS"
        SECRET_KEY = "5nWMXqwxJyyknuaVsLEsiDdLKB9ue9HNz2cnLL5j11Qo"
        BASE_URL = "https://paper-api.alpaca.markets"
        GEMINI_API_KEY = None

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
    if 'limit_price' in params: details.append(f"at ${params['limit_price']}")
    if 'stop_price' in params: details.append(f"triggered at ${params['stop_price']}")
    if 'trail_percent' in params: details.append(f"trailing by {params['trail_percent']}%")
    if params.get('order_class') == 'bracket':
        details.append(f"with Profit Goal at ${params['take_profit']['limit_price']} and Emergency Stop at ${params['stop_loss']['stop_price']}")
    
    detail_str = " ".join(details)

    advice = f"### 🛡️ Risk Analyst Report: {order_type} {side}\n\n"
    advice += f"Action: **{side} {qty} shares of {symbol}** {detail_str}.\n\n"
    
    # Logic-based advice
    if params['type'] == "market":
        advice += "**Risk**: You have no price control. In a volatile market, you might pay much more (or sell for much less) than the 'current' price you see.\n**Benefit**: Guaranteed immediate execution."
    elif params['type'] == "limit":
        advice += "**Risk**: If the price never hits your limit, the trade won't happen.\n**Benefit**: You have absolute price control. You'll never pay a penny more than your limit."
    elif params['type'] == "stop":
        advice += "**Risk**: Once triggered, it becomes a market order. If the stock is 'gapping' down, you could sell much lower than your trigger.\n**Benefit**: Automates an exit if a stock starts crashing."
    elif params['type'] == "stop_limit":
        advice += "**Risk**: High precision. If the stock skips over your narrow window, the trade won't fill.\n**Benefit**: Prevents the 'slippage' risk of a normal stop order."
    elif params['type'] == "trailing_stop":
        advice += "**Risk**: A temporary 'dip' might trigger a sell even if the stock is still in a long-term uptrend.\n**Benefit**: It locks in profits as the stock climbs without you having to watch it."
    elif params.get('order_class') == 'bracket':
        advice += "**Risk**: Requires the price to hit one of your targets. Your money is 'locked' in this strategy until it finishes.\n**Benefit**: The Ultimate 'Set and Forget'. It automates your exit plan—both for making money (Profit) and protecting against loss (Stop) simultaneously."

    if GEMINI_API_KEY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
            prompt = f"Act as a professional financial advisor. Analyze this specific trade: {side} {qty} {symbol} using a {order_type} order {detail_str}. List 2 pros and 2 cons in simple language."
            resp = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
            if resp.status_code == 200:
                ai_text = resp.json()['candidates'][0]['content']['parts'][0]['text']
                advice += f"\n\n---\n### ✨ Gemini Market Context\n{ai_text}"
        except: pass
            
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
    st.error("Account Connection Offline. Did you add your Secrets to Streamlit Cloud Settings?")
    st.info("💡 Go to Settings -> Secrets and paste the API keys provided by Desktop Commander.")

st.markdown("---")

# --- MANUAL ORDER SECTION ---
st.header("🕹️ Pro Manual Terminal")

if not st.session_state.order_review_mode:
    with st.form("pro_order_form"):
        r1c1, r1c2, r1c3, r1c4 = st.columns(4)
        t_symbol = r1c1.text_input("Ticker Symbol", value="TSLA", help="e.g., TSLA, NVDA").upper()
        t_qty = r1c2.number_input("Shares", min_value=1, value=1)
        t_side = r1c3.selectbox("Action", ["buy", "sell"], help="Buy to enter, Sell to exit.")
        t_type = r1c4.selectbox("Order Type", ["market", "limit", "stop", "stop_limit", "trailing_stop", "bracket"],
                                help="Market = Now. Limit = Fixed Price. Stop = Trigger. Stop-Limit = Trigger to Fixed Price. Trailing = Follows the price. Bracket = Auto Profit + Auto Stop.")

        r2c1, r2c2, r2c3, r2c4 = st.columns(4)
        t_limit = r2c1.number_input("Limit Price ($)", min_value=0.01, step=0.01) if t_type in ["limit", "stop_limit", "bracket"] else None
        t_stop = r2c2.number_input("Stop/Trigger Price ($)", min_value=0.01, step=0.01) if t_type in ["stop", "stop_limit"] else None
        t_trail = r2c3.number_input("Trailing Percent (%)", min_value=0.1, max_value=25.0, value=5.0, step=0.1) if t_type == "trailing_stop" else None
        
        # Bracket specific inputs
        t_tp = None
        t_sl = None
        if t_type == "bracket":
            t_tp = r2c3.number_input("Take Profit Price ($)", min_value=0.01, step=0.01, help="If price hits this, sell for a win.")
            t_sl = r2c4.number_input("Stop Loss Price ($)", min_value=0.01, step=0.01, help="If price hits this, sell to prevent further loss.")

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
    # --- AI REVIEW & CONFIRMATION ---
    params = st.session_state.pending_order_params
    st.warning("⚠️ **TRADE ON HOLD.** Review AI analysis before confirming.")
    
    with st.container(border=True):
        st.markdown(get_ai_advice(params))
    
    btn_col1, btn_col2 = st.columns(2)
    if btn_col1.button("🔥 Confirm & Execute Trade", type="primary", use_container_width=True):
        try:
            api.submit_order(time_in_force='gtc', **params)
            st.success("SUCCESS: Order sent to Alpaca.")
            st.session_state.order_review_mode = False
            st.session_state.pending_order_params = None
            st.rerun()
        except Exception as e:
            st.error(f"Execution Failed: {e}")
            
    if btn_col2.button("⬅️ Cancel / Go Back", use_container_width=True):
        st.session_state.order_review_mode = False
        st.rerun()

st.markdown("---")
# --- BOTTOM INFO ---
col_left, col_right = st.columns(2)
with col_left:
    st.subheader("📊 Active Positions")
    positions = api.list_positions()
    if positions:
        df = pd.DataFrame([[p.symbol, p.qty, p.current_price, f"{float(p.unrealized_pl):.2f}"] for p in positions], 
                          columns=['Symbol', 'Qty', 'Price', 'Unrealized P/L'])
        st.dataframe(df, use_container_width=True)
    else: st.info("No active trades.")

with col_right:
    st.subheader("🤖 Bot Activity (Last 5)")
    tag_map = {"Trailing Stop Bot v1": "[TRAILING-STOP]", "Politician Tracker": "[POLITICIAN-TRACKER]", "The Wheel (Income)": "[THE-WHEEL]"}
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            bot_lines = [l.strip() for l in f.readlines() if tag_map[active_bot] in l][-5:]
            if bot_lines: st.code("\n".join(bot_lines[::-1]))
