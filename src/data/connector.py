import os
import pandas as pd
import yfinance as yf
import ccxt
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from utils.logger import logger

class DataConnector:
    """Unified interface for market data ingestion, retrieval, and automated updates."""
    
    CRYPTO_MAP = {
        'BTC-USD': 'BTC/USDT',
        'ETH-USD': 'ETH/USDT',
        'SOL-USD': 'SOL/USDT',
    }

    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        
    def load_all_cached(self) -> Dict[str, pd.DataFrame]:
        """Load all compatible data files from the cache directory"""
        data = {}
        if not os.path.exists(self.cache_dir):
            return data
            
        for file in os.listdir(self.cache_dir):
            path = os.path.join(self.cache_dir, file)
            symbol = None
            df = None
            
            try:
                if file.endswith(".parquet"):
                    symbol = file.replace(".parquet", "").replace("_", "-")
                    df = pd.read_parquet(path)
                elif file.endswith(".csv"):
                    symbol = file.replace(".csv", "").replace("_", "-")
                    df = pd.read_csv(path, index_col=0, parse_dates=True)
                    
                if symbol and df is not None and not df.empty:
                    data[symbol] = df
            except Exception as e:
                logger.error(f"Error loading {file}: {e}")
                
        return data
        
    def load_symbol(self, symbol: str) -> Optional[pd.DataFrame]:
        """Load a specific symbol from cache"""
        clean_symbol = symbol.replace("-", "_")
        parquet_path = os.path.join(self.cache_dir, f"{clean_symbol}.parquet")
        csv_path = os.path.join(self.cache_dir, f"{clean_symbol}.csv")
        
        if os.path.exists(parquet_path):
            return pd.read_parquet(parquet_path)
        elif os.path.exists(csv_path):
            return pd.read_csv(csv_path, index_col=0, parse_dates=True)
            
        return None

    def fetch_and_cache(self, symbol: str, start_date: str = "2020-01-01"):
        """Fetch data from yfinance or CCXT and save to cache."""
        try:
            if symbol in self.CRYPTO_MAP:
                df = self._fetch_crypto_ccxt(symbol, start_date)
            else:
                df = self._fetch_yfinance(symbol, start_date)
            
            if df is not None and not df.empty:
                # Calculate required features
                df = self._add_features(df)
                self.save_data(symbol, df)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to fetch/cache {symbol}: {e}")
            return False

    def _fetch_yfinance(self, symbol: str, start_date: str) -> Optional[pd.DataFrame]:
        end_date = datetime.now().strftime('%Y-%m-%d')
        df = yf.download(symbol, start=start_date, end=end_date)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df

    def _fetch_crypto_ccxt(self, symbol: str, start_date: str) -> Optional[pd.DataFrame]:
        exchange = ccxt.binance()
        ccxt_symbol = self.CRYPTO_MAP.get(symbol, symbol.replace('-', '/'))
        since = exchange.parse8601(f"{start_date}T00:00:00Z")
        all_ohlcv = []
        
        while since < exchange.milliseconds():
            ohlcv = exchange.fetch_ohlcv(ccxt_symbol, timeframe='1d', since=since, limit=1000)
            if not ohlcv: break
            all_ohlcv.extend(ohlcv)
            since = ohlcv[-1][0] + 86400000
            time.sleep(exchange.rateLimit / 1000)
            
        df = pd.DataFrame(all_ohlcv, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['Date'] = pd.to_datetime(df['Timestamp'], unit='ms')
        df.set_index('Date', inplace=True)
        df.drop(columns=['Timestamp'], inplace=True)
        return df

    def _add_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['returns'] = df['Close'].pct_change()
        df['volatility'] = df['returns'].rolling(window=20).std()
        
        # ATR Calculation
        high, low, close_prev = df['High'], df['Low'], df['Close'].shift(1)
        tr = pd.concat([high - low, (high - close_prev).abs(), (low - close_prev).abs()], axis=1).max(axis=1)
        df['atr'] = tr.rolling(window=14).mean()
        return df

    def save_data(self, symbol: str, df: pd.DataFrame, format: str = "parquet"):
        clean_symbol = symbol.replace("-", "_")
        path = os.path.join(self.cache_dir, f"{clean_symbol}.{format}")
        if format == "parquet":
            df.to_parquet(path)
        else:
            df.to_csv(path)
        logger.info(f"Saved {symbol} data to {path}")

    def ingest_custom_csv(self, file_path: str, symbol: str):
        """Import a custom CSV file into the system cache"""
        try:
            df = pd.read_csv(file_path, index_col=0, parse_dates=True)
            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in df.columns for col in required_cols):
                logger.error(f"CSV missing required columns: {required_cols}")
                return False
            
            df = self._add_features(df)
            self.save_data(symbol, df)
            return True
        except Exception as e:
            logger.error(f"Failed to ingest custom CSV {file_path}: {e}")
            return False
