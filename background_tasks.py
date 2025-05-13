import os
import logging
import threading
import time
from datetime import datetime, timedelta
import pandas as pd
from polygon import RESTClient

from models import db, ProcessingTask, HistoricalPrice
from database import save_price_data, save_etf_score

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BackgroundTaskService:
    """Service for running background tasks"""
    
    # Threading lock to prevent multiple threads from processing the same task
    _task_lock = threading.Lock()
    
    # Task worker thread
    _worker_thread = None
    
    # Stop event for graceful shutdown
    _stop_event = threading.Event()
    
    @staticmethod
    def start_worker():
        """Start the background task worker thread"""
        if BackgroundTaskService._worker_thread is None or not BackgroundTaskService._worker_thread.is_alive():
            BackgroundTaskService._stop_event.clear()
            BackgroundTaskService._worker_thread = threading.Thread(
                target=BackgroundTaskService._process_tasks,
                daemon=True
            )
            BackgroundTaskService._worker_thread.start()
            logger.info("Background task worker started")
    
    @staticmethod
    def stop_worker():
        """Stop the background task worker thread"""
        if BackgroundTaskService._worker_thread is not None and BackgroundTaskService._worker_thread.is_alive():
            BackgroundTaskService._stop_event.set()
            BackgroundTaskService._worker_thread.join(timeout=5.0)
            logger.info("Background task worker stopped")
    
    @staticmethod
    def _process_tasks():
        """Main task processing loop"""
        logger.info("Starting background task processing loop")
        
        while not BackgroundTaskService._stop_event.is_set():
            try:
                # Look for pending tasks
                with BackgroundTaskService._task_lock:
                    task = ProcessingTask.query.filter_by(status='pending').order_by(
                        ProcessingTask.created_at.asc()
                    ).first()
                    
                    if task:
                        # Mark task as running
                        task.start()
                        db.session.commit()
                        logger.info(f"Starting task {task.id}: {task.task_type}")
                        
                        # Process task based on type
                        if task.task_type == 'fetch_historical_data':
                            BackgroundTaskService._fetch_historical_data(task)
                        elif task.task_type == 'update_etf_scores':
                            BackgroundTaskService._update_etf_scores(task)
                        elif task.task_type == 'batch_stock_analysis':
                            BackgroundTaskService._batch_stock_analysis(task)
                        else:
                            logger.warning(f"Unknown task type: {task.task_type}")
                            task.fail(f"Unknown task type: {task.task_type}")
                            db.session.commit()
                    else:
                        # No pending tasks, sleep before checking again
                        time.sleep(5)
                        
            except Exception as e:
                logger.error(f"Error in task processing loop: {str(e)}")
                time.sleep(10)  # Longer sleep on error
    
    @staticmethod
    def _fetch_historical_data(task):
        """
        Fetch historical price data for symbols
        
        Task parameters:
        - symbols: List of symbols to fetch data for
        - days: Number of days of historical data to fetch (default: 180)
        - force_refresh: Whether to force refresh existing data (default: False)
        """
        try:
            # Get task parameters
            params = task.parameters or {}
            symbols = params.get('symbols', [])
            days = params.get('days', 180)
            force_refresh = params.get('force_refresh', False)
            
            if not symbols:
                task.fail("No symbols specified")
                db.session.commit()
                return
            
            # Calculate date range
            to_date = datetime.utcnow()
            from_date = to_date - timedelta(days=days)
            
            # Get Polygon API key
            api_key = os.environ.get("POLYGON_API_KEY")
            if not api_key:
                task.fail("No Polygon API key found")
                db.session.commit()
                return
            
            # Initialize client
            client = RESTClient(api_key=api_key)
            
            # Process each symbol
            results = {}
            for symbol in symbols:
                try:
                    # Skip if data already exists and not forcing refresh
                    if not force_refresh:
                        existing_count = HistoricalPrice.query.filter(
                            HistoricalPrice.symbol == symbol,
                            HistoricalPrice.timestamp >= from_date
                        ).count()
                        
                        if existing_count > 0:
                            logger.info(f"Skipping {symbol} - {existing_count} records already exist")
                            results[symbol] = {'status': 'skipped', 'reason': 'data_exists'}
                            continue
                    
                    # Fetch data from Polygon
                    aggs = client.get_aggs(
                        ticker=symbol,
                        multiplier=1,
                        timespan="day",
                        from_=from_date.strftime('%Y-%m-%d'),
                        to=to_date.strftime('%Y-%m-%d'),
                        limit=50000
                    )
                    
                    if aggs:
                        # Convert to DataFrame
                        df = pd.DataFrame([{
                            'timestamp': datetime.fromtimestamp(item.timestamp / 1000),
                            'Open': item.open,
                            'High': item.high,
                            'Low': item.low,
                            'Close': item.close,
                            'Volume': item.volume
                        } for item in aggs])
                        
                        # Save to database
                        if save_price_data(symbol, df, source='polygon'):
                            logger.info(f"Saved {len(df)} records for {symbol}")
                            results[symbol] = {'status': 'success', 'count': len(df)}
                        else:
                            logger.warning(f"Failed to save data for {symbol}")
                            results[symbol] = {'status': 'error', 'reason': 'save_failed'}
                    else:
                        logger.warning(f"No data found for {symbol}")
                        results[symbol] = {'status': 'error', 'reason': 'no_data'}
                
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {str(e)}")
                    results[symbol] = {'status': 'error', 'reason': str(e)}
            
            # Complete task
            task.complete(results)
            db.session.commit()
            logger.info(f"Historical data fetch completed for {len(symbols)} symbols")
            
        except Exception as e:
            logger.error(f"Error in fetch_historical_data task: {str(e)}")
            task.fail(str(e))
            db.session.commit()
    
    @staticmethod
    def _update_etf_scores(task):
        """
        Update ETF scores for all symbols
        
        Task parameters:
        - symbols: List of symbols to update scores for
        - force_refresh: Whether to force refresh existing scores (default: False)
        """
        try:
            # Get task parameters
            params = task.parameters or {}
            symbols = params.get('symbols', [])
            force_refresh = params.get('force_refresh', False)
            
            if not symbols:
                task.fail("No symbols specified")
                db.session.commit()
                return
            
            # Process each symbol
            from enhanced_etf_scoring import EnhancedEtfScoringService
            
            scoring_service = EnhancedEtfScoringService()
            results = {}
            
            for symbol in symbols:
                try:
                    # Calculate score
                    score, price, indicators = scoring_service.get_etf_score(
                        symbol, force_refresh=force_refresh
                    )
                    
                    # Save to database
                    if score > 0:
                        if save_etf_score(symbol, score, price, indicators):
                            logger.info(f"Updated score for {symbol}: {score}/5 (${price:.2f})")
                            results[symbol] = {'status': 'success', 'score': score, 'price': price}
                        else:
                            logger.warning(f"Failed to save score for {symbol}")
                            results[symbol] = {'status': 'error', 'reason': 'save_failed'}
                    else:
                        logger.warning(f"Invalid score (0) for {symbol}")
                        results[symbol] = {'status': 'error', 'reason': 'invalid_score'}
                
                except Exception as e:
                    logger.error(f"Error calculating score for {symbol}: {str(e)}")
                    results[symbol] = {'status': 'error', 'reason': str(e)}
            
            # Complete task
            task.complete(results)
            db.session.commit()
            logger.info(f"ETF score update completed for {len(symbols)} symbols")
            
        except Exception as e:
            logger.error(f"Error in update_etf_scores task: {str(e)}")
            task.fail(str(e))
            db.session.commit()
    
    @staticmethod
    def _batch_stock_analysis(task):
        """
        Analyze a batch of stocks (for VIP version)
        
        Task parameters:
        - symbols: List of symbols to analyze
        - batch_size: Size of each batch for processing (default: 20)
        """
        try:
            # Get task parameters
            params = task.parameters or {}
            symbols = params.get('symbols', [])
            batch_size = params.get('batch_size', 20)
            
            if not symbols:
                task.fail("No symbols specified")
                db.session.commit()
                return
            
            # Split into batches
            batches = [symbols[i:i+batch_size] for i in range(0, len(symbols), batch_size)]
            logger.info(f"Processing {len(symbols)} symbols in {len(batches)} batches")
            
            # Process each batch
            results = {}
            from enhanced_etf_scoring import EnhancedEtfScoringService
            
            scoring_service = EnhancedEtfScoringService()
            
            for i, batch in enumerate(batches):
                logger.info(f"Processing batch {i+1}/{len(batches)} ({len(batch)} symbols)")
                
                for symbol in batch:
                    try:
                        # Calculate score
                        score, price, indicators = scoring_service.get_etf_score(symbol, force_refresh=True)
                        
                        # Save to database
                        if score > 0:
                            if save_etf_score(symbol, score, price, indicators):
                                logger.info(f"Analyzed {symbol}: Score {score}/5 (${price:.2f})")
                                results[symbol] = {'status': 'success', 'score': score, 'price': price}
                            else:
                                logger.warning(f"Failed to save score for {symbol}")
                                results[symbol] = {'status': 'error', 'reason': 'save_failed'}
                        else:
                            logger.warning(f"Invalid score (0) for {symbol}")
                            results[symbol] = {'status': 'error', 'reason': 'invalid_score'}
                    
                    except Exception as e:
                        logger.error(f"Error analyzing {symbol}: {str(e)}")
                        results[symbol] = {'status': 'error', 'reason': str(e)}
                
                # Sleep between batches to respect API rate limits
                if i < len(batches) - 1:
                    time.sleep(2)
            
            # Complete task
            task.complete(results)
            db.session.commit()
            logger.info(f"Batch stock analysis completed for {len(symbols)} symbols")
            
        except Exception as e:
            logger.error(f"Error in batch_stock_analysis task: {str(e)}")
            task.fail(str(e))
            db.session.commit()
    
    @staticmethod
    def schedule_fetch_historical_data(symbols, days=180, force_refresh=False):
        """
        Schedule a task to fetch historical price data
        
        Args:
            symbols (list): List of symbols to fetch data for
            days (int): Number of days of historical data to fetch
            force_refresh (bool): Whether to force refresh existing data
            
        Returns:
            int: Task ID
        """
        try:
            # Create task
            task = ProcessingTask(
                task_type='fetch_historical_data',
                status='pending',
                parameters={
                    'symbols': symbols,
                    'days': days,
                    'force_refresh': force_refresh
                }
            )
            
            # Save to database
            db.session.add(task)
            db.session.commit()
            
            logger.info(f"Scheduled historical data fetch for {len(symbols)} symbols (task ID: {task.id})")
            return task.id
            
        except Exception as e:
            logger.error(f"Error scheduling fetch_historical_data task: {str(e)}")
            return None
    
    @staticmethod
    def schedule_update_etf_scores(symbols, force_refresh=False):
        """
        Schedule a task to update ETF scores
        
        Args:
            symbols (list): List of symbols to update scores for
            force_refresh (bool): Whether to force refresh existing scores
            
        Returns:
            int: Task ID
        """
        try:
            # Create task
            task = ProcessingTask(
                task_type='update_etf_scores',
                status='pending',
                parameters={
                    'symbols': symbols,
                    'force_refresh': force_refresh
                }
            )
            
            # Save to database
            db.session.add(task)
            db.session.commit()
            
            logger.info(f"Scheduled ETF score update for {len(symbols)} symbols (task ID: {task.id})")
            return task.id
            
        except Exception as e:
            logger.error(f"Error scheduling update_etf_scores task: {str(e)}")
            return None
    
    @staticmethod
    def schedule_batch_stock_analysis(symbols, batch_size=20):
        """
        Schedule a task to analyze a batch of stocks
        
        Args:
            symbols (list): List of symbols to analyze
            batch_size (int): Size of each batch for processing
            
        Returns:
            int: Task ID
        """
        try:
            # Create task
            task = ProcessingTask(
                task_type='batch_stock_analysis',
                status='pending',
                parameters={
                    'symbols': symbols,
                    'batch_size': batch_size
                }
            )
            
            # Save to database
            db.session.add(task)
            db.session.commit()
            
            logger.info(f"Scheduled batch analysis for {len(symbols)} symbols (task ID: {task.id})")
            return task.id
            
        except Exception as e:
            logger.error(f"Error scheduling batch_stock_analysis task: {str(e)}")
            return None
    
    @staticmethod
    def get_task_status(task_id):
        """
        Get the status of a task
        
        Args:
            task_id (int): Task ID
            
        Returns:
            dict: Task status
        """
        try:
            task = ProcessingTask.query.get(task_id)
            
            if task:
                return {
                    'id': task.id,
                    'type': task.task_type,
                    'status': task.status,
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                    'started_at': task.started_at.isoformat() if task.started_at else None,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                    'result': task.result,
                    'error': task.error
                }
            else:
                return {'error': 'Task not found'}
                
        except Exception as e:
            logger.error(f"Error getting task status: {str(e)}")
            return {'error': str(e)}