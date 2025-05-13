import json
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON

db = SQLAlchemy()

class HistoricalPrice(db.Model):
    """Model for storing historical price data for ETFs and stocks"""
    __tablename__ = 'historical_prices'
    
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), index=True, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, nullable=False)
    open = db.Column(db.Float, nullable=False)
    high = db.Column(db.Float, nullable=False)
    low = db.Column(db.Float, nullable=False)
    close = db.Column(db.Float, nullable=False)
    volume = db.Column(db.BigInteger, nullable=False)
    source = db.Column(db.String(20), nullable=False, default='polygon')  # Source of data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Create a composite index for faster queries by symbol and date range
    __table_args__ = (
        db.Index('idx_historical_prices_symbol_timestamp', 'symbol', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<HistoricalPrice('{self.symbol}', {self.timestamp}, {self.close})>"
    
    @staticmethod
    def from_polygon_agg(symbol, agg):
        """Create a HistoricalPrice instance from a Polygon aggregates result"""
        return HistoricalPrice(
            symbol=symbol,
            timestamp=datetime.fromtimestamp(agg.timestamp / 1000),  # Convert ms to seconds
            open=agg.open,
            high=agg.high,
            low=agg.low,
            close=agg.close,
            volume=agg.volume,
            source='polygon'
        )


class ETFScore(db.Model):
    """Model for storing calculated ETF scores"""
    __tablename__ = 'etf_scores'
    
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), index=True, nullable=False)
    score = db.Column(db.Integer, nullable=False)
    current_price = db.Column(db.Float, nullable=False)
    indicators = db.Column(JSON, nullable=False)  # JSON field to store all indicator details
    calculation_timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<ETFScore('{self.symbol}', score={self.score}, price=${self.current_price})>"
    
    def get_indicators(self):
        """Parse the JSON indicators field"""
        if isinstance(self.indicators, str):
            return json.loads(self.indicators)
        return self.indicators
    
    def set_indicators(self, indicators_dict):
        """Store indicators as JSON"""
        if isinstance(indicators_dict, dict):
            self.indicators = indicators_dict
        else:
            self.indicators = json.loads(str(indicators_dict))


class BacktestResult(db.Model):
    """Model for storing backtest results"""
    __tablename__ = 'backtest_results'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, index=True, nullable=False)
    data = db.Column(JSON, nullable=False)  # JSON field to store all backtest data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<BacktestResult({self.date}, created at {self.created_at})>"


class ProcessingTask(db.Model):
    """Model for tracking background processing tasks"""
    __tablename__ = 'processing_tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    task_type = db.Column(db.String(50), index=True, nullable=False)  # e.g., 'update_etf_scores', 'fetch_historical'
    status = db.Column(db.String(20), index=True, nullable=False)  # 'pending', 'running', 'completed', 'failed'
    parameters = db.Column(JSON, nullable=True)  # Parameters for the task
    result = db.Column(JSON, nullable=True)  # Results, if any
    error = db.Column(db.Text, nullable=True)  # Error message, if failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f"<ProcessingTask({self.task_type}, {self.status})>"
    
    def start(self):
        """Mark the task as started"""
        self.status = 'running'
        self.started_at = datetime.utcnow()
    
    def complete(self, result=None):
        """Mark the task as completed"""
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
        if result:
            self.result = result
    
    def fail(self, error):
        """Mark the task as failed"""
        self.status = 'failed'
        self.completed_at = datetime.utcnow()
        self.error = str(error)