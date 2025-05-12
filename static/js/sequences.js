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

// Request cache for AJAX optimization
const requestCache = {
    data: new Map(),          // Cache storage: URL -> {data, timestamp}
    timeouts: new Map(),      // Request debounce timeouts
    maxAge: 30000,            // Default cache expiry (30 seconds)
    statusInterval: null,     // Interval timer for polling sequence status
    adaptivePolling: {        // Settings for adaptive polling frequency
        enabled: true,
        baseInterval: 1000,   // Base interval (1 second)
        slowInterval: 5000,   // Slower interval when idle (5 seconds)
        currentInterval: 1000 // Current polling interval
    },
    pendingPromises: new Map() // Map to track pending promises for the same URL
};

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
    totalHeight: 0,          // Total height of all items
    pendingUpdate: false,    // Flag to prevent concurrent updates
    heightMeasured: false,   // Flag to track if we've measured real item height
    renderThreshold: 25,     // Number of items above which virtualization is enabled
    recycledNodes: [],       // Pool of recycled DOM nodes for better performance
    nodePoolSize: 20,        // Maximum size of recycled nodes pool
    lastVisibleIndexes: null // Last visible indexes range to prevent unnecessary updates
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
 * Makes a cached, optimized AJAX request
 * @param {string} url - URL to make the request to
 * @param {string} [method='GET'] - HTTP method to use
 * @param {Object} [data=null] - Data to send with the request
 * @param {Object} [options={}] - Additional options
 * @param {boolean} [options.useCache=true] - Whether to use cache for GET requests
 * @param {number} [options.cacheTTL] - Cache time-to-live in ms (defaults to requestCache.maxAge)
 * @param {boolean} [options.background=false] - If true, won't show errors in UI
 * @returns {Promise} - Promise resolving to the response data
 */
function makeOptimizedRequest(url, method = 'GET', data = null, options = {}) {
    const useCache = options.useCache !== false && method === 'GET';
    const cacheTTL = options.cacheTTL || requestCache.maxAge;
    const background = options.background || false;
    
    // For GET requests with caching enabled, check cache first
    if (useCache && method === 'GET') {
        const cachedData = requestCache.data.get(url);
        
        if (cachedData && (Date.now() - cachedData.timestamp) < cacheTTL) {
            return Promise.resolve(cachedData.data);
        }
        
        // Check if we already have a pending request for this URL
        const pendingPromise = requestCache.pendingPromises.get(url);
        if (pendingPromise) {
            // Return the existing promise to avoid duplicate requests
            return pendingPromise;
        }
    }
    
    // Create the promise for this request
    const requestPromise = new Promise((resolve, reject) => {
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
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(responseData => {
                // For GET requests, cache the result
                if (useCache && method === 'GET') {
                    requestCache.data.set(url, {
                        data: responseData,
                        timestamp: Date.now()
                    });
                }
                
                resolve(responseData);
            })
            .catch(error => {
                if (!background) {
                    console.error(`Error making ${method} request to ${url}:`, error);
                }
                reject(error);
            })
            .finally(() => {
                // Remove from pending promises
                if (useCache && method === 'GET') {
                    requestCache.pendingPromises.delete(url);
                }
            });
    });
    
    // Store the promise if this is a cacheable request
    if (useCache && method === 'GET') {
        requestCache.pendingPromises.set(url, requestPromise);
    }
    
    return requestPromise;
}

/**
 * Clears the cache for specific URL patterns or all cache if no pattern provided
 * @param {string|RegExp} [pattern] - Optional URL pattern to clear from cache
 */
function clearRequestCache(pattern) {
    if (!pattern) {
        // Clear all cache
        requestCache.data.clear();
    } else {
        // Clear only matching URLs
        const patternObj = pattern instanceof RegExp ? pattern : new RegExp(pattern);
        
        // Use a separate array to avoid modifying while iterating
        const keysToRemove = [];
        
        requestCache.data.forEach((value, key) => {
            if (patternObj.test(key)) {
                keysToRemove.push(key);
            }
        });
        
        keysToRemove.forEach(key => {
            requestCache.data.delete(key);
        });
    }
}

