/**
 * Servo Control JavaScript
 * Handles servo positioning, movement, and firing actions with proper logging
 */

console.log('servo_control.js v2025-07-21-fix loaded'); // Version marker

// Check if we're on a mobile device
const isServoPanelMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) 
    || (window.innerWidth <= 768);

console.log('SERVO_CONTROL.JS VERSION 2025-07-21 FINAL FIX'); // CLEAR VERSION MARKER

/**
 * Set a button's disabled state with visual feedback
 * @param {HTMLElement} button - The button to modify
 * @param {boolean} disabled - Whether to disable the button
 */
function setButtonState(button, disabled) {
    if (button) {
        console.log(`setButtonState called: button=${button.id}, disabled=${disabled}, current disabled=${button.disabled}`);
        button.disabled = disabled;
        console.log(`setButtonState result: button=${button.id}, new disabled=${button.disabled}`);
    } else {
        console.log('setButtonState called with null/undefined button');
    }
}

document.addEventListener('DOMContentLoaded', function() {
    
    // Ensure addLogMessage function is available
    if (typeof window.addLogMessage !== 'function') {
        console.warn('window.addLogMessage not available, creating fallback');
        window.addLogMessage = function(message, isError = false, logType = 'info') {
            const prefix = isError ? '[ERROR]' : `[${logType.toUpperCase()}]`;
            console.log(`${prefix} ${message}`);
        };
    }
    
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
    
    // Enhance servo controls with touch-friendly features if on mobile
    if (isServoPanelMobile) {
        initMobileServoControls();
    }
    
    // Initialize existing servo controls
    initServoControls();
});

/**
 * Initialize mobile-specific servo controls
 */
function initMobileServoControls() {
    // Find all servo sliders
    const servoSliders = document.querySelectorAll('.servo-slider');
    
    servoSliders.forEach(slider => {
        // Replace with enhanced mobile slider if not already
        if (!slider.classList.contains('mobile-slider')) {
            slider.classList.add('mobile-slider');
            
            // Add touch value indicator
            const valueDisplay = document.createElement('div');
            valueDisplay.className = 'servo-value-display';
            valueDisplay.textContent = slider.value + '°';
            valueDisplay.style.position = 'absolute';
            valueDisplay.style.bottom = '100%';
            valueDisplay.style.left = '50%';
            valueDisplay.style.transform = 'translateX(-50%)';
            valueDisplay.style.backgroundColor = 'var(--bs-primary)';
            valueDisplay.style.color = 'white';
            valueDisplay.style.padding = '4px 8px';
            valueDisplay.style.borderRadius = '4px';
            valueDisplay.style.display = 'none';
            valueDisplay.style.marginBottom = '10px';
            valueDisplay.style.zIndex = '100';
            valueDisplay.style.fontSize = '14px';
            valueDisplay.style.fontWeight = 'bold';
            valueDisplay.style.boxShadow = '0 2px 5px rgba(0,0,0,0.2)';
            
            // Position the wrapper relatively
            const wrapper = document.createElement('div');
            wrapper.style.position = 'relative';
            wrapper.style.marginBottom = '30px';
            
            // Replace slider with wrapper containing slider and display
            slider.parentNode.insertBefore(wrapper, slider);
            wrapper.appendChild(slider);
            wrapper.appendChild(valueDisplay);
            
            // Show indicator on touch start
            slider.addEventListener('touchstart', function() {
                valueDisplay.style.display = 'block';
                valueDisplay.textContent = this.value + '°';
                
                // Apply haptic feedback if available
                if (window.navigator && window.navigator.vibrate) {
                    window.navigator.vibrate(20);
                }
            });
            
            // Update indicator on touch move
            slider.addEventListener('input', function() {
                valueDisplay.textContent = this.value + '°';
                
                // Calculate position based on slider value
                const percent = (this.value - this.min) / (this.max - this.min);
                const leftPosition = percent * (this.offsetWidth - 20) + 10; // 10px for thumb width offset
                valueDisplay.style.left = `${leftPosition}px`;
                valueDisplay.style.transform = 'translateX(-50%)';
                
                // Small haptic feedback on steps (every 10 degrees)
                if (window.navigator && window.navigator.vibrate && this.value % 10 === 0) {
                    window.navigator.vibrate(10);
                }
            });
            
            // Hide indicator on touch end
            slider.addEventListener('touchend', function() {
                valueDisplay.style.display = 'none';
            });
        }
    });
    
    // Add easy preset buttons for servo positions
    addServoPresetButtons();
    
    // Add gesture controls for fine-tuning
    addServoGestureControls();
}

