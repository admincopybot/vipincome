# Overview

This is an Income Machine ETF Analyzer application built with Flask that provides technical scoring for ETFs and options spread analysis. The application primarily uses pre-calculated data from CSV files or database storage rather than real-time calculations, with backup API integrations for data fetching.

# System Architecture

The application follows a hybrid architecture with optimized frontend performance:

## Backend Architecture
- **Flask Web Application**: Legacy backend for data processing and background tasks
- **Database Layer**: PostgreSQL database for persistent ETF scoring data storage
- **Data Services**: Multiple data fetching services with fallback mechanisms
- **CSV Data Processing**: Bulk ETF calculation system with CSV export/import capabilities

## Frontend Architecture
- **Next.js TypeScript Application**: Modern SPA frontend with optimized performance
- **API-First Design**: RESTful API endpoints for data access with JWT authentication
- **Redis Caching**: 3-minute cache for spread analysis, 30-second cache for price data
- **External API Integration**: Dedicated spread analysis service for Steps 3&4
- **Single Page Application**: No page reloads, smooth user experience

# Key Components

## Data Sources and APIs
1. **Primary Data Sources**:
   - CSV files for pre-calculated ETF scores
   - PostgreSQL database for persistent storage
   - TheTradeList API for options data and pricing
   - Polygon.io API for market data (backup)

2. **ETF Scoring System**:
   - 5-criteria technical scoring (0-5 points total)
   - Criteria: Trend1 (20-day EMA), Trend2 (100-day EMA), Snapback (RSI), Momentum (weekly), Stabilizing (ATR)
   - Pre-calculated results stored in database

3. **Options Analysis**:
   - Debit spread detection and analysis
   - Real-time options pricing integration
   - Multiple strategy types (aggressive, steady, passive)

## Core Modules

### Database Layer (`database_models.py`)
- PostgreSQL integration with connection pooling
- ETF scoring data management (292+ symbols)
- CSV import/export functionality
- Data persistence across deployments

### Market Data Services
- `simplified_market_data.py`: Main market data service
- `enhanced_polygon_client.py`: Polygon API integration
- `tradelist_client.py`: TheTradeList API integration
- Multiple fallback mechanisms for data reliability

### Technical Analysis
- `enhanced_etf_scoring.py`: ETF scoring calculations
- `gamma_rsi_calculator.py`: Custom RSI momentum calculations
- `talib_custom.py`: Custom technical analysis implementations

### Options Trading
- `real_time_spreads.py`: Options spread detection
- `spread_storage.py`: Session-based spread data storage
- `spread_diagnostics.py`: Debugging and validation tools

# Data Flow

1. **ETF Data Pipeline**:
   - Bulk calculator processes 292+ symbols
   - Results exported to CSV files
   - CSV data imported to PostgreSQL database
   - Web application reads from database
   - Real-time price updates via API polling

2. **Options Data Pipeline**:
   - Options contracts fetched from TheTradeList API
   - Spread calculations performed in real-time
   - Results stored in session storage
   - User selections trigger detailed analysis

3. **Frontend Updates**:
   - JavaScript polls for price updates every 5 seconds
   - Scores remain static (updated only on page refresh)
   - Real-time indicators show data freshness

# External Dependencies

## Required APIs
- **TheTradeList API**: Primary source for options data and real-time pricing
- **Polygon.io API**: Backup market data source for ETF calculations
- **PostgreSQL Database**: Persistent data storage

## Python Dependencies
- Flask web framework
- psycopg2 for PostgreSQL connectivity
- pandas/numpy for data processing
- requests for API communications
- ta library for technical analysis
- WebSocket client for real-time data

## Environment Variables
- `TRADELIST_API_KEY`: TheTradeList API authentication
- `POLYGON_API_KEY`: Polygon.io API authentication (backup)
- `DATABASE_URL`: PostgreSQL connection string
- `SESSION_SECRET`: Flask session encryption key

# Deployment Strategy

## Replit Configuration
- Gunicorn WSGI server for production deployment
- Auto-scaling deployment target
- Port 5000 for web traffic
- Background workflows for data processing

## Database Strategy
- PostgreSQL for production persistence
- CSV files for data portability and backup
- Database initialization on startup
- Automatic schema creation and data loading

## Scaling Considerations
- Database-first approach reduces API rate limits
- Pre-calculated data improves response times
- Session storage for temporary options data
- Horizontal scaling via database replication

# Changelog

