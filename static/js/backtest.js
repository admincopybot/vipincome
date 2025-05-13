/**
 * Backtest functionality for Income Machine
 * This script allows users to analyze ETF scores for past dates
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize date picker with default date (1 month ago)
    const today = new Date();
    const oneMonthAgo = new Date();
    oneMonthAgo.setMonth(today.getMonth() - 1);
    
    const dateInput = document.getElementById('backtest-date');
    if (dateInput) {
        dateInput.valueAsDate = oneMonthAgo;
    }
    
    // Add event listener to backtest button
    const backtestButton = document.getElementById('run-backtest');
    if (backtestButton) {
        backtestButton.addEventListener('click', runBacktest);
    }
    
    // Add event listener to reset button
    const resetButton = document.getElementById('reset-backtest');
    if (resetButton) {
        resetButton.addEventListener('click', resetBacktest);
    }
});

/**
 * Run a backtest for the selected date
 */
function runBacktest() {
    // Get selected date
    const dateInput = document.getElementById('backtest-date');
    const selectedDate = dateInput ? dateInput.value : '';
    
    if (!selectedDate) {
        showMessage('Please select a date', 'error');
        return;
    }
    
    // Show loading state
    showLoading(true);
    showMessage('Running backtest for ' + selectedDate + '...', 'info');
    
    // Selected ETFs
    let selectedETFs = [];
    const etfCheckboxes = document.querySelectorAll('input[name="backtest-etf"]:checked');
    etfCheckboxes.forEach(checkbox => {
        selectedETFs.push(checkbox.value);
    });
    
    // Default to all ETFs if none selected
    if (selectedETFs.length === 0) {
        const allCheckboxes = document.querySelectorAll('input[name="backtest-etf"]');
        allCheckboxes.forEach(checkbox => {
            selectedETFs.push(checkbox.value);
        });
    }
    
    // Run backtest
    fetch('/api/backtest', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            date: selectedDate,
            symbols: selectedETFs
        })
    })
    .then(response => response.json())
    .then(data => {
        showLoading(false);
        
        if (data.error) {
            showMessage('Error: ' + data.error, 'error');
            return;
        }
        
        // Display results
        displayBacktestResults(data);
        
        // Show success message
        showMessage('Backtest completed successfully!', 'success');
    })
    .catch(error => {
        showLoading(false);
        showMessage('Error: ' + error.message, 'error');
    });
}

/**
 * Display backtest results in the UI
 */
function displayBacktestResults(data) {
    const resultsDiv = document.getElementById('backtest-results');
    if (!resultsDiv) return;
    
    // Clear previous results
    resultsDiv.classList.remove('d-none');
    
    // Create header
    const header = document.createElement('div');
    header.className = 'backtest-header mb-3';
    header.innerHTML = `
        <h3>Backtest Results for ${data.date}</h3>
        <p class="text-muted small">Data source: ${data.source}</p>
    `;
    resultsDiv.appendChild(header);
    
    // Create results table
    const table = document.createElement('table');
    table.className = 'table table-striped';
    
    // Create table header
    const thead = document.createElement('thead');
    thead.innerHTML = `
        <tr>
            <th>Symbol</th>
            <th>Score</th>
            <th>Trend 1</th>
            <th>Trend 2</th>
            <th>Snapback</th>
            <th>Momentum</th>
            <th>Stabilizing</th>
        </tr>
    `;
    table.appendChild(thead);
    
    // Create table body
    const tbody = document.createElement('tbody');
    
    // Sort ETFs by score (descending)
    const sortedETFs = Object.entries(data.data).sort((a, b) => {
        return b[1].score - a[1].score;
    });
    
    // Add rows for each ETF
    sortedETFs.forEach(([symbol, info]) => {
        const row = document.createElement('tr');
        
        // Display error if present
        if (info.error) {
            row.innerHTML = `
                <td>${symbol}</td>
                <td colspan="6" class="text-danger">Error: ${info.error}</td>
            `;
            tbody.appendChild(row);
            return;
        }
        
        // Get indicator data
        const indicators = info.indicators || {};
        
        // Score cell with colored badge
        const scoreCell = document.createElement('td');
        const scoreBadge = document.createElement('span');
        scoreBadge.className = 'badge ' + getScoreBadgeClass(info.score);
        scoreBadge.textContent = info.score + '/5';
        scoreCell.appendChild(scoreBadge);
        
        // Create indicator cells
        const trend1Cell = createIndicatorCell(indicators.trend1 || {});
        const trend2Cell = createIndicatorCell(indicators.trend2 || {});
        const snapbackCell = createIndicatorCell(indicators.snapback || {});
        const momentumCell = createIndicatorCell(indicators.momentum || {});
        const stabilizingCell = createIndicatorCell(indicators.stabilizing || {});
        
        // Add cells to row
        row.appendChild(document.createElement('td')).textContent = symbol;
        row.appendChild(scoreCell);
        row.appendChild(trend1Cell);
        row.appendChild(trend2Cell);
        row.appendChild(snapbackCell);
        row.appendChild(momentumCell);
        row.appendChild(stabilizingCell);
        
        tbody.appendChild(row);
    });
    
    table.appendChild(tbody);
    resultsDiv.appendChild(table);
}

