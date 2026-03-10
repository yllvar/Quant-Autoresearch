import os
import pandas as pd
import yfinance as yf
import ccxt
from datetime import datetime
import time

SYMBOLS = ['SPY', 'QQQ', 'IWM', 'BTC-USD', 'ETH-USD']
CRYPTO_MAP = {
    'BTC-USD': 'BTC/USDT',
    'ETH-USD': 'ETH/USDT'
}
START_DATE = "2020-01-01"
CACHE_DIR = "data/cache"

def ensure_cache_dir():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

def calculate_atr(df, window=14):
    high = df['High']
    low = df['Low']
    close_prev = df['Close'].shift(1)
    
    tr1 = high - low
    tr2 = (high - close_prev).abs()
    tr3 = (low - close_prev).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=window).mean()
    return atr

def fetch_crypto_ccxt(symbol, start_date):
    """Fetches crypto data from Binance via CCXT."""
    exchange = ccxt.binance()
    ccxt_symbol = CRYPTO_MAP.get(symbol, symbol.replace('-', '/'))
    
    since = exchange.parse8601(f"{start_date}T00:00:00Z")
    all_ohlcv = []
    
    print(f"  [CCXT] Fetching {ccxt_symbol} from Binance...")
    while since < exchange.milliseconds():
        ohlcv = exchange.fetch_ohlcv(ccxt_symbol, timeframe='1d', since=since, limit=1000)
        if not ohlcv:
            break
        all_ohlcv.extend(ohlcv)
        since = ohlcv[-1][0] + 86400000  # increment since by one day
        time.sleep(exchange.rateLimit / 1000)
        
    df = pd.DataFrame(all_ohlcv, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df['Date'] = pd.to_datetime(df['Timestamp'], unit='ms')
    df.set_index('Date', inplace=True)
    df.drop(columns=['Timestamp'], inplace=True)
    return df

def prepare_data():
    ensure_cache_dir()
    cached_count = 0
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    for symbol in SYMBOLS:
        cache_path = os.path.join(CACHE_DIR, f"{symbol.replace('-', '_')}.parquet")
        
        if os.path.exists(cache_path):
            print(f"Skipping {symbol}, already cached.")
            cached_count += 1
            continue
            
        print(f"Processing {symbol}...")
        try:
            if symbol in CRYPTO_MAP:
                df = fetch_crypto_ccxt(symbol, START_DATE)
            else:
                print(f"  [yfinance] Downloading {symbol}...")
                df = yf.download(symbol, start=START_DATE, end=end_date)
                # Flatten columns if MultiIndex
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)

            if df.empty:
                print(f"Warning: No data found for {symbol}")
                continue
            
            # Feature Calculation (Safe from look-ahead bias)
            df['returns'] = df['Close'].pct_change()
            df['volatility'] = df['returns'].rolling(window=20).std()
            df['atr'] = calculate_atr(df)
            
            # Save to Parquet
            df.to_parquet(cache_path)
            cached_count += 1
            
        except Exception as e:
            print(f"Error processing {symbol}: {e}")

    print(f"Data Ready: {cached_count} symbols cached.")

if __name__ == "__main__":
    prepare_data()
