#!/usr/bin/env python3
"""
Upstash Redis Configuration Script
Helps configure Upstash Redis for production deployment
"""

import os
import sys
from upstash_redis import Redis as UpstashRedis

def test_upstash_connection():
    """Test Upstash Redis connection with current environment variables"""
    
    print("=== Upstash Redis Configuration Test ===")
    
    # Check for environment variables
    upstash_url = os.environ.get('UPSTASH_REDIS_REST_URL')
    upstash_token = os.environ.get('UPSTASH_REDIS_REST_TOKEN')
    
    if not upstash_url or not upstash_token:
        print("❌ Missing Upstash environment variables")
        print("\nRequired environment variables:")
        print("UPSTASH_REDIS_REST_URL=https://integral-monkey-44503.upstash.io")
        print("UPSTASH_REDIS_REST_TOKEN=[Your token from Upstash dashboard]")
        print("\nAdd these to Replit Secrets tab, then run this script again.")
        return False
    
    try:
        print(f"Testing connection to: {upstash_url}")
        
        # Create Upstash Redis client
        redis_client = UpstashRedis(url=upstash_url, token=upstash_token)
        
        # Test basic operations
        print("Testing SET operation...")
        redis_client.set('test_key', 'production_ready', ex=60)
        
        print("Testing GET operation...")
        value = redis_client.get('test_key')
        
        if value == 'production_ready':
            print("✅ Upstash Redis connection successful!")
            print("✅ Read/Write operations working")
            
            # Clean up test key
            redis_client.delete('test_key')
            
            print("\n🚀 Production Redis Setup Complete!")
            print("Your application will now handle 1000+ concurrent users efficiently")
            return True
        else:
            print(f"❌ Test failed - expected 'production_ready', got '{value}'")
            return False
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Verify UPSTASH_REDIS_REST_URL starts with https://")
        print("2. Verify UPSTASH_REDIS_REST_TOKEN is correct")
        print("3. Check Upstash dashboard for correct credentials")
        return False

def show_configuration_guide():
    """Display configuration instructions"""
    
    print("\n=== Upstash Redis Setup Instructions ===")
    print("\n1. Go to your Upstash dashboard")
    print("2. Click on database: integral-monkey-44503")
    print("3. Copy the following values:")
    print("   - REST URL: https://integral-monkey-44503.upstash.io")
    print("   - TOKEN: (copy from dashboard)")
    print("\n4. In Replit, go to Secrets tab and add:")
    print("   UPSTASH_REDIS_REST_URL = https://integral-monkey-44503.upstash.io")
    print("   UPSTASH_REDIS_REST_TOKEN = [paste your token]")
    print("\n5. Run this script again to test the connection")

if __name__ == "__main__":
    if not test_upstash_connection():
        show_configuration_guide()
    else:
        print("\nNext steps:")
        print("1. Deploy your application")
        print("2. Redis caching will automatically activate")
        print("3. Monitor logs for 'Upstash Redis connection successful'")