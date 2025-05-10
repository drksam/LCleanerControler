/**
 * sequences.js - Manages sequence operations for the laser cleaner controller
 * 
 * This module handles sequence loading, execution, and status reporting.
 * It implements simulation mode rules according to sim.txt:
 * - In simulation mode: Simulation should occur as expected
 * - In prototype mode: Hardware should be forced and errors returned when unavailable
 * - In normal mode: Simulation should not be a fallback; hardware errors should be displayed in UI
 */

// Get access to utility functions if available
const ShopUtils = window.ShopUtils || {};

let sequenceStatus = {
    running: false,
    paused: false,
    currentSequence: null,
    logMessages: [],
    progressPercent: 0,
    operationMode: 'normal', // Default to normal mode
    simulation: false,
    errors: [] // Array to track errors
};

// Virtualization settings
const virtualization = {
    enabled: true,           // Enable virtualization by default
    itemHeight: 150,         // Estimated height of each sequence card in pixels
    bufferSize: 5,           // Number of items to render above/below the visible area
    visibleItems: [],        // Currently visible items
    allSequences: [],        // All available sequences
    container: null,         // Container element for sequences
    lastScrollPosition: 0,   // Last known scroll position
    scrollContainer: null,   // The scrollable container (window or a specific element)
    scrollThrottleTimeout: null, // For scroll event throttling
    totalHeight: 0           // Total height of all items
};

// Operation mode constants
const OPERATION_MODES = {
    SIMULATION: 'simulation',
    NORMAL: 'normal',
    PROTOTYPE: 'prototype'
};

