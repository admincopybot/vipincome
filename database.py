import os
import logging
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize SQLAlchemy
db = SQLAlchemy()

def init_db(app):
    """Initialize database with app context"""
    # Configure database
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_size": 10,  # Maximum number of connections in the pool
        "pool_recycle": 300,  # Recycle connections after 5 minutes
        "pool_pre_ping": True,  # Test connections before using them
        "max_overflow": 20  # Allow up to 20 connections beyond pool_size
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Initialize database with app
    db.init_app(app)
    
    # Create tables
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {str(e)}")
            raise

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
    from models import HistoricalPrice
    import pandas as pd
    
    try:
        if from_date is None:
            # Default to 180 days ago if no date provided
            from_date = datetime.utcnow() - timedelta(days=180)
        
        # Query cache
        query = HistoricalPrice.query.filter(
            HistoricalPrice.symbol == symbol,
            HistoricalPrice.timestamp >= from_date
        ).order_by(
            HistoricalPrice.timestamp.desc()
        ).limit(limit)
        
        results = query.all()
        
        if results and len(results) > 0:
            # Convert to dataframe
            df = pd.DataFrame([{
                'timestamp': row.timestamp,
                'open': row.open,
                'high': row.high,
                'low': row.low,
                'close': row.close,
                'volume': row.volume
            } for row in results])
            
            # Sort by timestamp
            df = df.sort_values('timestamp')
            
            # Set timestamp as index
            df.set_index('timestamp', inplace=True)
            
            # Rename columns to match expected format
            df = df.rename(columns={
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            })
            
            logger.info(f"Retrieved {len(df)} cached price records for {symbol}")
            return df
        else:
            logger.info(f"No cached price data found for {symbol}")
            return None
    except Exception as e:
        logger.error(f"Error retrieving cached price data for {symbol}: {str(e)}")
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
    from models import HistoricalPrice
    from sqlalchemy.exc import IntegrityError
    
    try:
        # Reset index if timestamp is the index
        if df.index.name == 'timestamp':
            df = df.reset_index()
        
        # Create records to insert
        records = []
        for _, row in df.iterrows():
            # Extract timestamp - handle both string date formats and datetime objects
            if 'timestamp' in row:
                timestamp = row['timestamp']
            elif 'date' in row:
                timestamp = row['date']
            else:
                logger.error(f"No timestamp or date column found in data for {symbol}")
                return False
            
            # Convert string timestamps to datetime if needed
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
            # Extract price data - handle both capitalized and lowercase column names
            open_price = row.get('Open', row.get('open', 0))
            high_price = row.get('High', row.get('high', 0))
            low_price = row.get('Low', row.get('low', 0))
            close_price = row.get('Close', row.get('close', 0))
            volume = row.get('Volume', row.get('volume', 0))
            
            # Create price record
            price = HistoricalPrice(
                symbol=symbol,
                timestamp=timestamp,
                open=float(open_price),
                high=float(high_price),
                low=float(low_price),
                close=float(close_price),
                volume=int(volume),
                source=source
            )
            records.append(price)
        
        # Bulk insert
        try:
            db.session.bulk_save_objects(records)
            db.session.commit()
            logger.info(f"Saved {len(records)} price records for {symbol}")
            return True
        except IntegrityError:
            # Handle unique constraint violations - data already exists
            db.session.rollback()
            logger.warning(f"Some price records for {symbol} already exist - skipping duplicates")
            
            # Insert one by one to skip duplicates
            for record in records:
                try:
                    db.session.add(record)
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()
                    continue
            
            return True
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving price data for {symbol}: {str(e)}")
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
    from models import ETFScore
    
    try:
        # Calculate maximum age timestamp
        max_age = datetime.utcnow() - timedelta(minutes=max_age_minutes)
        
        # Query for most recent score that's not too old
        score = ETFScore.query.filter(
            ETFScore.symbol == symbol,
            ETFScore.calculation_timestamp >= max_age
        ).order_by(
            ETFScore.calculation_timestamp.desc()
        ).first()
        
        if score:
            logger.info(f"Retrieved cached score for {symbol}: {score.score}/5 (${score.current_price:.2f})")
            return score.score, score.current_price, score.get_indicators()
        else:
            logger.info(f"No valid cached score found for {symbol}")
            return None
    except Exception as e:
        logger.error(f"Error retrieving cached score for {symbol}: {str(e)}")
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
    from models import ETFScore
    
    try:
        # Create new score record
        etf_score = ETFScore(
            symbol=symbol,
            score=score,
            current_price=price,
            indicators=indicators,
            calculation_timestamp=datetime.utcnow()
        )
        
        # Save to database
        db.session.add(etf_score)
        db.session.commit()
        
        logger.info(f"Saved new score for {symbol}: {score}/5 (${price:.2f})")
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving score for {symbol}: {str(e)}")
        return False