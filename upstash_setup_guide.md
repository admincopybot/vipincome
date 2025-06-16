# Upstash Redis Configuration for Production

## Your Upstash Details
- Endpoint: `integral-monkey-44503.upstash.io`
- Port: `6379`
- TLS/SSL: Enabled

## Required Environment Variables

Add these to your Replit Secrets:

### Option 1: REST API (Recommended)
```
UPSTASH_REDIS_REST_URL=https://integral-monkey-44503.upstash.io
UPSTASH_REDIS_REST_TOKEN=[Your Token from Upstash Dashboard]
```

### Option 2: Standard Redis URL
```
REDIS_URL=rediss://default:[Your Password]@integral-monkey-44503.upstash.io:6379
```

## Get Your Token/Password
1. Go to your Upstash dashboard
2. Click on your database "integral-monkey-44503"
3. Copy the **TOKEN** value (for REST API)
4. Or copy the **Password** value (for Redis URL)

## Test Connection
After adding environment variables, your logs will show:
```
✅ Upstash Redis connection successful
```

Instead of:
```
CRITICAL: No Redis available
```