/**
 * Add preset buttons for common servo positions
 */
function addServoPresetButtons() {
    const servoForms = document.querySelectorAll('.servo-control-form');
    
    servoForms.forEach(form => {
        // Don't add presets if they already exist
        if (form.querySelector('.servo-presets')) return;
        
        const slider = form.querySelector('.servo-slider');
        if (!slider) return;
        
        const min = parseInt(slider.min);
        const max = parseInt(slider.max);
        
        // Create preset container
        const presetContainer = document.createElement('div');
        presetContainer.className = 'servo-presets d-flex justify-content-between mt-2 mb-3';
        
        // Add presets based on min and max
        [min, min + Math.floor((max-min)*0.25), min + Math.floor((max-min)*0.5), 
         min + Math.floor((max-min)*0.75), max].forEach(value => {
            const presetBtn = document.createElement('button');
            presetBtn.type = 'button';
            presetBtn.className = 'btn btn-sm btn-outline-secondary';
            presetBtn.textContent = value + '°';
            presetBtn.dataset.value = value;
            
            presetBtn.addEventListener('click', function() {
                slider.value = this.dataset.value;
                slider.dispatchEvent(new Event('input', { bubbles: true }));
                slider.dispatchEvent(new Event('change', { bubbles: true }));
                
                // Visual feedback
                this.classList.add('active');
                setTimeout(() => {
                    this.classList.remove('active');
                }, 300);
                
                // Haptic feedback
                if (window.navigator && window.navigator.vibrate) {
                    window.navigator.vibrate(30);
                }
            });
            
            presetContainer.appendChild(presetBtn);
        });
        
        // Add fine tuning buttons
        const fineTuneDiv = document.createElement('div');
        fineTuneDiv.className = 'servo-fine-tune d-flex justify-content-between mt-2 mb-3';
        
        // Decrement button
        const decrementBtn = document.createElement('button');
        decrementBtn.type = 'button';
        decrementBtn.className = 'btn btn-outline-primary mobile-control-btn';
        decrementBtn.innerHTML = '<i class="fas fa-minus"></i>';
        decrementBtn.addEventListener('click', function() {
            const currentVal = parseInt(slider.value);
            if (currentVal > min) {
                slider.value = currentVal - 1;
                slider.dispatchEvent(new Event('input', { bubbles: true }));
                slider.dispatchEvent(new Event('change', { bubbles: true }));
                
                // Haptic feedback
                if (window.navigator && window.navigator.vibrate) {
                    window.navigator.vibrate(20);
                }
            }
        });
        
        // Current value display
        const valueDisplay = document.createElement('div');
        valueDisplay.className = 'servo-current-value d-flex justify-content-center align-items-center';
        valueDisplay.style.fontSize = '1.2em';
        valueDisplay.style.fontWeight = 'bold';
        valueDisplay.textContent = slider.value + '°';
        
        // Update display when slider changes
        slider.addEventListener('input', function() {
            valueDisplay.textContent = this.value + '°';
        });
        
        // Increment button
        const incrementBtn = document.createElement('button');
        incrementBtn.type = 'button';
        incrementBtn.className = 'btn btn-outline-primary mobile-control-btn';
        incrementBtn.innerHTML = '<i class="fas fa-plus"></i>';
        incrementBtn.addEventListener('click', function() {
            const currentVal = parseInt(slider.value);
            if (currentVal < max) {
                slider.value = currentVal + 1;
                slider.dispatchEvent(new Event('input', { bubbles: true }));
                slider.dispatchEvent(new Event('change', { bubbles: true }));
                
                // Haptic feedback
                if (window.navigator && window.navigator.vibrate) {
                    window.navigator.vibrate(20);
                }
            }
        });
        
        fineTuneDiv.appendChild(decrementBtn);
        fineTuneDiv.appendChild(valueDisplay);
        fineTuneDiv.appendChild(incrementBtn);
        
        // Insert presets and fine tuning before the submit button
        const submitBtn = form.querySelector('button[type="submit"]');
        form.insertBefore(presetContainer, submitBtn);
        form.insertBefore(fineTuneDiv, submitBtn);
    });
}

