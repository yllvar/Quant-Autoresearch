import pytest
import os
import pandas as pd
from unittest.mock import patch, MagicMock
from data.preprocessor import prepare_data, CACHE_DIR, SYMBOLS

def test_prepare_data_logic(tmp_path, monkeypatch):
    """Verifies that prepare_data downloads and calculates features correctly."""
    # Use tmp_path for cache
    cache_dir = tmp_path / "data_cache_test"
    monkeypatch.setattr("data.preprocessor.CACHE_DIR", str(cache_dir))
    
    # Mock CCXT
    mock_exchange = MagicMock()
    # Mock fetch_ohlcv to return one day of data
    mock_exchange.fetch_ohlcv.return_value = [
        [1672531200000, 100.0, 105.0, 95.0, 102.0, 1000]
    ]
    # Mock parse8601
    mock_exchange.parse8601.return_value = 1672531200000
    # Mock milliseconds to return slightly after
    mock_exchange.milliseconds.return_value = 1672531200000 + 1000
    mock_exchange.rateLimit = 10
    
    # Mock data for yfinance too
    dates = pd.date_range(start="2023-01-01", periods=2, freq="D")
    mock_df_yf = pd.DataFrame({
        "Open": [100.0, 101.0],
        "High": [105.0, 106.0],
        "Low": [95.0, 96.0],
        "Close": [101.0, 102.0],
        "Volume": [1000, 1100]
    }, index=dates)
    
    with patch("ccxt.binance", return_value=mock_exchange), \
         patch("yfinance.download", return_value=mock_df_yf):
        
        prepare_data()
        
        # Verify cache directory exists
        assert cache_dir.exists()
        
        # Verify files are created
        for symbol in SYMBOLS:
            file_name = f"{symbol.replace('-', '_')}.parquet"
            assert (cache_dir / file_name).exists()
            
            # Load and check features
            df = pd.read_parquet(cache_dir / file_name)
            assert "returns" in df.columns
            assert "volatility" in df.columns
            assert "atr" in df.columns
