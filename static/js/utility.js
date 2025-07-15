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
window.currentOperationMode = window.currentOperationMode || 'unknown';

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
    console.log(`[UTILITY.JS] makeRequest called:`, { url, method, data, logFunction: typeof logFunction, onSuccess: typeof onSuccess, onError: typeof onError });
    
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    if (data && (method === 'POST' || method === 'PUT')) {
        options.body = JSON.stringify(data);
    }
    
    console.log(`[UTILITY.JS] Fetch options:`, options);
    
    return fetch(url, options)
        .then(response => {
            console.log(`[UTILITY.JS] Response received:`, { status: response.status, ok: response.ok });
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log(`[UTILITY.JS] Response data:`, data);
            if (typeof onSuccess === 'function') {
                console.log(`[UTILITY.JS] Calling onSuccess callback`);
                onSuccess(data);
            }
            return data;
        })
        .catch(error => {
            console.error(`[UTILITY.JS] Request failed:`, error);
            handleError(error, logFunction, null);
            
            if (typeof onError === 'function') {
                console.log(`[UTILITY.JS] Calling onError callback`);
                onError(error);
            }
            
            throw error; // Re-throw to allow further handling if needed
        })
        .finally(() => {
            if (typeof onFinally === 'function') {
                console.log(`[UTILITY.JS] Calling onFinally callback`);
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

/**
 * Temperature monitoring utilities
 */

/**
 * Global state for temperature monitoring
 */
window.temperatureState = window.temperatureState || {
    lastHighTempAlert: 0,      // Timestamp to prevent log spam
    lastTemperatureData: null, // Cache temperature data to prevent flickering
    lastTempLog: 0,            // Timestamp for regular temperature logs
    lastTempError: 0,          // Timestamp for temperature error logs
    lastSimWarning: 0          // Timestamp for simulation warnings
};

/**
 * Updates temperature status in the UI and handles temperature monitoring
 * @param {Object} [options] - Configuration options
 * @param {string} [options.statusSelector='#temperature-status'] - Selector for the temperature status element
 * @param {string} [options.iconSelector='#temperature-status-icon'] - Selector for the temperature icon element
 * @param {string} [options.logSelector='#status-log'] - Selector for the log element
 * @param {string} [options.warningSelector='#temperature-monitoring-card .card-body'] - Selector for the warning container
 * @returns {Promise} - A promise that resolves with the temperature data
 */
function updateTemperatureStatus(options = {}) {
    const statusSelector = options.statusSelector || '#temperature-status';
    const iconSelector = options.iconSelector || '#temperature-status-icon';
    const logSelector = options.logSelector || '#status-log';
    const warningSelector = options.warningSelector || '#temperature-monitoring-card .card-body';
    
    return fetch('/temperature/status')
        .then(response => response.json())
        .then(data => {
            const temperatureIcon = document.querySelector(iconSelector);
            const temperatureStatus = document.querySelector(statusSelector);
            
            if (!temperatureIcon || !temperatureStatus) {
                return data; // Elements not found in the current page
            }
            
            // Check if we have simulation data and handle appropriately
            if (data.simulated) {
                // For simulation mode, this is expected
                if (currentOperationMode === 'simulation') {
                    console.log('Temperature data is simulated (expected in simulation mode)');
                } 
                // For prototype mode, this should NEVER happen
                else if (currentOperationMode === 'prototype') {
                    console.error('ERROR: Temperature simulation in PROTOTYPE MODE. Hardware is required!');
                    addSimulationError('HARDWARE ERROR: Receiving simulated temperature values in PROTOTYPE MODE. Check your hardware connections.', warningSelector);
                    
                    // Add to status log if available
                    const log = document.querySelector(logSelector);
                    if (log) {
                        const now = new Date();
                        const timeString = now.toLocaleTimeString();
                        
                        const logEntry = document.createElement('p');
                        logEntry.classList.add('mb-1', 'text-danger');
                        logEntry.innerHTML = `<strong>${timeString}:</strong> ERROR: Temperature sensors are simulated in PROTOTYPE MODE`;
                        
                        log.appendChild(logEntry);
                        log.scrollTop = log.scrollHeight;
                    }
                } 
                // For normal mode, it's a warning
                else {
                    console.warn('WARNING: Temperature data is simulated due to hardware error');
                    addSimulationWarning('Hardware error detected - showing simulated temperature values', warningSelector);
                    
                    // Add to status log if available
                    const log = document.querySelector(logSelector);
                    if (log && (!temperatureState.lastSimWarning || (Date.now() - temperatureState.lastSimWarning) > 60000)) {
                        temperatureState.lastSimWarning = Date.now();
                        const now = new Date();
                        const timeString = now.toLocaleTimeString();
                        
                        const logEntry = document.createElement('p');
                        logEntry.classList.add('mb-1', 'text-warning');
                        logEntry.innerHTML = `<strong>${timeString}:</strong> WARNING: Using simulated temperature values due to hardware error`;
                        
                        log.appendChild(logEntry);
                        log.scrollTop = log.scrollHeight;
                    }
                }
            } else if (data.status === 'success') {
                // Clear any warnings if getting real hardware data
                clearSimulationWarnings();
            }
            
            // Cache the data for use between updates
            temperatureState.lastTemperatureData = data;
            
            // Check for the correct data structure (could be sensors or temperatures)
            const sensors = data.sensors || data.temperatures || {};
            
            // Check if we have temperature data
            if (Object.keys(sensors).length > 0) {
                // Find the highest temperature
                let highestTemp = -Infinity;
                let highestTempName = "";
                
                for (const sensorId in sensors) {
                    const sensor = sensors[sensorId];
                    // Handle different API response formats (temp vs temperature)
                    const temperature = sensor.temperature !== undefined ? sensor.temperature : sensor.temp;
                    
                    if (temperature > highestTemp) {
                        highestTemp = temperature;
                        highestTempName = sensor.name;
                    }
                }
                
                // Determine status color based on highest temperature
                let statusClass = 'bg-success';
                let iconClass = 'text-success';
                
                if (data.high_temp_condition) {
                    // High temperature alert
                    statusClass = 'bg-danger';
                    iconClass = 'text-danger';
                } else if (highestTemp > data.high_limit - 10) {
                    // Approaching high temperature
                    statusClass = 'bg-warning';
                    iconClass = 'text-warning';
                }
                
                // Update the UI
                temperatureIcon.innerHTML = `<i class="fas fa-thermometer-half fa-2x ${iconClass}"></i>`;
                temperatureStatus.className = `badge ${statusClass}`;
                temperatureStatus.innerText = `${highestTemp.toFixed(1)}°C (${highestTempName})`;
                
                // Add simulation indicator if data is simulated
                if (data.simulated) {
                    temperatureStatus.innerText += ' [SIM]';
                }
                
                // Dispatch event for any components that need temperature updates
                document.dispatchEvent(new CustomEvent('temperature-update', {
                    detail: {
                        temperature: highestTemp,
                        sensorName: highestTempName,
                        isHighTemp: data.high_temp_condition,
                        isSimulated: data.simulated
                    }
                }));
                
                // Add to status log
                const log = document.querySelector(logSelector);
                
                // Add a warning to the log if there's a high temperature condition
                if (data.high_temp_condition && (!temperatureState.lastHighTempAlert || 
                    (Date.now() - temperatureState.lastHighTempAlert) > 60000)) {
                    temperatureState.lastHighTempAlert = Date.now();
                    
                    // If status log exists, add message
                    if (log) {
                        const now = new Date();
                        const timeString = now.toLocaleTimeString();
                        
                        const logEntry = document.createElement('p');
                        logEntry.classList.add('mb-1', 'text-danger');
                        logEntry.innerHTML = `<strong>${timeString}:</strong> HIGH TEMPERATURE ALERT: ${highestTemp.toFixed(1)}°C on ${highestTempName}${data.simulated ? ' [SIMULATED]' : ''}`;
                        
                        log.appendChild(logEntry);
                        log.scrollTop = log.scrollHeight;
                        
                        // Also add normal log entry for temperature update
                        addTemperatureLogEntry(log, highestTemp, highestTempName, data.simulated);
                    }
                } else {
                    // Add regular temperature update to log every 30 seconds
                    if (log && (!temperatureState.lastTempLog || (Date.now() - temperatureState.lastTempLog) > 30000)) {
                        addTemperatureLogEntry(log, highestTemp, highestTempName, data.simulated);
                    }
                }
            } else {
                // No temperature data, but don't change display if we had data before (prevents flickering)
                if (!temperatureState.lastTemperatureData || !temperatureState.lastTemperatureData.sensors) {
                    temperatureIcon.innerHTML = '<i class="fas fa-thermometer-half fa-2x text-secondary"></i>';
                    temperatureStatus.className = 'badge bg-secondary';
                    temperatureStatus.innerText = '--°C';
                }
                
                // Log the error
                const log = document.querySelector(logSelector);
                if (log && (!temperatureState.lastTempError || (Date.now() - temperatureState.lastTempError) > 60000)) {
                    temperatureState.lastTempError = Date.now();
                    const now = new Date();
                    const timeString = now.toLocaleTimeString();
                    
                    const logEntry = document.createElement('p');
                    logEntry.classList.add('mb-1', 'text-warning');
                    logEntry.innerHTML = `<strong>${timeString}:</strong> Could not retrieve temperature data`;
                    
                    log.appendChild(logEntry);
                    log.scrollTop = log.scrollHeight;
                }
            }
            
            return data;
        })
        .catch(error => {
            console.error('Error updating temperature status:', error);
            
            // If we have cached data, don't change the display (prevent flickering)
            if (!temperatureState.lastTemperatureData) {
                const temperatureIcon = document.querySelector(iconSelector);
                const temperatureStatus = document.querySelector(statusSelector);
                
                if (temperatureIcon && temperatureStatus) {
                    temperatureIcon.innerHTML = '<i class="fas fa-thermometer-half fa-2x text-danger"></i>';
                    temperatureStatus.className = 'badge bg-danger';
                    temperatureStatus.innerText = 'Error';
                }
            }
            
            // Log the error
            const log = document.querySelector(logSelector);
            if (log && (!temperatureState.lastTempError || (Date.now() - temperatureState.lastTempError) > 60000)) {
                temperatureState.lastTempError = Date.now();
                const now = new Date();
                const timeString = now.toLocaleTimeString();
                
                const logEntry = document.createElement('p');
                logEntry.classList.add('mb-1', 'text-danger');
                logEntry.innerHTML = `<strong>${timeString}:</strong> Error retrieving temperature data: ${error.message}`;
                
                log.appendChild(logEntry);
                log.scrollTop = log.scrollHeight;
            }
            
            throw error;
        });
}

/**
 * Helper function to add temperature update to log
 * @param {HTMLElement} log - The log element to add the entry to
 * @param {number} temperature - The temperature value
 * @param {string} sensorName - The name of the sensor
 * @param {boolean} isSimulated - Whether the temperature data is simulated
 */
function addTemperatureLogEntry(log, temperature, sensorName, isSimulated) {
    temperatureState.lastTempLog = Date.now();
    const now = new Date();
    const timeString = now.toLocaleTimeString();
    
    const logEntry = document.createElement('p');
    logEntry.classList.add('mb-1', 'text-light');
    logEntry.innerHTML = `<strong>${timeString}:</strong> Temperature: ${temperature.toFixed(1)}°C (${sensorName})${isSimulated ? ' [SIMULATED]' : ''}`;
    
    log.appendChild(logEntry);
    log.scrollTop = log.scrollHeight;
}

/**
 * Set up temperature monitoring with a polling interval
 * @param {number} [interval=10000] - Polling interval in milliseconds
 * @param {Object} [options] - Options to pass to updateTemperatureStatus
 * @returns {number} - The interval ID for clearing if needed
 */
function setupTemperatureMonitoring(interval = 10000, options = {}) {
    // Initial update
    updateTemperatureStatus(options);
    
    // Set up regular polling
    return setInterval(() => {
        updateTemperatureStatus(options);
    }, interval);
}

/**
 * Position calculation and management utilities
 */

/**
 * Global state for position tracking
 */
const positionState = {
    lastPositions: {},  // Cache for positions by component ID
    positionHistory: {},  // History of positions for movement calculation
    movementInProgress: {},  // Flags for tracking ongoing movements
    positionLimits: {}  // Min/max position limits by component type
};

/**
 * Calculate the movement distance between two positions
 * @param {number} startPos - Starting position value
 * @param {number} endPos - Ending position value
 * @param {boolean} [isAngle=false] - Whether the positions are angles (handles wraparound)
 * @returns {number} - The movement distance (always positive)
 */
function calculateMovementDistance(startPos, endPos, isAngle = false) {
    if (isAngle) {
        // For angles, handle wraparound (e.g., moving from 350° to 10°)
        let directDistance = Math.abs(endPos - startPos);
        let wrapDistance = 360 - directDistance;
        
        // Return the shorter path
        return Math.min(directDistance, wrapDistance);
    } else {
        // For linear positions, simple absolute difference
        return Math.abs(endPos - startPos);
    }
}

/**
 * Calculate the direction of movement between two positions
 * @param {number} startPos - Starting position value
 * @param {number} endPos - Ending position value
 * @param {boolean} [isAngle=false] - Whether the positions are angles (handles wraparound)
 * @returns {string} - Direction: "forward", "backward", or "none"
 */
function calculateMovementDirection(startPos, endPos, isAngle = false) {
    if (startPos === endPos) {
        return "none";
    }
    
    if (isAngle) {
        // For angles, consider wraparound for shortest path
        const directDistance = Math.abs(endPos - startPos);
        const wrapDistance = 360 - directDistance;
        
        // Determine the shorter path direction
        if (directDistance <= wrapDistance) {
            // Direct path is shorter
            return endPos > startPos ? "forward" : "backward";
        } else {
            // Wraparound path is shorter
            return endPos > startPos ? "backward" : "forward";
        }
    } else {
        // For linear positions, simple comparison
        return endPos > startPos ? "forward" : "backward";
    }
}

/**
 * Calculate estimated movement time based on distance and speed
 * @param {number} distance - Distance to move
 * @param {number} speed - Speed of movement (units per second)
 * @returns {number} - Estimated time in milliseconds
 */
function calculateMovementTime(distance, speed) {
    if (!speed || speed <= 0) {
        return 0;
    }
    return (distance / speed) * 1000; // Convert to milliseconds
}

/**
 * Track a position update for a component
 * @param {string} componentId - ID of the component (e.g., "table", "servo")
 * @param {number} position - New position value
 * @param {Object} [options] - Additional options
 * @param {boolean} [options.isAngle=false] - Whether the position is an angle
 * @param {number} [options.timestamp=Date.now()] - Timestamp of the position update
 * @returns {Object} - Movement information including distance, direction, and speed
 */
function trackPositionUpdate(componentId, position, options = {}) {
    const isAngle = options.isAngle || false;
    const timestamp = options.timestamp || Date.now();
    
    // Initialize history array if it doesn't exist
    if (!positionState.positionHistory[componentId]) {
        positionState.positionHistory[componentId] = [];
    }
    
    const history = positionState.positionHistory[componentId];
    const lastPosition = positionState.lastPositions[componentId];
    
    let result = {
        position,
        timestamp,
        distance: 0,
        direction: "none",
        speed: 0
    };
    
    // Calculate movement metrics if we have a previous position
    if (lastPosition !== undefined) {
        // Calculate distance and direction
        result.distance = calculateMovementDistance(lastPosition.position, position, isAngle);
        result.direction = calculateMovementDirection(lastPosition.position, position, isAngle);
        
        // Calculate speed if we have a timestamp
        if (lastPosition.timestamp && timestamp > lastPosition.timestamp) {
            const timeElapsed = (timestamp - lastPosition.timestamp) / 1000; // in seconds
            if (timeElapsed > 0) {
                result.speed = result.distance / timeElapsed;
            }
        }
    }
    
    // Store the new position
    positionState.lastPositions[componentId] = {
        position,
        timestamp
    };
    
    // Add to history (keep only last 10 positions)
    history.push({
        position,
        timestamp,
        distance: result.distance,
        direction: result.direction,
        speed: result.speed
    });
    
    // Trim history to last 10 entries
    if (history.length > 10) {
        history.shift();
    }
    
    return result;
}

/**
 * Check if a position is within limits
 * @param {number} position - Position to check
 * @param {number} minLimit - Minimum allowed position
 * @param {number} maxLimit - Maximum allowed position
 * @returns {boolean} - True if position is within limits
 */
function isWithinPositionLimits(position, minLimit, maxLimit) {
    return position >= minLimit && position <= maxLimit;
}

/**
 * Set position limits for a component type
 * @param {string} componentType - Type of the component (e.g., "servo", "stepper")
 * @param {number} minLimit - Minimum position limit
 * @param {number} maxLimit - Maximum position limit
 */
function setPositionLimits(componentType, minLimit, maxLimit) {
    positionState.positionLimits[componentType] = {
        min: minLimit,
        max: maxLimit
    };
}

/**
 * Format a position value for display
 * @param {number} position - The position value
 * @param {Object} [options] - Formatting options
 * @param {boolean} [options.isAngle=false] - Whether the position is an angle
 * @param {number} [options.precision=1] - Number of decimal places
 * @param {boolean} [options.includeUnit=true] - Whether to include units
 * @returns {string} - Formatted position string
 */
function formatPosition(position, options = {}) {
    const isAngle = options.isAngle || false;
    const precision = options.precision !== undefined ? options.precision : 1;
    const includeUnit = options.includeUnit !== undefined ? options.includeUnit : true;
    
    const formattedValue = Number(position).toFixed(precision);
    
    if (includeUnit) {
        return isAngle ? `${formattedValue}°` : `${formattedValue}mm`;
    } else {
        return formattedValue;
    }
}

/**
 * Check if a component is at the target position
 * @param {string} componentId - ID of the component
 * @param {number} targetPosition - Target position
 * @param {Object} [options] - Additional options
 * @param {boolean} [options.isAngle=false] - Whether the position is an angle
 * @param {number} [options.tolerance=0.5] - Position tolerance
 * @returns {boolean} - True if at target position
 */
function isAtTargetPosition(componentId, targetPosition, options = {}) {
    const isAngle = options.isAngle || false;
    const tolerance = options.tolerance || 0.5;
    
    // Get current position
    const currentPosition = positionState.lastPositions[componentId]?.position;
    
    // If we don't have a current position, we can't determine if we're at target
    if (currentPosition === undefined) {
        return false;
    }
    
    // Calculate distance to target
    const distance = calculateMovementDistance(currentPosition, targetPosition, isAngle);
    
    // Compare to tolerance
    return distance <= tolerance;
}

/**
 * UI State Persistence Utilities
 */

/**
 * Namespace for UI state persistence
 */
const uiStateStorage = {
    /**
     * Prefix for all UI state keys to avoid conflicts with other localStorage usage
     */
    keyPrefix: 'lcleanerCtrl_ui_',
    
    /**
     * Check if storage is available (localStorage or sessionStorage)
     * @param {string} type - The type of storage to check ('localStorage' or 'sessionStorage')
     * @returns {boolean} - Whether the storage is available
     */
    storageAvailable: function(type) {
        let storage;
        try {
            storage = window[type];
            const x = '__storage_test__';
            storage.setItem(x, x);
            storage.removeItem(x);
            return true;
        }
        catch(e) {
            return e instanceof DOMException && (
                // everything except Firefox
                e.code === 22 ||
                // Firefox
                e.code === 1014 ||
                // test name field too, because code might not be present
                // everything except Firefox
                e.name === 'QuotaExceededError' ||
                // Firefox
                e.name === 'NS_ERROR_DOM_QUOTA_REACHED') &&
                // acknowledge QuotaExceededError only if there's something already stored
                (storage && storage.length !== 0);
        }
    },
    
    /**
     * In-memory fallback storage when localStorage is not available
     */
    memoryStorage: {},
    
    /**
     * Determine if localStorage is available
     */
    useLocalStorage: function() {
        if (this._useLocalStorageCache === undefined) {
            this._useLocalStorageCache = this.storageAvailable('localStorage');
        }
        return this._useLocalStorageCache;
    },
    
    /**
     * Save a value to storage (localStorage or memory fallback)
     * @param {string} key - Key to save under (will be prefixed automatically)
     * @param {*} value - Value to save (will be JSON stringified)
     * @param {Object} [options] - Additional options
     * @param {string} [options.scope='global'] - Scope for the state ('global', 'page', or custom)
     */
    saveState: function(key, value, options = {}) {
        const scope = options.scope || 'global';
        const fullKey = `${this.keyPrefix}${scope}_${key}`;
        
        try {
            const serialized = JSON.stringify(value);
            
            if (this.useLocalStorage()) {
                localStorage.setItem(fullKey, serialized);
            } else {
                this.memoryStorage[fullKey] = serialized;
            }
        } catch (error) {
            console.error(`Error saving UI state for ${key}:`, error);
        }
    },
    
    /**
     * Load a value from storage
     * @param {string} key - Key to load (will be prefixed automatically)
     * @param {*} defaultValue - Default value if key doesn't exist
     * @param {Object} [options] - Additional options
     * @param {string} [options.scope='global'] - Scope for the state ('global', 'page', or custom)
     * @returns {*} - The loaded value, or defaultValue if not found
     */
    loadState: function(key, defaultValue, options = {}) {
        const scope = options.scope || 'global';
        const fullKey = `${this.keyPrefix}${scope}_${key}`;
        
        try {
            let serialized;
            
            if (this.useLocalStorage()) {
                serialized = localStorage.getItem(fullKey);
            } else {
                serialized = this.memoryStorage[fullKey];
            }
            
            if (serialized === null || serialized === undefined) {
                return defaultValue;
            }
            
            return JSON.parse(serialized);
        } catch (error) {
            console.error(`Error loading UI state for ${key}:`, error);
            return defaultValue;
        }
    },
    
    /**
     * Remove a value from storage
     * @param {string} key - Key to remove (will be prefixed automatically)
     * @param {Object} [options] - Additional options
     * @param {string} [options.scope='global'] - Scope for the state ('global', 'page', or custom)
     */
    removeState: function(key, options = {}) {
        const scope = options.scope || 'global';
        const fullKey = `${this.keyPrefix}${scope}_${key}`;
        
        try {
            if (this.useLocalStorage()) {
                localStorage.removeItem(fullKey);
            } else {
                delete this.memoryStorage[fullKey];
            }
        } catch (error) {
            console.error(`Error removing UI state for ${key}:`, error);
        }
    },
    
    /**
     * Clear all UI state for a given scope
     * @param {string} [scope='global'] - Scope to clear ('global', 'page', or custom)
     */
    clearState: function(scope = 'global') {
        const prefix = `${this.keyPrefix}${scope}_`;
        
        try {
            if (this.useLocalStorage()) {
                // Find all keys with the given prefix
                const keysToRemove = [];
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i);
                    if (key && key.startsWith(prefix)) {
                        keysToRemove.push(key);
                    }
                }
                
                // Remove each key
                keysToRemove.forEach(key => localStorage.removeItem(key));
            } else {
                // Remove from memory storage
                Object.keys(this.memoryStorage).forEach(key => {
                    if (key.startsWith(prefix)) {
                        delete this.memoryStorage[key];
                    }
                });
            }
        } catch (error) {
            console.error(`Error clearing UI state for scope ${scope}:`, error);
        }
    }
};

/**
 * Save UI form state
 * @param {HTMLElement|string} form - Form element or selector
 * @param {string} [formId] - Identifier for the form (defaults to form ID or form's action)
 * @param {Object} [options] - Additional options
 * @param {Array<string>} [options.exclude=[]] - Form element names to exclude
 * @param {Array<string>} [options.include=[]] - Only save these form element names (if provided)
 * @param {string} [options.scope='form'] - Storage scope
 * @returns {boolean} - Success status
 */
function saveFormState(form, formId, options = {}) {
    // Handle string selectors
    if (typeof form === 'string') {
        form = document.querySelector(form);
    }
    
    if (!form || form.tagName !== 'FORM') {
        console.error('Invalid form element');
        return false;
    }
    
    // Use form ID, action, or provided formId as identifier
    const identifier = formId || form.id || form.getAttribute('action') || 'anonymous-form';
    const scope = options.scope || 'form';
    const exclude = options.exclude || [];
    const include = options.include || [];
    
    try {
        const formData = {};
        const elements = form.elements;
        
        for (let i = 0; i < elements.length; i++) {
            const element = elements[i];
            const name = element.name;
            
            // Skip elements without a name
            if (!name) continue;
            
            // Skip excluded elements
            if (exclude.includes(name)) continue;
            
            // Skip elements not in include list (if specified)
            if (include.length > 0 && !include.includes(name)) continue;
            
            // Handle different input types
            switch (element.type) {
                case 'checkbox':
                    formData[name] = element.checked;
                    break;
                    
                case 'radio':
                    if (element.checked) {
                        formData[name] = element.value;
                    }
                    break;
                    
                case 'select-multiple':
                    formData[name] = Array.from(element.selectedOptions).map(option => option.value);
                    break;
                    
                case 'file':
                    // Skip file inputs (can't save file references)
                    break;
                    
                default:
                    formData[name] = element.value;
                    break;
            }
        }
        
        // Save the form data
        uiStateStorage.saveState(identifier, formData, { scope });
        return true;
    } catch (error) {
        console.error(`Error saving form state for ${identifier}:`, error);
        return false;
    }
}

/**
 * Load and apply saved UI form state
 * @param {HTMLElement|string} form - Form element or selector
 * @param {string} [formId] - Identifier for the form (defaults to form ID or form's action)
 * @param {Object} [options] - Additional options
 * @param {Array<string>} [options.exclude=[]] - Form element names to exclude
 * @param {boolean} [options.triggerEvents=false] - Whether to trigger change events on form elements
 * @param {string} [options.scope='form'] - Storage scope
 * @returns {boolean} - Success status
 */
function loadFormState(form, formId, options = {}) {
    // Handle string selectors
    if (typeof form === 'string') {
        form = document.querySelector(form);
    }
    
    if (!form || form.tagName !== 'FORM') {
        console.error('Invalid form element');
        return false;
    }
    
    // Use form ID, action, or provided formId as identifier
    const identifier = formId || form.id || form.getAttribute('action') || 'anonymous-form';
    const scope = options.scope || 'form';
    const exclude = options.exclude || [];
    const triggerEvents = options.triggerEvents || false;
    
    try {
        const formData = uiStateStorage.loadState(identifier, {}, { scope });
        if (!formData || typeof formData !== 'object') {
            return false;
        }
        
        // Apply saved values to form elements
        Object.entries(formData).forEach(([name, value]) => {
            // Skip excluded elements
            if (exclude.includes(name)) return;
            
            const elements = form.elements[name];
            if (!elements) return;
            
            // Handle different types of form elements
            if (elements.length === undefined) {
                // Single element
                applyValueToElement(elements, value, triggerEvents);
            } else {
                // Multiple elements (e.g., radio buttons, multi-selects)
                for (let i = 0; i < elements.length; i++) {
                    applyValueToElement(elements[i], value, triggerEvents);
                }
            }
        });
        
        return true;
    } catch (error) {
        console.error(`Error loading form state for ${identifier}:`, error);
        return false;
    }
}

/**
 * Apply a value to a form element
 * @param {HTMLElement} element - Form element
 * @param {*} value - Value to apply
 * @param {boolean} triggerEvents - Whether to trigger change events
 */
function applyValueToElement(element, value, triggerEvents) {
    switch (element.type) {
        case 'checkbox':
            element.checked = Boolean(value);
            break;
            
        case 'radio':
            element.checked = (element.value === value);
            break;
            
        case 'select-multiple':
            if (Array.isArray(value)) {
                // Deselect all options first
                Array.from(element.options).forEach(option => {
                    option.selected = false;
                });
                
                // Select saved options
                Array.from(element.options).forEach(option => {
                    option.selected = value.includes(option.value);
                });
            }
            break;
            
        default:
            element.value = value;
            break;
    }
    
    // Trigger change event if requested
    if (triggerEvents) {
        const event = new Event('change', { bubbles: true });
        element.dispatchEvent(event);
    }
}

/**
 * Save UI element visibility state
 * @param {string} elementId - ID of the element
 * @param {boolean} isVisible - Current visibility state
 * @param {Object} [options] - Additional options
 * @param {string} [options.scope='visibility'] - Storage scope
 */
function saveVisibilityState(elementId, isVisible, options = {}) {
    const scope = options.scope || 'visibility';
    uiStateStorage.saveState(elementId, isVisible, { scope });
}

/**
 * Load and apply saved element visibility state
 * @param {string} elementId - ID of the element
 * @param {boolean} defaultState - Default visibility state
 * @param {Object} [options] - Additional options
 * @param {string} [options.scope='visibility'] - Storage scope
 * @param {string} [options.displayType='block'] - CSS display value when visible
 * @returns {boolean} - The current visibility state
 */
function loadVisibilityState(elementId, defaultState, options = {}) {
    const scope = options.scope || 'visibility';
    const displayType = options.displayType || 'block';
    
    const isVisible = uiStateStorage.loadState(elementId, defaultState, { scope });
    const element = document.getElementById(elementId);
    
    if (element) {
        element.style.display = isVisible ? displayType : 'none';
    }
    
    return isVisible;
}

/**
 * Save the active tab state
 * @param {string} tabGroupId - ID of the tab container
 * @param {string} activeTabId - ID of the currently active tab
 * @param {Object} [options] - Additional options
 * @param {string} [options.scope='tabs'] - Storage scope
 */
function saveActiveTab(tabGroupId, activeTabId, options = {}) {
    const scope = options.scope || 'tabs';
    uiStateStorage.saveState(tabGroupId, activeTabId, { scope });
}

/**
 * Load active tab state
 * @param {string} tabGroupId - ID of the tab container
 * @param {string} defaultTabId - Default tab ID to activate if no saved state
 * @param {Object} [options] - Additional options
 * @param {string} [options.scope='tabs'] - Storage scope
 * @param {Function} [options.activateTab] - Custom function to activate a tab
 * @returns {string} - ID of the activated tab
 */
function loadActiveTab(tabGroupId, defaultTabId, options = {}) {
    const scope = options.scope || 'tabs';
    const activeTabId = uiStateStorage.loadState(tabGroupId, defaultTabId, { scope });
    
    if (options.activateTab && typeof options.activateTab === 'function') {
        // Use custom activation function
        options.activateTab(activeTabId);
    } else {
        // Standard Bootstrap tab activation
        const tabElement = document.getElementById(activeTabId);
        if (tabElement) {
            const tab = new bootstrap.Tab(tabElement);
            tab.show();
        }
    }
    
    return activeTabId;
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
    clearSimulationWarnings,
    // Temperature monitoring utilities
    updateTemperatureStatus,
    addTemperatureLogEntry,
    setupTemperatureMonitoring,
    temperatureState,
    // Position calculation utilities
    calculateMovementDistance,
    calculateMovementDirection,
    calculateMovementTime,
    trackPositionUpdate,
    isWithinPositionLimits,
    setPositionLimits,
    formatPosition,
    isAtTargetPosition,
    positionState,
    // UI state persistence utilities
    saveFormState,
    loadFormState,
    saveVisibilityState,
    loadVisibilityState,
    saveActiveTab,
    loadActiveTab,
    uiStateStorage
};