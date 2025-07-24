// Get steps per mm conversion factor
function getStepsPerMm() {
    let stepsPerMm = 100; // Default value
    const stepsPerMmBadge = document.querySelector('.badge.bg-info');
    if (stepsPerMmBadge) {
        const badgeText = stepsPerMmBadge.textContent;
        const match = badgeText.match(/(\d+(?:\.\d+)?)\s+steps\s+per\s+mm/i);
        if (match && match[1]) {
            stepsPerMm = parseFloat(match[1]);
        }
    }
    return stepsPerMm;
}

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
    
    // Check if we have the handleSimulationResponse utility
    const handleSimulationResponse = ShopUtils.handleSimulationResponse || function(data, actionName) {
        if (!data.simulated) {
            // Real hardware values - clear any warnings
            clearSimulationWarnings();
            return false;
        }
        
        // For simulation mode, this is expected
        if (currentOperationMode === 'simulation') {
            addLogMessage(`${actionName} complete! (simulation mode)`, false, 'success');
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
    
    // Use the utility makeRequest function if available
    const makeRequest = ShopUtils.makeRequest || function(url, method, data, successCallback, errorCallback, finallyCallback) {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            }
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        return fetch(url, options)
            .then(response => response.json())
            .then(data => {
                if (typeof successCallback === 'function') {
                    successCallback(data);
                }
                return data;
            })
            .catch(error => {
                const errorMessage = error instanceof Error ? error.message : error;
                addLogMessage(`Error: ${errorMessage}`, true);
                
                if (typeof errorCallback === 'function') {
                    errorCallback(error);
                }
                
                throw error;
            })
            .finally(() => {
                if (typeof finallyCallback === 'function') {
                    finallyCallback();
                }
            });
    };

    /**
     * Updates the position display in the UI with the current position value
     * This includes updating numeric displays, mm conversion, and progress bar
     * 
     * @param {number} position - The current position in steps
     * @returns {void}
     * @throws {Error} If position is not a valid number
     */
    function updatePositionDisplay(position) {
        const positionDisplay = document.getElementById('position-display');
        const positionProgress = document.getElementById('position-progress');
        const positionDisplayMm = document.getElementById('position-display-mm');
        const stepsPerMm = getStepsPerMm();
        
        if (positionDisplay) {
            positionDisplay.textContent = position;
        }
        
        if (positionDisplayMm) {
            const positionMm = (position / stepsPerMm).toFixed(2);
            positionDisplayMm.textContent = positionMm;
        }
        
        if (positionProgress) {
            // Calculate percentage for progress bar (scale to MAX_POSITION)
            const MAX_POSITION = 1000;
            let percentage = (position / MAX_POSITION) * 100;
            
            // Ensure percentage is between 0 and 100
            percentage = Math.max(0, Math.min(100, percentage));
            
            positionProgress.style.width = `${percentage}%`;
            positionProgress.setAttribute('aria-valuenow', percentage);
        }
    }

    // Index Distance Update button
    const updateIndexDistanceBtn = document.getElementById('update-index-distance');
    const indexDistanceMmInput = document.getElementById('index-distance-mm');
    const indexDistanceStepsDisplay = document.getElementById('index-distance-steps-display');
    
    if (updateIndexDistanceBtn && indexDistanceMmInput) {
        updateIndexDistanceBtn.addEventListener('click', function() {
            const indexDistanceMm = parseFloat(indexDistanceMmInput.value);
            
            if (isNaN(indexDistanceMm) || indexDistanceMm <= 0) {
                addLogMessage('Please enter a valid index distance in millimeters.', true);
                return;
            }
            
            // Convert mm to steps
            const stepsPerMm = getStepsPerMm();
            const indexDistanceSteps = Math.round(indexDistanceMm * stepsPerMm);
            
            // Log the action
            addLogMessage(`Updating index distance to ${indexDistanceMm.toFixed(2)} mm...`, false, 'config');
            
            // Use makeRequest utility if available, otherwise use existing fetch
            if (typeof makeRequest === 'function') {
                makeRequest(
                    '/update_config',
                    'POST',
                    {
                        section: 'stepper',
                        key: 'index_distance',
                        value: indexDistanceSteps
                    },
                    function(data) {
                        if (data.status === 'success') {
                            addLogMessage(`Index distance updated to ${indexDistanceMm.toFixed(2)} mm (${indexDistanceSteps} steps).`, false, 'success');
                            
                            // Update the display
                            if (indexDistanceStepsDisplay) {
                                indexDistanceStepsDisplay.textContent = indexDistanceSteps;
                            }
                        } else {
                            addLogMessage('Error: ' + data.message, true);
                        }
                    }
                );
            } else {
                // Original implementation as fallback
                fetch('/update_config', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        section: 'stepper',
                        key: 'index_distance',
                        value: indexDistanceSteps
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        addLogMessage(`Index distance updated to ${indexDistanceMm.toFixed(2)} mm (${indexDistanceSteps} steps).`, false, 'success');
                        
                        // Update the display
                        if (indexDistanceStepsDisplay) {
                            indexDistanceStepsDisplay.textContent = indexDistanceSteps;
                        }
                    } else {
                        addLogMessage('Error: ' + data.message, true);
                    }
                })
                .catch(error => {
                    addLogMessage('Error: ' + error.message, true);
                });
            }
        });
    }

    // Index Forward button
    const indexButton = document.getElementById('index-button');
    
    if (indexButton) {
        indexButton.addEventListener('click', function() {
            addLogMessage('Indexing forward...', false, 'action');
            indexButton.disabled = true;
            clearSimulationWarnings();
            
            fetch('/index_move', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    direction: 'forward'
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const currentPosition = data.position;
                    updatePositionDisplay(currentPosition);
                    
                    // Handle simulation status based on mode
                    if (data.simulated) {
                        // For simulation mode, this is expected
                        if (currentOperationMode === 'simulation') {
                            addLogMessage('Index forward complete! (simulation mode)', false, 'success');
                        } 
                        // For prototype mode, this should NEVER happen
                        else if (currentOperationMode === 'prototype') {
                            addLogMessage('ERROR: Index forward simulation in PROTOTYPE MODE. Hardware is required!', true);
                            addSimulationError('HARDWARE ERROR: Receiving simulated values in PROTOTYPE MODE. Check your hardware connections.');
                        } 
                        // For normal mode, it's a warning
                        else {
                            addLogMessage('WARNING: Index forward simulated due to hardware error', false, 'warning');
                            addSimulationWarning('Hardware error detected - using simulation values');
                        }
                    } else {
                        // Real hardware values - clear any warnings
                        clearSimulationWarnings();
                        addLogMessage('Index forward complete!', false, 'success');
                    }
                } else {
                    addLogMessage('Error: ' + data.message, true);
                }
            })
            .catch(error => {
                addLogMessage('Error: ' + error.message, true);
            })
            .finally(() => {
                if (indexButton) indexButton.disabled = false;
            });
        });
    }
    
    // Index Backward button
    const indexBackButton = document.getElementById('index-back-button');
    
    if (indexBackButton) {
        indexBackButton.addEventListener('click', function() {
            addLogMessage('Indexing backward...', false, 'action');
            indexBackButton.disabled = true;
            clearSimulationWarnings();
            
            fetch('/index_move', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    direction: 'backward'
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const currentPosition = data.position;
                    updatePositionDisplay(currentPosition);
                    
                    // Handle simulation status based on mode
                    if (data.simulated) {
                        // For simulation mode, this is expected
                        if (currentOperationMode === 'simulation') {
                            addLogMessage('Index backward complete! (simulation mode)', false, 'success');
                        } 
                        // For prototype mode, this should NEVER happen
                        else if (currentOperationMode === 'prototype') {
                            addLogMessage('ERROR: Index backward simulation in PROTOTYPE MODE. Hardware is required!', true);
                            addSimulationError('HARDWARE ERROR: Receiving simulated values in PROTOTYPE MODE. Check your hardware connections.');
                        } 
                        // For normal mode, it's a warning
                        else {
                            addLogMessage('WARNING: Index backward simulated due to hardware error', false, 'warning');
                            addSimulationWarning('Hardware error detected - using simulation values');
                        }
                    } else {
                        // Real hardware values - clear any warnings
                        clearSimulationWarnings();
                        addLogMessage('Index backward complete!', false, 'success');
                    }
                } else {
                    addLogMessage('Error: ' + data.message, true);
                }
            })
            .catch(error => {
                addLogMessage('Error: ' + error.message, true);
            })
            .finally(() => {
                if (indexBackButton) indexBackButton.disabled = false;
            });
        });
    }
    
    // Home button
    const homeButton = document.getElementById('home-motor');
    
    if (homeButton) {
        homeButton.addEventListener('click', function() {
            addLogMessage('Homing cleaning head...', false, 'action');
            homeButton.disabled = true;
            clearSimulationWarnings();
            
            fetch('/home', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const currentPosition = data.position;
                    updatePositionDisplay(currentPosition);
                    
                    // Handle simulation status based on mode
                    if (data.simulated) {
                        // For simulation mode, this is expected
                        if (currentOperationMode === 'simulation') {
                            addLogMessage('Homing complete! (simulation mode)', false, 'success');
                        } 
                        // For prototype mode, this should NEVER happen
                        else if (currentOperationMode === 'prototype') {
                            addLogMessage('ERROR: Homing simulation in PROTOTYPE MODE. Hardware is required!', true);
                            addSimulationError('HARDWARE ERROR: Receiving simulated values in PROTOTYPE MODE. Check your hardware connections.');
                        } 
                        // For normal mode, it's a warning
                        else {
                            addLogMessage('WARNING: Homing simulated due to hardware error', false, 'warning');
                            addSimulationWarning('Hardware error detected - using simulation values');
                        }
                    } else {
                        // Real hardware values - clear any warnings
                        clearSimulationWarnings();
                        addLogMessage('Homing complete!', false, 'success');
                    }
                } else {
                    addLogMessage('Error: ' + data.message, true);
                }
            })
            .catch(error => {
                addLogMessage('Error: ' + error.message, true);
            })
            .finally(() => {
                if (homeButton) homeButton.disabled = false;
            });
        });
    }
    
    // Global jog interval variable for proper cleanup
    let jogInterval = null;
    let jogHoldTimer = null;
    let jogIsHolding = false;
    
    // Jog Forward button - Enhanced with hold-to-jog functionality
    const jogForwardButton = document.getElementById('jog-forward');
    
    if (jogForwardButton) {
        // Mouse events for hold-to-jog
        jogForwardButton.addEventListener('mousedown', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            console.log('Jog forward mousedown event');
            
            // Clear any existing timer
            if (jogHoldTimer) {
                clearTimeout(jogHoldTimer);
                jogHoldTimer = null;
            }
            
            jogIsHolding = false;
            
            // Start timer - if held for 150ms, start continuous jog (faster response)
            jogHoldTimer = setTimeout(() => {
                console.log('Jog timer fired, starting continuous jog');
                if (!jogIsHolding) { // Only start if not already holding
                    jogIsHolding = true;
                    startJogHold('forward', jogForwardButton);
                }
            }, 150);
        });
        
        jogForwardButton.addEventListener('mouseup', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            console.log('Jog forward mouseup event, jogIsHolding:', jogIsHolding);
            
            // Clear the hold timer
            if (jogHoldTimer) {
                clearTimeout(jogHoldTimer);
                jogHoldTimer = null;
                console.log('Cleared jog timer');
            }
            
            // If we were holding, stop the continuous jog
            if (jogIsHolding) {
                console.log('Stopping continuous jog');
                stopJogHold();
                jogIsHolding = false;
            }
        });
        
        jogForwardButton.addEventListener('mouseleave', function(e) {
            console.log('Jog forward mouseleave event, jogIsHolding:', jogIsHolding);
            
            // Clear timer and stop any continuous jog
            if (jogHoldTimer) {
                clearTimeout(jogHoldTimer);
                jogHoldTimer = null;
                console.log('Cleared jog timer on mouseleave');
            }
            if (jogIsHolding) {
                console.log('Stopping continuous jog on mouseleave');
                stopJogHold();
                jogIsHolding = false;
            }
        });
        
        // Touch events for mobile hold-to-jog
        jogForwardButton.addEventListener('touchstart', function(e) {
            e.preventDefault();
            jogIsHolding = false;
            
            // Start timer - faster response for touch
            jogHoldTimer = setTimeout(() => {
                jogIsHolding = true;
                startJogHold('forward', jogForwardButton);
            }, 150);
        });
        
        jogForwardButton.addEventListener('touchend', function(e) {
            e.preventDefault();
            
            if (jogHoldTimer) {
                clearTimeout(jogHoldTimer);
                jogHoldTimer = null;
            }
            
            if (jogIsHolding) {
                stopJogHold();
                jogIsHolding = false;
            }
            // Remove single-click functionality - only continuous jog on hold
        });
        
        jogForwardButton.addEventListener('touchcancel', function(e) {
            if (jogHoldTimer) {
                clearTimeout(jogHoldTimer);
                jogHoldTimer = null;
            }
            if (jogIsHolding) {
                stopJogHold();
                jogIsHolding = false;
            }
        });
    }
    
    // Helper function for single jog operation
    function performSingleJog(direction, stepSize, button) {
        addLogMessage(`Jogging ${direction} by ${stepSize} steps...`, false, 'action');
        button.disabled = true;
        clearSimulationWarnings();
        
        fetch('/jog', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                direction: direction,
                steps: stepSize
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                const currentPosition = data.position;
                updatePositionDisplay(currentPosition);
                
                // Handle simulation status based on mode
                if (data.simulated) {
                    // For simulation mode, this is expected
                    if (currentOperationMode === 'simulation') {
                        addLogMessage(`Jog ${direction} complete! (simulation mode)`, false, 'success');
                    } 
                    // For prototype mode, this should NEVER happen
                    else if (currentOperationMode === 'prototype') {
                        addLogMessage(`ERROR: Jog ${direction} simulation in PROTOTYPE MODE. Hardware is required!`, true);
                        addSimulationError('HARDWARE ERROR: Receiving simulated values in PROTOTYPE MODE. Check your hardware connections.');
                    } 
                    // For normal mode, it's a warning
                    else {
                        addLogMessage(`WARNING: Jog ${direction} simulated due to hardware error`, false, 'warning');
                        addSimulationWarning('Hardware error detected - using simulation values');
                    }
                } else {
                    // Real hardware values - clear any warnings
                    clearSimulationWarnings();
                    addLogMessage(`Jog ${direction} complete!`, false, 'success');
                }
            } else {
                addLogMessage('Error: ' + data.message, true);
            }
        })
        .catch(error => {
            addLogMessage('Error: ' + error.message, true);
        })
        .finally(() => {
            if (button) button.disabled = false;
        });
    }
    
    // Helper function to start continuous jogging
    function startJogHold(direction, button) {
        console.log('startJogHold called, direction:', direction, 'jogInterval exists:', !!jogInterval);
        
        if (jogInterval) return; // Already jogging
        
        // Get current step size from slider
        const stepSizeSlider = document.getElementById('step-size');
        const stepSize = stepSizeSlider ? parseInt(stepSizeSlider.value) : 10;
        
        console.log('Starting jog with step size:', stepSize);
        
        // Start immediately
        addLogMessage(`Starting continuous jog ${direction} with ${stepSize} steps...`, false, 'action');
        // Don't disable button here as it might trigger mouseleave
        clearSimulationWarnings();
        
        // Send continuous jog commands every 150ms for smooth movement
        jogInterval = setInterval(() => {
            console.log('Sending jog request:', direction, stepSize);
            fetch('/jog_continuous', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    direction: direction,
                    steps: stepSize
                })
            })
            .then(response => response.json())
            .then(data => {
                console.log('Jog response:', data);
                if (data.status === 'success') {
                    const currentPosition = data.position;
                    updatePositionDisplay(currentPosition);
                } else if (data.status === 'error') {
                    addLogMessage('Jog error: ' + data.message, true);
                    stopJogHold();
                }
            })
            .catch(error => {
                console.log('Jog fetch error:', error);
                addLogMessage('Jog error: ' + error.message, true);
                stopJogHold();
            });
        }, 100); // 100ms interval for smooth continuous movement
        
        console.log('Jog interval started with ID:', jogInterval);
    }
    
    // Helper function to stop continuous jogging
    function stopJogHold() {
        console.log('stopJogHold called, jogInterval exists:', !!jogInterval);
        
        if (jogInterval) {
            clearInterval(jogInterval);
            jogInterval = null;
            
            addLogMessage('Continuous jog stopped', false, 'info');
            console.log('Jog interval cleared');
        }
    }
    
    // Jog Backward button - Enhanced with hold-to-jog functionality
    const jogBackwardButton = document.getElementById('jog-backward');
    
    if (jogBackwardButton) {
        // Mouse events for hold-to-jog
        jogBackwardButton.addEventListener('mousedown', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            // Clear any existing timer
            if (jogHoldTimer) {
                clearTimeout(jogHoldTimer);
                jogHoldTimer = null;
            }
            
            jogIsHolding = false;
            
            // Start timer - if held for 150ms, start continuous jog (faster response)
            jogHoldTimer = setTimeout(() => {
                if (!jogIsHolding) { // Only start if not already holding
                    jogIsHolding = true;
                    startJogHold('backward', jogBackwardButton);
                }
            }, 150);
        });
        
        jogBackwardButton.addEventListener('mouseup', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            // Clear the hold timer
            if (jogHoldTimer) {
                clearTimeout(jogHoldTimer);
                jogHoldTimer = null;
            }
            
            // If we were holding, stop the continuous jog
            if (jogIsHolding) {
                stopJogHold();
                jogIsHolding = false;
            }
        });
        
        jogBackwardButton.addEventListener('mouseleave', function(e) {
            // Clear timer and stop any continuous jog
            if (jogHoldTimer) {
                clearTimeout(jogHoldTimer);
                jogHoldTimer = null;
            }
            if (jogIsHolding) {
                stopJogHold();
                jogIsHolding = false;
            }
        });
        
        // Touch events for mobile hold-to-jog
        jogBackwardButton.addEventListener('touchstart', function(e) {
            e.preventDefault();
            jogIsHolding = false;
            
            // Start timer - faster response for touch
            jogHoldTimer = setTimeout(() => {
                jogIsHolding = true;
                startJogHold('backward', jogBackwardButton);
            }, 150);
        });
        
        jogBackwardButton.addEventListener('touchend', function(e) {
            e.preventDefault();
            
            if (jogHoldTimer) {
                clearTimeout(jogHoldTimer);
                jogHoldTimer = null;
            }
            
            if (jogIsHolding) {
                stopJogHold();
                jogIsHolding = false;
            }
            // Remove single-click functionality - only continuous jog on hold
        });
        
        jogBackwardButton.addEventListener('touchcancel', function(e) {
            if (jogHoldTimer) {
                clearTimeout(jogHoldTimer);
                jogHoldTimer = null;
            }
            if (jogIsHolding) {
                stopJogHold();
                jogIsHolding = false;
            }
        });
    }
    
    // Absolute Position Move (mm)
    const moveToPositionMmButton = document.getElementById('move-to-position-mm');
    
    if (moveToPositionMmButton) {
        moveToPositionMmButton.addEventListener('click', function() {
            const positionMm = parseFloat(document.getElementById('absolute-position-mm').value || 0);
            
            if (isNaN(positionMm) || positionMm < 0) {
                addLogMessage('Please enter a valid position in millimeters.', true);
                return;
            }
            
            // Convert mm to steps
            const stepsPerMm = getStepsPerMm();
            const positionSteps = Math.round(positionMm * stepsPerMm);
            
            addLogMessage(`Moving to position ${positionMm.toFixed(2)} mm (${positionSteps} steps)...`, false, 'action');
            moveToPositionMmButton.disabled = true;
            clearSimulationWarnings();
            
            fetch('/move_to', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    position: positionSteps
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const currentPosition = data.position;
                    updatePositionDisplay(currentPosition);
                    
                    // Handle simulation status based on mode
                    if (data.simulated) {
                        // For simulation mode, this is expected
                        if (currentOperationMode === 'simulation') {
                            addLogMessage(`Move to ${positionMm.toFixed(2)} mm complete! (simulation mode)`, false, 'success');
                        } 
                        // For prototype mode, this should NEVER happen
                        else if (currentOperationMode === 'prototype') {
                            addLogMessage('ERROR: Move to position simulation in PROTOTYPE MODE. Hardware is required!', true);
                            addSimulationError('HARDWARE ERROR: Receiving simulated values in PROTOTYPE MODE. Check your hardware connections.');
                        } 
                        // For normal mode, it's a warning
                        else {
                            addLogMessage('WARNING: Move to position simulated due to hardware error', false, 'warning');
                            addSimulationWarning('Hardware error detected - using simulation values');
                        }
                    } else {
                        // Real hardware values - clear any warnings
                        clearSimulationWarnings();
                        addLogMessage(`Move to ${positionMm.toFixed(2)} mm complete!`, false, 'success');
                    }
                } else {
                    addLogMessage('Error: ' + data.message, true);
                }
            })
            .catch(error => {
                addLogMessage('Error: ' + error.message, true);
            })
            .finally(() => {
                if (moveToPositionMmButton) moveToPositionMmButton.disabled = false;
            });
        });
    }
    
    // Absolute Position Move (steps)
    const moveToPositionButton = document.getElementById('move-to-position');
    
    if (moveToPositionButton) {
        moveToPositionButton.addEventListener('click', function() {
            const position = parseInt(document.getElementById('absolute-position').value || 0);
            
            if (isNaN(position) || position < 0) {
                addLogMessage('Please enter a valid position in steps.', true);
                return;
            }
            
            addLogMessage(`Moving to position ${position} steps...`, false, 'action');
            moveToPositionButton.disabled = true;
            clearSimulationWarnings();
            
            fetch('/move_to', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    position: position
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const currentPosition = data.position;
                    updatePositionDisplay(currentPosition);
                    
                    // Handle simulation status based on mode
                    if (data.simulated) {
                        // For simulation mode, this is expected
                        if (currentOperationMode === 'simulation') {
                            addLogMessage(`Move to ${position} steps complete! (simulation mode)`, false, 'success');
                        } 
                        // For prototype mode, this should NEVER happen
                        else if (currentOperationMode === 'prototype') {
                            addLogMessage('ERROR: Move to position simulation in PROTOTYPE MODE. Hardware is required!', true);
                            addSimulationError('HARDWARE ERROR: Receiving simulated values in PROTOTYPE MODE. Check your hardware connections.');
                        } 
                        // For normal mode, it's a warning
                        else {
                            addLogMessage('WARNING: Move to position simulated due to hardware error', false, 'warning');
                            addSimulationWarning('Hardware error detected - using simulation values');
                        }
                    } else {
                        // Real hardware values - clear any warnings
                        clearSimulationWarnings();
                        addLogMessage(`Move to ${position} steps complete!`, false, 'success');
                    }
                } else {
                    addLogMessage('Error: ' + data.message, true);
                }
            })
            .catch(error => {
                addLogMessage('Error: ' + error.message, true);
            })
            .finally(() => {
                if (moveToPositionButton) moveToPositionButton.disabled = false;
            });
        });
    }
    
    // Speed control display updates and save functionality
    const jogSpeedInput = document.getElementById('jog-speed');
    const jogSpeedDisplay = document.getElementById('jog-speed-value');
    
    if (jogSpeedInput && jogSpeedDisplay) {
        jogSpeedInput.addEventListener('input', function() {
            jogSpeedDisplay.textContent = jogSpeedInput.value;
        });
        
        // Save on change (debounced)
        let jogSpeedTimer;
        jogSpeedInput.addEventListener('change', function() {
            clearTimeout(jogSpeedTimer);
            jogSpeedTimer = setTimeout(() => {
                saveSpeedSetting('jog_speed', jogSpeedInput.value);
            }, 500);
        });
    }
    
    const indexSpeedInput = document.getElementById('index-speed');
    const indexSpeedDisplay = document.getElementById('index-speed-value');
    
    if (indexSpeedInput && indexSpeedDisplay) {
        indexSpeedInput.addEventListener('input', function() {
            indexSpeedDisplay.textContent = indexSpeedInput.value;
        });
        
        // Save on change (debounced)
        let indexSpeedTimer;
        indexSpeedInput.addEventListener('change', function() {
            clearTimeout(indexSpeedTimer);
            indexSpeedTimer = setTimeout(() => {
                saveSpeedSetting('index_speed', indexSpeedInput.value);
            }, 500);
        });
    }
    
    const accelerationInput = document.getElementById('acceleration');
    const accelerationDisplay = document.getElementById('acceleration-value');
    
    if (accelerationInput && accelerationDisplay) {
        accelerationInput.addEventListener('input', function() {
            accelerationDisplay.textContent = accelerationInput.value;
        });
        
        // Save on change (debounced)
        let accelerationTimer;
        accelerationInput.addEventListener('change', function() {
            clearTimeout(accelerationTimer);
            accelerationTimer = setTimeout(() => {
                saveSpeedSetting('acceleration', accelerationInput.value);
            }, 500);
        });
    }
    
    const decelerationInput = document.getElementById('deceleration');
    const decelerationDisplay = document.getElementById('deceleration-value');
    
    if (decelerationInput && decelerationDisplay) {
        decelerationInput.addEventListener('input', function() {
            decelerationDisplay.textContent = decelerationInput.value;
        });
        
        // Save on change (debounced)
        let decelerationTimer;
        decelerationInput.addEventListener('change', function() {
            clearTimeout(decelerationTimer);
            decelerationTimer = setTimeout(() => {
                saveSpeedSetting('deceleration', decelerationInput.value);
            }, 500);
        });
    }
    
    // Function to save speed settings to configuration
    function saveSpeedSetting(setting, value) {
        addLogMessage(`Updating ${setting} to ${value}...`, false, 'config');
        
        fetch('/update_config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                section: 'stepper',
                key: setting,
                value: parseInt(value)
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                addLogMessage(`${setting} updated to ${value}`, false, 'success');
            } else {
                addLogMessage(`Error updating ${setting}: ${data.message}`, true);
            }
        })
        .catch(error => {
            addLogMessage(`Error updating ${setting}: ${error.message}`, true);
        });
    }
    
    // Motor enable/disable toggle
    const motorEnabledToggle = document.getElementById('motor-enabled');
    
    if (motorEnabledToggle) {
        motorEnabledToggle.addEventListener('change', function() {
            const enabled = motorEnabledToggle.checked;
            addLogMessage(`${enabled ? 'Enabling' : 'Disabling'} motor...`, false, 'action');
            clearSimulationWarnings();
            
            fetch('/enable_motor', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    enable: enabled
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Handle simulation status based on mode
                    if (data.simulated) {
                        // For simulation mode, this is expected
                        if (currentOperationMode === 'simulation') {
                            addLogMessage(`Motor ${enabled ? 'enabled' : 'disabled'}! (simulation mode)`, false, 'success');
                        } 
                        // For prototype mode, this should NEVER happen
                        else if (currentOperationMode === 'prototype') {
                            addLogMessage(`ERROR: Motor ${enabled ? 'enable' : 'disable'} simulation in PROTOTYPE MODE. Hardware is required!`, true);
                            addSimulationError('HARDWARE ERROR: Receiving simulated values in PROTOTYPE MODE. Check your hardware connections.');
                        } 
                        // For normal mode, it's a warning
                        else {
                            addLogMessage(`WARNING: Motor ${enabled ? 'enable' : 'disable'} simulated due to hardware error`, false, 'warning');
                            addSimulationWarning('Hardware error detected - using simulation values');
                        }
                    } else {
                        // Real hardware values - clear any warnings
                        clearSimulationWarnings();
                        addLogMessage(`Motor ${enabled ? 'enabled' : 'disabled'}!`, false, 'success');
                    }
                } else {
                    addLogMessage('Error: ' + data.message, true);
                }
            })
            .catch(error => {
                addLogMessage('Error: ' + error.message, true);
            });
        });
    }
    
    // Preset position buttons
    const presetButtons = document.querySelectorAll('.move-to-preset');
    
    presetButtons.forEach(button => {
        button.addEventListener('click', function() {
            const position = parseInt(button.getAttribute('data-position') || 0);
            addLogMessage(`Moving to preset position ${position} steps...`, false, 'action');
            button.disabled = true;
            clearSimulationWarnings();
            
            fetch('/move_to', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    position: position
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const currentPosition = data.position;
                    updatePositionDisplay(currentPosition);
                    
                    // Handle simulation status based on mode
                    if (data.simulated) {
                        // For simulation mode, this is expected
                        if (currentOperationMode === 'simulation') {
                            addLogMessage(`Move to preset complete! (simulation mode)`, false, 'success');
                        } 
                        // For prototype mode, this should NEVER happen
                        else if (currentOperationMode === 'prototype') {
                            addLogMessage('ERROR: Move to preset simulation in PROTOTYPE MODE. Hardware is required!', true);
                            addSimulationError('HARDWARE ERROR: Receiving simulated values in PROTOTYPE MODE. Check your hardware connections.');
                        } 
                        // For normal mode, it's a warning
                        else {
                            addLogMessage('WARNING: Move to preset simulated due to hardware error', false, 'warning');
                            addSimulationWarning('Hardware error detected - using simulation values');
                        }
                    } else {
                        // Real hardware values - clear any warnings
                        clearSimulationWarnings();
                        addLogMessage(`Move to preset complete!`, false, 'success');
                    }
                } else {
                    addLogMessage('Error: ' + data.message, true);
                }
            })
            .catch(error => {
                addLogMessage('Error: ' + error.message, true);
            })
            .finally(() => {
                button.disabled = false;
            });
        });
    });
    
    // Save position as preset
    const savePositionButton = document.getElementById('save-position');
    
    if (savePositionButton) {
        savePositionButton.addEventListener('click', function() {
            const presetName = document.getElementById('new-preset-name').value;
            
            if (!presetName) {
                addLogMessage('Please enter a preset name.', true);
                return;
            }
            
            addLogMessage(`Saving current position as "${presetName}"...`, false, 'action');
            savePositionButton.disabled = true;
            
            fetch('/save_position', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name: presetName
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    addLogMessage(`Position saved as "${presetName}"!`, false, 'success');
                    
                    // Reload the page to show updated presets
                    window.location.reload();
                } else {
                    addLogMessage('Error: ' + data.message, true);
                }
            })
            .catch(error => {
                addLogMessage('Error: ' + error.message, true);
            })
            .finally(() => {
                if (savePositionButton) savePositionButton.disabled = false;
            });
        });
    }

    // Speed Control Handlers
    document.addEventListener('DOMContentLoaded', function() {
        // Jog Speed Control
        const jogSpeedSlider = document.getElementById('jog-speed');
        const jogSpeedValue = document.getElementById('jog-speed-value');
        
        if (jogSpeedSlider && jogSpeedValue) {
            jogSpeedSlider.addEventListener('input', function() {
                jogSpeedValue.textContent = this.value;
            });
        }
        
        // Index Speed Control
        const indexSpeedSlider = document.getElementById('index-speed');
        const indexSpeedValue = document.getElementById('index-speed-value');
        
        if (indexSpeedSlider && indexSpeedValue) {
            indexSpeedSlider.addEventListener('input', function() {
                indexSpeedValue.textContent = this.value;
            });
        }
        
        // Acceleration Control
        const accelerationSlider = document.getElementById('acceleration');
        const accelerationValue = document.getElementById('acceleration-value');
        
        if (accelerationSlider && accelerationValue) {
            accelerationSlider.addEventListener('input', function() {
                accelerationValue.textContent = this.value;
            });
        }
        
        // Deceleration Control
        const decelerationSlider = document.getElementById('deceleration');
        const decelerationValue = document.getElementById('deceleration-value');
        
        if (decelerationSlider && decelerationValue) {
            decelerationSlider.addEventListener('input', function() {
                decelerationValue.textContent = this.value;
            });
        }
    });
});