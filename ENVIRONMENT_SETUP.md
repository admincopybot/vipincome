# Environment Setup for Integrated Debit Spread Analyzer

## Required Environment Variables

### 1. TRADELIST_API_KEY
Your professional-grade analysis engine requires TheTradeList API access.

**For Local Development:**
Create `.env.local` in your project root:
```
TRADELIST_API_KEY=your_tradelist_api_key_here
```

**For Vercel Production:**
1. Go to your Vercel dashboard
2. Select your project: `vipincome-68l4` (or current deployment)
3. Go to Settings → Environment Variables
4. Add:
   - **Name**: `TRADELIST_API_KEY`
   - **Value**: Your TheTradeList API key
   - **Environment**: Production

### 2. Optional Redis Caching (Already Configured)
Your application already has Redis caching configured with:
- `UPSTASH_REDIS_REST_URL`
- `UPSTASH_REDIS_REST_TOKEN`

## Integration Complete ✅

Your Income Machine VIP now includes:
- **Professional debit spread analysis** using TheTradeList API
- **Three strategy levels**: Aggressive (25-50% ROI), Balanced (12-25% ROI), Conservative (8-15% ROI)
- **Real-time options pricing** with authentic market data
- **9-point profit/loss scenarios** for different price movements
- **ThinkOrSwim pricing methodology** for professional-grade analysis

## API Response Format
```json
{
  "success": true,
  "ticker": "AAPL",
  "current_stock_price": 195.55,
  "strategies_found": 3,
  "strategies": {
    "aggressive": {
      "found": true,
      "contracts": {
        "long_contract": "O:AAPL250703C00187500",
        "long_strike": 187.5,
        "long_price": 10.38,
        "short_contract": "O:AAPL250703C00192500", 
        "short_strike": 192.5,
        "short_price": 6.75
      },
      "spread_details": {
        "spread_cost": 3.63,
        "max_profit": 1.37,
        "roi_percent": 37.7,
        "breakeven_price": 191.13,
        "days_to_expiration": 14
      },
      "price_scenarios": [
        {
          "stock_price": 156.44,
          "price_change_percent": -20,
          "profit_loss": -3.63,
          "profit_loss_percent": -100
        },
        // ... 8 more scenarios
      ]
    },
    "balanced": { ... },
    "conservative": { ... }
  }
}
```

## Next Steps
1. Add your `TRADELIST_API_KEY` to Vercel environment variables
2. Deploy the changes
3. Test the integrated analysis on your Income Machine VIP

Your users will now get professional-grade options analysis directly within your application! 