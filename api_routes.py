from flask import Blueprint, jsonify, request
import logging
import datetime
import json

from simplified_market_data import SimplifiedMarketDataService
from background_tasks import BackgroundTaskService
from backtest_service import BacktestService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create API blueprint
api = Blueprint('api', __name__)

@api.route('/etf/score/<symbol>', methods=['GET'])
def get_etf_score(symbol):
    """
    Get the technical score for an ETF
    
    Query Parameters:
    - force_refresh: Set to 'true' to force calculation of a new score (default: false)
    """
    force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
    
    try:
        score, price, indicators = SimplifiedMarketDataService.get_etf_score(symbol, force_refresh=force_refresh)
        
        return jsonify({
            'symbol': symbol,
            'score': score,
            'price': price,
            'indicators': indicators
        })
    except Exception as e:
        logger.error(f"Error getting ETF score for {symbol}: {str(e)}")
        return jsonify({
            'error': f"Failed to get score for {symbol}: {str(e)}"
        }), 500

@api.route('/etf/scores', methods=['GET'])
def get_etf_scores():
    """
    Get technical scores for multiple ETFs
    
    Query Parameters:
    - symbols: Comma-separated list of symbols (default: all tracked ETFs)
    - force_refresh: Set to 'true' to force calculation of new scores (default: false)
    """
    symbols_param = request.args.get('symbols', '')
    force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
    
    # If symbols parameter is provided, use it; otherwise use default ETFs
    if symbols_param:
        symbols = [s.strip().upper() for s in symbols_param.split(',')]
    else:
        symbols = SimplifiedMarketDataService.default_etfs
    
    try:
        result = SimplifiedMarketDataService.analyze_etfs(symbols, force_refresh=force_refresh)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting ETF scores: {str(e)}")
        return jsonify({
            'error': f"Failed to get ETF scores: {str(e)}"
        }), 500

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
        
        if not data or 'date' not in data:
            return jsonify({'error': 'Date is required'}), 400
        
        date_str = data.get('date')
        symbols = data.get('symbols')
        
        # Validate date format
        try:
            datetime.datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Run backtest
        result = BacktestService.create_backtest(date_str, symbols, cache_result=True)
        
        # Return results
        return jsonify({
            'date': date_str,
            'source': 'polygon.io' if 'polygon' in result.get('_source', '') else 'yahoo finance',
            'data': result
        })
    except Exception as e:
        logger.error(f"Error creating backtest: {str(e)}")
        return jsonify({
            'error': f"Failed to create backtest: {str(e)}"
        }), 500

@api.route('/backtest/<date>', methods=['GET'])
def get_backtest(date):
    """
    Get a cached backtest for a specific date
    
    Path Parameters:
    - date: Date in YYYY-MM-DD format
    
    Query Parameters:
    - force_recalculate: Set to 'true' to force calculation of a new backtest (default: false)
    """
    force_recalculate = request.args.get('force_recalculate', 'false').lower() == 'true'
    
    try:
        # Validate date format
        try:
            datetime.datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        if force_recalculate:
            # Run backtest with forced recalculation
            result = BacktestService.create_backtest(date, cache_result=True)
        else:
            # Get cached result
            result = BacktestService.get_cached_backtest(date)
            
            if not result:
                # No cached result, run backtest
                result = BacktestService.create_backtest(date, cache_result=True)
        
        # Return results
        return jsonify({
            'date': date,
            'source': 'polygon.io' if 'polygon' in result.get('_source', '') else 'yahoo finance',
            'data': result
        })
    except Exception as e:
        logger.error(f"Error getting backtest for {date}: {str(e)}")
        return jsonify({
            'error': f"Failed to get backtest for {date}: {str(e)}"
        }), 500

@api.route('/task', methods=['POST'])
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
        
        if not data or 'type' not in data:
            return jsonify({'error': 'Task type is required'}), 400
        
        task_type = data.get('type')
        parameters = data.get('parameters', {})
        
        task_id = None
        
        # Schedule task based on type
        if task_type == 'fetch_historical_data':
            symbols = parameters.get('symbols', SimplifiedMarketDataService.default_etfs)
            days = parameters.get('days', 180)
            force_refresh = parameters.get('force_refresh', False)
            
            task_id = BackgroundTaskService.schedule_fetch_historical_data(
                symbols, days, force_refresh
            )
        elif task_type == 'update_etf_scores':
            symbols = parameters.get('symbols', SimplifiedMarketDataService.default_etfs)
            force_refresh = parameters.get('force_refresh', False)
            
            task_id = BackgroundTaskService.schedule_update_etf_scores(
                symbols, force_refresh
            )
        elif task_type == 'batch_stock_analysis':
            symbols = parameters.get('symbols', [])
            batch_size = parameters.get('batch_size', 20)
            
            if not symbols:
                return jsonify({'error': 'Symbols are required for batch stock analysis'}), 400
            
            task_id = BackgroundTaskService.schedule_batch_stock_analysis(
                symbols, batch_size
            )
        else:
            return jsonify({'error': f'Unknown task type: {task_type}'}), 400
        
        if task_id is None:
            return jsonify({'error': 'Failed to schedule task'}), 500
        
        # Return task ID
        return jsonify({
            'task_id': task_id,
            'status': 'scheduled',
            'type': task_type
        })
    except Exception as e:
        logger.error(f"Error creating task: {str(e)}")
        return jsonify({
            'error': f"Failed to create task: {str(e)}"
        }), 500

@api.route('/task/<int:task_id>', methods=['GET'])
def get_task(task_id):
    """
    Get the status of a background processing task
    
    Path Parameters:
    - task_id: Task ID
    """
    try:
        task_status = BackgroundTaskService.get_task_status(task_id)
        
        if not task_status:
            return jsonify({'error': f'Task {task_id} not found'}), 404
        
        return jsonify(task_status)
    except Exception as e:
        logger.error(f"Error getting task {task_id}: {str(e)}")
        return jsonify({
            'error': f"Failed to get task {task_id}: {str(e)}"
        }), 500

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
        
        if not data or 'symbols' not in data:
            return jsonify({'error': 'Symbols are required'}), 400
        
        symbols = data.get('symbols')
        batch_size = data.get('batch_size', 20)
        
        # Schedule batch analysis task
        task_id = BackgroundTaskService.schedule_batch_stock_analysis(
            symbols, batch_size
        )
        
        if task_id is None:
            return jsonify({'error': 'Failed to schedule analysis task'}), 500
        
        # Return task ID
        return jsonify({
            'task_id': task_id,
            'status': 'scheduled',
            'type': 'batch_stock_analysis',
            'symbols_count': len(symbols)
        })
    except Exception as e:
        logger.error(f"Error scheduling VIP analysis: {str(e)}")
        return jsonify({
            'error': f"Failed to schedule VIP analysis: {str(e)}"
        }), 500