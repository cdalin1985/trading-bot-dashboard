# Trading Bot Dashboard

This is a live trading dashboard built with Streamlit and the Alpaca Trade API.

## Features
- Real-time portfolio metrics (Buying Power, Portfolio Value, Daily P/L)
- Active positions tracking
- Bot fleet status monitoring

## Setup
To run this on Streamlit Cloud, you must add your Alpaca API keys to the 'Secrets' section of the dashboard settings:

```toml
ALPACA_API_KEY = "your_api_key"
ALPACA_SECRET_KEY = "your_secret_key"
ALPACA_BASE_URL = "https://paper-api.alpaca.markets"
```