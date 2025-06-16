"""
Redis Cache Management Endpoint
Provides API endpoints for cache statistics and management
"""
from flask import Blueprint, jsonify
from redis_cache_service import cache_service

redis_bp = Blueprint('redis', __name__)

@redis_bp.route('/api/cache/stats')
def cache_stats():
    """Get Redis cache statistics"""
    try:
        stats = cache_service.get_cache_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': f'Failed to get cache stats: {str(e)}'}), 500

@redis_bp.route('/api/cache/clear/<pattern>')
def clear_cache_pattern(pattern):
    """Clear cache entries matching a pattern"""
    try:
        cache_service.invalidate_cache_pattern(pattern)
        return jsonify({'success': True, 'message': f'Cleared cache pattern: {pattern}'})
    except Exception as e:
        return jsonify({'error': f'Failed to clear cache: {str(e)}'}), 500

@redis_bp.route('/api/cache/clear/all')
def clear_all_cache():
    """Clear all cache entries"""
    try:
        cache_service.invalidate_cache_pattern('*')
        return jsonify({'success': True, 'message': 'Cleared all cache entries'})
    except Exception as e:
        return jsonify({'error': f'Failed to clear cache: {str(e)}'}), 500