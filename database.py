"""
Database module for Income Machine
This module provides database-related functions including initialization, caching, and retrieval.
"""

import logging
import json
import time
from datetime import datetime, timedelta
import pandas as pd
import os
from flask_sqlalchemy import SQLAlchemy
from models import HistoricalPrice, ETFScore, BacktestResult, ProcessingTask

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = None

def init_db(app):
    """Initialize database with app context"""
    global db
    from app import db as app_db
    db = app_db
    logger.info("Database initialized")

def get_cached_price_data(symbol, timespan="day", from_date=None, limit=200):
    """
    Get historical price data from database cache
    
    Args:
        symbol (str): Ticker symbol
        timespan (str): Timeframe ("day", "hour", etc.)
        from_date (datetime): Start date for data
        limit (int): Maximum number of records to return
        
    Returns:
        DataFrame or None: Historical price data or None if not in cache
    """
    try:
        if db is None:
            logger.error("Database not initialized")
            return None
        
        # Prepare query filters
        filters = {
            'symbol': symbol,
            'timespan': timespan
        }
        
        # Add from_date filter if provided
        if from_date:
            filters['timestamp__gte'] = from_date
        
        # Get historical prices from database
        query = HistoricalPrice.query.filter_by(**filters).order_by(HistoricalPrice.timestamp.desc()).limit(limit)
        records = query.all()
        
        if not records:
            logger.info(f"No cached price data for {symbol} ({timespan})")
            return None
        
        # Convert to DataFrame
        data = []
        for record in records:
            data.append({
                'timestamp': record.timestamp,
                'open': record.open_price,
                'high': record.high_price,
                'low': record.low_price,
                'close': record.close_price,
                'volume': record.volume
            })
        
        if not data:
            return None
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Set timestamp as index
        df.set_index('timestamp', inplace=True)
        
        # Sort by timestamp
        df.sort_index(inplace=True)
        
        logger.info(f"Retrieved {len(df)} cached price records for {symbol}")
        return df
    
    except Exception as e:
        logger.error(f"Error getting cached price data for {symbol}: {str(e)}")
        return None

def save_price_data(symbol, df, source='polygon'):
    """
    Save price data to database cache
    
    Args:
        symbol (str): Ticker symbol
        df (DataFrame): Price data
        source (str): Data source (default: 'polygon')
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if db is None:
            logger.error("Database not initialized")
            return False
        
        if df is None or df.empty:
            logger.warning(f"No data to save for {symbol}")
            return False
        
        # Reset index to access timestamp as column
        df_save = df.reset_index()
        
        # Get existing records to avoid duplicates
        existing_timestamps = set()
        existing_records = HistoricalPrice.query.filter_by(symbol=symbol).all()
        for record in existing_records:
            existing_timestamps.add(record.timestamp.timestamp() if isinstance(record.timestamp, datetime) else record.timestamp)
        
        # Prepare records to insert
        records_to_insert = []
        for _, row in df_save.iterrows():
            # Skip if already exists
            record_timestamp = row['timestamp']
            if isinstance(record_timestamp, (int, float)):
                # Convert Unix timestamp (ms) to seconds
                if record_timestamp > 1e12:  # If in milliseconds
                    record_timestamp = record_timestamp / 1000
                
                # Convert to datetime
                dt = datetime.fromtimestamp(record_timestamp)
            else:
                dt = record_timestamp
                record_timestamp = dt.timestamp()
            
            if record_timestamp in existing_timestamps:
                continue
            
            # Create new record
            record = HistoricalPrice(
                symbol=symbol,
                timestamp=dt,
                timespan='day',  # Default to daily data
                open_price=float(row['open']),
                high_price=float(row['high']),
                low_price=float(row['low']),
                close_price=float(row['close']),
                volume=int(row['volume']),
                source=source
            )
            
            records_to_insert.append(record)
        
        if records_to_insert:
            # Insert in chunks to avoid timeout
            chunk_size = 100
            for i in range(0, len(records_to_insert), chunk_size):
                chunk = records_to_insert[i:i+chunk_size]
                db.session.add_all(chunk)
                db.session.commit()
            
            logger.info(f"Saved {len(records_to_insert)} new price records for {symbol}")
        else:
            logger.info(f"No new price records to save for {symbol}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error saving price data for {symbol}: {str(e)}")
        # Rollback on error
        db.session.rollback()
        return False

def get_cached_etf_score(symbol, max_age_minutes=60):
    """
    Get cached ETF score from database
    
    Args:
        symbol (str): ETF symbol
        max_age_minutes (int): Maximum age of cached score in minutes
        
    Returns:
        tuple or None: (score, price, indicators) if found, None otherwise
    """
    try:
        if db is None:
            logger.error("Database not initialized")
            return None
        
        # Calculate the oldest acceptable timestamp
        oldest_time = datetime.now() - timedelta(minutes=max_age_minutes)
        
        # Get the most recent score
        score_record = ETFScore.query.filter_by(symbol=symbol).filter(ETFScore.timestamp > oldest_time).order_by(ETFScore.timestamp.desc()).first()
        
        if score_record:
            # Parse indicators JSON
            indicators = json.loads(score_record.indicators) if score_record.indicators else {}
            
            logger.info(f"Retrieved cached score for {symbol}: {score_record.score}/5 (timestamp: {score_record.timestamp})")
            return score_record.score, score_record.price, indicators
        
        logger.info(f"No recent cached score for {symbol}")
        return None
    
    except Exception as e:
        logger.error(f"Error getting cached ETF score for {symbol}: {str(e)}")
        return None

def save_etf_score(symbol, score, price, indicators):
    """
    Save ETF score to database
    
    Args:
        symbol (str): ETF symbol
        score (int): Technical score (0-5)
        price (float): Current price
        indicators (dict): Indicator details
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if db is None:
            logger.error("Database not initialized")
            return False
        
        # Create new score record
        score_record = ETFScore(
            symbol=symbol,
            score=score,
            price=float(price),
            indicators=json.dumps(indicators),
            timestamp=datetime.now()
        )
        
        # Save to database
        db.session.add(score_record)
        db.session.commit()
        
        logger.info(f"Saved new score for {symbol}: {score}/5")
        return True
    
    except Exception as e:
        logger.error(f"Error saving ETF score for {symbol}: {str(e)}")
        # Rollback on error
        db.session.rollback()
        return False