/**
 * Add gesture controls for fine tuning servo positions
 */
function addServoGestureControls() {
    const servoForms = document.querySelectorAll('.servo-control-form');
    
    servoForms.forEach(form => {
        const slider = form.querySelector('.servo-slider');
        if (!slider) return;
        
        // Create gesture area
        const gestureArea = document.createElement('div');
        gestureArea.className = 'servo-gesture-area mt-2';
        gestureArea.style.height = '60px';
        gestureArea.style.backgroundColor = 'var(--bs-gray-800)';
        gestureArea.style.borderRadius = '8px';
        gestureArea.style.position = 'relative';
        gestureArea.style.overflow = 'hidden';
        
        // Add gesture hint text
        const gestureHint = document.createElement('div');
        gestureHint.className = 'gesture-hint';
        gestureHint.textContent = 'Swipe left/right for fine control';
        gestureHint.style.position = 'absolute';
        gestureHint.style.top = '50%';
        gestureHint.style.left = '50%';
        gestureHint.style.transform = 'translate(-50%, -50%)';
        gestureHint.style.color = 'var(--bs-gray-500)';
        gestureHint.style.fontSize = '0.9em';
        gestureHint.style.textAlign = 'center';
        gestureHint.style.width = '100%';
        
        // Add indicator bar
        const indicatorBar = document.createElement('div');
        indicatorBar.className = 'gesture-indicator';
        indicatorBar.style.position = 'absolute';
        indicatorBar.style.bottom = '0';
        indicatorBar.style.left = '0';
        indicatorBar.style.height = '4px';
        indicatorBar.style.backgroundColor = 'var(--bs-primary)';
        indicatorBar.style.width = '50%';
        
        gestureArea.appendChild(gestureHint);
        gestureArea.appendChild(indicatorBar);
        
        // Track touch positions
        let startX = 0;
        let currentX = 0;
        
        gestureArea.addEventListener('touchstart', function(e) {
            startX = e.touches[0].clientX;
            currentX = startX;
            gestureHint.style.opacity = '0';
            
            // Initial haptic feedback
            if (window.navigator && window.navigator.vibrate) {
                window.navigator.vibrate(20);
            }
        });
        
        gestureArea.addEventListener('touchmove', function(e) {
            currentX = e.touches[0].clientX;
            const deltaX = currentX - startX;
            const sensitivity = 2; // Higher = more sensitive
            const sliderRange = parseInt(slider.max) - parseInt(slider.min);
            const gestureWidth = this.offsetWidth;
            
            // Calculate new value based on gesture movement
            const movementRatio = deltaX / gestureWidth;
            const valueChange = Math.round(movementRatio * sliderRange * sensitivity);
            const startValue = parseInt(slider.getAttribute('data-start-value') || slider.value);
            let newValue = Math.min(Math.max(parseInt(slider.min), startValue + valueChange), parseInt(slider.max));
            
            // Update slider with new value
            if (slider.value != newValue) {
                slider.value = newValue;
                slider.dispatchEvent(new Event('input', { bubbles: true }));
                
                // Update indicator position
                const percent = (newValue - slider.min) / (slider.max - slider.min);
                indicatorBar.style.width = `${percent * 100}%`;
                
                // Small haptic feedback on degree changes
                if (window.navigator && window.navigator.vibrate && 
                   (Math.abs(deltaX) % 10 < 2)) { // Throttle vibration
                    window.navigator.vibrate(5);
                }
            }
        });
        
        gestureArea.addEventListener('touchstart', function() {
            // Store start value for relative movement
            slider.setAttribute('data-start-value', slider.value);
            
            // Update indicator position initially
            const percent = (slider.value - slider.min) / (slider.max - slider.min);
            indicatorBar.style.width = `${percent * 100}%`;
        });
        
        gestureArea.addEventListener('touchend', function() {
            // Final haptic feedback
            if (window.navigator && window.navigator.vibrate) {
                window.navigator.vibrate(30);
            }
            
            // Dispatch change event at end of gesture
            slider.dispatchEvent(new Event('change', { bubbles: true }));
            
            // Reset hint after a moment
            setTimeout(() => {
                gestureHint.style.opacity = '1';
            }, 2000);
        });
        
        // Add gesture area before the submit button
        const submitBtn = form.querySelector('button[type="submit"]');
        form.insertBefore(gestureArea, submitBtn);
    });
}

