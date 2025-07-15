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
            if (isError) {
                console.error(`[${logType.toUpperCase()}] ${message}`);
            } else {
                console.log(`[${logType.toUpperCase()}] ${message}`);
            }
        };
    } else {
        console.log('window.addLogMessage function is available');
    }
            if (btn) {
                btn.classList.remove('active');
                console.log(`Removed active class from light button: ${btn.id}`);
            }
        });
        
        if (activeMode === 'on' && lightOnBtn) {
            lightOnBtn.classList.add('active');
            console.log('Added active class to light ON button');
        } else if (activeMode === 'off' && lightOffBtn) {
            lightOffBtn.classList.add('active');
            console.log('Added active class to light OFF button');
        } else if (activeMode === 'auto' && lightAutoBtn) {
            lightAutoBtn.classList.add('active');
            console.log('Added active class to light AUTO button');
        }
    }       console.log(`Log message (${logType}): ${message}`);
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
     * @param {Function} [logFunction=console.log] - Logging function
     * @param {Function} [onSuccess=null] - Function to call on success
     * @param {Function} [onError=null] - Function to call on error
     * @param {Function} [onFinally=null] - Function to call regardless of success/failure
     */
    const makeRequest = ShopUtils.makeRequest || function(url, method = 'GET', data = null, logFunction = console.log, onSuccess = null, onError = null, onFinally = null) {
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
                } else {
                    console.error(`Error: ${error.message}`);
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

    // Fan and Lights manual control buttons
    const fanOnBtn = document.getElementById('fan-on-btn');
    const fanOffBtn = document.getElementById('fan-off-btn');
    const fanAutoBtn = document.getElementById('fan-auto-btn');
    const lightsOnBtn = document.getElementById('lights-on-btn');
    const lightsOffBtn = document.getElementById('lights-off-btn');
    const lightsAutoBtn = document.getElementById('lights-auto-btn');
    const fanStateDisplay = document.getElementById('fan-state-display');
    const lightsStateDisplay = document.getElementById('lights-state-display');
    const estopBtn = document.getElementById('estop-btn');

    // Debug: Check if buttons were found
    console.log('Button elements found:', {
        fanOnBtn: !!fanOnBtn,
        fanOffBtn: !!fanOffBtn,
        fanAutoBtn: !!fanAutoBtn,
        lightsOnBtn: !!lightsOnBtn,
        lightsOffBtn: !!lightsOffBtn,
        lightsAutoBtn: !!lightsAutoBtn
    });

    if (!fanOnBtn) console.error('Fan ON button not found!');
    if (!fanOffBtn) console.error('Fan OFF button not found!');
    if (!fanAutoBtn) console.error('Fan AUTO button not found!');
    if (!lightsOnBtn) console.error('Lights ON button not found!');
    if (!lightsOffBtn) console.error('Lights OFF button not found!');
    if (!lightsAutoBtn) console.error('Lights AUTO button not found!');

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
    let fireToggleActive = false;
    if (fireToggleButton && stopFireButton) {
        fireToggleButton.addEventListener('click', function() {
            fireToggleActive = !fireToggleActive;
            fireToggleButton.classList.toggle('active', fireToggleActive);
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
        
        stopFireButton.addEventListener('click', function() {
            fireToggleActive = false;
            fireToggleButton.classList.remove('active');
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
    let fireFiberToggleActive = false;
    if (fireFiberToggleButton) {
        console.log("Fiber fire toggle button found and event listener attached");
        fireFiberToggleButton.addEventListener('click', function() {
            fireFiberToggleActive = !fireFiberToggleActive;
            fireFiberToggleButton.classList.toggle('active', fireFiberToggleActive);
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
        
        stopFireButton.addEventListener('click', function() {
            fireFiberToggleActive = false;
            fireFiberToggleButton.classList.remove('active');
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
    
    // Run Table button - now uses shared auto cycle system
    if (runTableButton) {
        runTableButton.addEventListener('click', function() {
            if (window.AutoCycleManager) {
                window.AutoCycleManager.start();
            } else {
                console.error('AutoCycleManager not available');
                window.addLogMessage('Auto cycle system not available', true);
            }
        });
    }
    
    // Stop Table button - now uses shared auto cycle system
    if (stopTableButton) {
        stopTableButton.addEventListener('click', function() {
            if (window.AutoCycleManager) {
                window.AutoCycleManager.stop();
            } else {
                console.error('AutoCycleManager not available');
            }
        });
    }
    
    // Configure the auto cycle manager for the operation page
    if (window.AutoCycleManager) {
        window.AutoCycleManager.configure({
            moveForward: function() {
                return new Promise((resolve, reject) => {
                    makeRequest('/table/forward', 'POST', { state: true }, function(data) {
                        if (data && data.status === 'success') {
                            resolve();
                        } else {
                            reject(new Error('Failed to start forward movement'));
                        }
                    });
                });
            },
            moveBackward: function() {
                return new Promise((resolve, reject) => {
                    makeRequest('/table/backward', 'POST', { state: true }, function(data) {
                        if (data && data.status === 'success') {
                            resolve();
                        } else {
                            reject(new Error('Failed to start backward movement'));
                        }
                    });
                });
            },
            stopMovement: function() {
                return new Promise((resolve) => {
                    makeRequest('/table/forward', 'POST', { state: false });
                    makeRequest('/table/backward', 'POST', { state: false });
                    resolve();
                });
            },
            onStart: function() {
                window.addLogMessage('Starting table auto cycle...', false, 'action');
                disableRunTableButton();
            },
            onStop: function(cycleCount) {
                window.addLogMessage(`Table auto cycle stopped. Completed ${cycleCount} cycles.`, false, 'success');
                enableRunTableButton();
            },
            onError: function(error) {
                window.addLogMessage('Table auto cycle error: ' + error.message, true);
                enableRunTableButton();
            }
        });
        
        // Set up state change callback to update button states
        window.AutoCycleManager.onStateChange = function() {
            const state = window.AutoCycleManager.getState();
            if (state.running) {
                disableRunTableButton();
            } else {
                enableRunTableButton();
            }
        };
    }
    
    // Helper to update fan/lights state display
    function updateFanStateDisplay(state, mode = 'manual') {
        if (fanStateDisplay) {
            let displayText = '';
            let badgeClass = 'badge ';
            
            if (mode === 'auto') {
                displayText = `Auto (${state ? 'On' : 'Off'})`;
                badgeClass += state ? 'bg-info' : 'bg-secondary';
            } else {
                displayText = state ? 'On' : 'Off';
                badgeClass += state ? 'bg-success' : 'bg-secondary';
            }
            
            fanStateDisplay.textContent = displayText;
            fanStateDisplay.className = badgeClass;
        }
        
        // Update button states based on mode and state
        if (mode === 'auto') {
            updateFanButtonStates('auto');
        } else {
            updateFanButtonStates(state ? 'on' : 'off');
        }
    }
    
    function updateLightsStateDisplay(state, mode = 'manual') {
        if (lightsStateDisplay) {
            let displayText = '';
            let badgeClass = 'badge ';
            
            if (mode === 'auto') {
                displayText = `Auto (${state ? 'On' : 'Off'})`;
                badgeClass += state ? 'bg-info' : 'bg-secondary';
            } else {
                displayText = state ? 'On' : 'Off';
                badgeClass += state ? 'bg-success' : 'bg-secondary';
            }
            
            lightsStateDisplay.textContent = displayText;
            lightsStateDisplay.className = badgeClass;
        }
        
        // Update button states based on mode and state
        if (mode === 'auto') {
            updateLightsButtonStates('auto');
        } else {
            updateLightsButtonStates(state ? 'on' : 'off');
        }
    }
    
    function updateFanButtonStates(activeMode) {
        console.log(`updateFanButtonStates called with activeMode: ${activeMode}`);
        console.log('Fan buttons:', { fanOnBtn, fanOffBtn, fanAutoBtn });
        
        [fanOnBtn, fanOffBtn, fanAutoBtn].forEach(btn => {
            if (btn) {
                btn.classList.remove('active');
                console.log(`Removed active class from button: ${btn.id}`);
            }
        });
        
        if (activeMode === 'on' && fanOnBtn) {
            fanOnBtn.classList.add('active');
            console.log('Added active class to fan ON button');
        } else if (activeMode === 'off' && fanOffBtn) {
            fanOffBtn.classList.add('active');
            console.log('Added active class to fan OFF button');
        } else if (activeMode === 'auto' && fanAutoBtn) {
            fanAutoBtn.classList.add('active');
            console.log('Added active class to fan AUTO button');
        }
    }
    
    function updateLightsButtonStates(activeMode) {
        [lightsOnBtn, lightsOffBtn, lightsAutoBtn].forEach(btn => {
            if (btn) btn.classList.remove('active');
        });
        
        if (activeMode === 'on' && lightsOnBtn) {
            lightsOnBtn.classList.add('active');
        } else if (activeMode === 'off' && lightsOffBtn) {
            lightsOffBtn.classList.add('active');
        } else if (activeMode === 'auto' && lightsAutoBtn) {
            lightsAutoBtn.classList.add('active');
        }
    }

    // Fan ON/OFF/AUTO
    if (fanOnBtn) {
        console.log('Adding click listener to Fan ON button');
        fanOnBtn.addEventListener('click', function() {
            console.log('Fan ON button clicked');
            window.addLogMessage('Fan ON button clicked', false, 'debug');
            
            makeRequest('/fan/set', 'POST', { state: true, mode: 'manual' }, window.addLogMessage, function(data) {
                console.log('Fan ON response received:', data);
                updateFanStateDisplay(data.fan_state !== undefined ? data.fan_state : true, 'manual');
                window.addLogMessage('Fan turned ON (manual)', false, 'action');
            });
        });
    } else {
        console.error('Fan ON button not found - cannot add click listener');
    }
    if (fanOffBtn) {
        console.log('Adding click listener to Fan OFF button');
        fanOffBtn.addEventListener('click', function() {
            console.log('Fan OFF button clicked');
            window.addLogMessage('Fan OFF button clicked', false, 'debug');
            
            makeRequest('/fan/set', 'POST', { state: false, mode: 'manual' }, window.addLogMessage, function(data) {
                console.log('Fan OFF response received:', data);
                updateFanStateDisplay(data.fan_state !== undefined ? data.fan_state : false, 'manual');
                window.addLogMessage('Fan turned OFF (manual)', false, 'action');
            });
        });
    } else {
        console.error('Fan OFF button not found - cannot add click listener');
    }
    if (fanAutoBtn) {
        fanAutoBtn.addEventListener('click', function() {
            console.log('Fan AUTO button clicked');
            window.addLogMessage('Fan AUTO button clicked', false, 'debug');
            
            makeRequest('/fan/set', 'POST', { mode: 'auto' }, window.addLogMessage, function(data) {
                console.log('Fan AUTO response received:', data);
                updateFanStateDisplay(data.fan_state || false, 'auto');
                window.addLogMessage('Fan set to AUTO mode', false, 'action');
            }, function(error) {
                console.error('Fan AUTO request failed:', error);
                window.addLogMessage('Fan AUTO request failed: ' + error, false, 'error');
            });
        });
    }

    // Lights ON/OFF/AUTO
    if (lightsOnBtn) {
        lightsOnBtn.addEventListener('click', function() {
            console.log('Lights ON button clicked');
            window.addLogMessage('Lights ON button clicked', false, 'debug');
            
            makeRequest('/lights/set', 'POST', { state: true, mode: 'manual' }, window.addLogMessage, function(data) {
                console.log('Lights ON response received:', data);
                updateLightsStateDisplay(data.lights_state !== undefined ? data.lights_state : true, 'manual');
                window.addLogMessage('Red lights turned ON (manual)', false, 'action');
            });
        });
    }
    if (lightsOffBtn) {
        lightsOffBtn.addEventListener('click', function() {
            console.log('Lights OFF button clicked');
            window.addLogMessage('Lights OFF button clicked', false, 'debug');
            
            makeRequest('/lights/set', 'POST', { state: false, mode: 'manual' }, window.addLogMessage, function(data) {
                console.log('Lights OFF response received:', data);
                updateLightsStateDisplay(data.lights_state !== undefined ? data.lights_state : false, 'manual');
                window.addLogMessage('Red lights turned OFF (manual)', false, 'action');
            });
        });
    }
    if (lightsAutoBtn) {
        lightsAutoBtn.addEventListener('click', function() {
            console.log('Lights AUTO button clicked');
            window.addLogMessage('Lights AUTO button clicked', false, 'debug');
            makeRequest('/lights/set', 'POST', { mode: 'auto' }, window.addLogMessage, function(data) {
                console.log('Lights AUTO response:', data);
                updateLightsStateDisplay(data.lights_state || false, 'auto');
                window.addLogMessage('Red lights set to AUTO mode', false, 'action');
            }, function(error) {
                console.error('Lights AUTO request failed:', error);
                window.addLogMessage('Lights AUTO request failed: ' + error, false, 'error');
            });
        });
    }

    // Status polling to keep UI in sync
    function pollFanLightsStatus() {
        // Poll fan status
        fetch('/fan/status')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    updateFanStateDisplay(data.fan_state || false, data.fan_mode || 'manual');
                }
            })
            .catch(error => {
                console.error('Error polling fan status:', error);
            });
        
        // Poll lights status
        fetch('/lights/status')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    updateLightsStateDisplay(data.lights_state || false, data.lights_mode || 'manual');
                }
            })
            .catch(error => {
                console.error('Error polling lights status:', error);
            });
    }
    
    // Start status polling every 2 seconds
    setInterval(pollFanLightsStatus, 2000);
    
    // Initial status poll
    pollFanLightsStatus();

    // E-Stop button
    if (estopBtn) {
        estopBtn.addEventListener('click', function() {
            if (confirm('Are you sure you want to EMERGENCY STOP all outputs?')) {
                makeRequest('/estop', 'POST', null, window.addLogMessage, function(data) {
                    window.addLogMessage('EMERGENCY STOP triggered! All outputs stopped.', false, 'danger');
                });
            }
        });
    }
});