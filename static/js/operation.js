/**
 * Operation Page JavaScript
 * Handles aim (formerly fire), fire (formerly fiber), and index operations on the main operation page
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
    
    // Add servo test function for debugging
    window.testServoConnection = function() {
        console.log("Testing servo connection...");
        window.addLogMessage('Testing servo connection...', false, 'info');
        
        makeRequest(
            '/servo_status',
            'GET',
            null,
            console.log,
            function(data) {
                console.log("Servo status response:", data);
                window.addLogMessage(`Servo status: ${JSON.stringify(data)}`, false, 'info');
            },
            function(error) {
                console.error("Servo status error:", error);
                window.addLogMessage(`Servo status error: ${error.message}`, true);
            }
        );
    };
    
    // Add simple aim test function
    window.testAimCommand = function() {
        console.log("Testing aim command...");
        window.addLogMessage('Testing aim command (toggle mode)...', false, 'info');
        
        makeRequest(
            '/fire',
            'POST',
            { mode: 'toggle' },
            console.log,
            function(data) {
                console.log("Aim command response:", data);
                window.addLogMessage(`Aim test result: ${JSON.stringify(data)}`, false, 'info');
            },
            function(error) {
                console.error("Aim command error:", error);
                window.addLogMessage(`Aim test error: ${error.message}`, true);
            }
        );
    };
    
    // Add emergency reset function for testing
    window.resetAllStates = function() {
        console.log("Resetting all button states...");
        window.addLogMessage('Resetting all button states...', false, 'info');
        
        // Reset all local states
        operationInProgress = false;
        momentaryFireActive = false;
        momentaryFiberActive = false;
        fireToggleActive = false;
        fireFiberToggleActive = false;
        
        // Reset all buttons
        if (fireButton) {
            fireButton.innerHTML = '<i class="fas fa-crosshairs"></i> AIM';
            fireButton.classList.remove('active');
            fireButton.disabled = false;
        }
        
        if (fireFiberButton) {
            fireFiberButton.innerHTML = '<i class="fas fa-fire-alt"></i> FIRE';
            fireFiberButton.classList.remove('active');
            fireFiberButton.disabled = false;
        }
        
        if (fireToggleButton) {
            fireToggleButton.classList.remove('active');
            fireToggleButton.innerHTML = '<i class="fas fa-crosshairs"></i> AIM';
            fireToggleButton.disabled = false;
        }
        
        if (fireFiberToggleButton) {
            fireFiberToggleButton.classList.remove('active');
            fireFiberToggleButton.innerHTML = '<i class="fas fa-fire-alt"></i> FIRE';
            fireFiberToggleButton.disabled = false;
        }
        
        resetFiringStatus();
        
        window.addLogMessage('All states reset locally', false, 'success');
    };
    
    // Initialize servo test on page load
    console.log("Adding servo test function to window - call window.testServoConnection() in console");
    
    // Add initialization log message
    window.addLogMessage('Operation controls initialized', false, 'info');
    
    // Test servo connection on startup - DISABLED due to table control interference
    // setTimeout(() => {
    //     console.log("Testing servo connection on startup...");
    //     window.testServoConnection();
    // }, 2000); // Wait 2 seconds for page to fully load

    /**
     * Makes a standardized AJAX request with consistent error handling
     * Use the global makeRequest function from utility.js
     */
    const makeRequest = window.makeRequest || function(url, method = 'GET', data = null, onSuccess = null, onError = null, onFinally = null) {
        console.log(`[OPERATION.JS] makeRequest called:`, { url, method, data });
        
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
                console.log(`[OPERATION.JS] Response:`, { url, status: response.status, ok: response.ok });
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                console.log(`[OPERATION.JS] Response data:`, { url, data });
                if (typeof onSuccess === 'function') {
                    onSuccess(data);
                }
                return data;
            })
            .catch(error => {
                console.error(`[OPERATION.JS] Request failed:`, { url, error: error.message });
                window.addLogMessage(`Request to ${url} failed: ${error.message}`, true);
                
                if (typeof onError === 'function') {
                    onError(error);
                } else {
                    // Default error handling - reset operation state
                    operationInProgress = false;
                }
                throw error; // Re-throw to maintain error chain
            })
            .finally(() => {
                if (typeof onFinally === 'function') {
                    onFinally();
                }
            });
    };
    
    /**
     * Set button disabled state with proper error handling
     * @param {boolean} enabled - Whether buttons should be enabled
     * @param {...HTMLElement} buttons - The buttons to modify
     */
    const setButtonState = function(enabled, ...buttons) {
        console.log(`setButtonState called: enabled=${enabled}, button count=${buttons.length}`);
        buttons.forEach((button, index) => {
            if (button && typeof button === 'object' && button.tagName) {
                const wasDisabled = button.disabled;
                button.disabled = !enabled;
                console.log(`Button ${index} (${button.id || 'no-id'}): disabled ${wasDisabled} -> ${button.disabled}`);
            } else {
                console.warn(`Button ${index} is null, undefined, or not a DOM element:`, button);
            }
        });
    };
    
    // Fire and Fiber buttons
    const fireButton = document.getElementById('fire-button');
    const fireFiberButton = document.getElementById('fire-fiber-button');
    
    // Index buttons
    const indexButton = document.getElementById('index-button');
    const indexBackButton = document.getElementById('index-back-button');
    
    // Home and stop cleaning head buttons
    const homeCleaningHeadButton = document.getElementById('home-cleaning-head');
    const goToZeroCleaningHeadButton = document.getElementById('go-to-zero-cleaning-head');
    const stopCleaningHeadButton = document.getElementById('stop-cleaning-head');
    
    // Table control buttons
    const runTableButton = document.getElementById('run-table-button');
    const stopTableButton = document.getElementById('stop-table-button');
    
    // Auto-cycle switch
    const autoCycleEnableSwitch = document.getElementById('auto-cycle-enable-switch');
    
    // Auto-cycle visual indicators
    const autoCycleStatus = document.getElementById('auto-cycle-status');
    const autoCycleProgress = document.getElementById('auto-cycle-progress');
    const autoCycleCount = document.getElementById('auto-cycle-count');
    
    // State tracking variables
    let momentaryFireActive = false;
    let momentaryFiberActive = false;
    let fireToggleActive = false;
    let fireFiberToggleActive = false;
    
    // Operation lock to prevent race conditions
    let operationInProgress = false;
    
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
    
    // Firing timer variables
    let firingTimerActive = false;
    let firingStartTime = 0;
    let currentFiringTime = 0;
    let firingTimerInterval = null;
    
    /**
     * Format time in milliseconds to HH:MM:SS
     * @param {number} timeMs - Time in milliseconds
     * @returns {string} Formatted time string (HH:MM:SS)
     */
    function formatTime(timeMs) {
        const totalSeconds = Math.floor(timeMs / 1000);
        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const seconds = totalSeconds % 60;
        
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
    
    /**
     * Update firing timer display while actively firing
     */
    function updateFiringTimer() {
        if (firingTimerActive) {
            const currentTime = Date.now();
            currentFiringTime = currentTime - firingStartTime;
            const formattedTime = formatTime(currentFiringTime);
            
            if (firingTimeDisplay) {
                firingTimeDisplay.textContent = formattedTime;
            }
            
            // Update progress bar if it exists
            if (firingProgress) {
                // Limit progress bar to 100% after 5 minutes (300000ms)
                const progressPercent = Math.min(100, (currentFiringTime / 300000) * 100);
                firingProgress.style.width = `${progressPercent}%`;
            }
        }
    }
    
    /**
     * Start the firing timer and update UI elements
     * @param {number} elapsedMs - Optional elapsed time in milliseconds to start from
     */
    function startFiringTimer(elapsedMs = 0) {
        console.log(`Starting firing timer... (elapsed: ${elapsedMs}ms)`);
        firingTimerActive = true;
        firingStartTime = Date.now() - elapsedMs; // Adjust start time to account for elapsed time
        
        // Start the timer interval
        firingTimerInterval = setInterval(updateFiringTimer, 100);
        
        // Update display immediately to show correct time
        updateFiringTimer();
    }
    
    /**
     * Stop the firing timer and reset displays
     */
    function stopFiringTimer() {
        if (firingTimerActive) {
            console.log('Stopping firing timer...');
            firingTimerActive = false;
            clearInterval(firingTimerInterval);
            
            // Reset the timer display
            if (firingTimeDisplay) {
                firingTimeDisplay.textContent = '00:00:00';
            }
            
            // Reset progress bar
            if (firingProgress) {
                firingProgress.style.width = '0%';
            }
        }
    }
    
    /**
     * Disables all fire buttons
     */
    function disableFireButtons() {
        setButtonState(false, fireButton, fireToggleButton, fireFiberButton, fireFiberToggleButton);
    }
    
    /**
     * Enables all fire buttons
     */
    function enableFireButtons() {
        setButtonState(true, fireButton, fireToggleButton, fireFiberButton, fireFiberToggleButton);
    }
    
    /**
     * Sets firing status to inactive/not firing and manages button states
     */
    function resetFiringStatus() {
        updateFiringStatus('Not Firing', 'badge bg-secondary');
        stopFiringTimer(); // Stop the timer when resetting firing status
    }
    
    // Stop button functionality removed as requested
    
    // Momentary Fire button (proper mousedown/mouseup behavior)
    if (fireButton) {
        console.log("Fire button found and event listener attached");
        
        // Use mousedown for immediate response
        fireButton.addEventListener('mousedown', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            if (momentaryFireActive || operationInProgress) {
                console.log("Fire already active or operation in progress, ignoring mousedown");
                return;
            }
            
            // Start momentary firing immediately
            console.log("Aim button (momentary) mousedown - starting");
            window.addLogMessage('AIMING (momentary) - Moving servo to position B...', false, 'action');
            
            operationInProgress = true;
            momentaryFireActive = true;
            fireButton.innerHTML = '<span style="color: orange;">●</span> AIMING - HOLD BUTTON';
            fireButton.classList.add('active');
            updateFiringStatus('Aiming (Momentary)', 'badge bg-warning text-dark');
            startFiringTimer(); // Start the firing timer
            
            makeRequest(
                '/fire',
                'POST',
                { mode: 'momentary' },
                console.log,
                function(data) {
                    console.log("Momentary fire success:", data);
                    if (data.status === 'success') {
                        window.addLogMessage('Momentary aiming started - release button to stop', false, 'success');
                    } else {
                        window.addLogMessage(`Error initiating aiming: ${data.message}`, true);
                        // Reset on error
                        momentaryFireActive = false;
                        fireButton.innerHTML = '<i class="fas fa-crosshairs"></i> AIM';
                        fireButton.classList.remove('active');
                        resetFiringStatus();
                    }
                    operationInProgress = false;
                },
                function(error) {
                    console.error("Momentary aim error:", error);
                    window.addLogMessage(`Error in momentary aim operation: ${error.message}`, true);
                    // Reset on error
                    momentaryFireActive = false;
                    fireButton.innerHTML = '<i class="fas fa-crosshairs"></i> AIM';
                    fireButton.classList.remove('active');
                    resetFiringStatus();
                    operationInProgress = false;
                }
            );
        });
        
        // Use mouseup for release response
        fireButton.addEventListener('mouseup', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            if (!momentaryFireActive) {
                console.log("Fire not active, ignoring mouseup");
                return;
            }
            
            // Stop momentary firing on release
            console.log("Aim button (momentary) mouseup - stopping");
            window.addLogMessage('STOPPING AIM - Moving servo to position A...', false, 'action');
            
            operationInProgress = true;
            
            makeRequest(
                '/stop_firing',
                'POST',
                null,
                console.log,
                function(data) {
                    console.log("Stop firing success:", data);
                    if (data.status === 'success') {
                        window.addLogMessage('Momentary aiming stopped', false, 'success');
                        resetFiringStatus();
                    } else {
                        window.addLogMessage(`Error stopping aiming: ${data.message}`, true);
                    }
                    // Always reset after stop attempt
                    momentaryFireActive = false;
                    fireButton.innerHTML = '<i class="fas fa-crosshairs"></i> AIM';
                    fireButton.classList.remove('active');
                    operationInProgress = false;
                    
                    // Reset table button states to prevent interference
                    if (typeof window.resetTableButtonStates === 'function') {
                        window.resetTableButtonStates();
                    }
                },
                function(error) {
                    console.error("Stop firing error:", error);
                    window.addLogMessage(`Error stopping momentary fire: ${error.message}`, true);
                    // Always reset after stop attempt
                    momentaryFireActive = false;
                    fireButton.innerHTML = '<i class="fas fa-crosshairs"></i> AIM';
                    fireButton.classList.remove('active');
                    resetFiringStatus();
                    operationInProgress = false;
                }
            );
        });
        
        // Handle mouseleave to ensure stop if user drags off button
        fireButton.addEventListener('mouseleave', function(e) {
            if (momentaryFireActive) {
                console.log("Fire button mouseleave - stopping");
                fireButton.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
            }
        });
    }
    
    // Toggle Fire button (fixed implementation with timeout)
    if (fireToggleButton && !fireToggleButton.hasAttribute('data-listener-attached')) {
        console.log("Fire toggle button found - attaching event listener");
        fireToggleButton.setAttribute('data-listener-attached', 'true');
        
        fireToggleButton.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            // Prevent race conditions
            if (operationInProgress) {
                console.log("Operation already in progress, ignoring click");
                window.addLogMessage('Operation in progress, please wait...', false, 'warning');
                return;
            }
            
            console.log("Fire toggle button clicked, current state:", fireToggleActive);
            
            // Set operation lock
            operationInProgress = true;
            
            // Disable button during processing
            fireToggleButton.disabled = true;
            const originalText = fireToggleButton.innerHTML;
            fireToggleButton.innerHTML = 'PROCESSING...';
            
            // Set a timeout to prevent permanent "PROCESSING" state
            const timeoutId = setTimeout(() => {
                console.error("Fire toggle request timed out");
                window.addLogMessage('Fire toggle request timed out - resetting', true);
                fireToggleButton.disabled = false;
                fireToggleButton.innerHTML = originalText;
                operationInProgress = false;
                
                // Reset table button states to prevent interference
                if (typeof window.resetTableButtonStates === 'function') {
                    window.resetTableButtonStates();
                }
                
                // Try to reset servo state
                window.addLogMessage('Attempting to reset servo state after timeout...', false, 'warning');
                makeRequest('/estop', 'POST', null, console.log,
                    function(data) {
                        window.addLogMessage('Servo state reset after timeout', false, 'success');
                    },
                    function(error) {
                        window.addLogMessage('Failed to reset servo state: ' + error.message, true);
                    }
                );
            }, 5000); // 5 second timeout
            
            makeRequest(
                '/fire',
                'POST',
                { mode: 'toggle' },
                console.log,
                function(data) {
                    clearTimeout(timeoutId);
                    console.log("Toggle fire response:", data);
                    if (data.status === 'success') {
                        // Update toggle state based on server response
                        if (data.toggle_state === 'active') {
                            fireToggleActive = true;
                            fireToggleButton.classList.add('active');
                            fireToggleButton.innerHTML = '<i class="fas fa-stop"></i> STOP AIM';
                            updateFiringStatus('Aiming (Toggle)', 'badge bg-warning text-dark');
                            startFiringTimer(); // Start the firing timer
                            window.addLogMessage('Aim toggle activated - servo at position B', false, 'success');
                        } else if (data.toggle_state === 'inactive') {
                            fireToggleActive = false;
                            fireToggleButton.classList.remove('active');
                            fireToggleButton.innerHTML = '<i class="fas fa-crosshairs"></i> AIM';
                            resetFiringStatus();
                            window.addLogMessage('Aim toggle deactivated - servo at position A', false, 'success');
                        } else {
                            console.warn("Unknown toggle_state:", data.toggle_state);
                            window.addLogMessage(`Fire toggle: ${data.message}`, false, 'info');
                            fireToggleButton.innerHTML = originalText;
                        }
                    } else {
                        console.error("Toggle fire error:", data);
                        window.addLogMessage(`Error with toggle firing: ${data.message}`, true);
                        fireToggleButton.innerHTML = originalText;
                    }
                    
                    // Reset table button states to prevent interference
                    if (typeof window.resetTableButtonStates === 'function') {
                        window.resetTableButtonStates();
                    }
                    
                    // Re-enable button and clear operation lock
                    fireToggleButton.disabled = false;
                    operationInProgress = false;
                    
                    // Poll status after fire operation to ensure consistency
                    setTimeout(() => pollStatusOnDemand('after fire toggle'), 300);
                },
                function(error) {
                    clearTimeout(timeoutId);
                    console.error("Toggle fire network error:", error);
                    window.addLogMessage(`Error in fire toggle operation: ${error.message}`, true);
                    
                    // Reset table button states to prevent interference
                    if (typeof window.resetTableButtonStates === 'function') {
                        window.resetTableButtonStates();
                    }
                    
                    // Re-enable button, restore text, and clear operation lock
                    fireToggleButton.disabled = false;
                    fireToggleButton.innerHTML = originalText;
                    operationInProgress = false;
                }
            );
        });
    } else {
        console.warn("Fire toggle button not found in DOM");
    }
    
    // Fire Fiber button (proper mousedown/mouseup behavior)
    if (fireFiberButton) {
        console.log("Fiber fire button found and event listener attached");
        
        // Use mousedown for immediate response
        fireFiberButton.addEventListener('mousedown', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            if (momentaryFiberActive) return; // Prevent double activation
            
            // Start fiber momentary firing immediately
            console.log("Fire button mousedown - starting");
            window.addLogMessage('Starting FIRE sequence (momentary A→B→A→B)...', false, 'action');
            
            momentaryFiberActive = true;
            fireFiberButton.innerHTML = '<span style="color: red;">●</span> FIRE - HOLD BUTTON';
            fireFiberButton.classList.add('active');
            updateFiringStatus('Fire Sequence (Momentary)', 'badge bg-danger');
            startFiringTimer(); // Start the firing timer
            
            makeRequest(
                '/fire_fiber',
                'POST',
                { mode: 'momentary' },
                console.log,
                function(data) {
                    if (data.status === 'success') {
                        window.addLogMessage('Fire momentary sequence started - release button to stop', false, 'success');
                    } else {
                        window.addLogMessage(`Error starting fire sequence: ${data.message}`, true);
                        // Reset on error
                        momentaryFiberActive = false;
                        fireFiberButton.innerHTML = '<i class="fas fa-fire-alt"></i> FIRE';
                        fireFiberButton.classList.remove('active');
                        resetFiringStatus();
                    }
                },
                function(error) {
                    window.addLogMessage('Error in fire momentary operation', true);
                    // Reset on error
                    momentaryFiberActive = false;
                    fireFiberButton.innerHTML = '<i class="fas fa-fire-alt"></i> FIRE';
                    fireFiberButton.classList.remove('active');
                    resetFiringStatus();
                }
            );
        });
        
        // Use mouseup for release response
        fireFiberButton.addEventListener('mouseup', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            if (!momentaryFiberActive) return; // Already stopped
            
            // Stop fiber momentary firing on release
            console.log("Fire button mouseup - stopping");
            window.addLogMessage('STOPPING FIRE - Moving servo to position A...', false, 'action');
            
            makeRequest(
                '/stop_firing',
                'POST',
                null,
                console.log,
                function(data) {
                    if (data.status === 'success') {
                        window.addLogMessage('Fire momentary sequence stopped', false, 'success');
                        resetFiringStatus();
                    } else {
                        window.addLogMessage(`Error stopping fire sequence: ${data.message}`, true);
                    }
                    // Always reset after stop attempt
                    momentaryFiberActive = false;
                    fireFiberButton.innerHTML = '<i class="fas fa-fire-alt"></i> FIRE';
                    fireFiberButton.classList.remove('active');
                },
                function(error) {
                    window.addLogMessage('Error stopping fire momentary', true);
                    // Always reset after stop attempt
                    momentaryFiberActive = false;
                    fireFiberButton.innerHTML = '<i class="fas fa-fire-alt"></i> FIRE';
                    fireFiberButton.classList.remove('active');
                    resetFiringStatus();
                }
            );
        });
        
        // Handle mouseleave to ensure stop if user drags off button
        fireFiberButton.addEventListener('mouseleave', function(e) {
            if (momentaryFiberActive) {
                console.log("Fire button mouseleave - stopping");
                fireFiberButton.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
            }
        });
    }
    
    // Fire Fiber Toggle button (fixed implementation)
    if (fireFiberToggleButton && !fireFiberToggleButton.hasAttribute('data-listener-attached')) {
        console.log("Fiber fire toggle button found - attaching event listener");
        fireFiberToggleButton.setAttribute('data-listener-attached', 'true');
        
        fireFiberToggleButton.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            // Prevent race conditions
            if (operationInProgress) {
                console.log("Operation already in progress, ignoring click");
                return;
            }
            
            console.log("Fiber fire toggle button clicked, current state:", fireFiberToggleActive);
            
            // Set operation lock
            operationInProgress = true;
            
            // Disable button during processing
            fireFiberToggleButton.disabled = true;
            const originalText = fireFiberToggleButton.innerHTML;
            fireFiberToggleButton.innerHTML = 'PROCESSING...';
            
            // Set a timeout to prevent permanent "PROCESSING" state
            const timeoutId = setTimeout(() => {
                console.error("Fiber toggle request timed out");
                window.addLogMessage('Fiber toggle request timed out - resetting', true);
                fireFiberToggleButton.disabled = false;
                fireFiberToggleButton.innerHTML = originalText;
                operationInProgress = false;
                
                // Try to reset servo state
                window.addLogMessage('Attempting to reset servo state after timeout...', false, 'warning');
                makeRequest('/estop', 'POST', null, console.log,
                    function(data) {
                        window.addLogMessage('Servo state reset after timeout', false, 'success');
                    },
                    function(error) {
                        window.addLogMessage('Failed to reset servo state: ' + error.message, true);
                    }
                );
            }, 5000); // 5 second timeout
            
            makeRequest(
                '/fire_fiber',
                'POST',
                { mode: 'toggle' },
                console.log,
                function(data) {
                    clearTimeout(timeoutId);
                    console.log("Toggle fiber response:", data);
                    if (data.status === 'success') {
                        // Update toggle state based on server response
                        if (data.toggle_state === 'active') {
                            fireFiberToggleActive = true;
                            fireFiberToggleButton.classList.add('active');
                            fireFiberToggleButton.innerHTML = '<i class="fas fa-stop"></i> STOP FIRE';
                            updateFiringStatus('Fire Sequence (Toggle)', 'badge bg-danger');
                            startFiringTimer(); // Start the firing timer when toggle is activated
                            window.addLogMessage('Fire toggle activated - sequence: A→B→A→B complete, servo at position B', false, 'success');
                        } else if (data.toggle_state === 'inactive') {
                            fireFiberToggleActive = false;
                            fireFiberToggleButton.classList.remove('active');
                            fireFiberToggleButton.innerHTML = '<i class="fas fa-fire-alt"></i> FIRE';
                            resetFiringStatus(); // This already calls stopFiringTimer()
                            window.addLogMessage('Fire toggle deactivated - servo at position A', false, 'success');
                        } else {
                            console.warn("Unknown fiber toggle_state:", data.toggle_state);
                            window.addLogMessage(`Fiber toggle: ${data.message}`, false, 'info');
                            fireFiberToggleButton.innerHTML = originalText;
                        }
                    } else {
                        console.error("Toggle fiber error:", data);
                        window.addLogMessage(`Error with fiber toggle: ${data.message}`, true);
                        fireFiberToggleButton.innerHTML = originalText;
                    }
                    
                    // Re-enable button and clear operation lock
                    fireFiberToggleButton.disabled = false;
                    operationInProgress = false;
                    
                    // Poll status after fiber operation to ensure consistency
                    setTimeout(() => pollStatusOnDemand('after fiber toggle'), 300);
                },
                function(error) {
                    clearTimeout(timeoutId);
                    console.error("Toggle fiber network error:", error);
                    window.addLogMessage('Error in fiber toggle operation', true);
                    
                    // Re-enable button, restore text, and clear operation lock
                    fireFiberToggleButton.disabled = false;
                    fireFiberToggleButton.innerHTML = originalText;
                    operationInProgress = false;
                }
            );
        });
    } else {
        console.warn("Fiber fire toggle button not found in DOM");
    }
    
    // Track cleaning head movement state
    let cleaningHeadBusy = false;
    
    /**
     * Disables all cleaning head control buttons except the stop button
     */
    function disableCleaningHeadButtons() {
        setButtonState(false, indexButton, indexBackButton, homeCleaningHeadButton, goToZeroCleaningHeadButton);
        cleaningHeadBusy = true;
    }
    
    /**
     * Enables all cleaning head control buttons
     */
    function enableCleaningHeadButtons() {
        setButtonState(true, indexButton, indexBackButton, homeCleaningHeadButton, goToZeroCleaningHeadButton);
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
                console.log,
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
                console.log,
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
                console.log,
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
    
    // GO to 0 Cleaning Head button
    if (goToZeroCleaningHeadButton) {
        console.log("GO to 0 cleaning head button listener attached");
        goToZeroCleaningHeadButton.addEventListener('click', function() {
            // Don't allow multiple operations at once
            if (cleaningHeadBusy) {
                window.addLogMessage('Cannot go to 0: cleaning head is busy. Stop current operation first.', true);
                return;
            }
            
            window.addLogMessage('Moving cleaning head to position 0...', false, 'action');
            
            // Disable all cleaning head buttons
            disableCleaningHeadButtons();
            
            makeRequest(
                '/go_to_zero',
                'POST',
                null,
                console.log,
                function(data) {
                    if (data.status === 'success') {
                        updateCleaningHeadPosition(0);
                        window.addLogMessage('Cleaning head moved to position 0 successfully', false, 'success');
                    } else {
                        window.addLogMessage(`Error moving to position 0: ${data.message}`, true);
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
                console.log,
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
        console.log(`setButtonState called: enabled=${false}, button count=2`);
        
        if (runTableButton) {
            runTableButton.disabled = true;
            runTableButton.classList.remove('btn-primary');
            runTableButton.classList.add('active');  // Remove btn-success, just use active
            runTableButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> RUNNING...';
        }
        
        if (stopTableButton) {
            stopTableButton.disabled = false;
            stopTableButton.classList.remove('btn-secondary');
            stopTableButton.classList.add('btn-danger');
        }
        
        // Show status indicators if auto-cycle is enabled
        if (autoCycleStatus && window.AutoCycleManager && window.AutoCycleManager.isEnabled()) {
            autoCycleStatus.style.display = 'block';
        }
    }
    
    /**
     * Enables the run table button and disables the stop table button
     */
    function enableRunTableButton() {
        console.log(`setButtonState called: enabled=${true}, button count=2`);
        
        if (runTableButton) {
            runTableButton.disabled = false;
            runTableButton.classList.remove('active');  // Remove btn-success reference since we're not using it
            runTableButton.classList.add('btn-primary');
            runTableButton.innerHTML = '<i class="fas fa-play-circle me-2"></i> RUN TABLE';
        }
        
        if (stopTableButton) {
            stopTableButton.disabled = true;
            stopTableButton.classList.remove('btn-danger');
            stopTableButton.classList.add('btn-secondary');
        }
        
        // Only hide status indicators if auto-cycle is not enabled
        if (autoCycleStatus && window.AutoCycleManager && !window.AutoCycleManager.isEnabled()) {
            autoCycleStatus.style.display = 'none';
        }
        
        // Reset progress
        if (autoCycleProgress) {
            autoCycleProgress.style.width = '0%';
        }
    }
    
    /**
     * Update auto-cycle progress and count
     */
    function updateAutoCycleStatus(cycleCount = 0, progress = 0) {
        if (autoCycleCount) {
            autoCycleCount.textContent = cycleCount;
        }
        
        if (autoCycleProgress) {
            autoCycleProgress.style.width = progress + '%';
        }
    }
    
    // Run Table button  
    if (runTableButton) {
        runTableButton.addEventListener('click', function() {
            window.addLogMessage('Starting auto-cycle table sequence...', false, 'action');
            
            // Check if button is disabled (should not execute if disabled)
            if (runTableButton.disabled) {
                console.log('Run table button is disabled - ignoring click');
                return;
            }
            
            disableRunTableButton();
            
            // Use AutoCycleManager if available
            if (window.AutoCycleManager) {
                // Check if auto-cycle switch is enabled before starting
                const switchChecked = autoCycleEnableSwitch ? autoCycleEnableSwitch.checked : false;
                
                console.log('Run button clicked - Switch checked:', switchChecked);
                
                if (switchChecked) {
                    try {
                        // Start the auto-cycle (don't change enabled state)
                        window.AutoCycleManager.start();
                        
                        // Set up callbacks for progress and cycle count updates
                        window.AutoCycleManager.onProgressChange = function(progress) {
                            updateAutoCycleStatus(window.AutoCycleManager.cycleCount, progress);
                        };
                        
                        window.AutoCycleManager.onCycleCountChange = function(count) {
                            updateAutoCycleStatus(count, 0);
                        };
                        
                        window.AutoCycleManager.onStateChange = function() {
                            if (!window.AutoCycleManager.isRunning()) {
                                enableRunTableButton();
                                // Clear callbacks when stopped
                                window.AutoCycleManager.onProgressChange = null;
                                window.AutoCycleManager.onCycleCountChange = null;
                                window.AutoCycleManager.onStateChange = null;
                            }
                        };
                        
                        window.addLogMessage('Auto-cycle started successfully', false, 'success');
                    } catch (error) {
                        console.error('Error starting auto-cycle:', error);
                        window.addLogMessage('Error starting auto-cycle: ' + error.message, true);
                        enableRunTableButton();
                    }
                } else {
                    // Auto-cycle not enabled - inform user and re-enable button
                    window.addLogMessage('Auto-cycle is not enabled. Please enable auto-cycle switch first.', true);
                    enableRunTableButton();
                }
            } else {
                // Fallback to manual forward movement if AutoCycleManager not available
                console.warn('AutoCycleManager not available - using manual forward movement');
                makeRequest(
                    '/table/forward',
                    'POST',
                    { state: true },
                    window.addLogMessage,
                    function(data) {
                        if (data.status !== 'success') {
                            window.addLogMessage(`Error starting table: ${data.message || 'Unknown error'}`, true);
                            enableRunTableButton();
                        }
                    },
                    function(error) {
                        console.error('Error starting table movement:', error);
                        enableRunTableButton();
                    }
                );
            }
        });
    }
    
    // Stop Table button
    if (stopTableButton) {
        stopTableButton.addEventListener('click', function() {
            console.log('Stop Table button clicked (operation page)');
            
            // Check if button is disabled (should not execute if disabled)
            if (stopTableButton.disabled) {
                console.log('Stop table button is disabled - ignoring click');
                return;
            }
            
            window.addLogMessage('Stopping table and auto-cycle...', false, 'action');
            
            // Stop auto cycle if running
            if (window.AutoCycleManager) {
                try {
                    // Only stop the cycle, don't disable the auto-cycle feature
                    window.AutoCycleManager.stop();
                    
                    // Clear the callbacks
                    window.AutoCycleManager.onProgressChange = null;
                    window.AutoCycleManager.onCycleCountChange = null;
                    window.AutoCycleManager.onStateChange = null;
                    
                    // Reset cycle counter display
                    updateAutoCycleStatus(0, 0);
                    
                    // DO NOT disable auto-cycle or change switch state
                    // The switch should remain in its current state for future starts
                    
                    console.log('AutoCycleManager stopped successfully (auto-cycle still enabled)');
                } catch (error) {
                    console.error('Error stopping AutoCycleManager:', error);
                }
            }
            
            // Stop all table movement (same as table_control.js)
            makeRequest('/table/forward', 'POST', { state: false }, window.addLogMessage, 
                function(data) {
                    console.log('Table forward movement stopped');
                }, 
                function(error) {
                    console.error('Error stopping table forward movement:', error);
                }
            );
            makeRequest('/table/backward', 'POST', { state: false }, window.addLogMessage, 
                function(data) {
                    console.log('Table backward movement stopped');
                }, 
                function(error) {
                    console.error('Error stopping table backward movement:', error);
                }
            );
            
            window.addLogMessage('Table and auto-cycle stopped', false, 'success');
            enableRunTableButton();
        });
    }
    
    // Helper to update fan/lights state display with mode support
    function updateFanStateDisplay(state, mode = 'manual') {
        console.log(`updateFanStateDisplay called with state: ${state}, mode: ${mode}`);
        
        // Store previous values to prevent unnecessary flickering
        const prevDisplayText = fanStateDisplay ? fanStateDisplay.textContent : '';
        const prevClassName = fanStateDisplay ? fanStateDisplay.className : '';
        
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
            
            // Only update if the values have actually changed
            if (displayText !== prevDisplayText || badgeClass !== prevClassName) {
                fanStateDisplay.textContent = displayText;
                fanStateDisplay.className = badgeClass;
                console.log(`Fan display updated from "${prevDisplayText}" to "${displayText}"`);
            }
        }
        
        // Update fan icon color
        const fanIcon = document.querySelector('#fan-status-icon i');
        if (fanIcon) {
            const prevIconClass = fanIcon.className;
            let newClass;
            
            if (mode === 'auto') {
                newClass = state ? 'fas fa-fan fa-2x text-info' : 'fas fa-fan fa-2x text-secondary';
            } else {
                newClass = state ? 'fas fa-fan fa-2x text-success' : 'fas fa-fan fa-2x text-secondary';
            }
            
            // Only update if the class has actually changed
            if (newClass !== prevIconClass) {
                console.log(`Setting fan icon class from "${prevIconClass}" to "${newClass}"`);
                fanIcon.className = newClass;
            }
        }
        
        // Update button states based on mode and state
        if (mode === 'auto') {
            updateFanButtonStates('auto');
        } else {
            updateFanButtonStates(state ? 'on' : 'off');
        }
    }
    
    function updateLightsStateDisplay(state, mode = 'manual') {
        console.log(`updateLightsStateDisplay called with state: ${state}, mode: ${mode}`);
        
        // Store previous values to prevent unnecessary flickering
        const prevDisplayText = lightsStateDisplay ? lightsStateDisplay.textContent : '';
        const prevClassName = lightsStateDisplay ? lightsStateDisplay.className : '';
        
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
            
            // Only update if the values have actually changed
            if (displayText !== prevDisplayText || badgeClass !== prevClassName) {
                lightsStateDisplay.textContent = displayText;
                lightsStateDisplay.className = badgeClass;
                console.log(`Lights display updated from "${prevDisplayText}" to "${displayText}"`);
            }
        }
        
        // Update lights icon color
        const lightsIcon = document.querySelector('#lights-status-icon i');
        if (lightsIcon) {
            const prevIconClass = lightsIcon.className;
            let newClass;
            
            if (mode === 'auto') {
                newClass = state ? 'fas fa-lightbulb fa-2x text-info' : 'fas fa-lightbulb fa-2x text-secondary';
            } else {
                newClass = state ? 'fas fa-lightbulb fa-2x text-success' : 'fas fa-lightbulb fa-2x text-secondary';
            }
            
            // Only update if the class has actually changed
            if (newClass !== prevIconClass) {
                console.log(`Setting lights icon class from "${prevIconClass}" to "${newClass}"`);
                lightsIcon.className = newClass;
            }
        }
        
        // Update button states based on mode and state
        if (mode === 'auto') {
            updateLightButtonStates('auto');
        } else {
            updateLightButtonStates(state ? 'on' : 'off');
        }
    }
    
    function updateTableStateDisplay(tableData) {
        console.log('updateTableStateDisplay called with data:', tableData);
        
        // Update table forward status
        const tableForwardStatus = document.getElementById('table-forward-status');
        const tableForwardIcon = document.querySelector('#table-forward-icon i');
        console.log('Table forward elements found:', { status: !!tableForwardStatus, icon: !!tableForwardIcon });
        if (tableForwardStatus && tableForwardIcon) {
            if (tableData.table_moving_forward) {
                console.log('Setting table forward to MOVING/warning');
                tableForwardStatus.textContent = 'MOVING';
                tableForwardStatus.className = 'badge bg-warning';
                tableForwardIcon.className = 'fas fa-arrow-right fa-2x text-warning';
            } else {
                console.log('Setting table forward to OFF/secondary');
                tableForwardStatus.textContent = 'OFF';
                tableForwardStatus.className = 'badge bg-secondary';
                tableForwardIcon.className = 'fas fa-arrow-right fa-2x text-secondary';
            }
        }
        
        // Update table backward status
        const tableBackwardStatus = document.getElementById('table-backward-status');
        const tableBackwardIcon = document.querySelector('#table-backward-icon i');
        console.log('Table backward elements found:', { status: !!tableBackwardStatus, icon: !!tableBackwardIcon });
        if (tableBackwardStatus && tableBackwardIcon) {
            if (tableData.table_moving_backward) {
                console.log('Setting table backward to MOVING/warning');
                tableBackwardStatus.textContent = 'MOVING';
                tableBackwardStatus.className = 'badge bg-warning';
                tableBackwardIcon.className = 'fas fa-arrow-left fa-2x text-warning';
            } else {
                console.log('Setting table backward to OFF/secondary');
                tableBackwardStatus.textContent = 'OFF';
                tableBackwardStatus.className = 'badge bg-secondary';
                tableBackwardIcon.className = 'fas fa-arrow-left fa-2x text-secondary';
            }
        }
        
        // Update front limit status
        const tableFrontLimitStatus = document.getElementById('table-front-limit-status');
        const tableFrontLimitIcon = document.querySelector('#table-front-limit-icon i');
        console.log('Table front limit elements found:', { status: !!tableFrontLimitStatus, icon: !!tableFrontLimitIcon });
        if (tableFrontLimitStatus && tableFrontLimitIcon) {
            if (tableData.table_at_front_limit) {
                console.log('Setting front limit to ACTIVE/danger');
                tableFrontLimitStatus.textContent = 'ACTIVE';
                tableFrontLimitStatus.className = 'badge bg-danger';
                tableFrontLimitIcon.className = 'fas fa-stop-circle fa-2x text-danger';
            } else {
                console.log('Setting front limit to Not Active/secondary');
                tableFrontLimitStatus.textContent = 'Not Active';
                tableFrontLimitStatus.className = 'badge bg-secondary';
                tableFrontLimitIcon.className = 'fas fa-stop-circle fa-2x text-secondary';
            }
        }
        
        // Update back limit status
        const tableBackLimitStatus = document.getElementById('table-back-limit-status');
        const tableBackLimitIcon = document.querySelector('#table-back-limit-icon i');
        console.log('Table back limit elements found:', { status: !!tableBackLimitStatus, icon: !!tableBackLimitIcon });
        if (tableBackLimitStatus && tableBackLimitIcon) {
            if (tableData.table_at_back_limit) {
                console.log('Setting back limit to ACTIVE/danger');
                tableBackLimitStatus.textContent = 'ACTIVE';
                tableBackLimitStatus.className = 'badge bg-danger';
                tableBackLimitIcon.className = 'fas fa-stop-circle fa-2x text-danger';
            } else {
                console.log('Setting back limit to Not Active/secondary');
                tableBackLimitStatus.textContent = 'Not Active';
                tableBackLimitStatus.className = 'badge bg-secondary';
                tableBackLimitIcon.className = 'fas fa-stop-circle fa-2x text-secondary';
            }
        }
    }

    // Fan ON/OFF/AUTO
    if (fanOnBtn) {
        console.log('Adding click listener to Fan ON button');
        fanOnBtn.addEventListener('click', function() {
            console.log('Fan ON button clicked!');
            window.addLogMessage('Fan ON button clicked', false, 'debug');
            
            makeRequest('/fan/set', 'POST', { state: true, mode: 'manual' }, 
                console.log,
                function(data) {
                    console.log('Fan ON response:', data);
                    updateFanStateDisplay(data.fan_state !== undefined ? data.fan_state : true, 'manual');
                    window.addLogMessage('Fan turned ON (manual)', false, 'action');
                    updateFanButtonStates('on');
                    
                    // Poll status immediately after action to ensure UI consistency
                    setTimeout(() => pollStatusOnDemand('after fan ON'), 200);
                }, function(error) {
                    console.error('Fan ON request failed:', error);
                    window.addLogMessage('Fan ON failed: ' + error.message, true);
                });
        });
    } else {
        console.error('Fan ON button not found - cannot add click listener');
    }
    if (fanOffBtn) {
        console.log('Adding click listener to Fan OFF button');
        fanOffBtn.addEventListener('click', function() {
            console.log('Fan OFF button clicked!');
            window.addLogMessage('Fan OFF button clicked', false, 'debug');
            
            makeRequest('/fan/set', 'POST', { state: false, mode: 'manual' }, 
                console.log, 
                function(data) {
                    console.log('Fan OFF response:', data);
                    updateFanStateDisplay(data.fan_state !== undefined ? data.fan_state : false, 'manual');
                    window.addLogMessage('Fan turned OFF (manual)', false, 'action');
                    updateFanButtonStates('off');
                    
                    // Poll status immediately after action to ensure UI consistency
                    setTimeout(() => pollStatusOnDemand('after fan OFF'), 200);
                }, function(error) {
                    console.error('Fan OFF request failed:', error);
                    window.addLogMessage('Fan OFF failed: ' + error.message, true);
                });
        });
    } else {
        console.error('Fan OFF button not found - cannot add click listener');
    }
    if (fanAutoBtn) {
        console.log('Adding click listener to Fan AUTO button');
        fanAutoBtn.addEventListener('click', function() {
            console.log('Fan AUTO button clicked!');
            window.addLogMessage('Fan AUTO button clicked', false, 'debug');
            
            makeRequest('/fan/set', 'POST', { mode: 'auto' }, 
                console.log, 
                function(data) {
                    console.log('Fan AUTO response:', data);
                    updateFanStateDisplay(data.fan_state || false, 'auto');
                    window.addLogMessage('Fan set to AUTO mode', false, 'action');
                    updateFanButtonStates('auto');
                }, function(error) {
                    console.error('Fan AUTO request failed:', error);
                    window.addLogMessage('Fan AUTO failed: ' + error.message, true);
                });
        });
    } else {
        console.error('Fan AUTO button not found - cannot add click listener');
    }

    // Lights ON/OFF/AUTO
    if (lightsOnBtn) {
        console.log('Adding click listener to Lights ON button');
        lightsOnBtn.addEventListener('click', function() {
            console.log('Lights ON button clicked!');
            window.addLogMessage('Lights ON button clicked', false, 'debug');
            
            makeRequest('/lights/set', 'POST', { state: true, mode: 'manual' }, 
                console.log, 
                function(data) {
                    console.log('Lights ON response:', data);
                    updateLightsStateDisplay(data.lights_state !== undefined ? data.lights_state : true, 'manual');
                    window.addLogMessage('Red lights turned ON (manual)', false, 'action');
                    updateLightButtonStates('on');
                    
                    // Poll status immediately after action to ensure UI consistency
                    setTimeout(() => pollStatusOnDemand('after lights ON'), 200);
                }, function(error) {
                    console.error('Lights ON request failed:', error);
                    window.addLogMessage('Lights ON failed: ' + error.message, true);
                });
        });
    } else {
        console.error('Lights ON button not found - cannot add click listener');
    }
    if (lightsOffBtn) {
        console.log('Adding click listener to Lights OFF button');
        lightsOffBtn.addEventListener('click', function() {
            console.log('Lights OFF button clicked!');
            window.addLogMessage('Lights OFF button clicked', false, 'debug');
            
            makeRequest('/lights/set', 'POST', { state: false, mode: 'manual' }, 
                console.log, 
                function(data) {
                    console.log('Lights OFF response:', data);
                    updateLightsStateDisplay(data.lights_state !== undefined ? data.lights_state : false, 'manual');
                    window.addLogMessage('Red lights turned OFF (manual)', false, 'action');
                    updateLightButtonStates('off');
                    
                    // Poll status immediately after action to ensure UI consistency
                    setTimeout(() => pollStatusOnDemand('after lights OFF'), 200);
                }, function(error) {
                    console.error('Lights OFF request failed:', error);
                    window.addLogMessage('Lights OFF failed: ' + error.message, true);
                });
        });
    } else {
        console.error('Lights OFF button not found - cannot add click listener');
    }
    if (lightsAutoBtn) {
        console.log('Adding click listener to Lights AUTO button');
        lightsAutoBtn.addEventListener('click', function() {
            console.log('Lights AUTO button clicked!');
            window.addLogMessage('Lights AUTO button clicked', false, 'debug');
            
            makeRequest('/lights/set', 'POST', { mode: 'auto' }, 
                console.log, 
                function(data) {
                    console.log('Lights AUTO response:', data);
                    updateLightsStateDisplay(data.lights_state || false, 'auto');
                    window.addLogMessage('Red lights set to AUTO mode', false, 'action');
                    updateLightButtonStates('auto');
                }, function(error) {
                    console.error('Lights AUTO request failed:', error);
                    window.addLogMessage('Lights AUTO failed: ' + error.message, true);
                });
        });
    } else {
        console.error('Lights AUTO button not found - cannot add click listener');
    }

    // E-Stop button
    if (estopBtn) {
        estopBtn.addEventListener('click', function() {
            showEmergencyStopDialog();
        });
    }
    
    /**
     * Show enhanced E-Stop confirmation dialog with timeout
     */
    function showEmergencyStopDialog() {
        // Get timeout from server configuration
        fetch('/api/config/timing')
            .then(response => response.json())
            .then(config => {
                const timeoutMs = config.estop_confirmation_timeout || 5000;
                createEstopDialog(timeoutMs);
            })
            .catch(error => {
                console.warn('Failed to get E-Stop timeout config, using default:', error);
                createEstopDialog(5000); // Default 5 seconds
            });
    }
    
    /**
     * Create the E-Stop dialog with specified timeout
     */
    function createEstopDialog(timeoutMs) {
        // Create modal backdrop
        const backdrop = document.createElement('div');
        backdrop.className = 'estop-modal-backdrop';
        backdrop.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
            backdrop-filter: blur(3px);
        `;
        
        // Create modal dialog
        const modal = document.createElement('div');
        modal.className = 'estop-modal';
        modal.style.cssText = `
            background: #fff;
            border-radius: 15px;
            padding: 30px;
            max-width: 500px;
            width: 90%;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
            text-align: center;
            border: 3px solid #dc3545;
        `;
        
        let countdown = Math.ceil(timeoutMs / 1000);
        
        // Create dialog content
        modal.innerHTML = `
            <div style="margin-bottom: 25px;">
                <i class="fas fa-exclamation-triangle" style="font-size: 48px; color: #dc3545; margin-bottom: 15px;"></i>
                <h3 style="color: #dc3545; margin: 0 0 10px 0; font-weight: bold;">EMERGENCY STOP</h3>
                <p style="font-size: 16px; margin: 0 0 10px 0; color: #333;">This will immediately stop all outputs!</p>
                <div id="estop-countdown" style="font-size: 14px; color: #666;">Auto-confirm in <span id="countdown-timer">${countdown}</span> seconds</div>
            </div>
            <div style="display: flex; gap: 20px; justify-content: center;">
                <button id="estop-yes-btn" style="
                    background: #dc3545;
                    color: white;
                    border: none;
                    border-radius: 10px;
                    padding: 20px 40px;
                    font-size: 24px;
                    font-weight: bold;
                    cursor: pointer;
                    min-width: 150px;
                    box-shadow: 0 4px 8px rgba(220, 53, 69, 0.3);
                    transition: all 0.2s;
                " onmouseover="this.style.background='#c82333'" onmouseout="this.style.background='#dc3545'">
                    <i class="fas fa-stop-circle" style="margin-right: 10px;"></i>YES
                </button>
                <button id="estop-no-btn" style="
                    background: #6c757d;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 12px 20px;
                    font-size: 16px;
                    cursor: pointer;
                    min-width: 80px;
                    transition: all 0.2s;
                " onmouseover="this.style.background='#5a6268'" onmouseout="this.style.background='#6c757d'">
                    NO
                </button>
            </div>
        `;
        
        backdrop.appendChild(modal);
        document.body.appendChild(backdrop);
        
        // Focus on YES button for accessibility
        const yesBtn = document.getElementById('estop-yes-btn');
        const noBtn = document.getElementById('estop-no-btn');
        const countdownDisplay = document.getElementById('countdown-timer');
        
        yesBtn.focus();
        
        // Countdown timer
        const countdownInterval = setInterval(() => {
            countdown--;
            if (countdownDisplay) {
                countdownDisplay.textContent = countdown;
            }
            
            if (countdown <= 0) {
                clearInterval(countdownInterval);
                executeEmergencyStop();
                document.body.removeChild(backdrop);
            }
        }, 1000);
        
        // Execute E-Stop function
        function executeEmergencyStop() {
            makeRequest('/estop', 'POST', null, window.addLogMessage, 
                function(data) {
                    window.addLogMessage('EMERGENCY STOP triggered! All outputs stopped.', false, 'danger');
                    // Update UI to reflect stopped state
                    updateUIAfterEstop();
                }
            );
        }
        
        // Button event handlers
        yesBtn.addEventListener('click', () => {
            clearInterval(countdownInterval);
            executeEmergencyStop();
            document.body.removeChild(backdrop);
        });
        
        noBtn.addEventListener('click', () => {
            clearInterval(countdownInterval);
            document.body.removeChild(backdrop);
        });
        
        // Close on Escape key
        const escapeHandler = (e) => {
            if (e.key === 'Escape') {
                clearInterval(countdownInterval);
                document.body.removeChild(backdrop);
                document.removeEventListener('keydown', escapeHandler);
            }
        };
        document.addEventListener('keydown', escapeHandler);
        
        // Close on backdrop click
        backdrop.addEventListener('click', (e) => {
            if (e.target === backdrop) {
                clearInterval(countdownInterval);
                document.body.removeChild(backdrop);
            }
        });
    }
    
    /**
     * Update UI after E-Stop to reflect stopped state
     */
    function updateUIAfterEstop() {
        // Update fan buttons
        if (fanOnBtn) fanOnBtn.classList.remove('active');
        if (fanAutoBtn) fanAutoBtn.classList.remove('active');
        if (fanOffBtn) fanOffBtn.classList.add('active');
        if (fanStateDisplay) fanStateDisplay.textContent = 'Off';
        
        // Update lights buttons
        if (lightsOnBtn) lightsOnBtn.classList.remove('active');
        if (lightsAutoBtn) lightsAutoBtn.classList.remove('active');
        if (lightsOffBtn) lightsOffBtn.classList.add('active');
        if (lightsStateDisplay) lightsStateDisplay.textContent = 'Off';
        
        // Update table buttons
        if (runTableButton) {
            runTableButton.disabled = false;
            runTableButton.textContent = 'RUN TABLE';
        }
        if (stopTableButton) {
            stopTableButton.disabled = true;
        }
        
        // Stop any running auto-cycle
        if (window.AutoCycleManager && window.AutoCycleManager.isRunning()) {
            window.AutoCycleManager.stop();
        }
        
        console.log('UI updated after E-Stop');
    }

    // Auto-cycle enable switch
    if (autoCycleEnableSwitch) {
        console.log('Adding change listener to auto-cycle enable switch (operation page)');
        
        autoCycleEnableSwitch.addEventListener('change', function() {
            console.log('Auto-cycle enable switch changed to:', this.checked);
            
            if (window.AutoCycleManager) {
                try {
                    window.AutoCycleManager.setEnabled(this.checked);
                    window.addLogMessage(`Auto cycle ${this.checked ? 'enabled' : 'disabled'}`, false, 'info');
                    console.log('AutoCycleManager state updated to:', this.checked);
                } catch (error) {
                    console.error('Error updating AutoCycleManager state:', error);
                    window.addLogMessage('Error updating auto-cycle state: ' + error.message, true);
                }
            } else {
                console.warn('AutoCycleManager not available');
                window.addLogMessage('Auto-cycle manager not available', true);
            }
        });
    } else {
        console.warn('Auto-cycle enable switch not found (operation page)');
    }

    // Tri-state button management functions
    function updateFanButtonStates(activeMode) {
        console.log(`updateFanButtonStates called with activeMode: ${activeMode}`);
        console.log('Fan buttons found:', { fanOnBtn: !!fanOnBtn, fanOffBtn: !!fanOffBtn, fanAutoBtn: !!fanAutoBtn });
        
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
        
        // Force a visual update by triggering a reflow
        if (fanOnBtn) fanOnBtn.offsetHeight;
        if (fanOffBtn) fanOffBtn.offsetHeight;
        if (fanAutoBtn) fanAutoBtn.offsetHeight;
    }

    function updateLightButtonStates(activeMode) {
        console.log(`updateLightButtonStates called with activeMode: ${activeMode}`);
        console.log('Light buttons found:', { lightsOnBtn: !!lightsOnBtn, lightsOffBtn: !!lightsOffBtn, lightsAutoBtn: !!lightsAutoBtn });
        
        [lightsOnBtn, lightsOffBtn, lightsAutoBtn].forEach(btn => {
            if (btn) {
                btn.classList.remove('active');
                console.log(`Removed active class from light button: ${btn.id}`);
            }
        });
        
        if (activeMode === 'on' && lightsOnBtn) {
            lightsOnBtn.classList.add('active');
            console.log('Added active class to light ON button');
        } else if (activeMode === 'off' && lightsOffBtn) {
            lightsOffBtn.classList.add('active');
            console.log('Added active class to light OFF button');
        } else if (activeMode === 'auto' && lightsAutoBtn) {
            lightsAutoBtn.classList.add('active');
            console.log('Added active class to light AUTO button');
        }
        
        // Force a visual update by triggering a reflow
        if (lightsOnBtn) lightsOnBtn.offsetHeight;
        if (lightsOffBtn) lightsOffBtn.offsetHeight;
        if (lightsAutoBtn) lightsAutoBtn.offsetHeight;
    }
    
    // Status polling to keep UI in sync
    let pollingInProgress = false;
    
    // Function to poll status on-demand (replaces constant polling)
    function pollStatusOnDemand(reason = 'on-demand') {
        console.log(`Polling status on-demand: ${reason}`);
        
        // Poll fan status
        makeRequest('/fan/status', 'GET', null, window.addLogMessage, 
            function(data) {
                if (data && typeof data.fan_state !== 'undefined') {
                    updateFanStateDisplay(data.fan_state, data.fan_mode || 'manual');
                }
            }, 
            function(error) {
                console.warn('Failed to poll fan status on-demand:', error);
            }
        );
        
        // Poll lights status  
        makeRequest('/lights/status', 'GET', null, window.addLogMessage, 
            function(data) {
                if (data && typeof data.lights_state !== 'undefined') {
                    updateLightsStateDisplay(data.lights_state, data.lights_mode || 'manual');
                }
            }, 
            function(error) {
                console.warn('Failed to poll lights status on-demand:', error);
            }
        );
        
        // Poll table status (if needed for UI updates)
        makeRequest('/table/status', 'GET', null, window.addLogMessage, 
            function(data) {
                if (data && data.status === 'success') {
                    updateTableStateDisplay(data);
                }
            }, 
            function(error) {
                console.warn('Failed to poll table status on-demand:', error);
            }
        );
    }

    function pollFanLightsStatus() {
        // Prevent overlapping polls that can cause flickering
        if (pollingInProgress) {
            console.log('Skipping poll - already in progress');
            return;
        }
        
        pollingInProgress = true;
        const startTime = performance.now();
        console.log('Starting status poll cycle...');
        
        let pollsCompleted = 0;
        const totalPolls = 3;
        
        function markPollComplete() {
            pollsCompleted++;
            if (pollsCompleted >= totalPolls) {
                pollingInProgress = false;
                const totalTime = performance.now() - startTime;
                console.log(`Status poll cycle completed in ${totalTime.toFixed(1)}ms`);
            }
        }
        
        // Poll fan status
        makeRequest('/fan/status', 'GET', null, window.addLogMessage, 
            function(data) {
                const fanTime = performance.now() - startTime;
                if (data && typeof data.fan_state !== 'undefined') {
                    console.log(`Fan status poll response (${fanTime.toFixed(1)}ms):`, data);
                    updateFanStateDisplay(data.fan_state, data.fan_mode || 'manual');
                }
                markPollComplete();
            }, 
            function(error) {
                console.error('Failed to poll fan status:', error);
                markPollComplete();
            }
        );
        
        // Poll lights status  
        makeRequest('/lights/status', 'GET', null, window.addLogMessage, 
            function(data) {
                const lightsTime = performance.now() - startTime;
                if (data && typeof data.lights_state !== 'undefined') {
                    console.log(`Lights status poll response (${lightsTime.toFixed(1)}ms):`, data);
                    updateLightsStateDisplay(data.lights_state, data.lights_mode || 'manual');
                }
                markPollComplete();
            }, 
            function(error) {
                console.error('Failed to poll lights status:', error);
                markPollComplete();
            }
        );
        
        // Poll table status
        makeRequest('/table/status', 'GET', null, window.addLogMessage, 
            function(data) {
                const tableTime = performance.now() - startTime;
                if (data && data.status === 'success') {
                    console.log(`Table status poll response (${tableTime.toFixed(1)}ms):`, data);
                    updateTableStateDisplay(data);
                }
                markPollComplete();
            }, 
            function(error) {
                console.error('Failed to poll table status:', error);
                markPollComplete();
            }
        );
    }
    
    // Function to check and sync servo toggle states with server
    function checkAndSyncServoState() {
        console.log('Checking current servo toggle states and table status...');
        
        makeRequest('/servo_status', 'GET', null, console.log,
            function(data) {
                if (data && data.status === 'success') {
                    console.log('Server response:', data);
                    
                    // Sync servo toggle states
                    if (data.toggle_states) {
                        const states = data.toggle_states;
                        console.log('Server servo states:', states);
                        console.log(`Current UI states - Fire: ${fireToggleActive}, Fiber: ${fireFiberToggleActive}, Timer: ${firingTimerActive}`);
                        
                        // Sync fiber toggle state
                        if (states.fiber_toggle_active !== fireFiberToggleActive) {
                            console.log(`Syncing fiber toggle: ${fireFiberToggleActive} -> ${states.fiber_toggle_active}`);
                            fireFiberToggleActive = states.fiber_toggle_active;
                            
                            if (fireFiberToggleButton) {
                                if (fireFiberToggleActive) {
                                    fireFiberToggleButton.classList.remove('btn-outline-warning');
                                    fireFiberToggleButton.classList.add('active', 'btn-warning');
                                    fireFiberToggleButton.innerHTML = '<i class="fas fa-stop"></i> STOP FIBER';
                                    
                                    // Restore firing timer if actively firing
                                    if (states.is_firing && !firingTimerActive) {
                                        console.log('Restoring firing timer for fiber');
                                        const elapsedMs = states.firing_duration_ms || 0;
                                        startFiringTimer(elapsedMs); // Pass elapsed time to restore timer
                                        updateFiringStatus('Fiber Sequence (Toggle)', 'badge bg-warning text-dark');
                                    }
                                } else {
                                    fireFiberToggleButton.classList.remove('active', 'btn-warning');
                                    fireFiberToggleButton.classList.add('btn-outline-warning');
                                    fireFiberToggleButton.innerHTML = '<i class="fas fa-bolt"></i> FIBER';
                                    
                                    // Stop firing timer if not actively firing
                                    if (!states.is_firing && firingTimerActive) {
                                        resetFiringStatus();
                                    }
                                }
                            }
                            
                            window.addLogMessage(`Synced fiber toggle state: ${fireFiberToggleActive ? 'active' : 'inactive'}`, false, 'info');
                        }
                        
                        // Sync regular fire toggle state  
                        if (states.fire_toggle_active !== fireToggleActive) {
                            console.log(`Syncing fire toggle: ${fireToggleActive} -> ${states.fire_toggle_active}`);
                            fireToggleActive = states.fire_toggle_active;
                            
                            if (fireToggleButton) {
                                if (fireToggleActive) {
                                    fireToggleButton.classList.remove('btn-danger');
                                    fireToggleButton.classList.add('active', 'btn-warning');
                                    fireToggleButton.innerHTML = '<i class="fas fa-stop"></i> STOP FIRE';
                                    
                                    // Restore firing timer if actively firing
                                    if (states.is_firing && !firingTimerActive) {
                                        console.log('Restoring firing timer for fire');
                                        const elapsedMs = states.firing_duration_ms || 0;
                                        startFiringTimer(elapsedMs); // Pass elapsed time to restore timer
                                        updateFiringStatus('Firing (Toggle)', 'badge bg-danger');
                                    }
                                } else {
                                    fireToggleButton.classList.remove('active', 'btn-warning');
                                    fireToggleButton.classList.add('btn-danger');
                                    fireToggleButton.innerHTML = '<i class="fas fa-fire-alt"></i> FIRE';
                                    
                                    // Stop firing timer if not actively firing
                                    if (!states.is_firing && firingTimerActive) {
                                        resetFiringStatus();
                                    }
                                }
                            }
                            
                            window.addLogMessage(`Synced fire toggle state: ${fireToggleActive ? 'active' : 'inactive'}`, false, 'info');
                        }
                        
                        // Handle case where neither toggle is active but server is still firing (cleanup)
                        if (!states.fire_toggle_active && !states.fiber_toggle_active && states.is_firing) {
                            console.log('Warning: Server reports firing but no toggles active - this may indicate a state inconsistency');
                            window.addLogMessage('State inconsistency detected - server firing without active toggles', false, 'warning');
                        }
                    }
                    
                    // Sync table and auto cycle states
                    if (data.table_states) {
                        const tableStates = data.table_states;
                        console.log('Server table states:', tableStates);
                        
                        // Sync auto cycle switch state - but don't override user actions
                        if (autoCycleEnableSwitch && typeof tableStates.auto_cycle_enabled !== 'undefined') {
                            const serverAutoCycleEnabled = tableStates.auto_cycle_enabled;
                            const currentSwitchState = autoCycleEnableSwitch.checked;
                            
                            // Always prioritize localStorage state over server state for auto-cycle
                            // BUT if server shows auto-cycle is running, enable the switch
                            if (window.AutoCycleManager) {
                                const localStorageState = window.AutoCycleManager.isEnabled();
                                const serverAutoCycleRunning = tableStates.auto_cycle_running;
                                const serverTableRunning = tableStates.table_running || tableStates.auto_cycle_running;
                                
                                // If server shows auto-cycle is actually running, enable the switch regardless of localStorage
                                let targetSwitchState = localStorageState;
                                if (serverAutoCycleRunning) {
                                    targetSwitchState = true;
                                    // Update localStorage to match reality
                                    window.AutoCycleManager.setEnabled(true);
                                } else if (serverTableRunning && !localStorageState) {
                                    // Table is running but auto-cycle is disabled in localStorage
                                    // This means table was started manually, keep switch as disabled
                                    targetSwitchState = false;
                                }
                                
                                // Update switch to match target state if they differ
                                if (targetSwitchState !== currentSwitchState) {
                                    console.log(`Syncing auto cycle switch: ${currentSwitchState} -> ${targetSwitchState} (server auto-cycle running: ${serverAutoCycleRunning}, table running: ${serverTableRunning})`);
                                    autoCycleEnableSwitch.checked = targetSwitchState;
                                    
                                    // Force visual update
                                    if (targetSwitchState) {
                                        autoCycleEnableSwitch.setAttribute('checked', 'checked');
                                    } else {
                                        autoCycleEnableSwitch.removeAttribute('checked');
                                    }
                                    
                                    // Trigger change event to update AutoCycleManager
                                    setTimeout(() => {
                                        autoCycleEnableSwitch.dispatchEvent(new Event('change', { bubbles: true }));
                                    }, 50);
                                    
                                    window.addLogMessage(`Auto cycle switch restored: ${targetSwitchState ? 'enabled' : 'disabled'}`, false, 'info');
                                }
                                
                                // Show auto-cycle status if auto-cycle is enabled (toggle switch is on)
                                if (autoCycleStatus && targetSwitchState) {
                                    autoCycleStatus.style.display = 'block';
                                } else if (autoCycleStatus) {
                                    autoCycleStatus.style.display = 'none';
                                }
                            }
                        }
                        
                        // Sync run table button state
                        if (runTableButton && typeof tableStates.table_running !== 'undefined') {
                            const serverTableRunning = tableStates.table_running || tableStates.auto_cycle_running;
                            const currentButtonRunning = runTableButton.disabled; // disabled when running
                            
                            if (serverTableRunning !== currentButtonRunning) {
                                console.log(`Syncing run table button: running ${currentButtonRunning} -> ${serverTableRunning}`);
                                
                                if (serverTableRunning) {
                                    // Table is running - disable run button, show running state
                                    disableRunTableButton();
                                    window.addLogMessage('Restored table running state', false, 'info');
                                    
                                    // If auto cycle is running, update progress display
                                    if (tableStates.auto_cycle_running && window.AutoCycleManager) {
                                        // Restore auto cycle progress - prioritize AutoCycleManager's stored count
                                        const storedCycleCount = window.AutoCycleManager.cycleCount;
                                        const serverCycleCount = tableStates.cycle_count || 0;
                                        const serverProgress = tableStates.cycle_progress || 0;
                                        
                                        // Use the higher of stored vs server count (user might have done cycles offline)
                                        const actualCycleCount = Math.max(storedCycleCount, serverCycleCount);
                                        updateAutoCycleStatus(actualCycleCount, serverProgress);
                                        
                                        // Update AutoCycleManager if server has higher count
                                        if (serverCycleCount > storedCycleCount) {
                                            window.AutoCycleManager.cycleCount = serverCycleCount;
                                            window.AutoCycleManager.saveState('cycleCount', serverCycleCount);
                                        }
                                        
                                        // Restore AutoCycleManager running state
                                        if (!window.AutoCycleManager.isRunning()) {
                                            console.log('Restoring AutoCycleManager running state');
                                            try {
                                                // Note: This may need adjustment based on AutoCycleManager implementation
                                                window.AutoCycleManager._isRunning = true; // Direct state restore
                                                
                                                // Set up callbacks for continued operation
                                                window.AutoCycleManager.onProgressChange = function(progress) {
                                                    updateAutoCycleStatus(window.AutoCycleManager.cycleCount, progress);
                                                };
                                                
                                                window.AutoCycleManager.onCycleCountChange = function(count) {
                                                    updateAutoCycleStatus(count, 0);
                                                };
                                                
                                                window.AutoCycleManager.onStateChange = function() {
                                                    if (!window.AutoCycleManager.isRunning()) {
                                                        enableRunTableButton();
                                                        // Clear callbacks when stopped
                                                        window.AutoCycleManager.onProgressChange = null;
                                                        window.AutoCycleManager.onCycleCountChange = null;
                                                        window.AutoCycleManager.onStateChange = null;
                                                    }
                                                };
                                            } catch (autoError) {
                                                console.warn('Could not restore AutoCycleManager state:', autoError);
                                            }
                                        }
                                    }
                                } else {
                                    // Table is not running - enable run button, show ready state
                                    enableRunTableButton();
                                    window.addLogMessage('Restored table ready state', false, 'info');
                                }
                            }
                        }
                    }
                } else {
                    console.log('No states found or error in servo status');
                }
            },
            function(error) {
                console.warn('Could not fetch servo and table states:', error);
            }
        );
    }
    
    // Function to sync UI with current system state
    function syncUIWithSystemState() {
        console.log('Syncing UI with current system state...');
        
        // Sync servo toggle states first
        checkAndSyncServoState();
        
        // Sync auto-cycle switch if available
        if (window.AutoCycleManager) {
            const autoCycleSwitch = document.getElementById('auto-cycle-enable-switch');
            if (autoCycleSwitch) {
                // Get current state from manager first
                const currentState = window.AutoCycleManager.isEnabled();
                autoCycleSwitch.checked = currentState;
                console.log('Auto-cycle switch synced to:', currentState);
                
                // Force visual update by removing and re-adding checked attribute
                if (currentState) {
                    autoCycleSwitch.setAttribute('checked', 'checked');
                } else {
                    autoCycleSwitch.removeAttribute('checked');
                }
                
                // Also trigger a change event for any CSS that depends on it
                setTimeout(() => {
                    autoCycleSwitch.dispatchEvent(new Event('change', { bubbles: true }));
                }, 100);
                
                console.log('Auto cycle switch initialized to localStorage state:', currentState);
            }
            
            // Always restore the cycle count from localStorage, regardless of running state
            const storedCycleCount = window.AutoCycleManager.cycleCount;
            if (storedCycleCount > 0) {
                console.log('Restoring cycle count from localStorage:', storedCycleCount);
                updateAutoCycleStatus(storedCycleCount, 0);
                
                // Show progress indicators if auto-cycle is enabled
                if (window.AutoCycleManager.isEnabled() && autoCycleStatus) {
                    autoCycleStatus.style.display = 'block';
                }
            }
        }
        
        // Trigger initial status poll only once
        console.log('Performing initial status poll from syncUIWithSystemState');
        pollFanLightsStatus();
    }
    
    // Call sync function after a short delay to ensure all scripts and CSS are loaded
    setTimeout(function() {
        if (window.AutoCycleManager) {
            console.log('AutoCycleManager available, initial state:', {
                enabled: window.AutoCycleManager.isEnabled(),
                running: window.AutoCycleManager.isRunning(),
                cycleCount: window.AutoCycleManager.cycleCount
            });
            
            // Initialize auto-cycle switch to match localStorage state
            const autoCycleSwitch = document.getElementById('auto-cycle-enable-switch');
            if (autoCycleSwitch) {
                const localStorageState = window.AutoCycleManager.isEnabled();
                console.log(`Initializing auto-cycle switch to localStorage state: ${localStorageState}`);
                
                // Set the input state
                autoCycleSwitch.checked = localStorageState;
                
                // Force DOM attribute updates
                if (localStorageState) {
                    autoCycleSwitch.setAttribute('checked', 'checked');
                } else {
                    autoCycleSwitch.removeAttribute('checked');
                }
                
                // Add click handler for the slider
                const toggleSlider = autoCycleSwitch.parentElement.querySelector('.toggle-slider');
                if (toggleSlider) {
                    console.log('Adding click handler to toggle slider');
                    
                    toggleSlider.addEventListener('click', function(e) {
                        e.preventDefault();
                        console.log('Toggle slider clicked, current state:', autoCycleSwitch.checked);
                        autoCycleSwitch.checked = !autoCycleSwitch.checked;
                        
                        // Update checked attribute to trigger CSS changes
                        if (autoCycleSwitch.checked) {
                            autoCycleSwitch.setAttribute('checked', 'checked');
                        } else {
                            autoCycleSwitch.removeAttribute('checked');
                        }
                        
                        autoCycleSwitch.dispatchEvent(new Event('change', { bubbles: true }));
                        console.log('Toggle slider changed to:', autoCycleSwitch.checked);
                    });
                }
                
                // Force a visual update by triggering a change event
                setTimeout(() => {
                    autoCycleSwitch.dispatchEvent(new Event('change', { bubbles: true }));
                }, 100);
            }
        } else {
            console.warn('AutoCycleManager not available during initialization');
        }
        syncUIWithSystemState();
    }, 300);
    
    // Sync state when page becomes visible (user returns from another page)
    document.addEventListener('visibilitychange', function() {
        if (!document.hidden) {
            console.log('Page became visible - syncing state');
            setTimeout(checkAndSyncServoState, 100); // Small delay to ensure page is fully loaded
        }
    });
    
    // Periodic state sync every 15 seconds for critical states only (reduced frequency)
    setInterval(checkAndSyncServoState, 15000);
    
    // Remove constant fan/lights polling - now handled on-demand only
    // setInterval(pollFanLightsStatus, 3000); // REMOVED - causing UI sluggishness
    
    // Initial status check when page loads
    setTimeout(() => {
        pollFanLightsStatus(); // One-time initial poll
    }, 500);
});