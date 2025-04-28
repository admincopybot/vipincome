/**
 * Income Machine - Real-time ETF Updates
 * This script handles fetching and displaying real-time ETF data without requiring page refresh
 */

// Store previous values to determine if prices/scores have changed
const previousValues = {
    prices: {},
    scores: {}
};

// Update frequency in milliseconds (5 seconds by default)
const UPDATE_INTERVAL = 5000;

/**
 * Fetch the latest ETF data from the API
 */
async function fetchEtfData() {
    try {
        const response = await fetch('/api/etf-data');
        if (!response.ok) {
            throw new Error(`API response error: ${response.status}`);
        }
        const data = await response.json();
        updateEtfUi(data);
        return data;
    } catch (error) {
        console.error('Error fetching ETF data:', error);
        return null;
    }
}

/**
 * Update the UI with the latest ETF data
 */
function updateEtfUi(data) {
    if (!data) return;
    
    // Only update each ETF's price, not the score (per user request)
    // Scores should only update when the page is manually refreshed
    Object.entries(data).forEach(([symbol, etfData]) => {
        // Update price in real-time
        updateEtfPrice(symbol, etfData.price);
        
        // Don't update score in real-time - scores should remain stable
        // updateEtfScore(symbol, etfData.score); - DISABLED
    });
}

/**
 * Update an ETF's price display
 */
function updateEtfPrice(symbol, newPrice) {
    const priceElement = document.querySelector(`[data-etf-price="${symbol}"]`);
    if (!priceElement) return;
    
    // Remove any existing animation classes
    priceElement.classList.remove('price-up', 'price-down');
    
    // Format price as currency
    const formattedPrice = `$${newPrice.toFixed(2)}`;
    
    // If we have a previous price, compare and add animation class
    if (previousValues.prices[symbol]) {
        const previousPrice = previousValues.prices[symbol];
        if (newPrice > previousPrice) {
            priceElement.classList.add('price-up');
        } else if (newPrice < previousPrice) {
            priceElement.classList.add('price-down');
        }
    }
    
    // Update the displayed price and store the new value
    priceElement.textContent = formattedPrice;
    previousValues.prices[symbol] = newPrice;
}

/**
 * Update an ETF's score display
 */
function updateEtfScore(symbol, score) {
    const scoreElement = document.querySelector(`[data-etf-score="${symbol}"]`);
    if (!scoreElement) return;
    
    // Remove any existing animation classes
    scoreElement.classList.remove('score-up', 'score-down');
    
    // If we have a previous score, compare and add animation class
    if (previousValues.scores[symbol] !== undefined) {
        const previousScore = previousValues.scores[symbol];
        if (score > previousScore) {
            scoreElement.classList.add('score-up');
            
            // Update badge styling based on new score
            updateScoreBadgeStyle(scoreElement, score);
        } else if (score < previousScore) {
            scoreElement.classList.add('score-down');
            
            // Update badge styling based on new score
            updateScoreBadgeStyle(scoreElement, score);
        }
    }
    
    // Update the score text and store the new value
    scoreElement.textContent = `${score}/5`;
    previousValues.scores[symbol] = score;
    
    // Also update progress bars if they exist
    updateProgressBar(symbol, score);
}

/**
 * Update the score badge style based on the score value
 */
function updateScoreBadgeStyle(element, score) {
    // Update the background and text color based on the score
    if (score >= 4) {
        element.style.background = 'linear-gradient(135deg, #00C8FF, #7970FF)';
        element.style.color = '#fff';
    } else if (score >= 3) {
        element.style.background = '#FFD700';
        element.style.color = '#000';
    } else {
        element.style.background = '#6c757d';
        element.style.color = '#fff';
    }
}

/**
 * Update the progress bar for an ETF if it exists
 */
function updateProgressBar(symbol, score) {
    // Find progress bars associated with this ETF by finding parent card and then progress bar
    const scoreElement = document.querySelector(`[data-etf-score="${symbol}"]`);
    if (!scoreElement) return;
    
    // Look for any progres bar in the parent card
    const card = scoreElement.closest('.card');
    if (!card) return;
    
    const progressBar = card.querySelector('.progress-bar');
    if (!progressBar) return;
    
    // Update progress bar width and class
    progressBar.style.width = `${score * 20}%`;
    progressBar.setAttribute('aria-valuenow', score * 20);
    
    // Remove all progress bar score classes
    for (let i = 0; i <= 5; i++) {
        progressBar.classList.remove(`progress-bar-score-${i}`);
    }
    
    // Add the new score class
    progressBar.classList.add(`progress-bar-score-${score}`);
}

/**
 * Apply a visual flash effect to an element
 */
function flashElement(element, color) {
    // Save original color
    const originalColor = element.style.color;
    
    // Change color
    element.style.color = color;
    
    // Revert after animation time
    setTimeout(() => {
        element.style.color = originalColor;
    }, 1000);
}

/**
 * Start the real-time updates
 */
function startRealtimeUpdates() {
    console.log("Starting real-time ETF price updates...");
    
    // Fetch initial data
    fetchEtfData();
    
    // Set up periodic updates
    setInterval(fetchEtfData, UPDATE_INTERVAL);
}

// Start updates when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', startRealtimeUpdates);