/**
 * Debounces a function call
 * @param {string} key - Unique identifier for this debounce operation
 * @param {Function} fn - Function to debounce
 * @param {number} delay - Delay time in ms
 */
function debounce(key, fn, delay) {
    // Clear existing timeout if any
    if (requestCache.timeouts.has(key)) {
        clearTimeout(requestCache.timeouts.get(key));
    }
    
    // Set new timeout
    const timeout = setTimeout(() => {
        fn();
        requestCache.timeouts.delete(key);
    }, delay);
    
    requestCache.timeouts.set(key, timeout);
}

/**
 * Initialize sequences module with optimized polling
 */
function initSequences() {
    // Get current operation mode from server
    makeOptimizedRequest(
        '/api/system/operation_mode',
        'GET'
    ).then(data => {
        sequenceStatus.operationMode = data.mode || 'normal';
        console.log('Operation mode:', sequenceStatus.operationMode);
    }).catch(error => {
        console.error('Error getting operation mode:', error);
        // Default to normal mode if there's an error
        sequenceStatus.operationMode = 'normal';
    });
    
    // Set up adaptive polling for sequence status
    setupAdaptivePolling();
    
    // Initialize virtualization if on sequences page
    if (!virtualization.enabled || !virtualization.container || virtualization.allSequences.length === 0) {
        return;
    }
    
    // Get current scroll position and container dimensions with better caching
    const scrollTop = virtualization.scrollContainer === window ? 
        window.scrollY : 
        virtualization.scrollContainer.scrollTop;
    
    const containerHeight = virtualization.scrollContainer === window ?
        window.innerHeight :
        virtualization.scrollContainer.clientHeight;
    
    // Skip processing if scrolled less than 5px from last position
    const scrollDelta = Math.abs(scrollTop - virtualization.lastScrollPosition);
    if (scrollDelta < 5 && virtualization.visibleItems.length > 0) {
        return;
    }
    
    // Calculate visible range with buffer
    const startIndex = Math.max(0, Math.floor(scrollTop / virtualization.itemHeight) - virtualization.bufferSize);
    const endIndex = Math.min(
        virtualization.allSequences.length - 1,
        Math.ceil((scrollTop + containerHeight) / virtualization.itemHeight) + virtualization.bufferSize
    );
    
    // Store the visible range for comparison
    if (!virtualization.lastVisibleIndexes) {
        virtualization.lastVisibleIndexes = { start: startIndex, end: endIndex };
    }
    
    // Update DOM only if the visible range has changed significantly
    if (hasVisibleRangeChangedSignificantly(startIndex, endIndex)) {
        updateVisibleItems(startIndex, endIndex);
        virtualization.lastVisibleIndexes = { start: startIndex, end: endIndex };
    }
    
    virtualization.lastScrollPosition = scrollTop;
}

/**
 * Check if the visible range of items has changed significantly
 * @param {number} startIndex - New start index
 * @param {number} endIndex - New end index
 * @returns {boolean} - True if range has changed significantly
 */
function hasVisibleRangeChangedSignificantly(startIndex, endIndex) {
    if (virtualization.visibleItems.length === 0) {
        return true;
    }
    
    // If we don't have a previous range, then it's changed
    if (!virtualization.lastVisibleIndexes) {
        return true;
    }
    
    const previousStart = virtualization.lastVisibleIndexes.start;
    const previousEnd = virtualization.lastVisibleIndexes.end;
    
    // Check if the start or end differs by more than a threshold
    const startDiff = Math.abs(startIndex - previousStart);
    const endDiff = Math.abs(endIndex - previousEnd);
    
    // If either end changed by more than 2 items, we update
    return startDiff > 2 || endDiff > 2;
}