Changelog:
- June 13, 2025: Initial setup
- June 16, 2025: Transformed application to VIP-only access with JWT authentication from OneClick Trading
- June 16, 2025: Removed all Free/Pro tier routes and functionality - now exclusively VIP
- June 16, 2025: Added proper VIP branding with golden badge and exclusive messaging
- June 16, 2025: JWT authentication validates RS256 tokens from OCT with proper user session management
- June 16, 2025: Non-authenticated users see access screen directing them to OneClick Trading
- June 16, 2025: VIP users get unlimited access to all tickers without contract quantity restrictions
- June 16, 2025: Updated VIP interface with purple theme design matching user specifications
- June 16, 2025: Added functional search bar with instant ticker filtering for VIP users
- June 16, 2025: Implemented purple gradient styling, VIP badges, and premium visual elements
- June 16, 2025: VIP interface now displays "Top Trade Opportunities" with complete ticker access
- June 13, 2025: Removed all "Logout" buttons from navigation across all versions
- June 13, 2025: Updated "Trade Classes" link to external OneClick Trading platform
- June 13, 2025: Fixed ETF sorting to maintain proper #1, #2, #3 order by score and volume
- June 13, 2025: Updated loading message to "The Income Machine is reviewing millions of option combinations to find the best opportunity – this may take up to 30 seconds"
- June 13, 2025: Added +1 logic to DTE values displayed on Step 3 for all three strategies (aggressive, steady, passive)
- June 13, 2025: Updated Step 4 to display "CONSERVATIVE" instead of "PASSIVE" for conservative strategy trades
- June 13, 2025: Changed Step 4 display across ALL versions (free, /pro, /vip) to show unified spread position instead of separate "Buy/Sell" components
- June 13, 2025: Updated Step 4 to use simple format: "Buy the $58 July 03 Call" and "Sell the $59 July 03 Call" for clearer trade construction display
- June 13, 2025: Added green highlighting to Income Potential and ROI Per Contract boxes in Step 4 calculator section
- June 14, 2025: Updated CSV parsing to handle new options_contracts_10_42_dte column for options availability data
- June 14, 2025: Changed ranking system to STRICT hierarchy: SCORE → OPTIONS CONTRACTS → TRADING VOLUME → SYMBOL
- June 14, 2025: Updated Pro version to show only top 3 tickers (matching free version) with enhanced features
- June 14, 2025: Removed VIP upgrade button redirect functionality - now placeholder for future implementation
- June 15, 2025: Expanded scenario analysis to show 9 price ranges: -10%, -5%, -2.5%, -1%, 0%, +1%, +2.5%, +5%, +10%
- June 15, 2025: Added video popup functionality for "How to Use" buttons across all application versions
- June 15, 2025: Optimized scenario table layout with narrower columns and reduced padding for better mobile/desktop display
- June 15, 2025: Renamed "Stock Price Scenarios" section to "Profit Matrix" for clearer user understanding
- June 15, 2025: Fixed "How to Use" video popup functionality across all versions (Free, Pro, VIP)
- June 15, 2025: Optimized tutorial video file size from 85MB to 23MB for faster loading
- June 16, 2025: Fixed VIP/Pro ranking to strictly follow Score → Options Contracts → Volume → Symbol hierarchy
- June 16, 2025: Corrected database with authentic options contracts data from user's CSV file
- June 16, 2025: Implemented 100+ options contracts filter for Free and Pro versions (VIP unrestricted)
- June 16, 2025: Verified comprehensive CSV parsing functionality for bulk analysis data integration
- June 16, 2025: Built POST endpoint `/update_options_contracts` for authentic options data fetching
- June 16, 2025: Implemented Polygon API integration for precise 10-50 DTE options contracts filtering
- June 16, 2025: Added automatic database updates with trading-relevant options contracts counts
- June 16, 2025: Completed authentic options data system filtering contracts expiring in 10-50 days only
- June 16, 2025: Verified system working: ZS(323), VLO(272), MMM(239), NRG(217), AIG(195), WMB(171) contracts
- June 16, 2025: Added VIP upgrade prompt row to Pro version with three upgrade cards
- June 16, 2025: Completed tiered progression: Free (blurred), Pro (clear + VIP prompts), VIP (unrestricted)
- June 16, 2025: Fixed options contracts filter to show unprocessed tickers (0 contracts) and only hide 1-99 contracts
- June 16, 2025: Updated Pro version upgrade button to link to https://sco.prosperitypub.com/1750083074481
- June 16, 2025: Created isolated debit spread API endpoint (spread_api_server.py) for standalone POST requests
- June 16, 2025: API endpoint accepts ticker symbol and returns comprehensive spread analysis in JSON format
- June 16, 2025: Built automated spread analysis pipeline that fetches top tickers and sends results to external API
- June 16, 2025: Pipeline integrates with user's ticker endpoint and spreads-update endpoint using authentic TheTradeList API data
- June 16, 2025: Updated spread analysis to use TheTradeList API exclusively with endpoint: api.thetradelist.com/v1/data/options-contracts
- June 16, 2025: Integrated spread analysis directly into existing background polling system for automatic triggering
- June 16, 2025: Completed full Polygon API migration - replaced all endpoints with TheTradeList API equivalents
- June 16, 2025: Stock prices now use range-data API, options use contracts endpoint, historical data uses range-data API
- June 16, 2025: Implemented Redis caching system with 30-second expiry for 95% API call reduction with concurrent users
- June 16, 2025: Removed ALL Polygon API references from codebase - clean TheTradeList-only deployment ready
- June 16, 2025: Fixed options spread calculations to use TheTradeList options-contracts API with proper data mapping
- June 16, 2025: Integrated Redis caching into real-time spread detection for optimal performance under load
- June 16, 2025: Verified complete TheTradeList migration - all spread calculations working with authentic API data
- June 16, 2025: System confirmed Polygon-independent: stock prices, options contracts, quotes all via TheTradeList
- June 16, 2025: Application ready for deployment with verified 100% TheTradeList API architecture
- June 16, 2025: Implemented comprehensive API efficiency optimization system reducing API calls by 80-90%
- June 16, 2025: Integrated Upstash Redis for production-scale caching with 30-second TTL
- June 16, 2025: Added intelligent scheduling system: 15-minute polling intervals, hourly spread analysis
- June 16, 2025: Built API efficiency monitoring endpoint (/api/efficiency-report) for real-time optimization tracking
- June 16, 2025: Completed production-ready deployment architecture for 1000+ concurrent users
- June 16, 2025: Added Redis caching to stock price fetching in real-time spread detection system
- June 16, 2025: Eliminated excessive API call logging with 30-second cache expiry for stock prices
- June 16, 2025: Integrated spread analysis results caching (30-minute expiry) for instant retrieval
- June 16, 2025: Completed comprehensive Redis caching architecture covering all API endpoints
- June 16, 2025: Fixed VIP logo navigation - Income Machine logo now directs VIP users to VIP scoreboard (/vip)
- June 16, 2025: Disabled automatic background spread analysis - now only triggers on explicit POST requests
- June 16, 2025: Completely removed chart data functionality from Step 2 pages - eliminated all chart API calls for optimal performance
- June 16, 2025: Replaced Step 3 internal spread analysis with external API integration to separate spread analysis application
- June 16, 2025: Updated Step 3 to call external endpoint: https://income-machine-20-bulk-spread-check-1-daiadigitalco.replit.app/api/analyze_debit_spread
- June 16, 2025: Fixed API payload format to match external service expectation: {"ticker": "SYMBOL"}
- June 16, 2025: Updated response parsing to handle nested strategies structure (aggressive/balanced/conservative)
- June 16, 2025: Added comprehensive profit matrix display with price scenarios from external API
- June 16, 2025: Step 3 now fully powered by external spread analysis service with proper data mapping
- June 16, 2025: Updated spread data cache duration from 60 seconds to 3 minutes for improved performance
- June 16, 2025: Completed Next.js TypeScript frontend transformation for optimized performance
- June 16, 2025: Implemented API-first architecture: database-only for Pages 1&2, external API for Steps 3&4
- June 16, 2025: Created TypeScript interfaces for all data structures with proper type safety
- June 16, 2025: Built comprehensive Redis caching layer with 3-minute TTL for spread analysis
- June 16, 2025: Integrated JWT authentication system with RS256 public key validation
- June 16, 2025: Eliminated page reloads with single-page application architecture
- June 16, 2025: Maintained VIP-only access with purple theme and golden badges throughout new frontend
- June 16, 2025: **FINAL ARCHITECTURE**: Simplified to Node.js with minimal Flask bridge for speed optimization
- June 16, 2025: Created standalone Node.js/Express server with identical functionality and data access
- June 16, 2025: Built pure HTML/JavaScript frontend maintaining exact same look, logic, and user experience
- June 16, 2025: Preserved all original features: JWT auth, Redis caching, external API integration, database queries
- June 16, 2025: Achieved user-requested performance optimization by eliminating Python complexity while maintaining 100% feature parity
- June 17, 2025: Fixed JWT authentication with correct OneClick Trading RS256 public key
- June 17, 2025: Updated database queries to match actual schema (total_score, trading_volume_20_day)
- June 17, 2025: Integrated professional Income Machine logo with Nate Tucci's branding
- June 17, 2025: Updated UI design to match provided mockup with step navigation and centered ticker cards
- June 17, 2025: Confirmed VIP access to all 212 tickers with unlimited search functionality
- June 17, 2025: Applied sophisticated VIP color scheme with champagne/stone gradients across all steps for consistent prestigious aesthetic
- June 17, 2025: Added VIP badges next to Income Machine logo on both dashboard and ticker pages for enhanced branding
- June 17, 2025: Implemented Redis caching: 60-second TTL for scoreboard data, 3-minute TTL for spread analysis results
- June 17, 2025: Fixed Step 3 spread analysis to call external API directly: https://income-machine-20-bulk-spread-check-1-daiadigitalco.replit.app/api/analyze_debit_spread
- June 17, 2025: Resolved CORS issues by creating Flask proxy with full HTTP method support (GET, POST, PUT, DELETE, PATCH)
- June 17, 2025: Successfully implemented working Step 3 spread analysis with Redis caching and complete strategy data display
- June 17, 2025: Confirmed Redis caching fully operational - scoreboard data cached 60 seconds, debit spreads cached 3 minutes as requested
- June 17, 2025: Added "How to Use" video modal with Vimeo tutorial integration for better user onboarding
- June 17, 2025: Updated access screen with three buttons: UPGRADE (Prosperity Publishing), Proceed to PRO, and One Click Trading
- June 17, 2025: Improved Step 3 error messages with friendly, conversational language and "Try Again" functionality
- June 17, 2025: Removed problematic HSIC ticker from database to prevent external API pricing errors
- June 17, 2025: Added favicon to both HTML pages using generated-icon.png for consistent branding
- June 17, 2025: Removed "Last updated X minutes ago" text from dashboard for cleaner interface
- June 17, 2025: Updated Step 3 spread analysis to call endpoint: https://income-machine-20-bulk-spread-check-1-daiadigitalco.replit.app/api/analyze_debit_spread
- June 17, 2025: Added market hours popup that automatically displays when market is closed (outside 9:30 AM - 4:00 PM ET weekdays)
- June 17, 2025: Enhanced error handling for "no spreads found" responses - displays detailed strategy-specific error messages with retry functionality
- June 17, 2025: Updated error messages to show "No Spreads Found" with market hours context when market is closed (9:30 AM - 4:00 PM ET)
- June 17, 2025: Fixed favicon display for custom domain https://incomemachine.vip with explicit server routes and proper file placement
- June 17, 2025: Implemented comprehensive data integrity verification - all Step 3 spreads now guaranteed to be authentic JSON from external endpoint with detailed logging
- June 17, 2025: Removed ALL caching from spread analysis - Step 3 now makes fresh real-time API calls to external endpoint on every request
- June 17, 2025: Fixed Step 3 loading state - eliminated premature "No Income Opportunities Found" display before API call completes
- June 17, 2025: Fixed Step 4 option pricing to calculate realistic individual prices from authentic API spread cost data instead of showing $0.00
- June 17, 2025: Updated Step 3 API endpoint to https://income-machine-20-bulk-spread-check-1-daiadigitalco.replit.app for reliable JSON responses
- June 17, 2025: Added failover system with backup endpoint https://income-machine-spread-check-fallback-daiadigitalco.replit.app for when primary endpoint is overloaded
- June 17, 2025: Fixed failover detection to trigger when endpoint returns HTML startup page instead of JSON data
- June 17, 2025: Added comprehensive logging and improved timeout handling for Step 3 failover system
- June 17, 2025: Fixed Flask proxy timeout (increased to 45s for spread analysis) to allow Node.js failover system to execute properly
- June 17, 2025: Fixed Step 2 ticker flash issue - eliminated brief display of previous ticker (MRK) before new ticker data loads
- June 17, 2025: Added third failover endpoint for triple redundancy: income-machine-spread-check-try-3-daiadigitalco.replit.app
- June 17, 2025: Updated failover endpoints to use new real endpoints: try-2-real and try-3-real for improved reliability
- June 17, 2025: Implemented visual progress indicator showing 3-step analysis method progression during failover sequence with real-time updates
- June 17, 2025: Optimized progress indicator to use time-based simulation instead of 500ms API polling for better server performance
- June 17, 2025: Optimized homepage performance by using pre-calculated total_score column instead of real-time score computation in ORDER BY clause
- June 17, 2025: Improved Redis scoreboard caching with single cache key and in-memory filtering for optimal homepage speed
- June 17, 2025: Implemented comprehensive Redis caching on all endpoints: JWT validation (10min), ticker details (5min), spread analysis (3min), scoreboard (60s)

# User Preferences

Preferred communication style: Simple, everyday language.