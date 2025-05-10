/**
 * Utility JavaScript - Common Utilities for ShopLaserRoom Controller
 * 
 * This file contains shared utilities used across multiple parts of the application
 * including error handling, simulation mode handling, and UI helper functions.
 */

/**
 * Current operation mode of the system
 * @type {string}
 */
let currentOperationMode = 'unknown';

/**
 * Initialize the utility library by fetching the current operation mode from the server
 * @returns {Promise<string>} A promise that resolves to the current operation mode
 */
function initializeUtilities() {
    return fetch('/api/system/mode')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                currentOperationMode = data.mode;
                console.log(`Current operation mode: ${currentOperationMode}`);
                return currentOperationMode;
            }
            return 'unknown';
        })
        .catch(error => {
            console.error('Error fetching operation mode:', error);
            return 'unknown';
        });
}

/**
 * Get the current operation mode
 * @returns {string} The current operation mode ('simulation', 'prototype', 'normal', or 'unknown')
 */
function getOperationMode() {
    return currentOperationMode;
}

/**
 * Standardized error handler for AJAX requests
 * 
 * @param {Error|string} error - The error object or message 
 * @param {Function} [logFunction=console.error] - Function to use for logging
 * @param {Function} [cleanupFunction=null] - Optional cleanup function to call
 * @returns {void}
 */
function handleError(error, logFunction = console.error, cleanupFunction = null) {
    const errorMessage = error instanceof Error ? error.message : error;
    
    // Log the error with the provided logging function or fall back to console
    if (typeof logFunction === 'function') {
        logFunction(`Error: ${errorMessage}`, true);
    } else {
        console.error(`Error: ${errorMessage}`);
    }
    
    // Call the cleanup function if provided
    if (typeof cleanupFunction === 'function') {
        cleanupFunction();
    }
}

/**
 * Enable or disable a set of buttons
 * 
 * @param {boolean} enabled - Whether the buttons should be enabled
 * @param {...HTMLElement} buttons - The buttons to enable/disable
 * @returns {void}
 */
function setButtonsState(enabled, ...buttons) {
    buttons.forEach(button => {
        if (button) {
            button.disabled = !enabled;
        }
    });
}

/**
 * Handle simulation mode responses from the API
 * 
 * @param {Object} data - Response data from an API call
 * @param {string} actionName - Name of the action being performed
 * @param {Function} addLogMessage - Function for adding log messages
 * @param {Function} addSimulationWarning - Function for adding simulation warnings to UI
 * @param {Function} addSimulationError - Function for adding simulation errors to UI
 * @param {Function} clearSimulationWarnings - Function for clearing simulation warnings
 * @returns {boolean} True if the response was simulated, false otherwise
 */
function handleSimulationResponse(data, actionName, addLogMessage, addSimulationWarning, addSimulationError, clearSimulationWarnings) {
    if (!data.simulated) {
        // Real hardware values - clear any warnings
        if (typeof clearSimulationWarnings === 'function') {
            clearSimulationWarnings();
        }
        return false;
    }
    
    // For simulation mode, this is expected
    if (currentOperationMode === 'simulation') {
        if (typeof addLogMessage === 'function') {
            addLogMessage(`${actionName} complete! (simulation mode)`, false, 'success');
        }
    } 
    // For prototype mode, this should NEVER happen
    else if (currentOperationMode === 'prototype') {
        if (typeof addLogMessage === 'function') {
            addLogMessage(`ERROR: ${actionName} simulation in PROTOTYPE MODE. Hardware is required!`, true);
        }
        if (typeof addSimulationError === 'function') {
            addSimulationError('HARDWARE ERROR: Receiving simulated values in PROTOTYPE MODE. Check your hardware connections.');
        }
    } 
    // For normal mode, it's a warning
    else {
        if (typeof addLogMessage === 'function') {
            addLogMessage(`WARNING: ${actionName} simulated due to hardware error`, false, 'warning');
        }
        if (typeof addSimulationWarning === 'function') {
            addSimulationWarning('Hardware error detected - using simulation values');
        }
    }
    
    return true;
}

/**
 * Make a standardized AJAX request with error handling
 * 
 * @param {string} url - URL to make the request to
 * @param {string} [method='GET'] - HTTP method to use
 * @param {Object} [data=null] - Data to send with the request
 * @param {Function} [logFunction=console.log] - Function to use for logging
 * @param {Function} [onSuccess=null] - Success callback
 * @param {Function} [onError=null] - Error callback
 * @param {Function} [onFinally=null] - Function to call regardless of success/failure
 * @returns {Promise} The fetch promise
 */
function makeRequest(url, method = 'GET', data = null, logFunction = console.log, onSuccess = null, onError = null, onFinally = null) {
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
            handleError(error, logFunction, null);
            
            if (typeof onError === 'function') {
                onError(error);
            }
            
            throw error; // Re-throw to allow further handling if needed
        })
        .finally(() => {
            if (typeof onFinally === 'function') {
                onFinally();
            }
        });
}

/**
 * Displays a warning about simulation mode in the UI
 * This is a default implementation which can be overridden
 * 
 * @param {string} message - The warning message to display
 * @param {string} [selector='.card-body'] - CSS selector for where to insert the warning
 * @returns {void}
 */
function addSimulationWarning(message, selector = '.card-body') {
    // Remove any existing warning first
    clearSimulationWarnings();
    
    // Create a new warning alert
    const warningDiv = document.createElement('div');
    warningDiv.className = 'alert alert-warning simulation-warning mt-3';
    warningDiv.innerHTML = '<i class="fas fa-exclamation-triangle me-2"></i>' + message;
    
    // Insert at the top of the selected container
    const container = document.querySelector(selector);
    if (container) {
        container.insertBefore(warningDiv, container.firstChild);
    }
}

/**
 * Displays an error about simulation mode in the UI (used for prototype mode)
 * This is a default implementation which can be overridden
 * 
 * @param {string} message - The error message to display
 * @param {string} [selector='.card-body'] - CSS selector for where to insert the error
 * @returns {void}
 */
function addSimulationError(message, selector = '.card-body') {
    // Remove any existing warning first
    clearSimulationWarnings();
    
    // Create a new error alert
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-danger simulation-warning mt-3';
    errorDiv.innerHTML = '<i class="fas fa-exclamation-triangle me-2"></i>' + message;
    
    // Insert at the top of the selected container
    const container = document.querySelector(selector);
    if (container) {
        container.insertBefore(errorDiv, container.firstChild);
    }
}

/**
 * Removes all simulation warning and error messages from the UI
 * @returns {void}
 */
function clearSimulationWarnings() {
    document.querySelectorAll('.simulation-warning').forEach(el => el.remove());
}

// Initialize immediately when the script is loaded
initializeUtilities();

// Export utilities for use in other files
window.ShopUtils = {
    initializeUtilities,
    getOperationMode,
    handleError,
    setButtonsState,
    handleSimulationResponse,
    makeRequest,
    addSimulationWarning,
    addSimulationError,
    clearSimulationWarnings
};