def get_cached_backtest(date_str):
    """
    Get cached backtest results
    
    Args:
        date_str (str): Date string (YYYY-MM-DD)
        
    Returns:
        dict or None: Backtest results if found, None otherwise
    """
    try:
        if db is None:
            logger.error("Database not initialized")
            return None
        
        # Get backtest record
        backtest_record = BacktestResult.query.filter_by(date=date_str).first()
        
        if backtest_record:
            # Parse JSON
            results = json.loads(backtest_record.results)
            
            logger.info(f"Retrieved cached backtest for {date_str}")
            return results
        
        logger.info(f"No cached backtest for {date_str}")
        return None
    
    except Exception as e:
        logger.error(f"Error getting cached backtest for {date_str}: {str(e)}")
        return None

def save_backtest(date_str, results):
    """
    Save backtest results to database
    
    Args:
        date_str (str): Date string (YYYY-MM-DD)
        results (dict): Backtest results
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if db is None:
            logger.error("Database not initialized")
            return False
        
        # Convert results to JSON
        results_json = json.dumps(results)
        
        # Check if record already exists
        existing_record = BacktestResult.query.filter_by(date=date_str).first()
        
        if existing_record:
            # Update existing record
            existing_record.results = results_json
            existing_record.timestamp = datetime.now()
        else:
            # Create new record
            record = BacktestResult(
                date=date_str,
                results=results_json,
                timestamp=datetime.now()
            )
            db.session.add(record)
        
        # Save to database
        db.session.commit()
        
        logger.info(f"Saved backtest results for {date_str}")
        return True
    
    except Exception as e:
        logger.error(f"Error saving backtest for {date_str}: {str(e)}")
        # Rollback on error
        db.session.rollback()
        return False

def get_task(task_id):
    """
    Get task by ID
    
    Args:
        task_id (int): Task ID
        
    Returns:
        ProcessingTask or None: Task if found, None otherwise
    """
    try:
        if db is None:
            logger.error("Database not initialized")
            return None
        
        # Get task record
        task = ProcessingTask.query.filter_by(id=task_id).first()
        
        if task:
            logger.debug(f"Retrieved task {task_id}")
            return task
        
        logger.info(f"No task found with ID {task_id}")
        return None
    
    except Exception as e:
        logger.error(f"Error getting task {task_id}: {str(e)}")
        return None

def save_task(task):
    """
    Save task to database
    
    Args:
        task (ProcessingTask): Task object
        
    Returns:
        int or None: Task ID if successful, None otherwise
    """
    try:
        if db is None:
            logger.error("Database not initialized")
            return None
        
        # Save to database
        db.session.add(task)
        db.session.commit()
        
        logger.info(f"Saved task {task.id}")
        return task.id
    
    except Exception as e:
        logger.error(f"Error saving task: {str(e)}")
        # Rollback on error
        db.session.rollback()
        return None