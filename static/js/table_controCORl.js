/**
 * Table Control JavaScript
 * Handles table movements with comprehensive logging
 */

document.addEventListener('DOMContentLoaded', function() {
    // Ensure addLogMessage         // Initialize enable switch state
        if (autoCycleEnableSwitch) {
            // Get current state from manager and sync switch
                   makeRequest('/table/forward',            makeRequest('/table/backward', 'POST', { state: false }, addLogMessage, function(data) {
                handleSimulationResponse(data, 'backward movement stop');
            }, function(error) {
                console.error('Failed to stop backward movement:', error);
            });OST', { state: false }, addLogMessage, function(data) {
                handleSimulationResponse(data, 'forward movement stop');
            }, function(error) {
                console.error('Failed to stop forward movement:', error);
            });  const managerState = autoCycleManager.isEnabled();
            autoCycleEnableSwitch.checked = managerState;
            console.log('Auto cycle enable switch synced with manager state:', managerState);
            
            // Add change listener
            autoCycleEnableSwitch.addEventListener('change', function() {
                console.log('Auto cycle enable switch changed to:', this.checked);
                autoCycleManager.setEnabled(this.checked);
                addLogMessage(`Auto cycle ${this.checked ? 'enabled' : 'disabled'}`, false, 'info');
            });
        } else {
            console.warn('Auto cycle enable switch not found');
        }lable
    if (typeof window.addLogMessage !== 'function') {
        console.error('window.addLogMessage function not available - creating fallback');
        
        // Create a fallback addLogMessage function
        window.addLogMessage = function(message, isError = false, logType = 'info') {
            console.log(`[${logType.toUpperCase()}] ${message}`);
        };
    }
    
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
    const runTableBtn = document.getElementById('run-table-button');
    
    // Auto cycle elements
    const autoCycleEnableSwitch = document.getElementById('auto-cycle-enable-switch');
    const cycleDelaySlider = document.getElementById('cycle-delay');
    const cycleDelayValue = document.getElementById('cycle-delay-value');
    const cycleCount = document.getElementById('cycle-count');
    const cycleProgress = document.getElementById('table-cycle-progress');
    
    // Get the global auto cycle manager
    const autoCycleManager = window.AutoCycleManager;
    
    /**
     * Initialize auto cycle functionality using shared manager
     */
    function initAutoCycle() {
        // Set up callbacks for UI updates
        autoCycleManager.onStateChange = updateRunTableButtonState;
        autoCycleManager.onCycleCountChange = updateCycleDisplay;
        autoCycleManager.onProgressChange = updateProgressBar;
        
        // Initialize enable switch state
        if (autoCycleEnableSwitch) {
            // Load initial state (default to disabled)
            const initialState = autoCycleEnableSwitch.checked || false;
            console.log('Auto cycle enable switch initial state:', initialState);
            autoCycleManager.setEnabled(initialState);
            
            // Enable/disable switch handler
            autoCycleEnableSwitch.addEventListener('change', function() {
                console.log('Auto cycle enable switch changed to:', this.checked);
                autoCycleManager.setEnabled(this.checked);
                addLogMessage(`Auto cycle ${this.checked ? 'enabled' : 'disabled'}`, false, 'info');
            });
        } else {
            console.warn('Auto cycle enable switch not found');
        }
        
        // Run Table button handler
        if (runTableBtn) {
            runTableBtn.addEventListener('click', function() {
                console.log('Run Table button clicked');
                autoCycleManager.start();
            });
        } else {
            console.warn('Run Table button not found');
        }
        
        // Stop Table button handler - handles both auto cycle and manual stop
        if (tableStopBtn) {
            tableStopBtn.addEventListener('click', function() {
                console.log('Stop Table button clicked');
                autoCycleManager.stop();
                stopTable(); // Also stop any manual movement
            });
        } else {
            console.warn('Stop Table button not found');
        }
        
        // Delay slider handler
        if (cycleDelaySlider && cycleDelayValue) {
            cycleDelaySlider.addEventListener('input', function() {
                const value = parseFloat(this.value);
                cycleDelayValue.textContent = value + 's';
                autoCycleManager.setDelay(value);
                console.log('Cycle delay set to:', value, 'seconds');
            });
            // Set initial delay
            autoCycleManager.setDelay(parseFloat(cycleDelaySlider.value || 1));
        }
        
        updateRunTableButtonState();
        console.log('Auto cycle initialization complete');
    }
    
    /**
     * Update the cycle count display
     */
    function updateCycleDisplay(count) {
        if (cycleCount) {
            cycleCount.textContent = `${count} cycles completed`;
        }
    }
    
    /**
     * Update the progress bar
     */
    function updateProgressBar(percentage) {
        if (cycleProgress) {
            cycleProgress.style.width = percentage + '%';
        }
    }
    
    /**
     * Update the Run Table button state based on auto cycle status
     */
    function updateRunTableButtonState() {
        const state = autoCycleManager.getState();
        
        if (runTableBtn) {
            if (state.running) {
                runTableBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Running...';
                runTableBtn.disabled = true;
                runTableBtn.classList.add('active');
            } else if (state.enabled) {
                runTableBtn.innerHTML = '<i class="fas fa-play me-2"></i> Run Table';
                runTableBtn.disabled = false;
                runTableBtn.classList.remove('active');
            } else {
                runTableBtn.innerHTML = '<i class="fas fa-play me-2"></i> Run Table (Disabled)';
                runTableBtn.disabled = true;
                runTableBtn.classList.remove('active');
            }
        }
        
        if (tableStopBtn) {
            if (state.running) {
                tableStopBtn.classList.add('active');
            } else {
                tableStopBtn.classList.remove('active');
            }
        }
    }
    
    // Configure the auto cycle manager with table movement functions
    if (autoCycleManager) {
        // Note: configure method doesn't exist, removing this call
        // The AutoCycleManager handles its own movement logic
    }
    
    // Manual button event handlers - Momentary (jog) style
    if (tableForwardBtn) {
        console.log('Setting up forward button as momentary');
        
        // Start forward movement on mousedown/touchstart
        const startForward = function() {
            console.log('Manual forward button pressed - starting movement');
            makeRequest('/table/forward', 'POST', { state: true }, addLogMessage, function(data) {
                handleSimulationResponse(data, 'forward movement');
            }, function(error) {
                console.error('Failed to start forward movement:', error);
            });
        };
        
        // Stop forward movement on mouseup/touchend/mouseleave
        const stopForward = function() {
            console.log('Manual forward button released - stopping movement');
            makeRequest('/table/forward', 'POST', { state: false }, function(data) {
                handleSimulationResponse(data, 'stop forward movement');
            });
        };
        
        // Mouse events
        tableForwardBtn.addEventListener('mousedown', startForward);
        tableForwardBtn.addEventListener('mouseup', stopForward);
        tableForwardBtn.addEventListener('mouseleave', stopForward); // Stop if mouse leaves button
        
        // Touch events for mobile
        tableForwardBtn.addEventListener('touchstart', startForward);
        tableForwardBtn.addEventListener('touchend', stopForward);
        tableForwardBtn.addEventListener('touchcancel', stopForward);
        
        // Prevent default click behavior
        tableForwardBtn.addEventListener('click', function(e) {
            e.preventDefault();
        });
    }
    
    if (tableBackwardBtn) {
        console.log('Setting up backward button as momentary');
        
        // Start backward movement on mousedown/touchstart
        const startBackward = function() {
            console.log('Manual backward button pressed - starting movement');
            makeRequest('/table/backward', 'POST', { state: true }, addLogMessage, function(data) {
                handleSimulationResponse(data, 'backward movement');
            }, function(error) {
                console.error('Failed to start backward movement:', error);
            });
        };
        
        // Stop backward movement on mouseup/touchend/mouseleave
        const stopBackward = function() {
            console.log('Manual backward button released - stopping movement');
            makeRequest('/table/backward', 'POST', { state: false }, function(data) {
                handleSimulationResponse(data, 'stop backward movement');
            });
        };
        
        // Mouse events
        tableBackwardBtn.addEventListener('mousedown', startBackward);
        tableBackwardBtn.addEventListener('mouseup', stopBackward);
        tableBackwardBtn.addEventListener('mouseleave', stopBackward); // Stop if mouse leaves button
        
        // Touch events for mobile
        tableBackwardBtn.addEventListener('touchstart', startBackward);
        tableBackwardBtn.addEventListener('touchend', stopBackward);
        tableBackwardBtn.addEventListener('touchcancel', stopBackward);
        
        // Prevent default click behavior
        tableBackwardBtn.addEventListener('click', function(e) {
            e.preventDefault();
        });
    }
    
    // Stop table function - stops all movement
    function stopTable() {
        console.log('stopTable() called - stopping all table movement');
        makeRequest('/table/forward', 'POST', { state: false });
        makeRequest('/table/backward', 'POST', { state: false });
    }
    
    // Initialize auto cycle when page loads
    initAutoCycle();

    // Initial table status update
    if (tableStatusMsg || tableFrontLimitIndicator || tableBackLimitIndicator) {
        updateTableStatus();
        setInterval(updateTableStatus, 2000);
    }
});