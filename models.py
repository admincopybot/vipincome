"""
Database models for Income Machine
This module defines the database models for storing historical data, ETF scores, and backtest results.
"""

import datetime
import json
import logging
from peewee import (
    Model, SqliteDatabase, PostgresqlDatabase,
    CharField, FloatField, IntegerField, TextField, DateTimeField,
    BooleanField, ForeignKeyField
)
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
if os.environ.get('DATABASE_URL'):
    # PostgreSQL - for production
    try:
        db = PostgresqlDatabase(
            database=os.environ.get('PGDATABASE'),
            user=os.environ.get('PGUSER'),
            password=os.environ.get('PGPASSWORD'),
            host=os.environ.get('PGHOST'),
            port=os.environ.get('PGPORT')
        )
        logger.info("Using PostgreSQL database")
    except Exception as e:
        logger.error(f"Error connecting to PostgreSQL: {str(e)}")
        # Fallback to SQLite
        db = SqliteDatabase('income_machine.db')
        logger.warning("Falling back to SQLite database")
else:
    # SQLite - for development
    db = SqliteDatabase('income_machine.db')
    logger.info("Using SQLite database")

class BaseModel(Model):
    """Base model class for all database models"""
    
    class Meta:
        database = db

class HistoricalPrice(BaseModel):
    """
    Model for caching historical price data
    """
    symbol = CharField(max_length=16)
    date = DateTimeField()
    open_price = FloatField()
    high = FloatField()
    low = FloatField()
    close = FloatField()
    volume = IntegerField(null=True)
    timespan = CharField(max_length=16, default='day')  # day, hour, minute, etc.
    source = CharField(max_length=16, default='polygon')  # polygon, yahoo, etc.
    created_at = DateTimeField(default=datetime.datetime.now)
    
    class Meta:
        indexes = (
            (('symbol', 'date', 'timespan'), True),  # Unique index
        )

class ETFScore(BaseModel):
    """
    Model for caching ETF technical scores
    """
    symbol = CharField(max_length=16)
    score = IntegerField()
    price = FloatField()
    indicators = TextField()  # JSON encoded indicators
    created_at = DateTimeField(default=datetime.datetime.now)
    
    class Meta:
        indexes = (
            (('symbol',), False),  # Non-unique index
        )
    
    def get_indicators(self):
        """Get parsed indicators dictionary"""
        try:
            return json.loads(self.indicators)
        except:
            return {}

class BacktestResult(BaseModel):
    """
    Model for caching backtest results
    """
    date = CharField(max_length=10)  # YYYY-MM-DD
    symbols = TextField()  # Comma-separated list of symbols
    results = TextField()  # JSON encoded results
    created_at = DateTimeField(default=datetime.datetime.now)
    
    class Meta:
        indexes = (
            (('date',), False),  # Non-unique index
        )

class ProcessingTask(BaseModel):
    """
    Model for tracking background processing tasks
    """
    type = CharField(max_length=32)  # fetch_historical_data, update_etf_scores, etc.
    parameters = TextField()  # JSON encoded parameters
    status = CharField(max_length=16, default='pending')  # pending, running, completed, failed
    progress = FloatField(default=0)  # 0-100
    result = TextField(null=True)  # JSON encoded result
    error = TextField(null=True)  # Error message if failed
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField(default=datetime.datetime.now)
    
    def update_progress(self, progress, status=None):
        """Update task progress"""
        self.progress = progress
        if status:
            self.status = status
        self.updated_at = datetime.datetime.now()
        self.save()
    
    def complete(self, result=None):
        """Mark task as completed"""
        self.status = 'completed'
        if result:
            self.result = json.dumps(result)
        self.progress = 100
        self.updated_at = datetime.datetime.now()
        self.save()
    
    def fail(self, error):
        """Mark task as failed"""
        self.status = 'failed'
        self.error = str(error)
        self.updated_at = datetime.datetime.now()
        self.save()
    
    def get_parameters(self):
        """Get parsed parameters dictionary"""
        try:
            return json.loads(self.parameters)
        except:
            return {}
    
    def get_result(self):
        """Get parsed result dictionary"""
        try:
            return json.loads(self.result) if self.result else None
        except:
            return None

# Create tables
def create_tables():
    """Create database tables for all models"""
    with db:
        db.create_tables([HistoricalPrice, ETFScore, BacktestResult, ProcessingTask])
        logger.info("Database tables created")

# Create tables if running as main
if __name__ == '__main__':
    create_tables()