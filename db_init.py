"""
Database initialization for Income Machine
This module provides database setup and shared database instance.
"""

import logging
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the base model class
class Base(DeclarativeBase):
    """Base class for SQLAlchemy models"""
    pass

# Create SQLAlchemy instance
db = SQLAlchemy(model_class=Base)

def init_app(app):
    """Initialize the app with SQLAlchemy"""
    db.init_app(app)
    logger.info("Database initialized with app")
    
    # Import models to ensure they're registered
    with app.app_context():
        import models
        db.create_all()
        logger.info("Database tables created")