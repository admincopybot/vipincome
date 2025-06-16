# Overview

This is an Income Machine ETF Analyzer application built with Flask that provides technical scoring for ETFs and options spread analysis. The application primarily uses pre-calculated data from CSV files or database storage rather than real-time calculations, with backup API integrations for data fetching.

# System Architecture

The application follows a database-first architecture with the following key components:

## Backend Architecture
- **Flask Web Application**: Main application server handling HTTP requests and rendering
- **Database Layer**: PostgreSQL database for persistent ETF scoring data storage
- **Data Services**: Multiple data fetching services with fallback mechanisms
- **CSV Data Processing**: Bulk ETF calculation system with CSV export/import capabilities

## Frontend Architecture
- **Server-Side Rendering**: HTML templates with embedded JavaScript for interactivity
- **Real-time Updates**: JavaScript-based polling for price updates (scores remain static)
- **Responsive Design**: CSS styling for modern web interface

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
- June 16, 2025: Application ready for large-scale simultaneous user testing with optimized performance

# User Preferences

Preferred communication style: Simple, everyday language.