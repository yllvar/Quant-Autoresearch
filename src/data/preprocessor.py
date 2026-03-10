import os
from data.connector import DataConnector
from utils.logger import logger

SYMBOLS = ['SPY', 'QQQ', 'IWM', 'BTC-USD', 'ETH-USD']
START_DATE = "2020-01-01"
CACHE_DIR = "data/cache"

def prepare_data():
    """Main function to prepare data for research, now using the DataConnector interface."""
    connector = DataConnector(CACHE_DIR)
    cached_count = 0
    
    logger.info(f"📊 Starting Data Preparation (Target Symbols: {len(SYMBOLS)})")
    
    for symbol in SYMBOLS:
        # Check if symbol is already cached
        clean_symbol = symbol.replace("-", "_")
        cache_path = os.path.join(CACHE_DIR, f"{clean_symbol}.parquet")
        
        if os.path.exists(cache_path):
            logger.info(f"   ✅ Skipping {symbol}, already cached.")
            cached_count += 1
            continue
            
        logger.info(f"   🔄 Processing {symbol}...")
        success = connector.fetch_and_cache(symbol, START_DATE)
        if success:
            cached_count += 1
        else:
            logger.error(f"   ❌ Failed to process {symbol}")

    logger.info(f"🏁 Data Ready: {cached_count} symbols cached.")

if __name__ == "__main__":
    prepare_data()