// Initialize existing servo controls (your current implementation)
function initServoControls() {
    // Update all servo slider min/max to 0/180
    document.querySelectorAll('#servo-position-a, #servo-position-b, #servo-direct-angle').forEach(function(slider) {
        slider.min = 0;
        slider.max = 180;
    });
    
    // Position sliders
    const servoPositionASlider = document.getElementById('servo-position-a');
    const servoPositionAValue = document.getElementById('servo-position-a-value');
    const servoPositionBSlider = document.getElementById('servo-position-b');
    const servoPositionBValue = document.getElementById('servo-position-b-value');
    const servoDirectAngleSlider = document.getElementById('servo-direct-angle');
    const servoDirectAngleValue = document.getElementById('servo-direct-angle-value');
    const moveToPositionABtn = document.getElementById('move-to-position-a');
    const moveToPositionBBtn = document.getElementById('move-to-position-b');
    const moveToAngleBtn = document.getElementById('move-to-angle');
    const detachServoBtn = document.getElementById('detach-servo');
    const reattachServoBtn = document.getElementById('reattach-servo');
    
    // Firing test buttons
    const fireButtonTest = document.getElementById('fire-button-test');
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
    
    // Fire test button - simple momentary operation like operations page
    if (fireButtonTest) {
        // Use mousedown for immediate response
        fireButtonTest.addEventListener('mousedown', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            console.log('Fire test button mousedown - starting momentary fire');
            addLogMessage('FIRING (TEST) - Momentary operation...', false, 'action');
            
            fireButtonTest.innerHTML = '<span style="color: yellow;">●</span> FIRING - HOLD BUTTON';
            
            makeRequest(
                '/fire',
                'POST',
                { mode: 'momentary' },
                console.log,
                function(data) {
                    console.log('Fire test success:', data);
                    if (data.status === 'success') {
                        addLogMessage('Fire test started - release button to stop', false, 'success');
                    } else {
                        addLogMessage(`Error with fire test: ${data.message}`, true);
                        fireButtonTest.innerHTML = '<i class="fas fa-fire-alt"></i> FIRE TEST';
                    }
                },
                function(error) {
                    console.log('Fire test error:', error);
                    addLogMessage(`Fire test error: ${error.message}`, true);
                    fireButtonTest.innerHTML = '<i class="fas fa-fire-alt"></i> FIRE TEST';
                }
            );
        });

        // Use mouseup for release response
        fireButtonTest.addEventListener('mouseup', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            console.log('Fire test button mouseup - stopping');
            addLogMessage('STOPPING FIRE TEST...', false, 'action');
            
            makeRequest(
                '/stop_firing',
                'POST',
                null,
                console.log,
                function(data) {
                    console.log('Stop fire test success:', data);
                    addLogMessage('Fire test stopped', false, 'success');
                    fireButtonTest.innerHTML = '<i class="fas fa-fire-alt"></i> FIRE TEST';
                },
                function(error) {
                    console.log('Stop fire test error:', error);
                    addLogMessage('Error stopping fire test', true);
                    fireButtonTest.innerHTML = '<i class="fas fa-fire-alt"></i> FIRE TEST';
                }
            );
        });

        // Handle mouseleave to ensure stop if user drags off button
        fireButtonTest.addEventListener('mouseleave', function(e) {
            console.log('Fire test button mouseleave - triggering mouseup');
            fireButtonTest.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
        });
    }

    // Fiber sequence test button - simple momentary operation like operations page
    if (fireFiberButtonTest) {
        // Use mousedown for immediate response
        fireFiberButtonTest.addEventListener('mousedown', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            console.log('Fiber test button mousedown - starting momentary sequence');
            addLogMessage('Starting FIBER sequence (TEST) - Momentary operation...', false, 'action');
            
            fireFiberButtonTest.innerHTML = '<span style="color: yellow;">●</span> FIBER - HOLD BUTTON';
            
            makeRequest(
                '/fire_fiber',
                'POST',
                { mode: 'momentary' },
                console.log,
                function(data) {
                    console.log('Fiber test success:', data);
                    if (data.status === 'success') {
                        addLogMessage('Fiber sequence started - release button to stop', false, 'success');
                    } else {
                        addLogMessage(`Error with fiber sequence: ${data.message}`, true);
                        fireFiberButtonTest.innerHTML = '<i class="fas fa-bolt"></i> FIBER TEST';
                    }
                },
                function(error) {
                    console.log('Fiber test error:', error);
                    addLogMessage(`Fiber sequence error: ${error.message}`, true);
                    fireFiberButtonTest.innerHTML = '<i class="fas fa-bolt"></i> FIBER TEST';
                }
            );
        });

        // Use mouseup for release response
        fireFiberButtonTest.addEventListener('mouseup', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            console.log('Fiber test button mouseup - stopping');
            addLogMessage('STOPPING FIBER TEST...', false, 'action');
            
            makeRequest(
                '/stop_firing',
                'POST',
                null,
                console.log,
                function(data) {
                    console.log('Stop fiber test success:', data);
                    addLogMessage('Fiber test stopped', false, 'success');
                    fireFiberButtonTest.innerHTML = '<i class="fas fa-bolt"></i> FIBER TEST';
                },
                function(error) {
                    console.log('Stop fiber test error:', error);
                    addLogMessage('Error stopping fiber test', true);
                    fireFiberButtonTest.innerHTML = '<i class="fas fa-bolt"></i> FIBER TEST';
                }
            );
        });

        // Handle mouseleave to ensure stop if user drags off button
        fireFiberButtonTest.addEventListener('mouseleave', function(e) {
            console.log('Fiber test button mouseleave - triggering mouseup');
            fireFiberButtonTest.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
        });
    }    // Initialize delay setting controls
    initDelayControls();
}