// Common error patterns to look for and provide better messages
const ERROR_PATTERNS = {
    'no lowest priority node found': 'Error in sequence execution order. The system couldn\'t find the next step to execute. Try reloading the sequence.',
    'hardware not available': 'Required hardware component not available. Check connections and try again.',
    'stepper not responding': 'Stepper motor not responding. Check power and connections.',
    'connection refused': 'Connection to hardware controller refused. Check if the controller service is running.',
    'timeout exceeded': 'Operation timed out. The hardware might be busy or not responding.',
    'invalid parameter': 'Invalid parameter in sequence step. Please edit the sequence configuration.',
    'position out of bounds': 'Target position is outside allowed limits. Check sequence configuration.',
    'emergency stop triggered': 'Emergency stop was triggered. Clear the emergency stop before continuing.',
    'temperature exceeded limit': 'Temperature limit exceeded. Allow system to cool down before continuing.',
    'undefined sequence step': 'Sequence contains an undefined or invalid step type.',
    'permission denied': 'Permission denied. Current user may not have sufficient privileges.',
    'network error': 'Network communication error. Check network connections and try again.'
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
 * @returns {boolean} - True if simulated, false otherwise
 */
const handleSimulationResponse = ShopUtils.handleSimulationResponse || function(data, actionName) {
    if (!data || !data.simulated) {
        clearSimulationNotifications();
        return false;
    }
    
    // For simulation mode, this is expected
    if (sequenceStatus.operationMode === OPERATION_MODES.SIMULATION) {
        displayInfoMessage(`${actionName} (simulation mode)`);
    } 
    // For prototype mode, this should NEVER happen
    else if (sequenceStatus.operationMode === OPERATION_MODES.PROTOTYPE) {
        displayErrorMessage(`ERROR: ${actionName} simulation in PROTOTYPE MODE. Hardware is required!`);
    } 
    // For normal mode, it's a warning
    else {
        displayWarningMessage(`WARNING: ${actionName} simulated due to hardware error`);
    }
    
    return true;
};

/**
 * Add a simulation warning message
 * @param {string} message - Warning message to display
 */
const addSimulationWarning = ShopUtils.addSimulationWarning || function(message) {
    displayWarningMessage(message);
};

/**
 * Add a simulation error message
 * @param {string} message - Error message to display
 */
const addSimulationError = ShopUtils.addSimulationError || function(message) {
    displayErrorMessage(message);
};

/**
 * Initialize sequences module
 */
function initSequences() {
    // Get current operation mode from server
    makeRequest(
        '/api/system/operation_mode',
        'GET',
        null,
        function(data) {
            sequenceStatus.operationMode = data.mode || 'normal';
            console.log('Operation mode:', sequenceStatus.operationMode);
        },
        function(error) {
            console.error('Error getting operation mode:', error);
            // Default to normal mode if there's an error
            sequenceStatus.operationMode = 'normal';
        }
    );
    
    // Set up update interval for sequence status
    setInterval(updateSequenceStatus, 1000);
    
    // Initialize virtualization if on sequences page
    if (document.getElementById('available-sequences')) {
        initVirtualizedScrolling();
    }
}

/**
 * Initialize virtualized scrolling for sequences
 */
function initVirtualizedScrolling() {
    virtualization.container = document.getElementById('available-sequences');
    
    if (!virtualization.container) {
        return;
    }
    
    // Determine scroll container (either window or a specific container)
    const sequencesContainer = document.querySelector('.sequences-container');
    virtualization.scrollContainer = sequencesContainer || window;
    
    // Add scroll event listener with throttling
    virtualization.scrollContainer.addEventListener('scroll', function() {
        if (virtualization.scrollThrottleTimeout) {
            window.cancelAnimationFrame(virtualization.scrollThrottleTimeout);
        }
        
        virtualization.scrollThrottleTimeout = window.requestAnimationFrame(function() {
            handleVirtualScroll();
        });
    });
    
    // Also handle resize events to recalculate visible area
    window.addEventListener('resize', function() {
        if (virtualization.scrollThrottleTimeout) {
            window.cancelAnimationFrame(virtualization.scrollThrottleTimeout);
        }
        
        virtualization.scrollThrottleTimeout = window.requestAnimationFrame(function() {
            handleVirtualScroll();
        });
    });
}

/**
 * Handle virtual scrolling - determine which items should be visible
 */
function handleVirtualScroll() {
    if (!virtualization.enabled || !virtualization.container || virtualization.allSequences.length === 0) {
        return;
    }
    
    // Get current scroll position and container dimensions
    const scrollTop = virtualization.scrollContainer === window ? 
        window.scrollY : 
        virtualization.scrollContainer.scrollTop;
    
    const containerHeight = virtualization.scrollContainer === window ?
        window.innerHeight :
        virtualization.scrollContainer.clientHeight;
    
    // Calculate visible range with buffer
    const startIndex = Math.max(0, Math.floor(scrollTop / virtualization.itemHeight) - virtualization.bufferSize);
    const endIndex = Math.min(
        virtualization.allSequences.length - 1,
        Math.ceil((scrollTop + containerHeight) / virtualization.itemHeight) + virtualization.bufferSize
    );
    
    // Update DOM only if the visible range has changed
    if (hasVisibleRangeChanged(startIndex, endIndex)) {
        updateVisibleItems(startIndex, endIndex);
    }
    
    virtualization.lastScrollPosition = scrollTop;
}

/**
 * Check if the visible range of items has changed
 * @param {number} startIndex - New start index
 * @param {number} endIndex - New end index
 * @returns {boolean} - True if range has changed
 */
function hasVisibleRangeChanged(startIndex, endIndex) {
    if (virtualization.visibleItems.length === 0) {
        return true;
    }
    
    const currentStartIndex = virtualization.visibleItems[0]?.index || 0;
    const currentEndIndex = virtualization.visibleItems[virtualization.visibleItems.length - 1]?.index || 0;
    
    return startIndex !== currentStartIndex || endIndex !== currentEndIndex;
}

/**
 * Update the visible items in the DOM
 * @param {number} startIndex - Start index of visible range
 * @param {number} endIndex - End index of visible range
 */
function updateVisibleItems(startIndex, endIndex) {
    // Clear the current visible items
    virtualization.container.innerHTML = '';
    virtualization.visibleItems = [];
    
    // Create spacer at the top to maintain scroll position
    const topSpacerHeight = startIndex * virtualization.itemHeight;
    if (topSpacerHeight > 0) {
        const topSpacer = document.createElement('div');
        topSpacer.className = 'virtual-spacer';
        topSpacer.style.height = `${topSpacerHeight}px`;
        virtualization.container.appendChild(topSpacer);
    }
    
    // Render visible items
    for (let i = startIndex; i <= endIndex; i++) {
        if (i >= 0 && i < virtualization.allSequences.length) {
            const sequence = virtualization.allSequences[i];
            const sequenceCard = createSequenceCard(sequence, i);
            virtualization.container.appendChild(sequenceCard);
            virtualization.visibleItems.push({ index: i, element: sequenceCard });
        }
    }
    
    // Create spacer at the bottom to maintain scroll height
    const remainingItems = virtualization.allSequences.length - endIndex - 1;
    const bottomSpacerHeight = remainingItems * virtualization.itemHeight;
    if (bottomSpacerHeight > 0) {
        const bottomSpacer = document.createElement('div');
        bottomSpacer.className = 'virtual-spacer';
        bottomSpacer.style.height = `${bottomSpacerHeight}px`;
        virtualization.container.appendChild(bottomSpacer);
    }
}

/**
 * Create a sequence card element
 * @param {Object} sequence - Sequence data
 * @param {number} index - Index of the sequence in the array
 * @returns {HTMLElement} - The created card element
 */
function createSequenceCard(sequence, index) {
    const sequenceCard = document.createElement('div');
    sequenceCard.className = 'card mb-3';
    sequenceCard.setAttribute('data-sequence-index', index);
    
    const cardBody = document.createElement('div');
    cardBody.className = 'card-body';
    
    const title = document.createElement('h5');
    title.className = 'card-title';
    title.textContent = sequence.name;
    
    const description = document.createElement('p');
    description.className = 'card-text';
    description.textContent = sequence.description || 'No description available';
    
    const stepsCount = document.createElement('p');
    stepsCount.className = 'card-text text-muted';
    stepsCount.textContent = `${sequence.steps.length} steps`;
    
    const startButton = document.createElement('button');
    startButton.className = 'btn btn-primary';
    startButton.textContent = 'Start Sequence';
    startButton.onclick = () => startSequence(sequence.id);
    
    // Assemble card
    cardBody.appendChild(title);
    cardBody.appendChild(description);
    cardBody.appendChild(stepsCount);
    cardBody.appendChild(startButton);
    
    sequenceCard.appendChild(cardBody);
    return sequenceCard;
}

/**
 * Measure the real height of a sequence card for better estimation
 */
function measureCardHeight() {
    if (virtualization.visibleItems.length > 0) {
        const card = virtualization.visibleItems[0].element;
        if (card) {
            const height = card.offsetHeight;
            if (height > 0) {
                virtualization.itemHeight = height;
                console.log('Updated item height:', height);
                
                // Recalculate total height
                virtualization.totalHeight = virtualization.allSequences.length * virtualization.itemHeight;
                
                // Update visible items with new height
                handleVirtualScroll();
            }
        }
    }
}

/**
 * Start a sequence by ID
 * @param {string} sequenceId - ID of the sequence to run
 * @returns {Promise} - Promise resolving to success status
 */
function startSequence(sequenceId) {
    clearNotifications();
    sequenceStatus.errors = []; // Clear any previous errors
    
    return new Promise((resolve) => {
        makeRequest(
            `/api/sequences/${sequenceId}/start`,
            'POST',
            null,
            function(data) {
                if (data.success) {
                    sequenceStatus.running = true;
                    sequenceStatus.paused = false;
                    sequenceStatus.currentSequence = data.sequence;
                    updateSequenceStatus();
                    resolve(true);
                } else {
                    const errorMessage = data.error || 'Unknown error';
                    handleSequenceError(errorMessage);
                    resolve(false);
                }
            },
            function(error) {
                handleSequenceError(error.message);
                resolve(false);
            }
        );
    });
}

/**
 * Process and handle sequence errors
 * @param {string} errorMessage - The raw error message
 */
function handleSequenceError(errorMessage) {
    console.error('Sequence error:', errorMessage);
    
    // Check against known error patterns to provide better messages
    let displayMessage = errorMessage;
    
    Object.entries(ERROR_PATTERNS).forEach(([pattern, betterMessage]) => {
        if (errorMessage.toLowerCase().includes(pattern.toLowerCase())) {
            displayMessage = betterMessage;
        }
    });
    
    // Store error for reference
    sequenceStatus.errors.push({
        timestamp: new Date(),
        raw: errorMessage,
        display: displayMessage
    });
    
    // Display to user
    displayErrorMessage('Failed to execute sequence: ' + displayMessage);
    
    // Log to global log if available
    if (window.addLogMessage) {
        window.addLogMessage('Sequence error: ' + displayMessage, true);
    }
}

/**
 * Stop the currently running sequence
 * @returns {Promise} - Promise resolving to success status
 */
function stopSequence() {
    return new Promise((resolve) => {
        makeRequest(
            '/api/sequences/stop',
            'POST',
            null,
            function(data) {
                if (data.success) {
                    sequenceStatus.running = false;
                    sequenceStatus.paused = false;
                    updateSequenceStatus();
                    resolve(true);
                } else {
                    handleSequenceError(data.error || 'Unknown error');
                    resolve(false);
                }
            },
            function(error) {
                handleSequenceError(error.message);
                resolve(false);
            }
        );
    });
}

/**
 * Pause the currently running sequence
 * @returns {Promise} - Promise resolving to success status
 */
function pauseSequence() {
    return new Promise((resolve) => {
        makeRequest(
            '/api/sequences/pause',
            'POST',
            null,
            function(data) {
                if (data.success) {
                    sequenceStatus.paused = true;
                    updateSequenceStatus();
                    resolve(true);
                } else {
                    handleSequenceError(data.error || 'Unknown error');
                    resolve(false);
                }
            },
            function(error) {
                handleSequenceError(error.message);
                resolve(false);
            }
        );
    });
}

/**
 * Resume the currently paused sequence
 * @returns {Promise} - Promise resolving to success status
 */
function resumeSequence() {
    return new Promise((resolve) => {
        makeRequest(
            '/api/sequences/resume',
            'POST',
            null,
            function(data) {
                if (data.success) {
                    sequenceStatus.paused = false;
                    updateSequenceStatus();
                    resolve(true);
                } else {
                    handleSequenceError(data.error || 'Unknown error');
                    resolve(false);
                }
            },
            function(error) {
                handleSequenceError(error.message);
                resolve(false);
            }
        );
    });
}

/**
 * Update sequence status from server
 * @returns {Promise} - Promise resolving to current status
 */
function updateSequenceStatus() {
    // Only poll the server if we're running a sequence or have a sequence loaded
    if (!sequenceStatus.running && !sequenceStatus.paused && !sequenceStatus.currentSequence) {
        return Promise.resolve(sequenceStatus);
    }
    
    return new Promise((resolve) => {
        makeRequest(
            '/api/sequences/status',
            'GET',
            null,
            function(data) {
                sequenceStatus.running = data.status === 'RUNNING';
                sequenceStatus.paused = data.status === 'PAUSED';
                sequenceStatus.progressPercent = data.progress_percent || 0;
                sequenceStatus.logMessages = data.execution_log || [];
                
                // Handle simulation status
                if (data.simulated) {
                    sequenceStatus.simulation = true;
                    handleSimulationResponse(data, 'Sequence execution');
                } else {
                    sequenceStatus.simulation = false;
                    clearSimulationNotifications();
                }
                
                // Check for specific errors in log messages
                checkLogForErrors(data.execution_log || []);
                
                // Update UI if we have UI elements
                updateSequenceUI();
                
                // If sequence is complete or error, reset status
                if (data.status === 'COMPLETED' || data.status === 'ERROR') {
                    sequenceStatus.running = false;
                    sequenceStatus.paused = false;
                    
                    // If there was an error, show it
                    if (data.status === 'ERROR') {
                        // Find the error message in the logs
                        const errorLogs = (data.execution_log || []).filter(
                            log => log.includes('Error:')
                        );
                        
                        if (errorLogs.length > 0) {
                            handleSequenceError(errorLogs[errorLogs.length - 1]);
                        } else {
                            handleSequenceError('Error in sequence execution. Check logs for details.');
                        }
                    }
                }
                
                resolve(sequenceStatus);
            },
            function(error) {
                console.error('Error updating sequence status:', error);
                resolve(sequenceStatus);
            }
        );
    });
}

/**
 * Check log messages for known errors and handle them
 * @param {Array} logMessages - Array of log messages
 */
function checkLogForErrors(logMessages) {
    // Look for the specific "No lowest priority node found" error
    const lowestPriorityError = logMessages.find(msg => 
        msg.includes('No lowest priority node found')
    );
    
    if (lowestPriorityError) {
        handleSequenceError(lowestPriorityError);
    }
}

/**
 * Handle simulation mode according to established rules
 * @param {string} operationMode - Current operation mode
 */
function handleSimulationMode(operationMode) {
    // Clear any existing simulation notifications
    clearSimulationNotifications();
    
    if (operationMode === OPERATION_MODES.SIMULATION) {
        // In simulation mode, simulation is expected
        displayInfoMessage('Running in simulation mode as expected.');
    } 
    else if (operationMode === OPERATION_MODES.PROTOTYPE) {
        // In prototype mode, simulation should not happen
        displayErrorMessage('ERROR: Simulation detected in prototype mode. Hardware should be forced.');
    }
    else if (operationMode === OPERATION_MODES.NORMAL) {
        // In normal mode, simulation should not be a fallback
        displayWarningMessage('WARNING: Hardware error detected, but simulation should not be used as a fallback in normal mode.');
    }
}

/**
 * Update the UI elements for sequence display
 */
function updateSequenceUI() {
    // Get UI elements
    const progressBar = document.getElementById('sequence-progress');
    const statusLabel = document.getElementById('sequence-status');
    const logContainer = document.getElementById('sequence-log');
    const pauseButton = document.getElementById('pause-sequence');
    const resumeButton = document.getElementById('resume-sequence');
    
    // Only update if elements exist
    if (progressBar) {
        progressBar.style.width = sequenceStatus.progressPercent + '%';
        progressBar.setAttribute('aria-valuenow', sequenceStatus.progressPercent);
    }
    
    if (statusLabel) {
        let statusText = 'Idle';
        if (sequenceStatus.running) {
            statusText = 'Running';
        } else if (sequenceStatus.paused) {
            statusText = 'Paused';
        }
        statusLabel.textContent = statusText;
    }
    
    if (logContainer) {
        // Clear existing log entries
        logContainer.innerHTML = '';
        
        // Add each log message
        sequenceStatus.logMessages.forEach(message => {
            const logEntry = document.createElement('div');
            logEntry.className = 'log-entry';
            
            // Style based on message type
            if (message.includes('Error:')) {
                logEntry.classList.add('log-error');
            } else if (message.includes('Warning:')) {
                logEntry.classList.add('log-warning');
            } else if (message.includes('Step:')) {
                logEntry.classList.add('log-step');
            }
            
            logEntry.textContent = message;
            logContainer.appendChild(logEntry);
        });
        
        // Scroll to bottom
        logContainer.scrollTop = logContainer.scrollHeight;
    }
    
    // Update button visibility
    if (pauseButton && resumeButton) {
        pauseButton.style.display = sequenceStatus.running && !sequenceStatus.paused ? 'inline-block' : 'none';
        resumeButton.style.display = sequenceStatus.paused ? 'inline-block' : 'none';
    }
}

/**
 * Load available sequences from server using virtualization
 * @returns {Promise} - Promise resolving to array of sequences
 */
function loadAvailableSequences() {
    return new Promise((resolve) => {
        makeRequest(
            '/api/sequences',
            'GET',
            null,
            function(data) {
                // Store all sequences in virtualization object
                virtualization.allSequences = data.sequences || [];
                
                // Calculate total height
                virtualization.totalHeight = virtualization.allSequences.length * virtualization.itemHeight;
                
                // Reset container
                const sequencesContainer = document.getElementById('available-sequences');
                
                if (!sequencesContainer) {
                    resolve(data);
                    return;
                }
                
                // Clear existing sequences
                sequencesContainer.innerHTML = '';
                
                // Enable virtual scrolling only for large datasets
                if (data.sequences.length > 20 && virtualization.enabled) {
                    // Initial render of visible items
                    handleVirtualScroll();
                    
                    // After first render, measure actual item height for better performance
                    setTimeout(measureCardHeight, 100);
                } else {
                    // For small datasets, render all at once (no virtualization)
                    virtualization.enabled = false;
                    data.sequences.forEach((sequence, index) => {
                        const card = createSequenceCard(sequence, index);
                        sequencesContainer.appendChild(card);
                    });
                }
                
                resolve(data);
            },
            function(error) {
                displayErrorMessage('Error loading sequences: ' + error.message);
                resolve({ sequences: [] });
            }
        );
    });
}

/**
 * Create a new sequence
 * @param {Object} sequenceData - Data for the new sequence
 * @returns {Promise} - Promise resolving to created sequence
 */
function createSequence(sequenceData) {
    return new Promise((resolve) => {
        makeRequest(
            '/api/sequences',
            'POST',
            sequenceData,
            function(data) {
                if (data.success) {
                    displaySuccessMessage('Sequence created successfully');
                    loadAvailableSequences();
                    resolve(data.sequence);
                } else {
                    displayErrorMessage('Failed to create sequence: ' + (data.error || 'Unknown error'));
                    resolve(null);
                }
            },
            function(error) {
                displayErrorMessage('Error creating sequence: ' + error.message);
                resolve(null);
            }
        );
    });
}

/**
 * Update an existing sequence
 * @param {string} sequenceId - ID of the sequence to update
 * @param {Object} sequenceData - New data for the sequence
 * @returns {Promise} - Promise resolving to updated sequence
 */
function updateSequence(sequenceId, sequenceData) {
    return new Promise((resolve) => {
        makeRequest(
            `/api/sequences/${sequenceId}`,
            'PUT',
            sequenceData,
            function(data) {
                if (data.success) {
                    displaySuccessMessage('Sequence updated successfully');
                    loadAvailableSequences();
                    resolve(data.sequence);
                } else {
                    displayErrorMessage('Failed to update sequence: ' + (data.error || 'Unknown error'));
                    resolve(null);
                }
            },
            function(error) {
                displayErrorMessage('Error updating sequence: ' + error.message);
                resolve(null);
            }
        );
    });
}

/**
 * Delete a sequence
 * @param {string} sequenceId - ID of the sequence to delete
 * @returns {Promise} - Promise resolving to success status
 */
function deleteSequence(sequenceId) {
    return new Promise((resolve) => {
        makeRequest(
            `/api/sequences/${sequenceId}`,
            'DELETE',
            null,
            function(data) {
                if (data.success) {
                    displaySuccessMessage('Sequence deleted successfully');
                    loadAvailableSequences();
                    resolve(true);
                } else {
                    displayErrorMessage('Failed to delete sequence: ' + (data.error || 'Unknown error'));
                    resolve(false);
                }
            },
            function(error) {
                displayErrorMessage('Error deleting sequence: ' + error.message);
                resolve(false);
            }
        );
    });
}

/**
 * Display an error message
 * @param {string} message - Error message to display
 */
function displayErrorMessage(message) {
    displayNotification(message, 'error');
}

/**
 * Display a warning message
 * @param {string} message - Warning message to display
 */
function displayWarningMessage(message) {
    displayNotification(message, 'warning');
}

/**
 * Display an info message
 * @param {string} message - Info message to display
 */
function displayInfoMessage(message) {
    displayNotification(message, 'info');
}

/**
 * Display a success message
 * @param {string} message - Success message to display
 */
function displaySuccessMessage(message) {
    displayNotification(message, 'success');
}

/**
 * Display a notification
 * @param {string} message - Message to display
 * @param {string} type - Type of notification (error, warning, info, success)
 */
function displayNotification(message, type) {
    const notifications = document.getElementById('notifications');
    
    if (!notifications) {
        console.log(`${type.toUpperCase()}: ${message}`);
        return;
    }
    
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type}`;
    notification.setAttribute('role', 'alert');
    
    // Add data attribute for simulation notifications
    if (message.includes('simulation') || message.includes('Simulation')) {
        notification.setAttribute('data-simulation-notification', 'true');
    }
    
    // Add close button
    const closeButton = document.createElement('button');
    closeButton.className = 'btn-close';
    closeButton.setAttribute('type', 'button');
    closeButton.setAttribute('data-bs-dismiss', 'alert');
    closeButton.setAttribute('aria-label', 'Close');
    
    notification.textContent = message;
    notification.appendChild(closeButton);
    notifications.appendChild(notification);
    
    // Auto-remove after 5 seconds for non-error notifications
    if (type !== 'error') {
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
}

/**
 * Clear all notifications
 */
function clearNotifications() {
    const notifications = document.getElementById('notifications');
    
    if (notifications) {
        notifications.innerHTML = '';
    }
}

/**
 * Clear only simulation-related notifications
 */
function clearSimulationNotifications() {
    const notifications = document.querySelectorAll('[data-simulation-notification="true"]');
    
    notifications.forEach(notification => {
        notification.remove();
    });
}

// Initialize when document is ready
document.addEventListener('DOMContentLoaded', () => {
    initSequences();
    
    // Load sequences if on sequences page
    if (document.getElementById('available-sequences')) {
        loadAvailableSequences();
    }
    
    // Set up event listeners for sequence controls
    const stopButton = document.getElementById('stop-sequence');
    const pauseButton = document.getElementById('pause-sequence');
    const resumeButton = document.getElementById('resume-sequence');
    
    if (stopButton) {
        stopButton.addEventListener('click', stopSequence);
    }
    
    if (pauseButton) {
        pauseButton.addEventListener('click', pauseSequence);
    }
    
    if (resumeButton) {
        resumeButton.addEventListener('click', resumeSequence);
    }
});