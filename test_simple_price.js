// Simple test to see the actual price API response
const API_KEY = "5b4960fc-2cd5-4bda-bae1-e84c1";

async function testPrice() {
  try {
    const url = 'https://api.thetradelist.com/v1/data/snapshot-locale';
    const params = new URLSearchParams({
      tickers: 'MS,',
      apiKey: API_KEY
    });
    
    console.log(`Testing: ${url}?${params}`);
    
    const response = await fetch(`${url}?${params}`);
    console.log(`Status: ${response.status}`);
    
    if (response.ok) {
      const data = await response.json();
      console.log('SUCCESS - Full Response:');
      console.log(JSON.stringify(data, null, 2));
    } else {
      const text = await response.text();
      console.log('ERROR Response:', text);
    }
  } catch (error) {
    console.log('EXCEPTION:', error);
  }
}

testPrice(); 