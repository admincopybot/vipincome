"""
Custom implementation of key TA-Lib functions for ETF scoring
This module mimics the TA-Lib API for the specific indicators we need
"""
import numpy as np
import pandas as pd

def MA(close, timeperiod=30, matype=0):
    """
    Moving Average - mimics TA-Lib's MA function
    
    Parameters:
    -----------
    close : numpy.ndarray or pd.Series
        Close prices
    timeperiod : int
        Number of periods for moving average
    matype : int
        Moving average type (0=SMA, 1=EMA, 2=WMA, 3=DEMA, 4=TEMA, 
               5=TRIMA, 6=KAMA, 7=MAMA, 8=T3)
        
    Returns:
    --------
    numpy.ndarray
        Moving average values
    """
    if isinstance(close, pd.Series):
        close = close.values
    
    if matype == 1:  # EMA
        # Calculate multiplier
        multiplier = 2.0 / (timeperiod + 1)
        
        # Initialize EMA with SMA
        ema = np.zeros_like(close)
        ema[:timeperiod] = np.nan
        ema[timeperiod-1] = np.mean(close[:timeperiod])
        
        # Calculate EMA
        for i in range(timeperiod, len(close)):
            ema[i] = (close[i] - ema[i-1]) * multiplier + ema[i-1]
            
        return ema
    else:  # Default to SMA
        result = np.zeros_like(close)
        for i in range(len(close)):
            if i < timeperiod - 1:
                result[i] = np.nan
            else:
                result[i] = np.mean(close[i-timeperiod+1:i+1])
        return result

def EMA(close, timeperiod=30):
    """
    Exponential Moving Average - mimics TA-Lib's EMA function
    
    Parameters:
    -----------
    close : numpy.ndarray or pd.Series
        Close prices
    timeperiod : int
        Number of periods for EMA
        
    Returns:
    --------
    numpy.ndarray
        EMA values
    """
    return MA(close, timeperiod, matype=1)

def SMA(close, timeperiod=30):
    """
    Simple Moving Average - mimics TA-Lib's SMA function
    
    Parameters:
    -----------
    close : numpy.ndarray or pd.Series
        Close prices
    timeperiod : int
        Number of periods for SMA
        
    Returns:
    --------
    numpy.ndarray
        SMA values
    """
    return MA(close, timeperiod, matype=0)

def RSI(close, timeperiod=14):
    """
    Relative Strength Index - mimics TA-Lib's RSI function
    
    Parameters:
    -----------
    close : numpy.ndarray or pd.Series
        Close prices
    timeperiod : int
        Number of periods for RSI
        
    Returns:
    --------
    numpy.ndarray
        RSI values
    """
    if isinstance(close, pd.Series):
        close = close.values
    
    # Calculate price differences
    delta = np.zeros_like(close)
    delta[1:] = close[1:] - close[:-1]
    
    # Separate gains and losses
    gain = np.zeros_like(delta)
    loss = np.zeros_like(delta)
    
    gain[delta > 0] = delta[delta > 0]
    loss[delta < 0] = -delta[delta < 0]
    
    # Calculate average gain and loss
    avg_gain = np.zeros_like(close)
    avg_loss = np.zeros_like(close)
    
    # First average is simple average
    avg_gain[timeperiod] = np.mean(gain[1:timeperiod+1])
    avg_loss[timeperiod] = np.mean(loss[1:timeperiod+1])
    
    # Rest uses smoothing
    for i in range(timeperiod + 1, len(close)):
        avg_gain[i] = (avg_gain[i-1] * (timeperiod-1) + gain[i]) / timeperiod
        avg_loss[i] = (avg_loss[i-1] * (timeperiod-1) + loss[i]) / timeperiod
    
    # Calculate RS and RSI
    rs = np.zeros_like(close)
    rsi = np.zeros_like(close)
    
    # Avoid division by zero
    avg_loss_nonzero = np.where(avg_loss == 0, 0.001, avg_loss)
    rs = avg_gain / avg_loss_nonzero
    
    rsi = 100 - (100 / (1 + rs))
    rsi[:timeperiod] = np.nan
    
    return rsi

def ATR(high, low, close, timeperiod=14):
    """
    Average True Range - mimics TA-Lib's ATR function
    
    Parameters:
    -----------
    high : numpy.ndarray or pd.Series
        High prices
    low : numpy.ndarray or pd.Series
        Low prices
    close : numpy.ndarray or pd.Series
        Close prices
    timeperiod : int
        Number of periods for ATR
        
    Returns:
    --------
    numpy.ndarray
        ATR values
    """
    # Convert to numpy arrays if Series
    if isinstance(high, pd.Series):
        high = high.values
    if isinstance(low, pd.Series):
        low = low.values
    if isinstance(close, pd.Series):
        close = close.values
    
    # Calculate true range
    tr = np.zeros_like(close)
    tr[0] = high[0] - low[0]  # First TR is just the first day's range
    
    for i in range(1, len(close)):
        hl = high[i] - low[i]
        hpc = abs(high[i] - close[i-1])
        lpc = abs(low[i] - close[i-1])
        tr[i] = max(hl, hpc, lpc)
    
    # Calculate ATR using simple moving average
    atr = np.zeros_like(close)
    atr[:timeperiod] = np.nan
    atr[timeperiod-1] = np.mean(tr[:timeperiod])
    
    # Rest uses smoothing (Wilder's method)
    for i in range(timeperiod, len(close)):
        atr[i] = (atr[i-1] * (timeperiod-1) + tr[i]) / timeperiod
    
    return atr