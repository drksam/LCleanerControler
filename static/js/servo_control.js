/**
 * Servo Control JavaScript
 * Handles servo positioning, movement, and firing actions with proper logging
 */

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
    
    /**
     * Handles simulation response data consistently based on operation mode
     * @param {Object} data - API response data
     * @param {string} actionName - Description of the action being performed
     * @returns {boolean} - True if simulated, false otherwise
     */
    const handleSimulationResponse = ShopUtils.handleSimulationResponse || function(data, actionName) {
        if (!data.simulated) {
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
    
    /**
     * Makes a standardized AJAX request with consistent error handling
     * @param {string} url - URL to make the request to
     * @param {string} method - HTTP method to use
     * @param {Object} data - Data to send with the request
     * @param {Function} successCallback - Function to call on success
     * @param {Function} errorCallback - Function to call on error
     * @param {Function} finallyCallback - Function to call regardless of success/failure
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
                addLogMessage(`Error: ${error.message}`, true);
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
    const setButtonState = ShopUtils.setButtonsState || function(button, disabled) {
        if (button) {
            button.disabled = disabled;
        }
    };
    
    // Position sliders
    const servoPositionASlider = document.getElementById('servo-position-a');
    const servoPositionAValue = document.getElementById('servo-position-a-value');
    const servoPositionBSlider = document.getElementById('servo-position-b');
    const servoPositionBValue = document.getElementById('servo-position-b-value');
    const servoInvertSwitch = document.getElementById('servo-invert');
    
    // Movement buttons
    const moveToPositionABtn = document.getElementById('move-to-position-a');
    const moveToPositionBBtn = document.getElementById('move-to-position-b');
    const servoDirectAngleSlider = document.getElementById('servo-direct-angle');
    const servoDirectAngleValue = document.getElementById('servo-direct-angle-value');
    const moveToAngleBtn = document.getElementById('move-to-angle');
    const detachServoBtn = document.getElementById('detach-servo');
    const reattachServoBtn = document.getElementById('reattach-servo');
    
    // Firing test buttons
    const fireButtonTest = document.getElementById('fire-button-test');
    const stopFireButtonTest = document.getElementById('stop-fire-button-test');
    const fireFiberButtonTest = document.getElementById('fire-fiber-button-test');
    
    // Position A slider
    if (servoPositionASlider && servoPositionAValue) {
        servoPositionASlider.addEventListener('input', function() {
            servoPositionAValue.textContent = this.value;
        });
        
        servoPositionASlider.addEventListener('change', function() {
            const position = parseInt(this.value);
            addLogMessage(`Setting servo position A to ${position}°...`, false, 'config');
            clearSimulationWarnings();
            
            // Use the makeRequest utility
            makeRequest(
                '/servo/set_position_a',
                'POST',
                { angle: position },
                function(data) {
                    if (data.status === 'success') {
                        // Use handleSimulationResponse utility
                        if (!handleSimulationResponse(data, `Set servo position A to ${position}°`)) {
                            // This is a real hardware response
                            addLogMessage(`Servo position A set to ${position}°`, false, 'success');
                        }
                    } else {
                        addLogMessage(`Error setting position A: ${data.message}`, true);
                    }
                }
            );
        });
    }
    
    // Position B slider
    if (servoPositionBSlider && servoPositionBValue) {
        servoPositionBSlider.addEventListener('input', function() {
            servoPositionBValue.textContent = this.value;
        });
        
        servoPositionBSlider.addEventListener('change', function() {
            const position = parseInt(this.value);
            addLogMessage(`Setting servo position B to ${position}°...`, false, 'config');
            clearSimulationWarnings();
            
            // Use the makeRequest utility
            makeRequest(
                '/servo/set_position_b',
                'POST',
                { angle: position },
                function(data) {
                    if (data.status === 'success') {
                        // Use handleSimulationResponse utility
                        if (!handleSimulationResponse(data, `Set servo position B to ${position}°`)) {
                            // This is a real hardware response
                            addLogMessage(`Servo position B set to ${position}°`, false, 'success');
                        }
                    } else {
                        addLogMessage(`Error setting position B: ${data.message}`, true);
                    }
                }
            );
        });
    }
    
    // Invert switch
    if (servoInvertSwitch) {
        servoInvertSwitch.addEventListener('change', function() {
            const inverted = this.checked;
            const originalState = inverted;
            addLogMessage(`${inverted ? 'Enabling' : 'Disabling'} servo inversion...`, false, 'config');
            clearSimulationWarnings();
            
            // Use the makeRequest utility
            makeRequest(
                '/servo/set_inverted',
                'POST',
                { inverted: inverted },
                function(data) {
                    if (data.status === 'success') {
                        // Use handleSimulationResponse utility
                        if (!handleSimulationResponse(data, `${inverted ? 'Enable' : 'Disable'} servo inversion`)) {
                            // This is a real hardware response
                            addLogMessage(`Servo inversion ${inverted ? 'enabled' : 'disabled'}`, false, 'success');
                        }
                    } else {
                        addLogMessage(`Error setting inversion: ${data.message}`, true);
                        // Revert switch state on error
                        servoInvertSwitch.checked = !inverted;
                    }
                },
                function(error) {
                    // Revert switch state on error
                    servoInvertSwitch.checked = !inverted;
                }
            );
        });
    }
    
    // Move to Position A button
    if (moveToPositionABtn) {
        moveToPositionABtn.addEventListener('click', function() {
            addLogMessage('Moving servo to position A...', false, 'action');
            clearSimulationWarnings();
            
            // Use the makeRequest utility
            makeRequest(
                '/servo/move_to_a',
                'POST',
                null,
                function(data) {
                    if (data.status === 'success') {
                        // Use handleSimulationResponse utility
                        if (!handleSimulationResponse(data, 'Move servo to position A')) {
                            // This is a real hardware response
                            addLogMessage(`Servo moved to position A (${data.angle}°)`, false, 'success');
                        }
                    } else {
                        addLogMessage(`Error moving to position A: ${data.message}`, true);
                    }
                }
            );
        });
    }
    
    // Move to Position B button
    if (moveToPositionBBtn) {
        moveToPositionBBtn.addEventListener('click', function() {
            addLogMessage('Moving servo to position B...', false, 'action');
            clearSimulationWarnings();
            
            // Use the makeRequest utility
            makeRequest(
                '/servo/move_to_b',
                'POST',
                null,
                function(data) {
                    if (data.status === 'success') {
                        // Use handleSimulationResponse utility
                        if (!handleSimulationResponse(data, 'Move servo to position B')) {
                            // This is a real hardware response
                            addLogMessage(`Servo moved to position B (${data.angle}°)`, false, 'success');
                        }
                    } else {
                        addLogMessage(`Error moving to position B: ${data.message}`, true);
                    }
                }
            );
        });
    }
    
    // Direct angle slider
    if (servoDirectAngleSlider && servoDirectAngleValue) {
        servoDirectAngleSlider.addEventListener('input', function() {
            servoDirectAngleValue.textContent = this.value;
        });
    }
    
    // Move to Angle button
    if (moveToAngleBtn && servoDirectAngleSlider) {
        moveToAngleBtn.addEventListener('click', function() {
            const angle = parseInt(servoDirectAngleSlider.value);
            addLogMessage(`Moving servo to ${angle}°...`, false, 'action');
            clearSimulationWarnings();
            
            // Use the makeRequest utility
            makeRequest(
                '/servo/move_to_angle',
                'POST',
                { angle: angle },
                function(data) {
                    if (data.status === 'success') {
                        // Use handleSimulationResponse utility
                        if (!handleSimulationResponse(data, `Move servo to ${angle}°`)) {
                            // This is a real hardware response
                            addLogMessage(`Servo moved to ${angle}°`, false, 'success');
                        }
                    } else {
                        addLogMessage(`Error moving to angle: ${data.message}`, true);
                    }
                }
            );
        });
    }
    
    // Detach servo button
    if (detachServoBtn) {
        detachServoBtn.addEventListener('click', function() {
            addLogMessage('Detaching servo...', false, 'action');
            clearSimulationWarnings();
            
            // Use the makeRequest utility
            makeRequest(
                '/servo/detach',
                'POST',
                null,
                function(data) {
                    if (data.status === 'success') {
                        // Use handleSimulationResponse utility
                        if (!handleSimulationResponse(data, 'Detach servo')) {
                            // This is a real hardware response
                            addLogMessage('Servo detached', false, 'success');
                        }
                    } else {
                        addLogMessage(`Error detaching servo: ${data.message}`, true);
                    }
                }
            );
        });
    }
    
    // Reattach servo button
    if (reattachServoBtn) {
        reattachServoBtn.addEventListener('click', function() {
            addLogMessage('Reattaching servo...', false, 'action');
            clearSimulationWarnings();
            
            // Use the makeRequest utility
            makeRequest(
                '/servo/reattach',
                'POST',
                null,
                function(data) {
                    if (data.status === 'success') {
                        // Use handleSimulationResponse utility
                        if (!handleSimulationResponse(data, 'Reattach servo')) {
                            // This is a real hardware response
                            addLogMessage('Servo reattached', false, 'success');
                        }
                    } else {
                        addLogMessage(`Error reattaching servo: ${data.message}`, true);
                    }
                }
            );
        });
    }
    
    // Fire test button
    if (fireButtonTest && stopFireButtonTest) {
        fireButtonTest.addEventListener('click', function() {
            addLogMessage('FIRING (TEST) - Moving servo to position B...', false, 'action');
            clearSimulationWarnings();
            
            // Disable fire button and enable stop button using utility function
            setButtonState(fireButtonTest, true);
            setButtonState(stopFireButtonTest, false);
            
            // Use the makeRequest utility
            makeRequest(
                '/fire',
                'POST',
                null,
                function(data) {
                    if (data.status === 'success') {
                        // Use handleSimulationResponse utility
                        if (!handleSimulationResponse(data, 'Fire test')) {
                            // This is a real hardware response
                            addLogMessage('Firing initiated (Test mode)', false, 'success');
                        }
                    } else {
                        addLogMessage(`Error initiating firing: ${data.message}`, true);
                        // Reset button states on error
                        setButtonState(fireButtonTest, false);
                        setButtonState(stopFireButtonTest, true);
                    }
                },
                function(error) {
                    // Reset button states on error
                    setButtonState(fireButtonTest, false);
                    setButtonState(stopFireButtonTest, true);
                }
            );
        });
        
        stopFireButtonTest.addEventListener('click', function() {
            addLogMessage('STOPPING FIRE (TEST) - Moving servo to position A...', false, 'action');
            clearSimulationWarnings();
            
            // Disable stop button and enable fire button using utility function
            setButtonState(stopFireButtonTest, true);
            setButtonState(fireButtonTest, false);
            
            // Use the makeRequest utility
            makeRequest(
                '/stop_fire',
                'POST',
                null,
                function(data) {
                    if (data.status === 'success') {
                        // Use handleSimulationResponse utility
                        if (!handleSimulationResponse(data, 'Stop fire test')) {
                            // This is a real hardware response
                            addLogMessage('Firing stopped (Test mode)', false, 'success');
                        }
                    } else {
                        addLogMessage(`Error stopping firing: ${data.message}`, true);
                        // Reset button states on error
                        setButtonState(stopFireButtonTest, false);
                        setButtonState(fireButtonTest, true);
                    }
                },
                function(error) {
                    // Reset button states on error
                    setButtonState(stopFireButtonTest, false);
                    setButtonState(fireButtonTest, true);
                }
            );
        });
    }
    
    // Fiber sequence test button
    if (fireFiberButtonTest) {
        fireFiberButtonTest.addEventListener('click', function() {
            addLogMessage('Starting FIBER sequence (TEST)...', false, 'action');
            clearSimulationWarnings();
            
            setButtonState(fireFiberButtonTest, true);
            
            // Use the makeRequest utility with finally callback for re-enabling button
            makeRequest(
                '/fire_fiber',
                'POST',
                null,
                function(data) {
                    if (data.status === 'success') {
                        // Use handleSimulationResponse utility
                        if (!handleSimulationResponse(data, 'Fire fiber sequence test')) {
                            // This is a real hardware response
                            addLogMessage('Fiber sequence started (Test mode)', false, 'success');
                        }
                    } else {
                        addLogMessage(`Error starting fiber sequence: ${data.message}`, true);
                    }
                },
                null,
                function() {
                    // Re-enable button after a short delay
                    setTimeout(() => {
                        setButtonState(fireFiberButtonTest, false);
                    }, 2000);
                }
            );
        });
    }
});