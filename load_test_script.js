/**
 * Comprehensive Load Testing Script for Income Machine Application
 * Tests concurrent user scenarios and Redis caching effectiveness
 * Usage: k6 run load_test_script.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');

// Test configuration
export const options = {
  stages: [
    // Warm-up phase
    { duration: '30s', target: 10 },
    // Load increase to test Redis caching
    { duration: '1m', target: 50 },
    // Peak load to test concurrent users
    { duration: '2m', target: 100 },
    // Sustained load test
    { duration: '3m', target: 150 },
    // Cool down
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 95% of requests under 2s
    http_req_failed: ['rate<0.01'],    // Error rate under 1%
    errors: ['rate<0.01'],
  },
};

// Replace with your deployed URL
const BASE_URL = 'https://your-app.replit.app';

// Test data
const TEST_TICKERS = ['AVGO', 'LIN', 'SWKS', 'CTAS', 'NRG'];

export default function () {
  // Simulate realistic user journey
  const scenario = Math.random();
  
  if (scenario < 0.4) {
    // 40% - Homepage load (tests database queries)
    testHomepage();
  } else if (scenario < 0.7) {
    // 30% - ETF data fetch (tests Redis caching)
    testETFData();
  } else if (scenario < 0.9) {
    // 20% - Spread analysis (tests complex calculations)
    testSpreadAnalysis();
  } else {
    // 10% - Full user journey (complete workflow)
    testFullJourney();
  }
  
  sleep(1); // Think time between requests
}

function testHomepage() {
  const response = http.get(`${BASE_URL}/`);
  
  const success = check(response, {
    'Homepage loads': (r) => r.status === 200,
    'Homepage response time < 2s': (r) => r.timings.duration < 2000,
    'Contains ETF data': (r) => r.body.includes('Income Machine'),
  });
  
  if (!success) {
    errorRate.add(1);
  }
}

function testETFData() {
  // Test API endpoint that benefits from Redis caching
  const response = http.get(`${BASE_URL}/api/etf-data`);
  
  const success = check(response, {
    'ETF data loads': (r) => r.status === 200,
    'ETF data response time < 1s': (r) => r.timings.duration < 1000,
    'Contains ticker data': (r) => r.body.includes('score'),
  });
  
  if (!success) {
    errorRate.add(1);
  }
}

function testSpreadAnalysis() {
  // Test spread analysis with random ticker
  const ticker = TEST_TICKERS[Math.floor(Math.random() * TEST_TICKERS.length)];
  
  const response = http.post(`${BASE_URL}/analyze`, {
    ticker: ticker,
    strategy: 'balanced'
  }, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  
  const success = check(response, {
    'Spread analysis completes': (r) => r.status === 200,
    'Analysis response time < 5s': (r) => r.timings.duration < 5000,
    'Contains spread data': (r) => r.body.includes('ROI') || r.body.includes('spread'),
  });
  
  if (!success) {
    errorRate.add(1);
  }
}

function testFullJourney() {
  // Complete user workflow
  
  // 1. Load homepage
  let response = http.get(`${BASE_URL}/`);
  check(response, { 'Journey - Homepage': (r) => r.status === 200 });
  
  sleep(2); // User reads content
  
  // 2. Get ETF data
  response = http.get(`${BASE_URL}/api/etf-data`);
  check(response, { 'Journey - ETF Data': (r) => r.status === 200 });
  
  sleep(3); // User selects ticker
  
  // 3. Analyze spread
  const ticker = TEST_TICKERS[Math.floor(Math.random() * TEST_TICKERS.length)];
  response = http.post(`${BASE_URL}/analyze`, {
    ticker: ticker,
    strategy: 'aggressive'
  }, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  
  const success = check(response, {
    'Journey - Analysis': (r) => r.status === 200,
    'Journey - Complete under 10s': (r) => r.timings.duration < 10000,
  });
  
  if (!success) {
    errorRate.add(1);
  }
}

// Test Redis cache effectiveness
export function handleSummary(data) {
  return {
    'load_test_results.json': JSON.stringify(data, null, 2),
    stdout: `
=== LOAD TEST RESULTS ===
Total Requests: ${data.metrics.http_reqs.values.count}
Failed Requests: ${data.metrics.http_req_failed.values.rate * 100}%
Average Response Time: ${data.metrics.http_req_duration.values.avg}ms
95th Percentile: ${data.metrics.http_req_duration.values['p(95)']}ms
Max Response Time: ${data.metrics.http_req_duration.values.max}ms

=== REDIS CACHE ANALYSIS ===
Expected behavior with Redis:
- First 10 users: Normal API response times (500-2000ms)
- Next 100 users: Fast cached responses (50-200ms)  
- After 30s: Cache expiry, back to normal times

Actual Results:
- Check if response times decrease for subsequent users
- Monitor logs for "cache hit" vs "cache miss" messages
- Verify API call reduction in TheTradeList usage
    `,
  };
}