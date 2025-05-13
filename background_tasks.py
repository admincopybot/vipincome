"""
Background task processing for Income Machine
This module provides a service for running background tasks like data fetching and ETF scoring.
"""

import logging
import json
import time
import threading
import datetime
import pandas as pd
from queue import Queue, Empty

from models import ProcessingTask, db
from database import save_price_data, save_etf_score
from enhanced_polygon_client import EnhancedPolygonService
from simplified_market_data import SimplifiedMarketDataService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BackgroundTaskService:
    """Service for running background tasks"""
    
    _tasks = {}  # Dictionary to hold task objects by ID
    _task_lock = threading.Lock()  # Lock for accessing tasks
    _task_queue = Queue()  # Queue of task IDs to process
    _worker_thread = None  # Worker thread
    _stop_event = threading.Event()  # Event to signal worker to stop
    
    @classmethod
    def start_worker(cls):
        """Start the background task worker thread"""
        if cls._worker_thread is not None and cls._worker_thread.is_alive():
            logger.info("Worker thread already running")
            return
        
        cls._stop_event.clear()
        cls._worker_thread = threading.Thread(target=cls._process_tasks)
        cls._worker_thread.daemon = True
        cls._worker_thread.start()
        logger.info("Started background task worker thread")
    
    @classmethod
    def stop_worker(cls):
        """Stop the background task worker thread"""
        if cls._worker_thread is None or not cls._worker_thread.is_alive():
            logger.info("No worker thread running")
            return
        
        logger.info("Stopping background task worker thread...")
        cls._stop_event.set()
        
        # Give the worker thread time to finish
        cls._worker_thread.join(timeout=5.0)
        if cls._worker_thread.is_alive():
            logger.warning("Worker thread did not stop cleanly")
        else:
            logger.info("Worker thread stopped")
        
        cls._worker_thread = None
    
    @classmethod
    def _process_tasks(cls):
        """Main task processing loop"""
        logger.info("Task processing loop started")
        
        while not cls._stop_event.is_set():
            try:
                # Get next task from queue with timeout
                try:
                    task_id = cls._task_queue.get(timeout=1.0)
                except Empty:
                    continue
                
                logger.info(f"Processing task {task_id}")
                
                # Get task from database or memory
                task = cls._get_task(task_id)
                if not task:
                    logger.warning(f"Task {task_id} not found")
                    continue
                
                # Update task status
                task.status = 'running'
                task.save()
                
                # Process task based on type
                try:
                    if task.type == 'fetch_historical_data':
                        cls._fetch_historical_data(task)
                    elif task.type == 'update_etf_scores':
                        cls._update_etf_scores(task)
                    elif task.type == 'batch_stock_analysis':
                        cls._batch_stock_analysis(task)
                    else:
                        logger.warning(f"Unknown task type: {task.type}")
                        task.fail(f"Unknown task type: {task.type}")
                        continue
                    
                    logger.info(f"Task {task_id} completed")
                    task.complete()
                
                except Exception as e:
                    logger.error(f"Error processing task {task_id}: {str(e)}")
                    task.fail(str(e))
                
                finally:
                    # Mark task as done in queue
                    cls._task_queue.task_done()
            
            except Exception as e:
                logger.error(f"Error in task processing loop: {str(e)}")
                time.sleep(1.0)  # Prevent tight loop on error
    
    @classmethod
    def _get_task(cls, task_id):
        """Get task by ID from memory or database"""
        with cls._task_lock:
            task = cls._tasks.get(task_id)
            if task:
                return task
        
        # Not in memory, try database
        try:
            task = ProcessingTask.select().where(ProcessingTask.id == task_id).first()
            if task:
                # Store in memory for future access
                with cls._task_lock:
                    cls._tasks[task_id] = task
                return task
        except Exception as e:
            logger.error(f"Error getting task {task_id} from database: {str(e)}")
        
        return None
    
    @classmethod
    def _fetch_historical_data(cls, task):
        """
        Fetch historical price data for symbols
        
        Task parameters:
        - symbols: List of symbols to fetch data for
        - days: Number of days of historical data to fetch (default: 180)
        - force_refresh: Whether to force refresh existing data (default: False)
        """
        params = task.get_parameters()
        symbols = params.get('symbols', [])
        days = params.get('days', 180)
        force_refresh = params.get('force_refresh', False)
        
        if not symbols:
            raise ValueError("No symbols specified")
        
        # Calculate from_date
        to_date = datetime.datetime.now()
        from_date = to_date - datetime.timedelta(days=days)
        
        # Process each symbol
        results = {'success': [], 'failed': []}
        total_symbols = len(symbols)
        
        for i, symbol in enumerate(symbols):
            # Update progress
            progress = int((i / total_symbols) * 100)
            task.update_progress(progress)
            
            try:
                logger.info(f"Fetching historical data for {symbol} ({i+1}/{total_symbols})")
                
                # Get data from Polygon.io
                df = EnhancedPolygonService.get_historical_data(
                    symbol, 
                    timespan="day",
                    from_date=from_date.strftime('%Y-%m-%d'),
                    to_date=to_date.strftime('%Y-%m-%d'),
                    limit=5000
                )
                
                if df is not None and not df.empty:
                    # Convert polygon.io data format
                    df = pd.DataFrame({
                        'timestamp': df.index / 1000000000,  # Convert nanoseconds to seconds
                        'open': df['open'],
                        'high': df['high'],
                        'low': df['low'],
                        'close': df['close'],
                        'volume': df['volume']
                    })
                    
                    # Convert timestamp to datetime
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                    
                    # Save to database
                    success = save_price_data(symbol, df, source='polygon')
                    
                    if success:
                        results['success'].append(symbol)
                    else:
                        results['failed'].append({'symbol': symbol, 'error': 'Failed to save data'})
                else:
                    # Fall back to yfinance
                    logger.info(f"No data from Polygon.io for {symbol}, trying yfinance")
                    
                    import yfinance as yf
                    df = yf.download(
                        symbol, 
                        start=from_date.strftime('%Y-%m-%d'),
                        end=to_date.strftime('%Y-%m-%d'),
                        progress=False
                    )
                    
                    if df is not None and not df.empty:
                        # Rename columns to match our format
                        df = df.rename(columns={
                            'Open': 'open',
                            'High': 'high',
                            'Low': 'low',
                            'Close': 'close',
                            'Volume': 'volume'
                        })
                        
                        # Save to database
                        success = save_price_data(symbol, df, source='yfinance')
                        
                        if success:
                            results['success'].append(symbol)
                        else:
                            results['failed'].append({'symbol': symbol, 'error': 'Failed to save data'})
                    else:
                        results['failed'].append({'symbol': symbol, 'error': 'No data available'})
            
            except Exception as e:
                logger.error(f"Error fetching data for {symbol}: {str(e)}")
                results['failed'].append({'symbol': symbol, 'error': str(e)})
        
        # Return summary of results
        return {
            'total': total_symbols,
            'successful': len(results['success']),
            'failed': len(results['failed']),
            'symbols': {
                'success': results['success'],
                'failed': results['failed']
            }
        }
    
    @classmethod
    def _update_etf_scores(cls, task):
        """
        Update ETF scores for all symbols
        
        Task parameters:
        - symbols: List of symbols to update scores for
        - force_refresh: Whether to force refresh existing scores (default: False)
        """
        params = task.get_parameters()
        symbols = params.get('symbols', [])
        force_refresh = params.get('force_refresh', False)
        
        if not symbols:
            raise ValueError("No symbols specified")
        
        # Process each symbol
        results = {'success': [], 'failed': []}
        total_symbols = len(symbols)
        
        for i, symbol in enumerate(symbols):
            # Update progress
            progress = int((i / total_symbols) * 100)
            task.update_progress(progress)
            
            try:
                logger.info(f"Calculating score for {symbol} ({i+1}/{total_symbols})")
                
                # Calculate score
                score, price, indicators = SimplifiedMarketDataService.get_etf_score(symbol, force_refresh=force_refresh)
                
                if score is not None:
                    # Save to database
                    success = save_etf_score(symbol, score, price, indicators)
                    
                    if success:
                        results['success'].append(symbol)
                    else:
                        results['failed'].append({'symbol': symbol, 'error': 'Failed to save score'})
                else:
                    results['failed'].append({'symbol': symbol, 'error': 'Failed to calculate score'})
            
            except Exception as e:
                logger.error(f"Error calculating score for {symbol}: {str(e)}")
                results['failed'].append({'symbol': symbol, 'error': str(e)})
        
        # Return summary of results
        return {
            'total': total_symbols,
            'successful': len(results['success']),
            'failed': len(results['failed']),
            'symbols': {
                'success': results['success'],
                'failed': results['failed']
            }
        }
    
    @classmethod
    def _batch_stock_analysis(cls, task):
        """
        Analyze a batch of stocks (for VIP version)
        
        Task parameters:
        - symbols: List of symbols to analyze
        - batch_size: Size of each batch for processing (default: 20)
        """
        params = task.get_parameters()
        symbols = params.get('symbols', [])
        batch_size = params.get('batch_size', 20)
        
        if not symbols:
            raise ValueError("No symbols specified")
        
        # Process symbols in batches
        results = {'scores': {}, 'failed': []}
        total_symbols = len(symbols)
        
        for i in range(0, total_symbols, batch_size):
            # Get current batch
            batch = symbols[i:i+batch_size]
            batch_size_actual = len(batch)
            
            # Update progress
            progress = int((i / total_symbols) * 100)
            task.update_progress(progress, f"Processing batch {i//batch_size + 1}")
            
            # Process each symbol in batch
            for j, symbol in enumerate(batch):
                try:
                    logger.info(f"Analyzing {symbol} ({i+j+1}/{total_symbols})")
                    
                    # Calculate score (use same method as ETFs for now)
                    score, price, indicators = SimplifiedMarketDataService.get_etf_score(symbol, force_refresh=True)
                    
                    if score is not None:
                        results['scores'][symbol] = {
                            'score': score,
                            'price': price,
                            'indicators': indicators
                        }
                    else:
                        results['failed'].append({'symbol': symbol, 'error': 'Failed to calculate score'})
                
                except Exception as e:
                    logger.error(f"Error analyzing {symbol}: {str(e)}")
                    results['failed'].append({'symbol': symbol, 'error': str(e)})
        
        # Return results
        return {
            'total': total_symbols,
            'successful': len(results['scores']),
            'failed': len(results['failed']),
            'scores': results['scores'],
            'failed_symbols': results['failed']
        }
    
    @classmethod
    def schedule_fetch_historical_data(cls, symbols, days=180, force_refresh=False):
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
                type='fetch_historical_data',
                parameters=json.dumps({
                    'symbols': symbols,
                    'days': days,
                    'force_refresh': force_refresh
                }),
                status='pending',
                progress=0,
                created_at=datetime.datetime.now(),
                updated_at=datetime.datetime.now()
            )
            task.save()
            
            # Add to queue
            cls._task_queue.put(task.id)
            
            # Store in memory
            with cls._task_lock:
                cls._tasks[task.id] = task
            
            logger.info(f"Scheduled fetch_historical_data task {task.id} for {len(symbols)} symbols")
            return task.id
        
        except Exception as e:
            logger.error(f"Error scheduling fetch_historical_data task: {str(e)}")
            return None
    
    @classmethod
    def schedule_update_etf_scores(cls, symbols, force_refresh=False):
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
                type='update_etf_scores',
                parameters=json.dumps({
                    'symbols': symbols,
                    'force_refresh': force_refresh
                }),
                status='pending',
                progress=0,
                created_at=datetime.datetime.now(),
                updated_at=datetime.datetime.now()
            )
            task.save()
            
            # Add to queue
            cls._task_queue.put(task.id)
            
            # Store in memory
            with cls._task_lock:
                cls._tasks[task.id] = task
            
            logger.info(f"Scheduled update_etf_scores task {task.id} for {len(symbols)} symbols")
            return task.id
        
        except Exception as e:
            logger.error(f"Error scheduling update_etf_scores task: {str(e)}")
            return None
    
    @classmethod
    def schedule_batch_stock_analysis(cls, symbols, batch_size=20):
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
                type='batch_stock_analysis',
                parameters=json.dumps({
                    'symbols': symbols,
                    'batch_size': batch_size
                }),
                status='pending',
                progress=0,
                created_at=datetime.datetime.now(),
                updated_at=datetime.datetime.now()
            )
            task.save()
            
            # Add to queue
            cls._task_queue.put(task.id)
            
            # Store in memory
            with cls._task_lock:
                cls._tasks[task.id] = task
            
            logger.info(f"Scheduled batch_stock_analysis task {task.id} for {len(symbols)} symbols")
            return task.id
        
        except Exception as e:
            logger.error(f"Error scheduling batch_stock_analysis task: {str(e)}")
            return None
    
    @classmethod
    def get_task_status(cls, task_id):
        """
        Get the status of a task
        
        Args:
            task_id (int): Task ID
            
        Returns:
            dict: Task status
        """
        try:
            task = cls._get_task(task_id)
            
            if not task:
                return None
            
            # Get result if completed
            result = None
            if task.status == 'completed':
                result = task.get_result()
            
            # Get error if failed
            error = None
            if task.status == 'failed':
                error = task.error
            
            return {
                'id': task.id,
                'type': task.type,
                'status': task.status,
                'progress': task.progress,
                'parameters': task.get_parameters(),
                'result': result,
                'error': error,
                'created_at': task.created_at.isoformat() if task.created_at else None,
                'updated_at': task.updated_at.isoformat() if task.updated_at else None
            }
        
        except Exception as e:
            logger.error(f"Error getting task status for {task_id}: {str(e)}")
            return None