/**
 * Initialize delay setting controls for fan and red lights
 */
function initDelayControls() {
    // Fan off delay slider
    const fanDelaySlider = document.getElementById('fan-off-delay');
    const fanDelayValue = document.getElementById('fan-off-delay-value');
    const saveFanDelayBtn = document.getElementById('save-fan-delay');
    
    // Red light off delay slider
    const redLightDelaySlider = document.getElementById('red-light-off-delay');
    const redLightDelayValue = document.getElementById('red-light-off-delay-value');
    const saveRedLightDelayBtn = document.getElementById('save-red-light-delay');
    
    // Fan delay slider handler
    if (fanDelaySlider && fanDelayValue) {
        fanDelaySlider.addEventListener('input', function() {
            fanDelayValue.textContent = this.value + 's';
        });
    }
    
    // Red light delay slider handler
    if (redLightDelaySlider && redLightDelayValue) {
        redLightDelaySlider.addEventListener('input', function() {
            redLightDelayValue.textContent = this.value + 's';
        });
    }
    
    // Save fan delay button
    if (saveFanDelayBtn && fanDelaySlider) {
        saveFanDelayBtn.addEventListener('click', function() {
            const delaySeconds = parseInt(fanDelaySlider.value);
            
            // Disable button and show loading
            setButtonState(saveFanDelayBtn, true);
            saveFanDelayBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Saving...';
            
            makeRequest(
                '/settings/fan_off_delay',
                'POST',
                { delay_seconds: delaySeconds },
                function(data) {
                    if (data.status === 'success') {
                        addLogMessage(`Fan off delay updated to ${delaySeconds} seconds`, false, 'success');
                        
                        // Update button to show success
                        saveFanDelayBtn.innerHTML = '<i class="fas fa-check me-1"></i> Saved!';
                        saveFanDelayBtn.classList.remove('btn-outline-primary');
                        saveFanDelayBtn.classList.add('btn-success');
                        
                        // Reset button after 2 seconds
                        setTimeout(() => {
                            saveFanDelayBtn.innerHTML = '<i class="fas fa-save me-1"></i> Save Fan Delay';
                            saveFanDelayBtn.classList.remove('btn-success');
                            saveFanDelayBtn.classList.add('btn-outline-primary');
                            setButtonState(saveFanDelayBtn, false);
                        }, 2000);
                    } else {
                        addLogMessage(`Error saving fan delay: ${data.message || 'Unknown error'}`, true);
                        // Reset button
                        saveFanDelayBtn.innerHTML = '<i class="fas fa-save me-1"></i> Save Fan Delay';
                        setButtonState(saveFanDelayBtn, false);
                    }
                },
                function(error) {
                    addLogMessage(`Error saving fan delay: ${error.message}`, true);
                    // Reset button
                    saveFanDelayBtn.innerHTML = '<i class="fas fa-save me-1"></i> Save Fan Delay';
                    setButtonState(saveFanDelayBtn, false);
                }
            );
        });
    }
    
    // Save red light delay button
    if (saveRedLightDelayBtn && redLightDelaySlider) {
        saveRedLightDelayBtn.addEventListener('click', function() {
            const delaySeconds = parseInt(redLightDelaySlider.value);
            
            // Disable button and show loading
            setButtonState(saveRedLightDelayBtn, true);
            saveRedLightDelayBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Saving...';
            
            makeRequest(
                '/settings/red_lights_off_delay',
                'POST',
                { delay_seconds: delaySeconds },
                function(data) {
                    if (data.status === 'success') {
                        addLogMessage(`Red light off delay updated to ${delaySeconds} seconds`, false, 'success');
                        
                        // Update button to show success
                        saveRedLightDelayBtn.innerHTML = '<i class="fas fa-check me-1"></i> Saved!';
                        saveRedLightDelayBtn.classList.remove('btn-outline-primary');
                        saveRedLightDelayBtn.classList.add('btn-success');
                        
                        // Reset button after 2 seconds
                        setTimeout(() => {
                            saveRedLightDelayBtn.innerHTML = '<i class="fas fa-save me-1"></i> Save Light Delay';
                            saveRedLightDelayBtn.classList.remove('btn-success');
                            saveRedLightDelayBtn.classList.add('btn-outline-primary');
                            setButtonState(saveRedLightDelayBtn, false);
                        }, 2000);
                    } else {
                        addLogMessage(`Error saving red light delay: ${data.message || 'Unknown error'}`, true);
                        // Reset button
                        saveRedLightDelayBtn.innerHTML = '<i class="fas fa-save me-1"></i> Save Light Delay';
                        setButtonState(saveRedLightDelayBtn, false);
                    }
                },
                function(error) {
                    addLogMessage(`Error saving red light delay: ${error.message}`, true);
                    // Reset button
                    saveRedLightDelayBtn.innerHTML = '<i class="fas fa-save me-1"></i> Save Light Delay';
                    setButtonState(saveRedLightDelayBtn, false);
                }
            );
        });
    }
}