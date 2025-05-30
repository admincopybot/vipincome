"""
Gamma RSI Momentum Calculator
Implements the exact TradingView Pine Script calculation for Gamma RSI Momentum indicator
"""

import pandas as pd
import numpy as np
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class GammaRSICalculator:
    """
    Implements the exact Gamma RSI Momentum calculation from TradingView Pine Script
    """
    
    @staticmethod
    def calculate_gamma_rsi(df: pd.DataFrame, nFE: int = 13) -> Optional[float]:
        """
        Calculate Gamma RSI Momentum using the exact TradingView Pine Script logic
        
        Args:
            df: DataFrame with OHLC data
            nFE: Fractal Efficiency Period (default: 13)
            
        Returns:
            Current Gamma RSI value or None if insufficient data
        """
        if len(df) < nFE + 10:  # Need extra periods for recursive smoothing
            logger.warning(f"Insufficient data for Gamma RSI calculation: {len(df)} < {nFE + 10}")
            return None
            
        # Ensure we have the required columns
        required_cols = ['Open', 'High', 'Low', 'Close']
        if not all(col in df.columns for col in required_cols):
            logger.error(f"Missing required columns. Have: {list(df.columns)}, Need: {required_cols}")
            return None
            
        # Convert to numpy arrays for faster calculation
        open_prices = df['Open'].values
        high_prices = df['High'].values
        low_prices = df['Low'].values
        close_prices = df['Close'].values
        
        n = len(df)
        
        # Initialize arrays for calculations
        o = np.zeros(n)
        h = np.zeros(n)
        l = np.zeros(n)
        c = np.zeros(n)
        gamma = np.zeros(n)
        
        # Initialize recursive smoothing variables
        L0 = np.zeros(n)
        L1 = np.zeros(n)
        L2 = np.zeros(n)
        L3 = np.zeros(n)
        
        # Calculate for each period
        for i in range(1, n):  # Start from 1 because we need previous close
            # === Gamma Calculation (Fractal Efficiency) ===
            o[i] = (open_prices[i] + close_prices[i-1]) / 2
            h[i] = max(high_prices[i], close_prices[i-1])
            l[i] = min(low_prices[i], close_prices[i-1])
            c[i] = (o[i] + h[i] + l[i] + close_prices[i]) / 4
            
            # Calculate HL Range for the fractal efficiency period
            if i >= nFE:
                hlRange_sum = 0
                for j in range(i - nFE + 1, i + 1):
                    hlRange = max(high_prices[j], close_prices[j-1] if j > 0 else high_prices[j]) - \
                             min(low_prices[j], close_prices[j-1] if j > 0 else low_prices[j])
                    hlRange_sum += hlRange
                
                # Find highest high and lowest low in the period
                period_high = high_prices[i - nFE + 1:i + 1].max()
                period_low = low_prices[i - nFE + 1:i + 1].min()
                
                # Include previous close in the range check
                for j in range(max(0, i - nFE + 1), i + 1):
                    if j > 0:
                        period_high = max(period_high, close_prices[j-1])
                        period_low = min(period_low, close_prices[j-1])
                
                denominator = period_high - period_low
                if denominator != 0:
                    gamma[i] = np.log(hlRange_sum / denominator) / np.log(nFE)
                else:
                    gamma[i] = 0.0
            else:
                gamma[i] = gamma[i-1] if i > 0 else 0.0
            
            # === Recursive Smoothing ===
            if i == 1:
                # Initialize first values
                L0[i] = (open_prices[i] + close_prices[i]) / 4
                L1[i] = L0[i]
                L2[i] = L0[i]
                L3[i] = L0[i]
            else:
                # Recursive formulas from Pine Script
                L0[i] = (1 - gamma[i]) * c[i] + gamma[i] * L0[i-1]
                L1[i] = -gamma[i] * L0[i] + L0[i-1] + gamma[i] * L1[i-1]
                L2[i] = -gamma[i] * L1[i] + L1[i-1] + gamma[i] * L2[i-1]
                L3[i] = -gamma[i] * L2[i] + L2[i-1] + gamma[i] * L3[i-1]
        
        # === Up/Down Components ===
        CU = np.zeros(n)
        CD = np.zeros(n)
        
        for i in range(1, n):
            # CU1, CD1
            CU1 = L0[i] - L1[i] if L0[i] >= L1[i] else 0
            CD1 = L1[i] - L0[i] if L0[i] < L1[i] else 0
            
            # CU2, CD2
            CU2 = CU1 + (L1[i] - L2[i]) if L1[i] >= L2[i] else CU1
            CD2 = CD1 + (L2[i] - L1[i]) if L1[i] < L2[i] else CD1
            
            # CU, CD
            CU[i] = CU2 + (L2[i] - L3[i]) if L2[i] >= L3[i] else CU2
            CD[i] = CD2 + (L3[i] - L2[i]) if L2[i] < L3[i] else CD2
        
        # === Final RSI Calculation ===
        RSI = np.zeros(n)
        for i in range(n):
            if (CU[i] + CD[i]) != 0:
                RSI[i] = (CU[i] / (CU[i] + CD[i])) - 0.5
            else:
                RSI[i] = np.nan
        
        # Return the most recent valid RSI value
        valid_rsi = RSI[~np.isnan(RSI)]
        if len(valid_rsi) > 0:
            return float(valid_rsi[-1])
        else:
            return None
    
    @staticmethod
    def calculate_gamma_rsi_signal(df: pd.DataFrame, nFE: int = 13) -> Optional[dict]:
        """
        Calculate Gamma RSI with signal detection (change direction)
        
        Returns:
            Dictionary with current RSI, previous RSI, change, and signal
        """
        if len(df) < nFE + 15:  # Need extra periods for change calculation
            return None
            
        # Calculate RSI for the last few periods to detect change
        current_rsi = GammaRSICalculator.calculate_gamma_rsi(df, nFE)
        
        # Calculate previous RSI
        if len(df) > 1:
            df_prev = df.iloc[:-1].copy()
            previous_rsi = GammaRSICalculator.calculate_gamma_rsi(df_prev, nFE)
        else:
            previous_rsi = None
        
        if current_rsi is not None and previous_rsi is not None:
            change = current_rsi - previous_rsi
            signal = 1 if change > 0 else -1 if change < 0 else 0
            
            return {
                'current_rsi': current_rsi,
                'previous_rsi': previous_rsi,
                'change': change,
                'signal': signal,
                'direction': 'BREAK UP' if change > 0 else 'BREAK DOWN' if change < 0 else 'NEUTRAL'
            }
        
        return {
            'current_rsi': current_rsi,
            'previous_rsi': previous_rsi,
            'change': None,
            'signal': 0,
            'direction': 'INSUFFICIENT_DATA'
        }