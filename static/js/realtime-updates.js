/**
 * Real-time ETF price updates for Income Machine
 * 
 * This script fetches ETF data from the server via API calls and updates the UI
 * without requiring page refreshes. It includes visual effects to highlight price changes.
 */

// Store previous prices to identify changes for highlighting
let previousPrices = {};

// Polling interval in milliseconds (3 seconds)
const POLLING_INTERVAL = 3000;

// Colors for price changes
const PRICE_UP_COLOR = '#4CAF50';   // Green
const PRICE_DOWN_COLOR = '#F44336'; // Red
const NORMAL_COLOR = ''; // Default (inherit from CSS)

// Get updated ETF data from the server
async function fetchEtfData() {
    try {
        const response = await fetch('/api/etf-data');
        
        if (!response.ok) {
            console.error('Error fetching ETF data:', response.status);
            return null;
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error fetching ETF data:', error);
        return null;
    }
}

// Update the UI with new ETF data
function updateEtfUi(data) {
    if (!data) return;
    
    // Loop through each ETF in the data
    for (const [symbol, etfData] of Object.entries(data)) {
        // Update price
        updateEtfPrice(symbol, etfData.price);
        
        // Update score
        updateEtfScore(symbol, etfData.score);
    }
}

// Update ETF price with visual effect
function updateEtfPrice(symbol, newPrice) {
    const priceElement = document.querySelector(`[data-etf-price="${symbol}"]`);
    if (!priceElement) return;
    
    // Format the price to 2 decimal places
    const formattedPrice = parseFloat(newPrice).toFixed(2);
    
    // Check if we have a previous price for this symbol
    if (previousPrices[symbol] !== undefined) {
        const oldPrice = previousPrices[symbol];
        
        // Determine if price went up or down
        if (newPrice > oldPrice) {
            // Price went up - flash green
            flashElement(priceElement, PRICE_UP_COLOR);
        } else if (newPrice < oldPrice) {
            // Price went down - flash red
            flashElement(priceElement, PRICE_DOWN_COLOR);
        }
    }
    
    // Update the price display
    priceElement.textContent = `$${formattedPrice}`;
    
    // Store the new price for future comparison
    previousPrices[symbol] = newPrice;
}

// Update ETF score
function updateEtfScore(symbol, score) {
    const scoreElement = document.querySelector(`[data-etf-score="${symbol}"]`);
    if (!scoreElement) return;
    
    // Update the score display
    scoreElement.textContent = score;
}

// Flash an element with a color transition effect
function flashElement(element, color) {
    // Save the original background color
    const originalColor = element.style.backgroundColor;
    const originalTransition = element.style.transition;
    
    // Apply the new color and transition
    element.style.backgroundColor = color;
    element.style.transition = 'background-color 1.5s';
    element.style.color = '#FFFFFF';  // White text for better contrast
    
    // Reset back to original after animation
    setTimeout(() => {
        element.style.backgroundColor = originalColor;
        element.style.color = '';     // Reset to default text color
        
        // Remove transition after returning to normal
        setTimeout(() => {
            element.style.transition = originalTransition;
        }, 1500);
    }, 1500);
}

// Start periodic polling for ETF data
function startRealtimeUpdates() {
    console.log('Starting real-time ETF price updates...');
    
    // Initial fetch to store base prices
    fetchEtfData().then(data => {
        if (data) {
            // Store initial prices without highlighting
            for (const [symbol, etfData] of Object.entries(data)) {
                previousPrices[symbol] = etfData.price;
            }
        }
    });
    
    // Set up interval for periodic updates
    setInterval(() => {
        fetchEtfData().then(data => updateEtfUi(data));
    }, POLLING_INTERVAL);
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', startRealtimeUpdates);