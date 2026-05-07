import requests
import re
import time
from datetime import datetime

def scan_congressional_trades():
    """
    Scrapes Capitol Trades for the most recent ticker symbols traded by politicians.
    """
    url = "https://www.capitoltrades.com/trades"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        
        # Look for ticker symbols like "TSLA:US" or "PLTR:US" in the HTML
        # Tickers on Capitol Trades often appear in links like /issuers/432035 and then the text is "Ticker:US"
        tickers = re.findall(r'([A-Z]+):US', response.text)
        
        # Filter out common false positives and return the most recent one
        valid_tickers = [t for t in tickers if t not in ["USD", "US"]]
        if valid_tickers:
            # Return the first one (most recent)
            return valid_tickers[0]
            
    except Exception as e:
        print(f"Error scanning trades: {e}")
        
    return None

if __name__ == "__main__":
    ticker = scan_congressional_trades()
    print(f"Latest detected ticker: {ticker}")
