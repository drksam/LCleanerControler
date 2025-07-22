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
    
    // Cycle settings elements
    const cycleSpeedSlider = document.getElementById('cycle-speed');
    const cycleSpeedValue = document.getElementById('cycle-speed-value');
    const cycleDelaySlider = document.getElementById('cycle-delay');
    const cycleDelayValue = document.getElementById('cycle-delay-value');
    
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
    
    // Debounce mechanism to prevent rapid stop table calls
    let lastStopTime = 0;
    const STOP_DEBOUNCE_MS = 250; // Minimum time between stop calls

    /**
     * Stop the table movement in both directions
     */
    function stopTable() {
        const now = Date.now();
        
        // Debounce rapid stop calls to prevent servo interference
        if (now - lastStopTime < STOP_DEBOUNCE_MS) {
            console.log('Table stop debounced - too soon after last stop');
            return;
        }
        
        lastStopTime = now;
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
    
    /**
     * Update table cycle progress and count
     */
    function updateTableCycleStatus(cycleCount = 0, progress = 0) {
        if (cycleCountDisplay) {
            cycleCountDisplay.textContent = `${cycleCount} cycles completed`;
        }
        
        if (tableCycleProgress) {
            tableCycleProgress.style.width = progress + '%';
        }
    }
      // Track active table button interactions
    let tableButtonPressed = false;
    let activeTableButton = null;

    // Forward button
    if (tableForwardBtn) {
        tableForwardBtn.addEventListener('mousedown', function() {
            tableButtonPressed = true;
            activeTableButton = 'forward';
            moveTableForward(false);
        });
        
        tableForwardBtn.addEventListener('mouseup', function() {
            if (tableButtonPressed && activeTableButton === 'forward') {
                stopTable();
            }
            tableButtonPressed = false;
            activeTableButton = null;
        });
        
        tableForwardBtn.addEventListener('mouseleave', function() {
            if (tableButtonPressed && activeTableButton === 'forward') {
                stopTable();
            }
            tableButtonPressed = false;
            activeTableButton = null;
        });
        
        // Touch support
        tableForwardBtn.addEventListener('touchstart', function(e) {
            e.preventDefault(); // Prevent scrolling
            tableButtonPressed = true;
            activeTableButton = 'forward';
            moveTableForward(true);
        });
        
        tableForwardBtn.addEventListener('touchend', function() {
            if (tableButtonPressed && activeTableButton === 'forward') {
                stopTable();
            }
            tableButtonPressed = false;
            activeTableButton = null;
        });
    }

    // Backward button
    if (tableBackwardBtn) {
        tableBackwardBtn.addEventListener('mousedown', function() {
            tableButtonPressed = true;
            activeTableButton = 'backward';
            moveTableBackward(false);
        });
        
        tableBackwardBtn.addEventListener('mouseup', function() {
            if (tableButtonPressed && activeTableButton === 'backward') {
                stopTable();
            }
            tableButtonPressed = false;
            activeTableButton = null;
        });
        
        tableBackwardBtn.addEventListener('mouseleave', function() {
            if (tableButtonPressed && activeTableButton === 'backward') {
                stopTable();
            }
            tableButtonPressed = false;
            activeTableButton = null;
        });
        
        // Touch support
        tableBackwardBtn.addEventListener('touchstart', function(e) {
            e.preventDefault(); // Prevent scrolling
            tableButtonPressed = true;
            activeTableButton = 'backward';
            moveTableBackward(true);
        });
        
        tableBackwardBtn.addEventListener('touchend', function() {
            if (tableButtonPressed && activeTableButton === 'backward') {
                stopTable();
            }
            tableButtonPressed = false;
            activeTableButton = null;
        });
    }
    
    // Stop button - handled in auto cycle initialization
    
    // Global function to reset table button states (called from other modules)
    window.resetTableButtonStates = function() {
        tableButtonPressed = false;
        activeTableButton = null;
        console.log('Table button states reset');
    };

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
    
    // Visual indicators for table page
    const tableCycleProgress = document.getElementById('table-cycle-progress');
    const cycleCountDisplay = document.getElementById('cycle-count');
    
    // Initialize slider handlers for cycle settings
    function initSliders() {
        console.log('Initializing table page slider handlers...');
        
        // Speed slider handler
        if (cycleSpeedSlider && cycleSpeedValue) {
            console.log('Adding input listener to cycle speed slider');
            cycleSpeedSlider.addEventListener('input', function() {
                const value = this.value;
                cycleSpeedValue.textContent = value + '%';
                console.log('Cycle speed changed to:', value + '%');
                
                // TODO: Later we can send this value to the server or AutoCycleManager
                addLogMessage(`Cycle speed set to ${value}%`, false, 'info');
            });
            
            // Initialize display
            cycleSpeedValue.textContent = cycleSpeedSlider.value + '%';
        } else {
            console.warn('Cycle speed slider elements not found');
        }
        
        // Delay slider handler (if it exists)
        if (cycleDelaySlider && cycleDelayValue) {
            console.log('Adding input listener to cycle delay slider');
            cycleDelaySlider.addEventListener('input', function() {
                const value = this.value;
                cycleDelayValue.textContent = value + 's';
                console.log('Cycle delay changed to:', value + 's');
                
                // TODO: Later we can send this value to the server or AutoCycleManager
                addLogMessage(`Cycle delay set to ${value}s`, false, 'info');
            });
            
            // Initialize display
            cycleDelayValue.textContent = cycleDelaySlider.value + 's';
        } else {
            console.warn('Cycle delay slider elements not found');
        }
        
        console.log('Slider handlers initialized');
    }
    
    // Initial table status update
    if (tableStatusMsg || tableFrontLimitIndicator || tableBackLimitIndicator) {
        updateTableStatus();
        setInterval(updateTableStatus, 2000);
    }
    
    // Initialize sliders for cycle settings
    initSliders();
});