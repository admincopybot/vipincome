import os
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from models import db, HistoricalPrice, ETFScore, BacktestResult, ProcessingTask
from database import get_cached_etf_score
from backtest_service import BacktestService
from background_tasks import BackgroundTaskService
from simplified_market_data import SimplifiedMarketDataService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Blueprint for API routes
api = Blueprint('api', __name__)

@api.route('/etf/score/<symbol>', methods=['GET'])
def get_etf_score(symbol):
    """
    Get the technical score for an ETF
    
    Query Parameters:
    - force_refresh: Set to 'true' to force calculation of a new score (default: false)
    """
    try:
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        
        # Check cache first unless force refresh
        if not force_refresh:
            cached_score = get_cached_etf_score(symbol)
            if cached_score:
                score, price, indicators = cached_score
                return jsonify({
                    'symbol': symbol,
                    'score': score,
                    'price': price,
                    'indicators': indicators
                })
        
        # Calculate new score
        score, price, indicators = SimplifiedMarketDataService._calculate_etf_score(
            symbol, force_refresh=True
        )
        
        return jsonify({
            'symbol': symbol,
            'score': score,
            'price': price,
            'indicators': indicators
        })
    
    except Exception as e:
        logger.error(f"Error getting ETF score: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api.route('/etf/scores', methods=['GET'])
def get_etf_scores():
    """
    Get technical scores for multiple ETFs
    
    Query Parameters:
    - symbols: Comma-separated list of symbols (default: all tracked ETFs)
    - force_refresh: Set to 'true' to force calculation of new scores (default: false)
    """
    try:
        symbols_param = request.args.get('symbols', '')
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        
        if symbols_param:
            symbols = symbols_param.split(',')
        else:
            symbols = SimplifiedMarketDataService.default_etfs
        
        results = {}
        
        for symbol in symbols:
            try:
                # Check cache first unless force refresh
                if not force_refresh:
                    cached_score = get_cached_etf_score(symbol)
                    if cached_score:
                        score, price, indicators = cached_score
                        results[symbol] = {
                            'score': score,
                            'price': price,
                            'indicators': indicators
                        }
                        continue
                
                # Calculate new score
                score, price, indicators = SimplifiedMarketDataService._calculate_etf_score(
                    symbol, force_refresh=True
                )
                
                results[symbol] = {
                    'score': score,
                    'price': price,
                    'indicators': indicators
                }
            
            except Exception as e:
                logger.error(f"Error getting score for {symbol}: {str(e)}")
                results[symbol] = {'error': str(e)}
        
        return jsonify(results)
    
    except Exception as e:
        logger.error(f"Error getting ETF scores: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api.route('/backtest', methods=['POST'])
def create_backtest():
    """
    Create a backtest for a specific date
    
    Request Body:
    {
        "date": "YYYY-MM-DD",
        "symbols": ["XLK", "XLF", ...] (optional)
    }
    """
    try:
        data = request.json
        
        # Validate date
        date_str = data.get('date')
        if not date_str:
            return jsonify({'error': 'Date is required'}), 400
        
        try:
            # Validate date format
            datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Get symbols
        symbols = data.get('symbols', [])
        
        # Check for cached backtest
        cached_result = BacktestService.get_cached_backtest(date_str)
        if cached_result:
            return jsonify({
                'date': date_str,
                'data': cached_result,
                'source': 'cache'
            })
        
        # Create new backtest
        results = BacktestService.create_backtest(date_str, symbols)
        
        return jsonify({
            'date': date_str,
            'data': results,
            'source': 'calculated'
        })
    
    except Exception as e:
        logger.error(f"Error creating backtest: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api.route('/backtests/<date>', methods=['GET'])
def get_backtest(date):
    """
    Get a cached backtest for a specific date
    
    Path Parameters:
    - date: Date in YYYY-MM-DD format
    
    Query Parameters:
    - force_recalculate: Set to 'true' to force calculation of a new backtest (default: false)
    """
    try:
        # Validate date format
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        force_recalculate = request.args.get('force_recalculate', 'false').lower() == 'true'
        
        # Check for cached backtest unless forcing recalculation
        if not force_recalculate:
            cached_result = BacktestService.get_cached_backtest(date)
            if cached_result:
                return jsonify({
                    'date': date,
                    'data': cached_result,
                    'source': 'cache'
                })
        
        # Get symbols
        symbols_param = request.args.get('symbols', '')
        if symbols_param:
            symbols = symbols_param.split(',')
        else:
            symbols = SimplifiedMarketDataService.default_etfs
        
        # Create new backtest
        results = BacktestService.create_backtest(date, symbols)
        
        return jsonify({
            'date': date,
            'data': results,
            'source': 'calculated'
        })
    
    except Exception as e:
        logger.error(f"Error getting backtest: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api.route('/tasks', methods=['POST'])
def create_task():
    """
    Create a background processing task
    
    Request Body:
    {
        "type": "fetch_historical_data" | "update_etf_scores" | "batch_stock_analysis",
        "parameters": {
            // Task-specific parameters
        }
    }
    """
    try:
        data = request.json
        
        # Validate task type
        task_type = data.get('type')
        if not task_type:
            return jsonify({'error': 'Task type is required'}), 400
        
        if task_type not in ['fetch_historical_data', 'update_etf_scores', 'batch_stock_analysis']:
            return jsonify({'error': 'Invalid task type'}), 400
        
        # Get parameters
        parameters = data.get('parameters', {})
        
        # Create task based on type
        task_id = None
        
        if task_type == 'fetch_historical_data':
            symbols = parameters.get('symbols', [])
            days = parameters.get('days', 180)
            force_refresh = parameters.get('force_refresh', False)
            
            if not symbols:
                return jsonify({'error': 'Symbols are required for fetch_historical_data task'}), 400
            
            task_id = BackgroundTaskService.schedule_fetch_historical_data(
                symbols, days, force_refresh
            )
        
        elif task_type == 'update_etf_scores':
            symbols = parameters.get('symbols', [])
            force_refresh = parameters.get('force_refresh', False)
            
            if not symbols:
                return jsonify({'error': 'Symbols are required for update_etf_scores task'}), 400
            
            task_id = BackgroundTaskService.schedule_update_etf_scores(
                symbols, force_refresh
            )
        
        elif task_type == 'batch_stock_analysis':
            symbols = parameters.get('symbols', [])
            batch_size = parameters.get('batch_size', 20)
            
            if not symbols:
                return jsonify({'error': 'Symbols are required for batch_stock_analysis task'}), 400
            
            task_id = BackgroundTaskService.schedule_batch_stock_analysis(
                symbols, batch_size
            )
        
        if task_id:
            return jsonify({
                'task_id': task_id,
                'type': task_type,
                'status': 'pending'
            })
        else:
            return jsonify({'error': 'Failed to create task'}), 500
    
    except Exception as e:
        logger.error(f"Error creating task: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api.route('/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    """
    Get the status of a background processing task
    
    Path Parameters:
    - task_id: Task ID
    """
    try:
        status = BackgroundTaskService.get_task_status(task_id)
        
        if 'error' in status and status['error'] == 'Task not found':
            return jsonify({'error': 'Task not found'}), 404
        
        return jsonify(status)
    
    except Exception as e:
        logger.error(f"Error getting task status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api.route('/vip/analyze', methods=['POST'])
def vip_analyze():
    """
    VIP endpoint to analyze a batch of stocks
    
    Request Body:
    {
        "symbols": ["AAPL", "MSFT", ...],
        "batch_size": 20 (optional)
    }
    """
    try:
        data = request.json
        
        # Validate symbols
        symbols = data.get('symbols', [])
        if not symbols:
            return jsonify({'error': 'Symbols are required'}), 400
        
        # Limit batch size to prevent abuse
        batch_size = min(data.get('batch_size', 20), 50)
        
        # Schedule background task
        task_id = BackgroundTaskService.schedule_batch_stock_analysis(
            symbols, batch_size
        )
        
        if task_id:
            return jsonify({
                'task_id': task_id,
                'status': 'pending',
                'message': f'Analysis of {len(symbols)} symbols has been scheduled'
            })
        else:
            return jsonify({'error': 'Failed to schedule analysis'}), 500
    
    except Exception as e:
        logger.error(f"Error in VIP analysis: {str(e)}")
        return jsonify({'error': str(e)}), 500