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
            
            // Use makeRequest utility if available
            if (typeof makeRequest === 'function') {
                makeRequest(
                    '/index_move',
                    'POST',
                    { direction: 'forward' },
                    function(data) {
                        if (data.status === 'success') {
                            const currentPosition = data.position;
                            updatePositionDisplay(currentPosition);
                            
                            // Use handleSimulationResponse utility for simulation mode handling
                            if (!handleSimulationResponse(data, 'Index forward')) {
                                // This was a real hardware response
                                addLogMessage('Index forward complete!', false, 'success');
                            }
                        } else {
                            addLogMessage('Error: ' + data.message, true);
                        }
                    },
                    null,
                    function() {
                        if (indexButton) indexButton.disabled = false;
                    }
                );
            } else {
                // Original implementation as fallback
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
            }
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
    
    // Jog Forward button
    const jogForwardButton = document.getElementById('jog-forward');
    
    if (jogForwardButton) {
        jogForwardButton.addEventListener('click', function() {
            const stepSize = parseInt(document.getElementById('step-size').value || 10);
            addLogMessage(`Jogging forward by ${stepSize} steps...`, false, 'action');
            jogForwardButton.disabled = true;
            clearSimulationWarnings();
            
            fetch('/jog', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    direction: 'forward',
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
                            addLogMessage('Jog forward complete! (simulation mode)', false, 'success');
                        } 
                        // For prototype mode, this should NEVER happen
                        else if (currentOperationMode === 'prototype') {
                            addLogMessage('ERROR: Jog forward simulation in PROTOTYPE MODE. Hardware is required!', true);
                            addSimulationError('HARDWARE ERROR: Receiving simulated values in PROTOTYPE MODE. Check your hardware connections.');
                        } 
                        // For normal mode, it's a warning
                        else {
                            addLogMessage('WARNING: Jog forward simulated due to hardware error', false, 'warning');
                            addSimulationWarning('Hardware error detected - using simulation values');
                        }
                    } else {
                        // Real hardware values - clear any warnings
                        clearSimulationWarnings();
                        addLogMessage('Jog forward complete!', false, 'success');
                    }
                } else {
                    addLogMessage('Error: ' + data.message, true);
                }
            })
            .catch(error => {
                addLogMessage('Error: ' + error.message, true);
            })
            .finally(() => {
                if (jogForwardButton) jogForwardButton.disabled = false;
            });
        });
    }
    
    // Jog Backward button
    const jogBackwardButton = document.getElementById('jog-backward');
    
    if (jogBackwardButton) {
        jogBackwardButton.addEventListener('click', function() {
            const stepSize = parseInt(document.getElementById('step-size').value || 10);
            addLogMessage(`Jogging backward by ${stepSize} steps...`, false, 'action');
            jogBackwardButton.disabled = true;
            clearSimulationWarnings();
            
            fetch('/jog', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    direction: 'backward',
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
                            addLogMessage('Jog backward complete! (simulation mode)', false, 'success');
                        } 
                        // For prototype mode, this should NEVER happen
                        else if (currentOperationMode === 'prototype') {
                            addLogMessage('ERROR: Jog backward simulation in PROTOTYPE MODE. Hardware is required!', true);
                            addSimulationError('HARDWARE ERROR: Receiving simulated values in PROTOTYPE MODE. Check your hardware connections.');
                        } 
                        // For normal mode, it's a warning
                        else {
                            addLogMessage('WARNING: Jog backward simulated due to hardware error', false, 'warning');
                            addSimulationWarning('Hardware error detected - using simulation values');
                        }
                    } else {
                        // Real hardware values - clear any warnings
                        clearSimulationWarnings();
                        addLogMessage('Jog backward complete!', false, 'success');
                    }
                } else {
                    addLogMessage('Error: ' + data.message, true);
                }
            })
            .catch(error => {
                addLogMessage('Error: ' + error.message, true);
            })
            .finally(() => {
                if (jogBackwardButton) jogBackwardButton.disabled = false;
            });
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
    
    // Step size display update
    const stepSizeInput = document.getElementById('step-size');
    const stepSizeDisplay = document.getElementById('step-size-value');
    
    if (stepSizeInput && stepSizeDisplay) {
        stepSizeInput.addEventListener('input', function() {
            stepSizeDisplay.textContent = stepSizeInput.value;
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
});