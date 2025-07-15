/**
 * Table Control JavaScript
 * Handles table movements with comprehensive logging
 */

document.addEventListener('DOMContentLoaded', function() {
    // Use the utility library for simulation mode
    const ShopUtils = window.ShopUtils || {};
    let currentOperationMode = 'unknown';
    
    // Initialize with the operation mode from the utility library
    if (ShopUtils.getOperationMode) {
        currentOperationMode = ShopUtils.getOperationMode();
        console.log(`Using operation mode from utility: ${currentOperationMode}`);
    } else {
        // Fall back to original method if utility is not available
        fetch('/api/system/mode')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    currentOperationMode = data.mode;
                    console.log(`Current operation mode: ${currentOperationMode}`);
                }
            })
            .catch(error => {
                console.error('Error fetching operation mode:', error);
            });
    }
    
    // Use utility functions if available, otherwise use local implementations
    const addSimulationWarning = ShopUtils.addSimulationWarning || function(message) {
        // Remove any existing warning first
        clearSimulationWarnings();
        
        // Create a new warning alert
        const warningDiv = document.createElement('div');
        warningDiv.className = 'alert alert-warning simulation-warning mt-3';
        warningDiv.innerHTML = '<i class="fas fa-exclamation-triangle me-2"></i>' + message;
        
        // Insert at the top of the card body
        const cardBody = document.querySelector('.card-body');
        if (cardBody) {
            cardBody.insertBefore(warningDiv, cardBody.firstChild);
        }
    };
    
    const addSimulationError = ShopUtils.addSimulationError || function(message) {
        // Remove any existing warning first
        clearSimulationWarnings();
        
        // Create a new error alert
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger simulation-warning mt-3';
        errorDiv.innerHTML = '<i class="fas fa-exclamation-triangle me-2"></i>' + message;
        
        // Insert at the top of the card body
        const cardBody = document.querySelector('.card-body');
        if (cardBody) {
            cardBody.insertBefore(errorDiv, cardBody.firstChild);
        }
    };
    
    const clearSimulationWarnings = ShopUtils.clearSimulationWarnings || function() {
        document.querySelectorAll('.simulation-warning').forEach(el => el.remove());
    };
    
    /**
     * Makes a standardized AJAX request with consistent error handling
     * @param {string} url - URL to make the request to
     * @param {string} [method='GET'] - HTTP method to use
     * @param {Object} [data=null] - Data to send with the request
     * @param {Function} [successCallback=null] - Function to call on success
     * @param {Function} [errorCallback=null] - Function to call on error
     * @param {Function} [finallyCallback=null] - Function to call regardless of success/failure
     */
    const makeRequest = window.makeRequest || function(url, method = 'GET', data = null, logFunction = addLogMessage, onSuccess = null, onError = null, onFinally = null) {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            }
        };
        
        if (data && (method === 'POST' || method === 'PUT')) {
            options.body = JSON.stringify(data);
        }
        
        return fetch(url, options)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (typeof onSuccess === 'function') {
                    onSuccess(data);
                }
                return data;
            })
            .catch(error => {
                console.error(`[TABLE_CONTROL.JS] Request failed:`, error);
                if (typeof logFunction === 'function') {
                    logFunction(`Error: ${error.message}`, true);
                }
                if (typeof onError === 'function') {
                    onError(error);
                }
            })
            .finally(() => {
                if (typeof onFinally === 'function') {
                    onFinally();
                }
            });
    };
    
    /**
     * Handles simulation response data consistently based on operation mode
     * @param {Object} data - API response data
     * @param {string} actionName - Description of the action being performed
     * @param {boolean} [logSuccess=true] - Whether to log success messages
     * @returns {boolean} - True if simulated, false otherwise
     */
    const handleSimulationResponse = ShopUtils.handleSimulationResponse || function(data, actionName, logSuccess = true) {
        if (!data || !data.simulated) {
            clearSimulationWarnings();
            return false;
        }
        
        // For simulation mode, this is expected
        if (currentOperationMode === 'simulation') {
            if (logSuccess) {
                addLogMessage(`${actionName} complete! (simulation mode)`, false, 'success');
            } else {
                console.log(`${actionName} (simulation mode)`);
            }
        } 
        // For prototype mode, this should NEVER happen
        else if (currentOperationMode === 'prototype') {
            addLogMessage(`ERROR: ${actionName} simulation in PROTOTYPE MODE. Hardware is required!`, true);
            addSimulationError('HARDWARE ERROR: Receiving simulated values in PROTOTYPE MODE. Check your hardware connections.');
        } 
        // For normal mode, it's a warning
        else {
            addLogMessage(`WARNING: ${actionName} simulated due to hardware error`, false, 'warning');
            addSimulationWarning('Hardware error detected - using simulation values');
        }
        
        return true;
    };
    
    // Table control buttons
    const tableForwardBtn = document.getElementById('table-forward-button');
    const tableBackwardBtn = document.getElementById('table-backward-button');
    const tableStopBtn = document.getElementById('stop-table-button');
    const tableRunBtn = document.getElementById('run-table-button'); // For table page start button
    
    // Table status elements
    const tableStatusMsg = document.getElementById('table-movement-status');
    const tableFrontLimitIndicator = document.getElementById('table-front-limit-status');
    const tableBackLimitIndicator = document.getElementById('table-back-limit-status');
    
    // Initialize with a log message
    if (window.addLogMessage) {
        window.addLogMessage('Table control system ready', false, 'info');
    } else {
        console.error('addLogMessage function not found in global scope');
    }
    
    // Track table status query error count to avoid flooding logs
    let tableStatusErrorCount = 0;
    
    /**
     * Move the table forward
     * @param {boolean} [touch=false] - Whether this was triggered by touch event
     */
    function moveTableForward(touch = false) {
        addLogMessage('Moving table forward...', false, 'action');
        clearSimulationWarnings();
        
        makeRequest(
            '/table/forward',
            'POST',
            { state: true },
            addLogMessage,
            function(data) {
                if (data.status === 'success') {
                    // Use handleSimulationResponse utility but don't log success messages
                    // since the user is holding the button and we don't want to spam logs
                    handleSimulationResponse(data, 'Table moving forward', false);
                } else {
                    addLogMessage(`Error moving table forward: ${data.message}`, true);
                }
            },
            function(error) {
                console.error('Forward movement request failed:', error);
            }
        );
    }
    
    /**
     * Move the table backward
     * @param {boolean} [touch=false] - Whether this was triggered by touch event
     */
    function moveTableBackward(touch = false) {
        addLogMessage('Moving table backward...', false, 'action');
        clearSimulationWarnings();
        
        makeRequest(
            '/table/backward',
            'POST',
            { state: true },
            addLogMessage,
            function(data) {
                if (data.status === 'success') {
                    // Use handleSimulationResponse utility but don't log success messages
                    // since the user is holding the button and we don't want to spam logs
                    handleSimulationResponse(data, 'Table moving backward', false);
                } else {
                    addLogMessage(`Error moving table backward: ${data.message}`, true);
                }
            },
            function(error) {
                console.error('Backward movement request failed:', error);
            }
        );
    }
    
    /**
     * Stop the table movement in both directions
     */
    function stopTable() {
        addLogMessage('Stopping table...', false, 'action');
        clearSimulationWarnings();
        
        // Stop forward direction first
        makeRequest(
            '/table/forward',
            'POST',
            { state: false },
            addLogMessage,
            function(data) {
                // Check for simulation when stopping forward movement
                handleSimulationResponse(data, 'Table forward stop', false);
                
                // Then stop backward direction
                makeRequest(
                    '/table/backward',
                    'POST',
                    { state: false },
                    addLogMessage,
                    function(data) {
                        // Check for simulation when stopping backward movement
                        handleSimulationResponse(data, 'Table backward stop', false);
                        addLogMessage('Table stopped', false, 'success');
                    },
                    function(error) {
                        console.error('Failed to stop backward movement:', error);
                    }
                );
            },
            function(error) {
                console.error('Failed to stop forward movement:', error);
                // Still try to stop the backward movement even if forward fails
                makeRequest(
                    '/table/backward',
                    'POST',
                    { state: false },
                    addLogMessage,
                    function(data) {
                        addLogMessage('Table stopped', false, 'success');
                    },
                    function(error) {
                        addLogMessage('Error stopping table in both directions', true);
                    }
                );
            }
        );
    }
    
    // Forward button
    if (tableForwardBtn) {
        tableForwardBtn.addEventListener('mousedown', function() {
            moveTableForward(false);
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
            moveTableForward(true);
        });
        
        tableForwardBtn.addEventListener('touchend', function() {
            stopTable();
        });
    }
    
    // Backward button
    if (tableBackwardBtn) {
        tableBackwardBtn.addEventListener('mousedown', function() {
            moveTableBackward(false);
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
            moveTableBackward(true);
        });
        
        tableBackwardBtn.addEventListener('touchend', function() {
            stopTable();
        });
    }
    
    // Stop button - handled in auto cycle initialization
    
    /**
     * Updates the table status UI with current position data
     * Polls the server to get status of table position, direction, and limit switches
     */
    function updateTableStatus() {
        makeRequest(
            '/table/status',
            'GET',
            null,
            null, // No logging for status updates to avoid spam
            function(data) {
                // Reset error count on success
                tableStatusErrorCount = 0;
                
                // Check if we're getting simulated data when we shouldn't
                if (data.simulated && currentOperationMode === 'prototype') {
                    addSimulationError('HARDWARE ERROR: Receiving simulated status in PROTOTYPE MODE. Check your hardware connections.');
                    console.error('Received simulated table status in prototype mode');
                } else if (data.simulated && currentOperationMode !== 'simulation') {
                    // For normal mode, show a warning
                    addSimulationWarning('Hardware error detected - showing simulated table status values');
                } else if (!data.simulated) {
                    // Clear warnings if we're getting real hardware data
                    clearSimulationWarnings();
                }
                
                updateStatusDisplay(data);
            },
            function(error) {
                // Only log every 5th error to avoid flooding the log
                tableStatusErrorCount++;
                if (tableStatusErrorCount % 5 === 1) {
                    console.error('Error checking table status:', error);
                }
                
                setStatusToUnknown();
            }
        );
    }
    
    /**
     * Updates the status display UI elements based on table data
     * @param {Object} data - Table status data from the server
     */
    function updateStatusDisplay(data) {
        if (tableStatusMsg) {
            if (data.table_forward_state) {
                tableStatusMsg.textContent = 'Moving Forward';
                tableStatusMsg.className = 'badge bg-success';
            } else if (data.table_backward_state) {
                tableStatusMsg.textContent = 'Moving Backward';
                tableStatusMsg.className = 'badge bg-success';
            } else {
                tableStatusMsg.textContent = 'Stopped';
                tableStatusMsg.className = 'badge bg-secondary';
            }
        }
        
        // Update limit switch indicators
        if (tableFrontLimitIndicator) {
            if (data.table_front_switch_state) {
                tableFrontLimitIndicator.className = 'badge bg-danger';
                tableFrontLimitIndicator.textContent = 'Activated';
            } else {
                tableFrontLimitIndicator.className = 'badge bg-secondary';
                tableFrontLimitIndicator.textContent = 'Not Active';
            }
        }
        
        if (tableBackLimitIndicator) {
            if (data.table_back_switch_state) {
                tableBackLimitIndicator.className = 'badge bg-danger';
                tableBackLimitIndicator.textContent = 'Activated';
            } else {
                tableBackLimitIndicator.className = 'badge bg-secondary';
                tableBackLimitIndicator.textContent = 'Not Active';
            }
        }
    }
    
    /**
     * Sets the status display to "Unknown" when communication fails
     */
    function setStatusToUnknown() {
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
    }
    
    // Auto cycle elements
    const autoCycleEnableSwitch = document.getElementById('auto-cycle-enable-switch');
    
    // Get the global auto cycle manager
    const autoCycleManager = window.AutoCycleManager;
    
    /**
     * Initialize auto cycle functionality using shared manager
     */
    function initAutoCycle() {
        if (!autoCycleManager) {
            console.warn('AutoCycleManager not available - auto cycle features disabled');
            return;
        }
        
        // Configure the auto cycle manager with table movement functions
        autoCycleManager.setForwardFunction(() => {
            makeRequest('/table/forward', 'POST', { state: true }, addLogMessage, null, function(error) {
                console.error('Auto cycle forward failed:', error);
            });
        });
        
        autoCycleManager.setBackwardFunction(() => {
            makeRequest('/table/backward', 'POST', { state: true }, addLogMessage, null, function(error) {
                console.error('Auto cycle backward failed:', error);
            });
        });
        
        autoCycleManager.setStopFunction(() => {
            stopTable();
        });
        
        // Initialize enable switch state
        if (autoCycleEnableSwitch) {
            // Get current state from manager and sync switch
            const managerState = autoCycleManager.isEnabled();
            autoCycleEnableSwitch.checked = managerState;
            console.log('Auto cycle enable switch synced with manager state:', managerState);
            
            // Also try to get state from server to ensure consistency
            setTimeout(() => {
                makeRequest('/table/status', 'GET', null, addLogMessage, 
                    function(data) {
                        if (data && typeof data.auto_cycle_enabled !== 'undefined') {
                            const serverState = data.auto_cycle_enabled;
                            console.log('Server auto-cycle state:', serverState);
                            
                            // Update both switch and manager
                            autoCycleEnableSwitch.checked = serverState;
                            autoCycleManager.setEnabled(serverState);
                            
                            console.log('Auto cycle switch and manager synced with server state:', serverState);
                        }
                    },
                    function(error) {
                        console.warn('Could not fetch auto-cycle state from server:', error);
                    }
                );
            }, 500); // Small delay to ensure other scripts are loaded
            
            // Add change listener
            autoCycleEnableSwitch.addEventListener('change', function() {
                console.log('Auto cycle enable switch changed to:', this.checked);
                autoCycleManager.setEnabled(this.checked);
                addLogMessage(`Auto cycle ${this.checked ? 'enabled' : 'disabled'}`, false, 'info');
            });
        } else {
            console.warn('Auto cycle enable switch not found');
        }
        
        console.log('Auto cycle initialization complete');
    }
    
    // Initialize table button handlers (independent of AutoCycleManager)
    function initTableButtons() {
        console.log('Initializing table page button handlers...');
        
        // Run Table button handler - starts auto cycle if enabled
        if (tableRunBtn) {
            console.log('Adding click listener to table run button');
            tableRunBtn.addEventListener('click', function() {
                console.log('Table run button clicked');
                
                if (autoCycleManager && autoCycleManager.isEnabled()) {
                    try {
                        console.log('Starting auto-cycle from table page');
                        autoCycleManager.start();
                        addLogMessage('Auto-cycle started from table page', false, 'success');
                    } catch (error) {
                        console.error('Error starting auto-cycle:', error);
                        addLogMessage('Error starting auto-cycle: ' + error.message, true);
                    }
                } else if (autoCycleManager) {
                    console.log('Auto-cycle not enabled, performing manual forward movement');
                    addLogMessage('Auto-cycle not enabled. Using manual forward movement.', false, 'warning');
                    moveTableForward();
                } else {
                    console.log('AutoCycleManager not available, performing manual forward movement');
                    addLogMessage('Auto-cycle manager not available. Using manual forward movement.', false, 'warning');
                    moveTableForward();
                }
            });
        } else {
            console.warn('Table run button not found');
        }
        
        // Stop Table button handler - handles both auto cycle and manual stop
        if (tableStopBtn) {
            console.log('Adding click listener to table stop button');
            tableStopBtn.addEventListener('click', function() {
                console.log('Stop Table button clicked on table page');
                
                if (autoCycleManager) {
                    try {
                        autoCycleManager.stop();
                        console.log('Auto-cycle stopped successfully');
                    } catch (error) {
                        console.error('Error stopping auto-cycle:', error);
                    }
                }
                
                stopTable(); // Also stop any manual movement
                addLogMessage('Table movement stopped', false, 'info');
            });
        } else {
            console.warn('Stop Table button not found');
        }
        
        console.log('Table button handlers initialized');
    }
    
    // Initial table status update
    if (tableStatusMsg || tableFrontLimitIndicator || tableBackLimitIndicator) {
        updateTableStatus();
        setInterval(updateTableStatus, 2000);
    }
    
    // Initialize table buttons (always)
    initTableButtons();
    
    // Initialize auto cycle functionality
    initAutoCycle();
});