from app import db
from datetime import datetime

class EtfScore(db.Model):
    """Database model to store calculated ETF scores and criteria results"""
    __tablename__ = 'etf_scores'
    
    symbol = db.Column(db.String(10), primary_key=True)
    current_price = db.Column(db.Numeric(12, 4))
    total_score = db.Column(db.Integer)
    
    # Trend 1: Price > 20 EMA
    trend1_pass = db.Column(db.Boolean)
    trend1_current = db.Column(db.Numeric(12, 4))
    trend1_threshold = db.Column(db.Numeric(12, 4))
    trend1_description = db.Column(db.Text)
    
    # Trend 2: Price > 100 EMA
    trend2_pass = db.Column(db.Boolean)
    trend2_current = db.Column(db.Numeric(12, 4))
    trend2_threshold = db.Column(db.Numeric(12, 4))
    trend2_description = db.Column(db.Text)
    
    # Snapback: RSI < 50
    snapback_pass = db.Column(db.Boolean)
    snapback_current = db.Column(db.Numeric(6, 2))
    snapback_threshold = db.Column(db.Numeric(6, 2))
    snapback_description = db.Column(db.Text)
    
    # Momentum: Price > Previous Week Close
    momentum_pass = db.Column(db.Boolean)
    momentum_current = db.Column(db.Numeric(12, 4))
    momentum_threshold = db.Column(db.Numeric(12, 4))
    momentum_description = db.Column(db.Text)
    
    # Stabilizing: 3-day ATR < 6-day ATR
    stabilizing_pass = db.Column(db.Boolean)
    stabilizing_current = db.Column(db.Numeric(10, 6))
    stabilizing_threshold = db.Column(db.Numeric(10, 6))
    stabilizing_description = db.Column(db.Text)
    
    # Metadata
    calculation_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    data_age_hours = db.Column(db.Integer)
    sector = db.Column(db.String(50))
    
    def to_dict(self):
        """Convert to dictionary format matching the original app structure"""
        return {
            'symbol': self.symbol,
            'price': float(self.current_price) if self.current_price else 0.0,
            'score': self.total_score or 0,
            'sector': self.sector or 'Unknown',
            'indicators': {
                'trend1': {
                    'pass': self.trend1_pass or False,
                    'current': float(self.trend1_current) if self.trend1_current else 0.0,
                    'threshold': float(self.trend1_threshold) if self.trend1_threshold else 0.0,
                    'description': self.trend1_description or 'No data available'
                },
                'trend2': {
                    'pass': self.trend2_pass or False,
                    'current': float(self.trend2_current) if self.trend2_current else 0.0,
                    'threshold': float(self.trend2_threshold) if self.trend2_threshold else 0.0,
                    'description': self.trend2_description or 'No data available'
                },
                'snapback': {
                    'pass': self.snapback_pass or False,
                    'current': float(self.snapback_current) if self.snapback_current else 50.0,
                    'threshold': float(self.snapback_threshold) if self.snapback_threshold else 50.0,
                    'description': self.snapback_description or 'No data available'
                },
                'momentum': {
                    'pass': self.momentum_pass or False,
                    'current': float(self.momentum_current) if self.momentum_current else 0.0,
                    'threshold': float(self.momentum_threshold) if self.momentum_threshold else 0.0,
                    'description': self.momentum_description or 'No data available'
                },
                'stabilizing': {
                    'pass': self.stabilizing_pass or False,
                    'current': float(self.stabilizing_current) if self.stabilizing_current else 0.0,
                    'threshold': float(self.stabilizing_threshold) if self.stabilizing_threshold else 0.0,
                    'description': self.stabilizing_description or 'No data available'
                }
            }
        }