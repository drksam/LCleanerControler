/**
 * Table Control JavaScript
 * Handles table movements with comprehensive logging
 */

document.addEventListener('DOMContentLoaded', function() {
    // Table control buttons
    const tableForwardBtn = document.getElementById('table-forward-button');
    const tableBackwardBtn = document.getElementById('table-backward-button');
    const tableStopBtn = document.getElementById('stop-table-button');
    
    // Table status elements
    const tableStatusMsg = document.getElementById('table-movement-status');
    const tableFrontLimitIndicator = document.getElementById('table-front-limit-status');
    const tableBackLimitIndicator = document.getElementById('table-back-limit-status');
    
    // addLogMessage function is defined in base.html and will use localStorage
    // for log persistence across page changes
    
    // Initialize with a log message
    if (window.addLogMessage) {
        window.addLogMessage('Table control system ready', false, 'info');
    } else {
        console.error('addLogMessage function not found in global scope');
    }
    
    // Track table status query error count to avoid flooding logs
    let tableStatusErrorCount = 0;
    
    // Forward button
    if (tableForwardBtn) {
        tableForwardBtn.addEventListener('mousedown', function() {
            addLogMessage('Moving table forward...', false, 'action');
            
            fetch('/table/forward', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    state: true
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status !== 'success') {
                    addLogMessage(`Error moving table forward: ${data.message}`, true);
                }
            })
            .catch(error => {
                addLogMessage(`Error: ${error.message}`, true);
            });
        });
        
        tableForwardBtn.addEventListener('mouseup', function() {
            stopTable();
        });
        
        tableForwardBtn.addEventListener('mouseleave', function() {
            stopTable();
        });
        
        // Touch support
        tableForwardBtn.addEventListener('touchstart', function(e) {
            e.preventDefault(); // Prevent scrolling
            addLogMessage('Moving table forward...', false, 'action');
            
            fetch('/table/forward', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    state: true
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status !== 'success') {
                    addLogMessage(`Error moving table forward: ${data.message}`, true);
                }
            })
            .catch(error => {
                addLogMessage(`Error: ${error.message}`, true);
            });
        });
        
        tableForwardBtn.addEventListener('touchend', function() {
            stopTable();
        });
    }
    
    // Backward button
    if (tableBackwardBtn) {
        tableBackwardBtn.addEventListener('mousedown', function() {
            addLogMessage('Moving table backward...', false, 'action');
            
            fetch('/table/backward', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    state: true
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status !== 'success') {
                    addLogMessage(`Error moving table backward: ${data.message}`, true);
                }
            })
            .catch(error => {
                addLogMessage(`Error: ${error.message}`, true);
            });
        });
        
        tableBackwardBtn.addEventListener('mouseup', function() {
            stopTable();
        });
        
        tableBackwardBtn.addEventListener('mouseleave', function() {
            stopTable();
        });
        
        // Touch support
        tableBackwardBtn.addEventListener('touchstart', function(e) {
            e.preventDefault(); // Prevent scrolling
            addLogMessage('Moving table backward...', false, 'action');
            
            fetch('/table/backward', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    state: true
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status !== 'success') {
                    addLogMessage(`Error moving table backward: ${data.message}`, true);
                }
            })
            .catch(error => {
                addLogMessage(`Error: ${error.message}`, true);
            });
        });
        
        tableBackwardBtn.addEventListener('touchend', function() {
            stopTable();
        });
    }
    
    // Stop button
    if (tableStopBtn) {
        tableStopBtn.addEventListener('click', function() {
            stopTable();
        });
    }
    
    function stopTable() {
        addLogMessage('Stopping table...', false, 'action');
        
        // Stop both directions
        fetch('/table/forward', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                state: false
            })
        }).then(() => {
            return fetch('/table/backward', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    state: false
                })
            });
        }).then(() => {
            addLogMessage('Table stopped', false, 'success');
        }).catch(error => {
            addLogMessage(`Error stopping table: ${error.message}`, true);
        });
    }
    
    // Update table status every 2 seconds
    function updateTableStatus() {
        fetch('/table/status')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                // Reset error count on success
                tableStatusErrorCount = 0;
                
                if (tableStatusMsg) {
                    if (data.forward) {
                        tableStatusMsg.textContent = 'Moving Forward';
                        tableStatusMsg.className = 'badge bg-success';
                    } else if (data.backward) {
                        tableStatusMsg.textContent = 'Moving Backward';
                        tableStatusMsg.className = 'badge bg-success';
                    } else {
                        tableStatusMsg.textContent = 'Stopped';
                        tableStatusMsg.className = 'badge bg-secondary';
                    }
                }
                
                // Update limit switch indicators
                if (tableFrontLimitIndicator) {
                    if (data.front_limit) {
                        tableFrontLimitIndicator.className = 'badge bg-danger';
                        tableFrontLimitIndicator.textContent = 'Activated';
                    } else {
                        tableFrontLimitIndicator.className = 'badge bg-secondary';
                        tableFrontLimitIndicator.textContent = 'Not Active';
                    }
                }
                
                if (tableBackLimitIndicator) {
                    if (data.back_limit) {
                        tableBackLimitIndicator.className = 'badge bg-danger';
                        tableBackLimitIndicator.textContent = 'Activated';
                    } else {
                        tableBackLimitIndicator.className = 'badge bg-secondary';
                        tableBackLimitIndicator.textContent = 'Not Active';
                    }
                }
            })
            .catch(error => {
                // Only log every 5th error to avoid flooding the log
                tableStatusErrorCount++;
                if (tableStatusErrorCount % 5 === 1) {
                    console.error('Error checking table status:', error);
                }
                
                // Set status indicators to "Unknown" state
                if (tableStatusMsg) {
                    tableStatusMsg.textContent = 'Unknown';
                    tableStatusMsg.className = 'badge bg-warning';
                }
                
                if (tableFrontLimitIndicator) {
                    tableFrontLimitIndicator.className = 'badge bg-warning';
                    tableFrontLimitIndicator.textContent = 'Unknown';
                }
                
                if (tableBackLimitIndicator) {
                    tableBackLimitIndicator.className = 'badge bg-warning';
                    tableBackLimitIndicator.textContent = 'Unknown';
                }
            });
    }
    
    // Initial table status update
    if (tableStatusMsg || tableFrontLimitIndicator || tableBackLimitIndicator) {
        updateTableStatus();
        setInterval(updateTableStatus, 2000);
    }
});