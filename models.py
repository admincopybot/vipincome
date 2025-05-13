"""
Database models for Income Machine
This module defines SQLAlchemy models for the database.
"""

import json
from datetime import datetime
from db_init import db

class BaseModel(db.Model):
    """Base model with common methods"""
    __abstract__ = True
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class HistoricalPrice(BaseModel):
    """Historical price data for a symbol"""
    __tablename__ = 'historical_prices'
    
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    timespan = db.Column(db.String(20), nullable=False, default='day')
    open_price = db.Column(db.Float, nullable=False)
    high_price = db.Column(db.Float, nullable=False)
    low_price = db.Column(db.Float, nullable=False)
    close_price = db.Column(db.Float, nullable=False)
    volume = db.Column(db.BigInteger, nullable=False)
    source = db.Column(db.String(20), nullable=False, default='polygon')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    
    class Meta:
        """Model metadata"""
        indexes = [
            db.Index('idx_historical_prices_symbol_timestamp', 'symbol', 'timestamp'),
            db.Index('idx_historical_prices_timespan', 'timespan')
        ]
    
    def __repr__(self):
        return f"<HistoricalPrice {self.symbol} @ {self.timestamp}: {self.close_price}>"

class ETFScore(BaseModel):
    """Technical score for an ETF"""
    __tablename__ = 'etf_scores'
    
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), nullable=False, index=True)
    score = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    indicators = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now, index=True)
    
    class Meta:
        """Model metadata"""
        indexes = [
            db.Index('idx_etf_scores_symbol_timestamp', 'symbol', 'timestamp')
        ]
    
    def __repr__(self):
        return f"<ETFScore {self.symbol}: {self.score}/5 @ {self.price}>"
    
    def get_indicators(self):
        """Get indicators as dictionary"""
        if not self.indicators:
            return {}
        return json.loads(self.indicators)

class BacktestResult(BaseModel):
    """Backtest results for a specific date"""
    __tablename__ = 'backtest_results'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(10), nullable=False, index=True, unique=True)
    results = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now, index=True)
    
    class Meta:
        """Model metadata"""
        indexes = [
            db.Index('idx_backtest_results_date', 'date')
        ]
    
    def __repr__(self):
        return f"<BacktestResult {self.date}>"
    
    def get_results(self):
        """Get results as dictionary"""
        if not self.results:
            return {}
        return json.loads(self.results)

class ProcessingTask(BaseModel):
    """Background processing task"""
    __tablename__ = 'processing_tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    task_type = db.Column(db.String(50), nullable=False, index=True)
    parameters = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='pending', index=True)
    progress = db.Column(db.Integer, nullable=False, default=0)
    results = db.Column(db.Text, nullable=True)
    error = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now, index=True)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f"<ProcessingTask {self.id}: {self.task_type} ({self.status})>"
    
    def get_parameters(self):
        """Get parameters as dictionary"""
        if not self.parameters:
            return {}
        return json.loads(self.parameters)
    
    def get_results(self):
        """Get results as dictionary"""
        if not self.results:
            return {}
        return json.loads(self.results)
    
    def update_status(self, status, progress=None, results=None, error=None):
        """Update task status"""
        self.status = status
        
        if progress is not None:
            self.progress = progress
        
        if status == 'running' and not self.started_at:
            self.started_at = datetime.now()
        
        if status in ['completed', 'failed']:
            self.completed_at = datetime.now()
        
        if results:
            self.results = json.dumps(results) if isinstance(results, dict) else results
        
        if error:
            self.error = error
        
        return self