/**
 * Update the visible items in the DOM with node recycling for better performance
 * @param {number} startIndex - Start index of visible range
 * @param {number} endIndex - End index of visible range
 */
function updateVisibleItems(startIndex, endIndex) {
    // Create map of existing nodes by index for recycling
    const existingNodeMap = new Map();
    virtualization.visibleItems.forEach(item => {
        existingNodeMap.set(item.index, item.element);
    });
    
    // Determine which elements to keep and which to recycle
    const newVisibleIndexes = new Set();
    for (let i = startIndex; i <= endIndex; i++) {
        newVisibleIndexes.add(i);
    }
    
    // Collect nodes to recycle or keep
    const nodesToKeep = [];
    const nodesToRecycle = [];
    
    virtualization.visibleItems.forEach(item => {
        if (newVisibleIndexes.has(item.index)) {
            // Keep this node as it's still visible
            nodesToKeep.push(item);
        } else {
            // Recycle this node as it's no longer visible
            nodesToRecycle.push(item.element);
        }
    });
    
    // Add recycled nodes to pool
    nodesToRecycle.forEach(node => {
        if (virtualization.recycledNodes.length < virtualization.nodePoolSize) {
            virtualization.recycledNodes.push(node);
        }
    });
    
    // Clear the container but don't recreate everything
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
    
    // Render visible items - reusing existing nodes where possible
    for (let i = startIndex; i <= endIndex; i++) {
        if (i >= 0 && i < virtualization.allSequences.length) {
            const sequence = virtualization.allSequences[i];
            let sequenceCard;
            
            // Check if we have an existing node for this index
            const existingNode = existingNodeMap.get(i);
            if (existingNode) {
                // Reuse existing node
                sequenceCard = existingNode;
            } else if (virtualization.recycledNodes.length > 0) {
                // Reuse a recycled node
                sequenceCard = virtualization.recycledNodes.pop();
                updateSequenceCard(sequenceCard, sequence, i);
            } else {
                // Create a new node if we must
                sequenceCard = createSequenceCard(sequence, i);
            }
            
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
    
    // Measure actual height if we haven't yet
    if (!virtualization.heightMeasured && virtualization.visibleItems.length > 0) {
        requestAnimationFrame(measureCardHeight);
    }
}

/**
 * Update an existing sequence card with new data
 * @param {HTMLElement} card - Existing card element to update
 * @param {Object} sequence - New sequence data
 * @param {number} index - New index
 */
function updateSequenceCard(card, sequence, index) {
    // Update data attributes
    card.setAttribute('data-sequence-index', index);
    
    // Update title
    const titleElement = card.querySelector('.card-title');
    if (titleElement) {
        titleElement.textContent = sequence.name;
    }
    
    // Update description
    const descriptionElement = card.querySelector('.card-text:not(.text-muted)');
    if (descriptionElement) {
        descriptionElement.textContent = sequence.description || 'No description available';
    }
    
    // Update steps count
    const stepsCountElement = card.querySelector('.card-text.text-muted');
    if (stepsCountElement) {
        stepsCountElement.textContent = `${sequence.steps.length} steps`;
    }
    
    // Update start button (ensure click handler is updated)
    const startButton = card.querySelector('.btn-primary');
    if (startButton) {
        startButton.onclick = () => startSequence(sequence.id);
    }
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
                virtualization.heightMeasured = true;
                console.log('Measured item height:', height);
                
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
 * Load available sequences from server using enhanced virtualization
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
                
                // Reset recycled nodes
                virtualization.recycledNodes = [];
                virtualization.visibleItems = [];
                virtualization.lastVisibleIndexes = null;
                
                // Enable virtual scrolling for datasets above the threshold
                if (data.sequences.length > virtualization.renderThreshold && virtualization.enabled) {
                    // Initial render of visible items
                    handleVirtualScroll();
                    
                    // After first render, measure actual item height for better performance
                    setTimeout(() => {
                        if (!virtualization.heightMeasured) {
                            measureCardHeight();
                        }
                    }, 100);
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