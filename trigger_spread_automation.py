#!/usr/bin/env python3
"""
Simple trigger for the automated spread analysis pipeline
Run this script to process top tickers and send results to your endpoint
"""
import logging
from robust_spread_pipeline import RobustSpreadPipeline

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Run the complete automated pipeline"""
    logger.info("Starting automated debit spread analysis pipeline")
    
    pipeline = RobustSpreadPipeline()
    
    try:
        # Execute the full pipeline
        pipeline.process_pipeline()
        logger.info("Pipeline completed successfully")
        
    except KeyboardInterrupt:
        logger.info("Pipeline stopped by user")
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise

if __name__ == '__main__':
    main()