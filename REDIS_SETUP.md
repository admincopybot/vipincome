# Redis Setup for 1000+ Concurrent Users

## Quick Setup (5 minutes)

### Option 1: Upstash Redis (Recommended - Free tier)
1. Go to https://upstash.com/
2. Sign up (Google/GitHub login available)
3. Create new Redis database
4. Copy the Redis URL
5. In Replit: Secrets tab → Add `REDIS_URL` → Paste URL
6. Deploy - Redis will work automatically

### Option 2: Railway Redis  
1. Go to https://railway.app/
2. Create project → Add Redis service
3. Copy connection URL from Variables tab
4. In Replit: Secrets tab → Add `REDIS_URL` → Paste URL

### Option 3: Redis Cloud
1. Go to https://redis.com/try-free/
2. Create free account
3. Create database
4. Copy connection string
5. In Replit: Secrets tab → Add `REDIS_URL` → Paste URL

## Verification
After adding REDIS_URL, your logs will show:
```
Redis cache service initialized successfully
```

Instead of:
```
CRITICAL: No Redis available
```

## Performance Impact
- Without Redis: Each user makes fresh API calls
- With Redis: 95% API call reduction for concurrent users
- Critical for 1000+ simultaneous users