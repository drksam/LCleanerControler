/**
 * GPIO Test Panel JavaScript
 * Handles the functionality for GPIO input monitoring and output control
 */

document.addEventListener('DOMContentLoaded', function() {
    // Use the utility library
    const ShopUtils = window.ShopUtils || {};
    let currentOperationMode = 'unknown';
    
    /**
     * Initialize status toast for displaying temporary notifications
     * @type {Object}
     */
    const statusToast = {
        element: document.getElementById('statusToast') || createStatusToast(),
        bodyElement: document.getElementById('statusToastBody'),
        
        /**
         * Shows a toast message with the appropriate styling
         * @param {string} message - The message to display
         * @param {boolean} isError - Whether this is an error message
         * @param {boolean} isWarning - Whether this is a warning message
         */
        show: function(message, isError = false, isWarning = false) {
            // Set the toast content and styles
            this.bodyElement.textContent = message;
            
            // Reset classes
            this.element.classList.remove('bg-success', 'bg-danger', 'bg-warning');
            
            if (isError) {
                this.element.classList.add('bg-danger');
            } else if (isWarning) {
                this.element.classList.add('bg-warning');
                this.element.classList.add('text-dark');
            } else {
                this.element.classList.add('bg-success');
            }
            
            // Show the toast using Bootstrap
            const bsToast = new bootstrap.Toast(this.element);
            bsToast.show();
        }
    };
    
    /**
     * Creates a status toast element if it doesn't exist
     * @returns {HTMLElement} - The created toast element
     */
    function createStatusToast() {
        const toast = document.createElement('div');
        toast.id = 'statusToast';
        toast.className = 'toast align-items-center text-white bg-success border-0 position-fixed bottom-0 end-0 m-3';
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        const flexDiv = document.createElement('div');
        flexDiv.className = 'd-flex';
        
        const body = document.createElement('div');
        body.id = 'statusToastBody';
        body.className = 'toast-body';
        
        const closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'btn-close btn-close-white me-2 m-auto';
        closeBtn.setAttribute('data-bs-dismiss', 'toast');
        closeBtn.setAttribute('aria-label', 'Close');
        
        flexDiv.appendChild(body);
        flexDiv.appendChild(closeBtn);
        toast.appendChild(flexDiv);
        
        document.body.appendChild(toast);
        return toast;
    }
    
    /**
     * Creates a permanent operation mode indicator
     * @returns {HTMLElement} - The created mode indicator element
     */
    function createModeIndicator() {
        const indicator = document.createElement('div');
        indicator.id = 'operation-mode';
        indicator.className = 'position-fixed top-0 end-0 m-3 p-2 rounded';
        indicator.style.zIndex = 1050; // Above most elements
        indicator.style.opacity = 0.9;
        document.body.appendChild(indicator);
        return indicator;
    }
    
    // Get or create a mode indicator
    const modeIndicator = document.getElementById('operation-mode') || createModeIndicator();
    
    // Use utility functions if available, otherwise use local implementations
    const addSimulationWarning = ShopUtils.addSimulationWarning || function(message) {
        // Remove any existing warning first
        clearSimulationWarnings();
        
        // Create a new warning alert
        const warningDiv = document.createElement('div');
        warningDiv.className = 'alert alert-warning simulation-warning mt-3';
        warningDiv.innerHTML = '<i class="fas fa-exclamation-triangle me-2"></i>' + message;
        
        // Insert at the top of the inputs section
        const inputsSection = document.querySelector('.card-body');
        if (inputsSection) {
            inputsSection.insertBefore(warningDiv, inputsSection.firstChild);
        }
    };
    
    const addSimulationError = ShopUtils.addSimulationError || function(message) {
        // Remove any existing error message first
        clearSimulationWarnings();
        
        // Create a new error alert
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger simulation-warning mt-3';
        errorDiv.innerHTML = '<i class="fas fa-exclamation-triangle me-2"></i>' + message;
        
        // Insert at the top of the inputs section
        const inputsSection = document.querySelector('.card-body');
        if (inputsSection) {
            inputsSection.insertBefore(errorDiv, inputsSection.firstChild);
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
    const makeRequest = ShopUtils.makeRequest || function(url, method = 'GET', data = null, successCallback = null, errorCallback = null, finallyCallback = null) {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            }
        };
        
        if (data && (method === 'POST' || method === 'PUT')) {
            options.body = JSON.stringify(data);
        }
        
        fetch(url, options)
            .then(response => response.json())
            .then(data => {
                if (typeof successCallback === 'function') {
                    successCallback(data);
                }
                return data;
            })
            .catch(error => {
                console.error(`Error making ${method} request to ${url}:`, error);
                if (typeof errorCallback === 'function') {
                    errorCallback(error);
                }
            })
            .finally(() => {
                if (typeof finallyCallback === 'function') {
                    finallyCallback();
                }
            });
    };
    
    /**
     * Handles simulation response data consistently based on operation mode
     * @param {Object} data - API response data
     * @param {string} actionName - Description of the action being performed
     * @param {boolean} [useToast=false] - Whether to use toast notifications instead of log messages
     * @returns {boolean} - True if simulated, false otherwise
     */
    const handleSimulationResponse = ShopUtils.handleSimulationResponse || function(data, actionName, useToast = false) {
        if (!data || !data.simulated) {
            clearSimulationWarnings();
            return false;
        }
        
        // For simulation mode, this is expected
        if (currentOperationMode === 'simulation') {
            if (useToast) {
                statusToast.show(`${actionName} (simulation mode)`, false);
            } else {
                console.log(`${actionName} (simulation mode)`);
            }
        } 
        // For prototype mode, this should NEVER happen
        else if (currentOperationMode === 'prototype') {
            if (useToast) {
                statusToast.show(`ERROR: ${actionName} simulation in PROTOTYPE MODE. Hardware is required!`, true);
            }
            addSimulationError('HARDWARE ERROR: Receiving simulated values in PROTOTYPE MODE. Check your hardware connections.');
        } 
        // For normal mode, it's a warning
        else {
            if (useToast) {
                statusToast.show(`WARNING: ${actionName} simulated due to hardware error`, false, true);
            }
            addSimulationWarning('Hardware error detected - using simulation values');
        }
        
        return true;
    };

    // Get references to all input and output buttons
    const refreshInputsButton = document.getElementById('refresh-inputs');
    
    // Fan control buttons
    const fanOnButton = document.getElementById('fan-on');
    const fanOffButton = document.getElementById('fan-off');
    
    // Lights control buttons
    const lightsOnButton = document.getElementById('lights-on');
    const lightsOffButton = document.getElementById('lights-off');
    
    // Table forward control buttons
    const tableForwardOnButton = document.getElementById('table-forward-on');
    const tableForwardOffButton = document.getElementById('table-forward-off');
    
    // Table backward control buttons
    const tableBackwardOnButton = document.getElementById('table-backward-on');
    const tableBackwardOffButton = document.getElementById('table-backward-off');
    
    // Initialize with the operation mode from the utility library
    if (ShopUtils.getOperationMode) {
        currentOperationMode = ShopUtils.getOperationMode();
        updateOperationModeIndicator(currentOperationMode);
        console.log(`Using operation mode from utility: ${currentOperationMode}`);
    } else {
        // Fall back to original method if utility is not available
        getOperationMode();
    }
    
    // Attach event listeners to buttons if they exist
    if (refreshInputsButton) {
        refreshInputsButton.addEventListener('click', refreshInputStates);
    }
    
    // Fan control
    if (fanOnButton) {
        fanOnButton.addEventListener('click', function() {
            setOutput('fan', true);
        });
    }
    
    if (fanOffButton) {
        fanOffButton.addEventListener('click', function() {
            setOutput('fan', false);
        });
    }
    
    // Lights control
    if (lightsOnButton) {
        lightsOnButton.addEventListener('click', function() {
            setOutput('red_lights', true);
        });
    }
    
    if (lightsOffButton) {
        lightsOffButton.addEventListener('click', function() {
            setOutput('red_lights', false);
        });
    }
    
    // Table forward control
    if (tableForwardOnButton) {
        tableForwardOnButton.addEventListener('click', function() {
            setOutput('table_forward', true);
        });
    }
    
    if (tableForwardOffButton) {
        tableForwardOffButton.addEventListener('click', function() {
            setOutput('table_forward', false);
        });
    }
    
    // Table backward control
    if (tableBackwardOnButton) {
        tableBackwardOnButton.addEventListener('click', function() {
            setOutput('table_backward', true);
        });
    }
    
    if (tableBackwardOffButton) {
        tableBackwardOffButton.addEventListener('click', function() {
            setOutput('table_backward', false);
        });
    }
    
    /**
     * Gets the current operation mode from server
     */
    function getOperationMode() {
        makeRequest(
            '/api/system/mode',
            'GET',
            null,
            function(data) {
                if (data.status === 'success') {
                    updateOperationModeIndicator(data.mode);
                }
            }
        );
    }
    
    /**
     * Updates the operation mode indicator
     * @param {string} mode - The operation mode to display
     */
    function updateOperationModeIndicator(mode) {
        currentOperationMode = mode;
        
        // Update the indicator style based on mode
        if (mode === 'simulation') {
            modeIndicator.className = 'position-fixed top-0 end-0 m-3 p-2 rounded bg-warning text-dark';
            modeIndicator.textContent = 'SIMULATION MODE';
        } else if (mode === 'prototype') {
            modeIndicator.className = 'position-fixed top-0 end-0 m-3 p-2 rounded bg-danger text-white';
            modeIndicator.textContent = 'PROTOTYPE MODE';
        } else {
            modeIndicator.className = 'position-fixed top-0 end-0 m-3 p-2 rounded bg-primary text-white';
            modeIndicator.textContent = 'NORMAL MODE';
        }
    }
    
    /**
     * Refreshes all GPIO input states
     */
    function refreshInputStates() {
        // Show loading indicator
        const refreshButton = document.getElementById('refresh-inputs');
        if (refreshButton) {
            refreshButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Refreshing...';
            refreshButton.disabled = true;
        }
        
        makeRequest(
            '/api/gpio/inputs',
            'GET',
            null,
            function(data) {
                if (data.status === 'success') {
                    // Update all GPIO input states by their pin number
                    Object.keys(data).forEach(key => {
                        if (key.startsWith('gpio') && key !== 'status' && key !== 'simulated') {
                            updateInputState(key + '-state', data[key]);
                        }
                    });
                    
                    // Get operation mode from a hidden field added by Flask
                    const modeElement = document.getElementById('operation-mode-value');
                    if (modeElement) {
                        currentOperationMode = modeElement.value;
                    }
                    
                    // Use our simulation handling utility
                    if (!handleSimulationResponse(data, 'Input states refreshed', true)) {
                        // Real hardware values
                        statusToast.show('Input states refreshed from hardware', false);
                    }
                } else {
                    statusToast.show('Error refreshing inputs: ' + (data.message || 'Unknown error'), true);
                }
            },
            function(error) {
                statusToast.show('Network error while refreshing inputs', true);
            },
            function() {
                // Restore button state
                if (refreshButton) {
                    refreshButton.innerHTML = '<i class="fas fa-sync-alt me-1"></i> Refresh Inputs';
                    refreshButton.disabled = false;
                }
            }
        );
    }
    
    /**
     * Updates a single input state indicator in the UI
     * @param {string} elementId - The ID of the element to update
     * @param {boolean} state - The state to display (HIGH or LOW)
     */
    function updateInputState(elementId, state) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = state ? 'HIGH' : 'LOW';
            element.className = state ? 'text-success' : 'text-danger';
        }
    }
    
    /**
     * Sets an output device to a specified state
     * @param {string} device - The device to control
     * @param {boolean} state - The state to set (on/off)
     */
    function setOutput(device, state) {
        const deviceName = getDeviceDisplayName(device);
        const stateText = state ? 'ON' : 'OFF';
        const actionName = `${deviceName} set to ${stateText}`;
        
        makeRequest(
            '/api/gpio/outputs',
            'POST',
            {
                device: device,
                state: state
            },
            function(data) {
                if (data.status === 'success') {
                    // Get operation mode from a hidden field added by Flask
                    const modeElement = document.getElementById('operation-mode-value');
                    if (modeElement) {
                        currentOperationMode = modeElement.value;
                    }
                    
                    // Use our simulation handling utility with toast notifications
                    if (!handleSimulationResponse(data, actionName, true)) {
                        // Real hardware values
                        statusToast.show(actionName, false);
                    }
                } else {
                    statusToast.show('Error: ' + (data.message || 'Unknown error'), true);
                }
            },
            function(error) {
                statusToast.show('Network error while setting output', true);
            }
        );
    }
    
    /**
     * Gets a display-friendly name for a device
     * @param {string} device - The device identifier
     * @returns {string} - The display name
     */
    function getDeviceDisplayName(device) {
        switch (device) {
            case 'fan':
                return 'Fan';
            case 'red_lights':
                return 'Red Lights';
            case 'table_forward':
                return 'Table Forward';
            case 'table_backward':
                return 'Table Backward';
            default:
                return 'Unknown Device';
        }
    }
    
    // Initial state refresh when page loads
    refreshInputStates();
    
    // Set up automatic refresh every 5 seconds
    const autoRefreshInterval = setInterval(refreshInputStates, 5000);
    
    // Clean up on page unload
    window.addEventListener('beforeunload', function() {
        clearInterval(autoRefreshInterval);
    });
});