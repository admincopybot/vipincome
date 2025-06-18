// Test with TSLA ticker that we know works
const API_KEY = "5b4960fc-2cd5-4bda-bae1-e84c1db1f3f5"; // Use the full API key from your example

async function testTSLA() {
  console.log('=== TESTING WITH WORKING TSLA EXAMPLE ===');
  
  // Test the exact URL from your working example
  try {
    const url = 'https://api.thetradelist.com/v1/data/options-contracts?underlying_ticker=TSLA&limit=1000&apiKey=5b4960fc-2cd5-4bda-bae1-e84c1db1f3f5';
    
    console.log(`Testing: ${url}`);
    
    const response = await fetch(url);
    console.log(`Status: ${response.status}`);
    console.log(`Headers:`, Object.fromEntries(response.headers.entries()));
    
    if (response.ok) {
      const data = await response.json();
      console.log('✅ TSLA API SUCCESS');
      console.log(`Status: ${data.status}`);
      console.log(`Results count: ${data.results?.length || 0}`);
      
      if (data.results && data.results.length > 0) {
        console.log('First contract:', JSON.stringify(data.results[0], null, 2));
      }
    } else {
      const errorText = await response.text();
      console.log('❌ TSLA API ERROR:', errorText.substring(0, 500));
    }
  } catch (error) {
    console.log('❌ TSLA API EXCEPTION:', error.message);
  }
  
  // Now test with MS using the same full API key
  console.log('\n=== TESTING MS WITH FULL API KEY ===');
  try {
    const msUrl = 'https://api.thetradelist.com/v1/data/options-contracts?underlying_ticker=MS&limit=1000&apiKey=5b4960fc-2cd5-4bda-bae1-e84c1db1f3f5';
    
    console.log(`Testing: ${msUrl}`);
    
    const msResponse = await fetch(msUrl);
    console.log(`MS Status: ${msResponse.status}`);
    
    if (msResponse.ok) {
      const msData = await msResponse.json();
      console.log('✅ MS API SUCCESS');
      console.log(`MS Status: ${msData.status}`);
      console.log(`MS Results count: ${msData.results?.length || 0}`);
      
      if (msData.results && msData.results.length > 0) {
        console.log('MS First contract:', JSON.stringify(msData.results[0], null, 2));
      } else {
        console.log('MS has no options contracts available');
      }
    } else {
      const msErrorText = await msResponse.text();
      console.log('❌ MS API ERROR:', msErrorText.substring(0, 500));
    }
  } catch (error) {
    console.log('❌ MS API EXCEPTION:', error.message);
  }
}

testTSLA(); 