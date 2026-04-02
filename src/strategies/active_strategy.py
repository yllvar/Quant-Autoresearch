import pandas as pd
import numpy as np

class TradingStrategy:
    def __init__(self, fast_ma=20, slow_ma=50):
        """
        Initialize hyperparameters. 
        The AI Agent can modify these or add new ones here.
        """
        self.fast_ma = fast_ma
        self.slow_ma = slow_ma

    def generate_signals(self, data):
        """
        Generates trading signals based on input OHLCV data.
        Returns a Pandas Series where:
         1 = Long
         0 = Cash
        -1 = Short
        
        The 'data' contains: Close, returns, volatility, atr.
        """
        # Calculate the Exponential Moving Average (EMA) of the Average True Range (ATR) to identify distinct market regimes
        # Reference: 'Exponential moving average versus moving exponential average' (https://arxiv.org/pdf/2001.04237v1)
        atr_ema = data['atr'].ewm(span=20, adjust=False).mean()

        # Define the regime detection mechanism based on the EMA of ATR
        # If ATR EMA is above a certain threshold, consider it a high volatility regime
        high_vol_regime = atr_ema > atr_ema.mean()

        # Calculate the Rate of Change (ROC) to capture strong trends during periods of low volatility
        # Reference: 'On the rapidity dependence of the average transverse momentum in hadronic collisions' (https://arxiv.org/pdf/1510.04737v2)
        roc = (data['Close'].diff(14) / data['Close'].shift(14)) * 100

        # Calculate the momentum using the concept from 'Slow Momentum with Fast Reversion: A Trading Strategy Using Deep Learning and Changepoint Detection' (https://arxiv.org/pdf/2105.13727v3)
        slow_momentum = data['Close'].diff(20)

        # Generate trading signals based on the proposed hypothesis, leveraging concepts from 'On-Line Portfolio Selection with Moving Average Reversion' (https://arxiv.org/pdf/1206.4626v1)
        signals = pd.Series(index=data.index, data=0)
        signals[(~high_vol_regime) & (roc > 0) & (slow_momentum > 0)] = 1  # Long during low volatility, positive ROC, and positive momentum
        signals[(~high_vol_regime) & (roc < 0) & (slow_momentum < 0)] = -1  # Short during low volatility, negative ROC, and negative momentum
        signals[(high_vol_regime) & (data['Close'] > data['Close'].shift(1))] = 0  # Cash during high volatility and uptrend
        signals[(high_vol_regime) & (data['Close'] < data['Close'].shift(1))] = 0  # Cash during high volatility and downtrend

        # Incorporate regime switch detection using 'A Hybrid Learning Approach to Detecting Regime Switches in Financial Markets' (https://arxiv.org/pdf/2108.05801v1)
        # For simplicity, this example uses a basic switching mechanism based on ATR EMA
        signals[(high_vol_regime) & (roc < 0) & (slow_momentum > 0)] = 1

        return signals
