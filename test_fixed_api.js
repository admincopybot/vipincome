// Test the corrected API calls for MS ticker
const API_KEY = "5b4960fc-2cd5-4bda-bae1-e84c1";

async function testFixedAPI() {
  console.log('=== TESTING CORRECTED TRADELIST API FOR MS ===');
  
  const symbol = 'MS';
  
  // Test 1: Corrected Options Contracts API
  console.log('\n=== TEST 1: CORRECTED OPTIONS CONTRACTS API ===');
  try {
    const url = 'https://api.thetradelist.com/v1/data/options-contracts';
    const params = new URLSearchParams({
      underlying_ticker: symbol,  // CORRECT: underlying_ticker instead of symbol
      limit: 1000,
      apiKey: API_KEY
    });
    
    console.log(`Testing: ${url}?${params}`);
    
    const response = await fetch(`${url}?${params}`);
    console.log(`Status: ${response.status}`);
    
    if (response.ok) {
      const data = await response.json();
      console.log('✅ OPTIONS API SUCCESS');
      console.log(`Status: ${data.status}`);
      console.log(`Results count: ${data.results?.length || 0}`);
      
      if (data.results && data.results.length > 0) {
        console.log('Sample contract:', JSON.stringify(data.results[0], null, 2));
        
        // Filter for call options
        const callOptions = data.results.filter(contract => contract.contract_type === 'call');
        console.log(`Call options found: ${callOptions.length}`);
        
        if (callOptions.length > 0) {
          console.log('Sample call option:', JSON.stringify(callOptions[0], null, 2));
          
          // Test quotes for the first call option
          console.log('\n=== TEST 2: QUOTES FOR SAMPLE CONTRACT ===');
          const sampleTicker = callOptions[0].ticker;
          
          const quoteUrl = 'https://api.thetradelist.com/v1/data/last-quote';
          const quoteParams = new URLSearchParams({
            ticker: sampleTicker,
            apiKey: API_KEY
          });
          
          console.log(`Testing quotes: ${quoteUrl}?${quoteParams}`);
          
          const quoteResponse = await fetch(`${quoteUrl}?${quoteParams}`);
          console.log(`Quote Status: ${quoteResponse.status}`);
          
          if (quoteResponse.ok) {
            const quoteData = await quoteResponse.json();
            console.log('✅ QUOTES API SUCCESS');
            console.log('Quote data:', JSON.stringify(quoteData, null, 2));
          } else {
            const quoteError = await quoteResponse.text();
            console.log('❌ QUOTES API ERROR:', quoteError);
          }
        }
      }
    } else {
      const errorText = await response.text();
      console.log('❌ OPTIONS API ERROR:', errorText);
    }
  } catch (error) {
    console.log('❌ API EXCEPTION:', error.message);
  }
  
  console.log('\n=== CORRECTED API TEST COMPLETE ===');
}

testFixedAPI(); 