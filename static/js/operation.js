/**
 * Operation Page JavaScript
 * Handles fire, fire fiber, and index operations on the main operation page
 */

document.addEventListener('DOMContentLoaded', function() {
    // Use the utility library for simulation mode
    const ShopUtils = window.ShopUtils || {};

    // Handle logging setup
    if (typeof window.addLogMessage !== 'function') {
        console.error('window.addLogMessage function not available - global logging will not work');
        
        // This should never happen with our current implementation, but just in case
        // the base template changes, we'll add a console-only fallback
        window.addLogMessage = function(message, isError = false, logType = 'info') {
            console.log(`Log message (${logType}): ${message}`);
        };
    } else {
        // Log that we're using the main logging function
        console.log("Using addLogMessage function from base.html");
    }
    
    // Add initialization log message
    window.addLogMessage('Operation controls initialized', false, 'info');

    /**
     * Makes a standardized AJAX request with consistent error handling
     * @param {string} url - URL to make the request to
     * @param {string} [method='GET'] - HTTP method to use
     * @param {Object} [data=null] - Data to send with the request
     * @param {Function} [successCallback=null] - Function to call on success
     * @param {Function} [errorCallback=null] - Function to call on error
     * @param {Function} [finallyCallback=null] - Function to call regardless of success/failure
     */
    const makeRequest = ShopUtils.makeRequest || function(url, method, data, successCallback, errorCallback, finallyCallback) {
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
                window.addLogMessage(`Error: ${error.message}`, true);
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
     * Set a button's disabled state with visual feedback
     * @param {HTMLElement} button - The button to modify
     * @param {boolean} disabled - Whether to disable the button
     */
    const setButtonState = ShopUtils.setButtonsState || function(enabled, ...buttons) {
        buttons.forEach(button => {
            if (button) {
                button.disabled = !enabled;
            }
        });
    };
    
    // Fire and Fiber buttons
    const fireButton = document.getElementById('fire-button');
    const fireFiberButton = document.getElementById('fire-fiber-button');
    const stopFireButton = document.getElementById('stop-fire-button');
    
    // Index buttons
    const indexButton = document.getElementById('index-button');
    const indexBackButton = document.getElementById('index-back-button');
    
    // Home and stop cleaning head buttons
    const homeCleaningHeadButton = document.getElementById('home-cleaning-head');
    const stopCleaningHeadButton = document.getElementById('stop-cleaning-head');
    
    // Table control buttons
    const runTableButton = document.getElementById('run-table-button');
    const stopTableButton = document.getElementById('stop-table-button');
    
    // Status indicators
    const firingStatus = document.getElementById('firing-status');
    const firingProgress = document.getElementById('firing-progress');
    const firingTimeDisplay = document.getElementById('firing-time-display');
    const cleaningHeadStatus = document.getElementById('cleaning-head-status');
    
    // Regular Fire Buttons (both toggle and momentary)
    const fireToggleButton = document.getElementById('fire-toggle-button');
    // Add fiber toggle button reference
    const fireFiberToggleButton = document.getElementById('fire-fiber-toggle-button');

    /**
     * Updates the firing status indicator in the UI
     * @param {string} status - The status text to display
     * @param {string} className - The CSS class to apply to the status indicator
     */
    function updateFiringStatus(status, className) {
        if (firingStatus) {
            firingStatus.textContent = status;
            firingStatus.className = className;
        }
    }
    
    /**
     * Disables all fire buttons and enables the stop button
     */
    function disableFireButtons() {
        setButtonState(false, fireButton, fireToggleButton, fireFiberButton, fireFiberToggleButton);
        setButtonState(true, stopFireButton);
    }
    
    /**
     * Enables all fire buttons and disables the stop button
     */
    function enableFireButtons() {
        setButtonState(true, fireButton, fireToggleButton, fireFiberButton, fireFiberToggleButton);
        setButtonState(false, stopFireButton);
    }
    
    /**
     * Sets firing status to inactive/not firing
     */
    function resetFiringStatus() {
        updateFiringStatus('Not Firing', 'badge bg-secondary');
    }
    
    // Momentary Fire button (original behavior)
    if (fireButton && stopFireButton) {
        console.log("Fire button found and event listener attached");
        fireButton.addEventListener('click', function() {
            console.log("Fire button (momentary) clicked");
            window.addLogMessage('FIRING (momentary) - Moving servo to position B...', false, 'action');
            
            disableFireButtons();
            updateFiringStatus('Firing', 'badge bg-danger');
            
            makeRequest(
                '/fire',
                'POST',
                { mode: 'momentary' },
                function(data) {
                    if (data.status === 'success') {
                        window.addLogMessage('Firing initiated', false, 'success');
                    } else {
                        window.addLogMessage(`Error initiating firing: ${data.message}`, true);
                        enableFireButtons();
                        resetFiringStatus();
                    }
                },
                function(error) {
                    // Error handling is done in makeRequest
                    enableFireButtons();
                    resetFiringStatus();
                }
            );
        });
    }
    
    // Toggle Fire button (new behavior)
    if (fireToggleButton && stopFireButton) {
        console.log("Fire toggle button found and event listener attached");
        fireToggleButton.addEventListener('click', function() {
            console.log("Fire toggle button clicked");
            window.addLogMessage('FIRING (toggle) - Moving servo to position B...', false, 'action');
            
            disableFireButtons();
            updateFiringStatus('Firing (Toggle)', 'badge bg-danger');
            
            makeRequest(
                '/fire',
                'POST',
                { mode: 'toggle' },
                function(data) {
                    if (data.status === 'success') {
                        window.addLogMessage('Firing (toggle mode) initiated', false, 'success');
                    } else {
                        window.addLogMessage(`Error initiating toggle firing: ${data.message}`, true);
                        enableFireButtons();
                        resetFiringStatus();
                    }
                },
                function(error) {
                    // Error handling is done in makeRequest
                    enableFireButtons();
                    resetFiringStatus();
                }
            );
        });
        
        console.log("Stop fire button listener attached");
        stopFireButton.addEventListener('click', function() {
            console.log("Stop fire button clicked");
            window.addLogMessage('STOPPING FIRE - Moving servo to position A...', false, 'action');
            
            // Disable stop button
            setButtonState(false, stopFireButton);
            
            makeRequest(
                '/stop_fire',
                'POST',
                null,
                function(data) {
                    if (data.status === 'success') {
                        window.addLogMessage('Firing stopped', false, 'success');
                        resetFiringStatus();
                    } else {
                        window.addLogMessage(`Error stopping firing: ${data.message}`, true);
                    }
                    // Always re-enable all fire buttons after stop operation
                    enableFireButtons();
                },
                function(error) {
                    // Error handling is done in makeRequest
                    // Always re-enable all fire buttons after stop operation
                    enableFireButtons();
                }
            );
        });
    }
    
    // Fire Fiber button (momentary) event 
    if (fireFiberButton) {
        console.log("Fiber fire button found and event listener attached");
        fireFiberButton.addEventListener('click', function() {
            window.addLogMessage('Starting FIBER sequence (momentary)...', false, 'action');
            
            disableFireButtons();
            updateFiringStatus('Fiber Sequence', 'badge bg-warning text-dark');
            
            makeRequest(
                '/fire_fiber',
                'POST',
                { mode: 'momentary' },
                function(data) {
                    if (data.status === 'success') {
                        window.addLogMessage('Fiber sequence started', false, 'success');
                    } else {
                        window.addLogMessage(`Error starting fiber sequence: ${data.message}`, true);
                        resetFiringStatus();
                        enableFireButtons();
                    }
                },
                function(error) {
                    // Error handling is done in makeRequest
                    resetFiringStatus();
                    enableFireButtons();
                }
            );
        });
    }
    
    // Fire Fiber Toggle button event
    if (fireFiberToggleButton) {
        console.log("Fiber fire toggle button found and event listener attached");
        fireFiberToggleButton.addEventListener('click', function() {
            window.addLogMessage('Starting FIBER sequence (toggle mode)...', false, 'action');
            
            disableFireButtons();
            updateFiringStatus('Fiber Sequence (Toggle)', 'badge bg-warning text-dark');
            
            makeRequest(
                '/fire_fiber',
                'POST',
                { mode: 'toggle' },
                function(data) {
                    if (data.status === 'success') {
                        window.addLogMessage('Fiber sequence started (toggle mode)', false, 'success');
                    } else {
                        window.addLogMessage(`Error starting fiber sequence: ${data.message}`, true);
                        resetFiringStatus();
                        enableFireButtons();
                    }
                },
                function(error) {
                    // Error handling is done in makeRequest
                    resetFiringStatus();
                    enableFireButtons();
                }
            );
        });
    }
    
    // Track cleaning head movement state
    let cleaningHeadBusy = false;
    
    /**
     * Disables all cleaning head control buttons except the stop button
     */
    function disableCleaningHeadButtons() {
        setButtonState(false, indexButton, indexBackButton, homeCleaningHeadButton);
        cleaningHeadBusy = true;
    }
    
    /**
     * Enables all cleaning head control buttons
     */
    function enableCleaningHeadButtons() {
        setButtonState(true, indexButton, indexBackButton, homeCleaningHeadButton);
        cleaningHeadBusy = false;
    }
    
    /**
     * Updates the cleaning head position display
     * @param {number|string} position - The position to display
     */
    function updateCleaningHeadPosition(position) {
        if (cleaningHeadStatus) {
            cleaningHeadStatus.textContent = `Position: ${position}`;
        }
    }
    
    // Index Forward button
    if (indexButton) {
        console.log("Index button found and event listener attached");
        indexButton.addEventListener('click', function() {
            // Don't allow multiple operations at once
            if (cleaningHeadBusy) {
                window.addLogMessage('Cannot index forward: cleaning head is busy. Stop current operation first.', true);
                return;
            }
            
            console.log("Index button clicked");
            window.addLogMessage('Indexing forward...', false, 'action');
            
            // Disable all cleaning head buttons
            disableCleaningHeadButtons();
            
            makeRequest(
                '/index_move',
                'POST',
                { direction: 'forward' },
                function(data) {
                    if (data.status === 'success') {
                        const currentPosition = data.position;
                        updateCleaningHeadPosition(currentPosition);
                        window.addLogMessage(`Index forward complete! Position: ${currentPosition}`, false, 'success');
                    } else {
                        window.addLogMessage(`Error: ${data.message}`, true);
                    }
                },
                null,
                function() {
                    // Re-enable all buttons in finally
                    enableCleaningHeadButtons();
                }
            );
        });
    }
    
    // Index Backward button
    if (indexBackButton) {
        indexBackButton.addEventListener('click', function() {
            // Don't allow multiple operations at once
            if (cleaningHeadBusy) {
                window.addLogMessage('Cannot index backward: cleaning head is busy. Stop current operation first.', true);
                return;
            }
            
            window.addLogMessage('Indexing backward...', false, 'action');
            
            // Disable all cleaning head buttons
            disableCleaningHeadButtons();
            
            makeRequest(
                '/index_move',
                'POST',
                { direction: 'backward' },
                function(data) {
                    if (data.status === 'success') {
                        const currentPosition = data.position;
                        updateCleaningHeadPosition(currentPosition);
                        window.addLogMessage(`Index backward complete! Position: ${currentPosition}`, false, 'success');
                    } else {
                        window.addLogMessage(`Error: ${data.message}`, true);
                    }
                },
                null,
                function() {
                    // Re-enable all buttons in finally
                    enableCleaningHeadButtons();
                }
            );
        });
    }
    
    // Home Cleaning Head button
    if (homeCleaningHeadButton) {
        homeCleaningHeadButton.addEventListener('click', function() {
            // Don't allow multiple operations at once
            if (cleaningHeadBusy) {
                window.addLogMessage('Cannot home cleaning head: cleaning head is busy. Stop current operation first.', true);
                return;
            }
            
            window.addLogMessage('Homing cleaning head...', false, 'action');
            
            // Disable all cleaning head buttons
            disableCleaningHeadButtons();
            
            makeRequest(
                '/home',
                'POST',
                null,
                function(data) {
                    if (data.status === 'success') {
                        updateCleaningHeadPosition(0);
                        window.addLogMessage('Cleaning head homed successfully', false, 'success');
                    } else {
                        window.addLogMessage(`Error homing cleaning head: ${data.message}`, true);
                    }
                },
                null,
                function() {
                    // Re-enable all buttons in finally
                    enableCleaningHeadButtons();
                }
            );
        });
    }
    
    // Stop Cleaning Head button
    if (stopCleaningHeadButton) {
        console.log("Stop cleaning head button listener attached");
        stopCleaningHeadButton.addEventListener('click', function() {
            console.log("Stop cleaning head button clicked");
            window.addLogMessage('STOPPING CLEANING HEAD...', false, 'action');
            
            makeRequest(
                '/stop_motor',
                'POST',
                null,
                function(data) {
                    if (data.status === 'success') {
                        const currentPosition = data.position || 'unknown';
                        window.addLogMessage(`Cleaning head stopped at position: ${currentPosition}`, false, 'success');
                        
                        if (data.position) {
                            updateCleaningHeadPosition(currentPosition);
                        }
                    } else {
                        window.addLogMessage(`Error stopping cleaning head: ${data.message}`, true);
                    }
                    // Always re-enable buttons after stopping
                    enableCleaningHeadButtons();
                },
                function(error) {
                    // Error handling is done in makeRequest
                    // Make sure to re-enable buttons even on error
                    enableCleaningHeadButtons();
                }
            );
        });
    }
    
    /**
     * Disables the run table button and enables the stop table button
     */
    function disableRunTableButton() {
        setButtonState(false, runTableButton);
        setButtonState(true, stopTableButton);
    }
    
    /**
     * Enables the run table button and disables the stop table button
     */
    function enableRunTableButton() {
        setButtonState(true, runTableButton);
        setButtonState(false, stopTableButton);
    }
    
    // Run Table button
    if (runTableButton) {
        runTableButton.addEventListener('click', function() {
            window.addLogMessage('Running table sequence...', false, 'action');
            
            disableRunTableButton();
            
            makeRequest(
                '/table/forward',
                'POST',
                { state: true },
                function(data) {
                    if (data.status !== 'success') {
                        window.addLogMessage(`Error starting table: ${data.message || 'Unknown error'}`, true);
                        // Reset buttons on error
                        enableRunTableButton();
                    }
                },
                function(error) {
                    // Error handling is done in makeRequest
                    // Reset buttons on error
                    enableRunTableButton();
                }
            );
        });
    }
    
    // Stop Table button
    if (stopTableButton) {
        stopTableButton.addEventListener('click', function() {
            window.addLogMessage('Stopping table...', false, 'action');
            
            // First, stop forward movement
            makeRequest(
                '/table/forward',
                'POST',
                { state: false },
                function(data) {
                    // Then stop backward movement
                    makeRequest(
                        '/table/backward',
                        'POST',
                        { state: false },
                        function(data) {
                            window.addLogMessage('Table stopped', false, 'success');
                            enableRunTableButton();
                        },
                        function(error) {
                            // Still try to reset buttons even on error
                            enableRunTableButton();
                        }
                    );
                },
                function(error) {
                    // Still try to stop backward movement even if forward fails
                    makeRequest(
                        '/table/backward',
                        'POST',
                        { state: false },
                        function(data) {
                            window.addLogMessage('Table stopped', false, 'success');
                            enableRunTableButton();
                        },
                        function(error) {
                            window.addLogMessage('Error stopping table in both directions', true);
                            enableRunTableButton();
                        }
                    );
                }
            );
        });
    }
});