/**
 * Create a table cell for an indicator
 */
function createIndicatorCell(indicator) {
    const cell = document.createElement('td');
    
    if (!indicator || typeof indicator.pass === 'undefined') {
        cell.innerHTML = '<span class="text-muted">N/A</span>';
        return cell;
    }
    
    const icon = document.createElement('i');
    if (indicator.pass) {
        icon.className = 'bi bi-check-circle-fill text-success';
        cell.title = indicator.description || 'Indicator passed';
    } else {
        icon.className = 'bi bi-x-circle-fill text-danger';
        cell.title = indicator.description || 'Indicator failed';
    }
    
    cell.appendChild(icon);
    return cell;
}

/**
 * Get the appropriate badge class for a score
 */
function getScoreBadgeClass(score) {
    if (score >= 4) return 'bg-success';
    if (score >= 3) return 'bg-primary';
    if (score >= 2) return 'bg-warning text-dark';
    return 'bg-danger';
}

/**
 * Reset the backtest form and results
 */
function resetBacktest() {
    // Reset date to 1 month ago
    const today = new Date();
    const oneMonthAgo = new Date();
    oneMonthAgo.setMonth(today.getMonth() - 1);
    
    const dateInput = document.getElementById('backtest-date');
    if (dateInput) {
        dateInput.valueAsDate = oneMonthAgo;
    }
    
    // Clear results
    const resultsDiv = document.getElementById('backtest-results');
    if (resultsDiv) {
        resultsDiv.innerHTML = '';
        resultsDiv.classList.add('d-none');
    }
    
    // Reset checkboxes
    const etfCheckboxes = document.querySelectorAll('input[name="backtest-etf"]');
    etfCheckboxes.forEach(checkbox => {
        checkbox.checked = false;
    });
    
    // Clear messages
    showMessage('', '');
}

/**
 * Show a message to the user
 */
function showMessage(message, type) {
    const messageDiv = document.getElementById('backtest-message');
    if (!messageDiv) return;
    
    if (!message) {
        messageDiv.innerHTML = '';
        messageDiv.className = 'd-none';
        return;
    }
    
    messageDiv.innerHTML = message;
    messageDiv.className = 'alert alert-' + (type || 'info');
}

/**
 * Show or hide loading spinner
 */
function showLoading(show) {
    const loadingSpinner = document.getElementById('backtest-loading');
    if (!loadingSpinner) return;
    
    if (show) {
        loadingSpinner.classList.remove('d-none');
    } else {
        loadingSpinner.classList.add('d-none');
    }
    
    // Also disable/enable the run button
    const runButton = document.getElementById('run-backtest');
    if (runButton) {
        runButton.disabled = show;
    }
}