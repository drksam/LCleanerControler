/**
 * main.js - Main control interface for the Laser Cleaner Controller
 * 
 * This module handles the main UI components including:
 * - Temperature monitoring
 * - Stepper motor control
 * - Position presets
 * - Fan and light controls
 * - System logging
 * 
 * @requires ShopUtils
 */

// Get access to utility functions if available
const ShopUtils = window.ShopUtils || {};

// Get steps per mm conversion factor is defined in cleaning_head.js
// This prevents duplication of the function if it's already defined
if (typeof getStepsPerMm !== 'function') {
    /**
     * Get the steps per mm conversion factor from the UI
     * @returns {number} Steps per mm value (default: 100)
     */
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
}

// Initialize global variables
window.lastTempLogTime = 0;

document.addEventListener('DOMContentLoaded', function() {
    // Temperature Monitor Elements
    const temperatureMonitor = document.getElementById('temperature-monitor');
    const noSensorsWarning = document.getElementById('no-sensors-warning');
    
    // Set up temperature monitoring if we're on the main page
    if (temperatureMonitor) {
        updateTemperatureMonitor();
        // Update temperature every 5 seconds
        setInterval(updateTemperatureMonitor, 5000);
    }
    
    // Stepper Motor Elements
    const positionDisplay = document.getElementById('position-display');
    const positionProgress = document.getElementById('position-progress');
    const stepSizeInput = document.getElementById('step-size');
    const stepSizeValue = document.getElementById('step-size-value');
    const jogBackwardBtn = document.getElementById('jog-backward');
    const jogForwardBtn = document.getElementById('jog-forward');
    const homeMotorBtn = document.getElementById('home-motor');
    const motorEnabledSwitch = document.getElementById('motor-enabled');
    const savePositionBtn = document.getElementById('save-position');
    const newPresetNameInput = document.getElementById('new-preset-name');
    const presetContainer = document.getElementById('presets-container');
    const absolutePositionInput = document.getElementById('absolute-position');
    const moveToPositionBtn = document.getElementById('move-to-position');
    const absolutePositionMmInput = document.getElementById('absolute-position-mm');
    const moveToPositionMmBtn = document.getElementById('move-to-position-mm');
    const statusLog = document.getElementById('status-log');
    
    // Servo Control Elements
    const servoPositionASlider = document.getElementById('servo-position-a');
    const servoPositionAValue = document.getElementById('servo-position-a-value');
    const servoPositionBSlider = document.getElementById('servo-position-b');
    const servoPositionBValue = document.getElementById('servo-position-b-value');
    const servoInvertSwitch = document.getElementById('servo-invert');
    const moveToPositionABtn = document.getElementById('move-to-position-a');
    const moveToPositionBBtn = document.getElementById('move-to-position-b');
    const servoDirectAngleSlider = document.getElementById('servo-direct-angle');
    const servoDirectAngleValue = document.getElementById('servo-direct-angle-value');
    const moveToAngleBtn = document.getElementById('move-to-angle');
    
    // Servo Sequence Elements
    const sequenceSwitch = document.getElementById('sequence-mode-switch');
    const fireButton = document.getElementById('fire-button');
    const stopFireButton = document.getElementById('stop-fire-button');
    const firingStatus = document.getElementById('firing-status');
    const firingStatusIcon = document.getElementById('firing-status-icon');
    const firingProgress = document.getElementById('firing-progress');
    const firingTimeDisplay = document.getElementById('firing-time-display');
    
    // Fan and Light Controls
    const fanSwitch = document.getElementById('fan-switch');
    const fanOnBtn = document.getElementById('fan-on');
    const fanOffBtn = document.getElementById('fan-off');
    const fanStateDisplay = document.getElementById('fan-state-display');
    const fanTimerProgress = document.getElementById('fan-timer-progress');
    const fanTimeRemaining = document.getElementById('fan-time-remaining');
    
    const lightsSwitch = document.getElementById('lights-switch');
    const lightsOnBtn = document.getElementById('lights-on');
    const lightsOffBtn = document.getElementById('lights-off');
    const lightsStateDisplay = document.getElementById('lights-state-display');
    const lightsTimerProgress = document.getElementById('lights-timer-progress');
    const lightsTimeRemaining = document.getElementById('lights-time-remaining');
    
    // Quick action buttons
    const indexButton = document.getElementById('index-button');
    
    // Max position for progress bar visualization
    const MAX_POSITION = 1000;
    
    // Initialize
    let currentPosition = 0;
    if (positionDisplay) {
        currentPosition = parseInt(positionDisplay.textContent) || 0;
        updatePositionDisplay(currentPosition);
    }
    
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
     * Update button state during async operation
     * @param {HTMLButtonElement} button - Button to update
     * @param {boolean} isLoading - Whether the button is in loading state
     * @param {string} loadingText - Text to display while loading
     * @param {string} defaultText - Text to display when not loading
     */
    const updateButtonState = ShopUtils.updateButtonState || function(button, isLoading, loadingText, defaultText) {
        if (!button) return;
        
        button.disabled = isLoading;
        button.innerHTML = isLoading 
            ? `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> ${loadingText}`
            : defaultText;
    };

    // Update step size value display
    if (stepSizeInput) {
        stepSizeInput.addEventListener('input', function() {
            stepSizeValue.textContent = this.value;
        });
    }
    
    /**
     * Jog the motor in specified direction
     * @param {string} direction - Direction to jog ('forward' or 'backward')
     * @param {number} steps - Number of steps to jog
     */
    function jogMotor(direction, steps) {
        // Log before jogging
        addLogMessage(`Jogging ${direction} ${steps} steps...`, false, 'action');
        
        makeRequest(
            '/jog',
            'POST',
            {
                direction: direction,
                steps: steps
            },
            function(data) {
                if (data.status === 'success') {
                    currentPosition = data.position;
                    updatePositionDisplay(currentPosition);
                    addLogMessage(`Jog ${direction} complete - position: ${currentPosition}`, false, 'success');
                } else {
                    addLogMessage(`Error during jog ${direction}: ${data.message}`, true);
                }
            },
            function(error) {
                addLogMessage(`Error: ${error.message}`, true);
            }
        );
    }
    
    // Jog backward
    if (jogBackwardBtn) {
        jogBackwardBtn.addEventListener('click', function() {
            const steps = parseInt(stepSizeInput.value);
            jogMotor('backward', steps);
        });
    }
    
    // Jog forward
    if (jogForwardBtn) {
        jogForwardBtn.addEventListener('click', function() {
            const steps = parseInt(stepSizeInput.value);
            jogMotor('forward', steps);
        });
    }
    
    // Home motor
    if (homeMotorBtn) {
        homeMotorBtn.addEventListener('click', function() {
            addLogMessage('Starting homing sequence...', false, 'action');
            
            const originalButtonHtml = homeMotorBtn.innerHTML;
            updateButtonState(homeMotorBtn, true, 'Homing...', originalButtonHtml);
            
            makeRequest(
                '/home',
                'POST',
                null,
                function(data) {
                    if (data.status === 'success') {
                        currentPosition = data.position;
                        updatePositionDisplay(currentPosition);
                        addLogMessage('Homing complete.', false, 'success');
                    } else {
                        addLogMessage('Error: ' + data.message, true);
                    }
                },
                function(error) {
                    addLogMessage('Error: ' + error.message, true);
                },
                function() {
                    updateButtonState(homeMotorBtn, false, '', originalButtonHtml);
                }
            );
        });
    }
    
    // Motor enable/disable toggle
    if (motorEnabledSwitch) {
        motorEnabledSwitch.addEventListener('change', function() {
            const enabled = this.checked;
            
            makeRequest(
                '/enable_motor',
                'POST',
                {
                    enable: enabled
                },
                function(data) {
                    if (data.status === 'success') {
                        addLogMessage(`Motor ${enabled ? 'enabled' : 'disabled'}.`, false, 'info');
                    } else {
                        addLogMessage('Error: ' + data.message, true);
                        // Revert switch state if failed
                        motorEnabledSwitch.checked = !enabled;
                    }
                },
                function(error) {
                    addLogMessage('Error: ' + error.message, true);
                    // Revert switch state if failed
                    motorEnabledSwitch.checked = !enabled;
                }
            );
        });
    }
    
    // Save current position as preset
    if (savePositionBtn) {
        savePositionBtn.addEventListener('click', function() {
            const presetName = newPresetNameInput.value.trim();
        
            if (!presetName) {
                addLogMessage('Please enter a name for the preset.', true);
                return;
            }
            
            makeRequest(
                '/save_position',
                'POST',
                {
                    name: presetName
                },
                function(data) {
                    if (data.status === 'success') {
                        addLogMessage(`Position saved as "${presetName}".`, false, 'success');
                        newPresetNameInput.value = '';
                        updatePresetsList(data.preset_positions);
                    } else {
                        addLogMessage('Error: ' + data.message, true);
                    }
                },
                function(error) {
                    addLogMessage('Error: ' + error.message, true);
                }
            );
        });
    }
    
    // Set up click handlers for move-to-preset buttons
    document.addEventListener('click', function(event) {
        if (event.target.classList.contains('move-to-preset') || 
            event.target.parentElement.classList.contains('move-to-preset')) {
            
            const button = event.target.classList.contains('move-to-preset') ? 
                event.target : event.target.parentElement;
            
            const position = parseInt(button.dataset.position);
            moveToPosition(position);
        }
    });
    
    /**
     * Move to an absolute position
     * @param {number} position - Position to move to in steps
     */
    function moveToPosition(position) {
        // Log the action
        addLogMessage(`Moving to position ${position}...`, false, 'action');
        
        makeRequest(
            '/move_to',
            'POST',
            {
                position: position
            },
            function(data) {
                if (data.status === 'success') {
                    currentPosition = data.position;
                    updatePositionDisplay(currentPosition);
                    addLogMessage(`Move complete - position: ${currentPosition}`, false, 'success');
                } else {
                    addLogMessage(`Error during move: ${data.message}`, true);
                }
            },
            function(error) {
                addLogMessage(`Error: ${error.message}`, true);
            }
        );
    }
    
    /**
     * Update position display in UI
     * @param {number} position - Current position in steps
     */
    function updatePositionDisplay(position) {
        if (positionDisplay) {
            positionDisplay.textContent = position;
        }
        
        if (positionProgress) {
            // Calculate percentage for progress bar (limit to 0-100%)
            const percentage = Math.min(100, Math.max(0, (position / MAX_POSITION) * 100));
            positionProgress.style.width = percentage + '%';
            positionProgress.setAttribute('aria-valuenow', percentage);
        }
    }
    
    // Move to absolute position in mm
    if (moveToPositionMmBtn) {
        moveToPositionMmBtn.addEventListener('click', function() {
            const mmPosition = parseFloat(absolutePositionMmInput.value);
            if (isNaN(mmPosition)) {
                addLogMessage('Please enter a valid position in mm.', true);
                return;
            }
            
            // Convert mm to steps using the steps per mm factor
            const stepsPerMm = getStepsPerMm();
            const position = Math.round(mmPosition * stepsPerMm);
            
            // Log before moving
            addLogMessage(`Moving to ${mmPosition} mm (${position} steps)...`, false, 'action');
            
            makeRequest(
                '/move_to',
                'POST',
                {
                    position: position
                },
                function(data) {
                    if (data.status === 'success') {
                        currentPosition = data.position;
                        updatePositionDisplay(currentPosition);
                        
                        // Calculate the mm position for the log message
                        const mmPositionCurrent = (currentPosition / stepsPerMm).toFixed(2);
                        addLogMessage(`Move complete - position: ${currentPosition} steps (${mmPositionCurrent} mm)`, false, 'success');
                    } else {
                        addLogMessage(`Error during move: ${data.message}`, true);
                    }
                },
                function(error) {
                    addLogMessage(`Error: ${error.message}`, true);
                }
            );
        });
    }
    
    // Move to absolute position in steps
    if (moveToPositionBtn) {
        moveToPositionBtn.addEventListener('click', function() {
            const position = parseInt(absolutePositionInput.value);
            if (isNaN(position)) {
                addLogMessage('Please enter a valid position.', true);
                return;
            }
            
            // Use the existing moveToPosition function
            moveToPosition(position);
        });
    }
    
    /**
     * Update temperature monitor on main page
     */
    function updateTemperatureMonitor() {
        if (!temperatureMonitor) return;
        
        makeRequest(
            '/temperature/status',
            'GET',
            null,
            function(data) {
                // Check if we have sensors data in any format
                if (data.sensors && Object.keys(data.sensors).length > 0) {
                    // Find existing sensor divs and update them
                    let existingSensors = new Set();
                    
                    // Update existing sensors
                    Object.entries(data.sensors).forEach(([sensorId, sensorData]) => {
                        existingSensors.add(sensorId);
                        let sensorDiv = temperatureMonitor.querySelector(`[data-sensor-id="${sensorId}"]`);
                        
                        // If sensor div doesn't exist, create it
                        if (!sensorDiv) {
                            sensorDiv = document.createElement('div');
                            sensorDiv.className = 'px-3 d-flex align-items-center';
                            sensorDiv.dataset.sensorId = sensorId;
                            
                            // Remove no-sensors warning if it exists
                            const noSensorsWarning = document.getElementById('no-sensors-warning');
                            if (noSensorsWarning) {
                                noSensorsWarning.style.display = 'none';
                            }
                            
                            temperatureMonitor.appendChild(sensorDiv);
                        }
                        
                        // Get the temperature value (handles both old 'temp' and new 'temperature' properties)
                        const tempValue = sensorData.temperature !== undefined ? sensorData.temperature : sensorData.temp;
                        
                        // Determine temperature display class based on temperature relative to limit
                        let tempClass = 'text-success';
                        if (tempValue >= sensorData.high_limit * 0.9) {
                            tempClass = 'text-warning';
                        }
                        if (tempValue >= sensorData.high_limit) {
                            tempClass = 'text-danger';
                        }
                        
                        sensorDiv.innerHTML = `
                            <span class="${tempClass}">
                                <i class="fas fa-thermometer-half me-1"></i>
                                ${sensorData.name}: ${tempValue.toFixed(1)}°C
                                <small class="text-muted">(Limit: ${sensorData.high_limit}°C)</small>
                            </span>`;
                    });
                    
                    // Remove sensors that no longer exist
                    temperatureMonitor.querySelectorAll('[data-sensor-id]').forEach(div => {
                        if (!existingSensors.has(div.dataset.sensorId)) {
                            temperatureMonitor.removeChild(div);
                        }
                    });
                    
                    // Also update the temperature status in the IO Status card if it exists
                    const temperatureStatus = document.getElementById('temperature-status');
                    const temperatureStatusIcon = document.getElementById('temperature-status-icon');
                    
                    if (temperatureStatus && temperatureStatusIcon) {
                        // Use primary sensor if set, otherwise find the sensor with highest temperature relative to its limit
                        let selectedSensor = null;
                        
                        // Check if a primary sensor is configured
                        if (data.primary_sensor && data.sensors[data.primary_sensor]) {
                            selectedSensor = data.sensors[data.primary_sensor];
                        } else {
                            // Fall back to highest temperature ratio
                            let highestTempRatio = 0;
                            
                            Object.values(data.sensors).forEach(sensor => {
                                const tempValue = sensor.temperature !== undefined ? sensor.temperature : sensor.temp;
                                const ratio = tempValue / sensor.high_limit;
                                if (ratio > highestTempRatio) {
                                    highestTempRatio = ratio;
                                    selectedSensor = sensor;
                                }
                            });
                        }
                        
                        if (selectedSensor) {
                            const tempValue = selectedSensor.temperature !== undefined ? 
                                selectedSensor.temperature : selectedSensor.temp;
                                
                            temperatureStatus.textContent = `${tempValue.toFixed(1)}°C (${selectedSensor.name})`;
                            
                            // Set appropriate icon and badge status
                            const icon = temperatureStatusIcon.querySelector('i');
                            if (icon) {
                                // Default status
                                icon.className = 'fas fa-thermometer-half fa-2x text-success';
                                temperatureStatus.className = 'badge bg-success';
                                
                                if (tempValue >= selectedSensor.high_limit * 0.9) {
                                    icon.className = 'fas fa-thermometer-half fa-2x text-warning';
                                    temperatureStatus.className = 'badge bg-warning';
                                }
                                
                                if (tempValue >= selectedSensor.high_limit) {
                                    icon.className = 'fas fa-thermometer-half fa-2x text-danger';
                                    temperatureStatus.className = 'badge bg-danger';
                                }
                            }
                            
                            // Dispatch an event with the selected temperature data for other components to use
                            document.dispatchEvent(new CustomEvent('temperature-update', {
                                detail: {
                                    temperature: tempValue,
                                    sensorName: selectedSensor.name,
                                    sensorId: selectedSensor.id || null,
                                    highLimit: selectedSensor.high_limit,
                                    isPrimary: data.primary_sensor === selectedSensor.id
                                }
                            }));
                        }
                    }
                } else {
                    // Show no sensors warning if it's hidden
                    const noSensorsWarning = document.getElementById('no-sensors-warning');
                    if (noSensorsWarning && noSensorsWarning.style.display === 'none') {
                        noSensorsWarning.style.display = 'block';
                        
                        // Remove any existing sensor divs
                        temperatureMonitor.querySelectorAll('[data-sensor-id]').forEach(div => {
                            temperatureMonitor.removeChild(div);
                        });
                    }
                    
                    // Update status indicators
                    const temperatureStatus = document.getElementById('temperature-status');
                    if (temperatureStatus) {
                        temperatureStatus.textContent = 'No Sensors';
                        temperatureStatus.className = 'badge bg-secondary';
                    }
                    
                    const temperatureStatusIcon = document.getElementById('temperature-status-icon');
                    if (temperatureStatusIcon && temperatureStatusIcon.querySelector('i')) {
                        temperatureStatusIcon.querySelector('i').className = 'fas fa-thermometer-half fa-2x text-secondary';
                    }
                }
            },
            function(error) {
                console.error('Error updating temperature status:', error);
                
                // Show error in status indicator
                const temperatureStatus = document.getElementById('temperature-status');
                if (temperatureStatus) {
                    temperatureStatus.textContent = 'Error';
                    temperatureStatus.className = 'badge bg-danger';
                }
            }
        );
    }
    
    /**
     * Add a message to the status log
     * @param {string} message - Message to log
     * @param {boolean} [isError=false] - Whether this is an error message
     * @param {string} [logType='info'] - Type of log message ('info', 'warning', 'error', 'success', etc.)
     */
    const originalAddLogMessage = window.addLogMessage;
    window.addLogMessage = function(message, isError = false, logType = 'info') {
        // If the original function exists in base.html, use it
        if (typeof originalAddLogMessage === 'function') {
            originalAddLogMessage(message, isError, logType);
            return;
        }
        
        const statusLog = document.getElementById('status-log');
        if (!statusLog) return;
        
        console.log(message); // Always log to console
        
        const logItem = document.createElement('div');
        
        // Apply appropriate styling based on log type
        if (isError) {
            logItem.className = 'alert alert-danger mb-1 py-1 small';
        } else if (logType === 'success') {
            logItem.className = 'alert alert-success mb-1 py-1 small';
        } else if (logType === 'action') {
            logItem.className = 'alert alert-primary mb-1 py-1 small';
        } else if (logType === 'warning') {
            logItem.className = 'alert alert-warning mb-1 py-1 small';
        } else if (logType === 'temperature') {
            logItem.className = 'alert alert-info mb-1 py-1 small';
        } else {
            logItem.className = 'alert alert-info mb-1 py-1 small';
        }
        
        logItem.textContent = message;
        
        statusLog.prepend(logItem);
        
        // Limit log items
        const maxItems = 20;
        const items = statusLog.querySelectorAll('div');
        if (items.length > maxItems) {
            for (let i = maxItems; i < items.length; i++) {
                statusLog.removeChild(items[i]);
            }
        }
    };
    
    // Listen for temperature status changes to add to log
    document.addEventListener('temperature-update', function(e) {
        if (statusLog) {
            // Only log temperature updates at most once per minute
            const now = Date.now();
            if (!window.lastTempLogTime || (now - window.lastTempLogTime) > 60000) {
                window.lastTempLogTime = now;
                const { temperature, sensorName } = e.detail || {};
                if (temperature && sensorName) {
                    addLogMessage(`Temperature: ${temperature.toFixed(1)}°C (${sensorName})`, false, 'temperature');
                }
            }
        }
    });
    
    // Additional system events for the log
    window.addEventListener('load', function() {
        if (statusLog) {
            addLogMessage('System initialized and ready', false, 'success');
        }
    });
    
    /**
     * Set the fan state
     * @param {boolean} state - New fan state (true for on, false for off)
     */
    function setFanState(state) {
        makeRequest(
            '/fan',
            'POST',
            {
                state: state
            },
            function(data) {
                if (data.status === 'success') {
                    // Update UI state
                    if (fanSwitch) fanSwitch.checked = state;
                    addLogMessage(`Fan turned ${state ? 'ON' : 'OFF'}`, false);
                    updateFanStatus(); // Update UI immediately
                } else {
                    addLogMessage(`Error controlling fan: ${data.message || 'Unknown error'}`, true);
                    // Revert switch if it failed
                    if (fanSwitch) fanSwitch.checked = !state;
                }
            },
            function(error) {
                addLogMessage(`Error controlling fan: ${error.message}`, true);
                // Revert switch if it failed
                if (fanSwitch) fanSwitch.checked = !state;
            }
        );
    }

    /**
     * Set the lights state
     * @param {boolean} state - New lights state (true for on, false for off)
     */
    function setLightsState(state) {
        makeRequest(
            '/lights',
            'POST',
            {
                state: state
            },
            function(data) {
                if (data.status === 'success') {
                    // Update UI state
                    if (lightsSwitch) lightsSwitch.checked = state;
                    addLogMessage(`Lights turned ${state ? 'ON' : 'OFF'}`, false);
                    updateLightsStatus(); // Update UI immediately
                } else {
                    addLogMessage(`Error controlling lights: ${data.message || 'Unknown error'}`, true);
                    // Revert switch if it failed
                    if (lightsSwitch) lightsSwitch.checked = !state;
                }
            },
            function(error) {
                addLogMessage(`Error controlling lights: ${error.message}`, true);
                // Revert switch if it failed
                if (lightsSwitch) lightsSwitch.checked = !state;
            }
        );
    }
    
    /**
     * Update list of position presets
     * @param {Array} presets - Array of preset position objects
     */
    function updatePresetsList(presets) {
        if (!presetContainer) return;
        
        // Clear existing presets
        presetContainer.innerHTML = '';
        
        if (!presets || presets.length === 0) {
            presetContainer.innerHTML = '<div class="alert alert-info">No presets saved</div>';
            return;
        }
        
        presets.forEach(preset => {
            const presetDiv = document.createElement('div');
            presetDiv.className = 'card mb-2';
            
            presetDiv.innerHTML = `
                <div class="card-body py-2">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h5 class="card-title mb-0">${preset.name}</h5>
                            <p class="card-text text-muted small mb-0">Position: ${preset.position}</p>
                        </div>
                        <div>
                            <button class="btn btn-sm btn-primary move-to-preset" data-position="${preset.position}">
                                <i class="fas fa-arrow-right"></i> Move
                            </button>
                            <button class="btn btn-sm btn-danger delete-preset" data-id="${preset.id}">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
            
            presetContainer.appendChild(presetDiv);
        });
        
        // Set up delete buttons
        const deleteButtons = presetContainer.querySelectorAll('.delete-preset');
        deleteButtons.forEach(button => {
            button.addEventListener('click', function() {
                const presetId = this.dataset.id;
                deletePreset(presetId);
            });
        });
    }
    
    /**
     * Delete a position preset
     * @param {string} presetId - ID of the preset to delete
     */
    function deletePreset(presetId) {
        if (!presetId) return;
        
        makeRequest(
            `/delete_preset/${presetId}`,
            'POST',
            null,
            function(data) {
                if (data.status === 'success') {
                    addLogMessage(`Preset deleted successfully.`, false, 'success');
                    updatePresetsList(data.preset_positions);
                } else {
                    addLogMessage(`Error deleting preset: ${data.message}`, true);
                }
            },
            function(error) {
                addLogMessage(`Error deleting preset: ${error.message}`, true);
            }
        );
    }
    
    /**
     * Update fan status display from server
     */
    function updateFanStatus() {
        makeRequest(
            '/fan/status',
            'GET',
            null,
            function(data) {
                if (data.status === 'success') {
                    const fanState = data.fan_state;
                    const timeRemaining = data.time_remaining || 0;
                    
                    // Update switch
                    if (fanSwitch) {
                        fanSwitch.checked = fanState;
                    }
                    
                    // Update state display
                    if (fanStateDisplay) {
                        fanStateDisplay.innerHTML = fanState 
                            ? '<span class="badge bg-success">ON</span>' 
                            : '<span class="badge bg-danger">OFF</span>';
                    }
                    
                    // Update timer progress
                    if (fanTimerProgress && timeRemaining) {
                        const maxTime = 10 * 60 * 1000; // 10 minutes in ms
                        const percentage = (timeRemaining / maxTime) * 100;
                        fanTimerProgress.style.width = `${percentage}%`;
                        fanTimerProgress.setAttribute('aria-valuenow', percentage);
                        
                        // Format time remaining
                        const minutes = Math.floor(timeRemaining / 60000);
                        const seconds = Math.floor((timeRemaining % 60000) / 1000);
                        fanTimeRemaining.textContent = `Timer: ${minutes}m ${seconds}s remaining`;
                    } else if (fanTimeRemaining) {
                        fanTimeRemaining.textContent = 'Timer: Not active';
                        fanTimerProgress.style.width = '0%';
                        fanTimerProgress.setAttribute('aria-valuenow', 0);
                    }
                }
            },
            function(error) {
                console.error('Error fetching fan status:', error);
            }
        );
    }
    
    /**
     * Update lights status display from server
     */
    function updateLightsStatus() {
        makeRequest(
            '/lights/status',
            'GET',
            null,
            function(data) {
                if (data.status === 'success') {
                    const lightsState = data.lights_state;
                    const timeRemaining = data.time_remaining || 0;
                    
                    // Update switch
                    if (lightsSwitch) {
                        lightsSwitch.checked = lightsState;
                    }
                    
                    // Update state display
                    if (lightsStateDisplay) {
                        lightsStateDisplay.innerHTML = lightsState 
                            ? '<span class="badge bg-danger">ON</span>' 
                            : '<span class="badge bg-secondary">OFF</span>';
                    }
                    
                    // Update timer progress
                    if (lightsTimerProgress && timeRemaining) {
                        const maxTime = 60 * 1000; // 1 minute in ms
                        const percentage = (timeRemaining / maxTime) * 100;
                        lightsTimerProgress.style.width = `${percentage}%`;
                        lightsTimerProgress.setAttribute('aria-valuenow', percentage);
                        
                        // Format time remaining
                        const seconds = Math.floor(timeRemaining / 1000);
                        lightsTimeRemaining.textContent = `Timer: ${seconds}s remaining`;
                    } else if (lightsTimeRemaining) {
                        lightsTimeRemaining.textContent = 'Timer: Not active';
                        lightsTimerProgress.style.width = '0%';
                        lightsTimerProgress.setAttribute('aria-valuenow', 0);
                    }
                }
            },
            function(error) {
                console.error('Error fetching lights status:', error);
            }
        );
    }
    
    // Set up fan toggle switch
    if (fanSwitch) {
        fanSwitch.addEventListener('change', function() {
            const state = this.checked;
            setFanState(state);
        });
    }
    
    // Set up fan on/off buttons
    if (fanOnBtn) {
        fanOnBtn.addEventListener('click', function() {
            setFanState(true);
        });
    }
    
    if (fanOffBtn) {
        fanOffBtn.addEventListener('click', function() {
            setFanState(false);
        });
    }
    
    // Set up lights toggle switch
    if (lightsSwitch) {
        lightsSwitch.addEventListener('change', function() {
            const state = this.checked;
            setLightsState(state);
        });
    }
    
    // Set up lights on/off buttons
    if (lightsOnBtn) {
        lightsOnBtn.addEventListener('click', function() {
            setLightsState(true);
        });
    }
    
    if (lightsOffBtn) {
        lightsOffBtn.addEventListener('click', function() {
            setLightsState(false);
        });
    }
    
    // Set up periodic status updates for fan and lights
    if (fanStateDisplay || lightsStateDisplay) {
        // Initial update
        updateFanStatus();
        updateLightsStatus();
        
        // Periodic update every 3 seconds
        setInterval(function() {
            updateFanStatus();
            updateLightsStatus();
        }, 3000);
    }
    
    /**
     * Initialize position presets
     */
    function initializePresets() {
        // Load presets on startup
        makeRequest(
            '/get_presets',
            'GET',
            null,
            function(data) {
                if (data.status === 'success' && data.preset_positions) {
                    updatePresetsList(data.preset_positions);
                } else {
                    console.error('Failed to load presets:', data.message || 'Unknown error');
                }
            },
            function(error) {
                console.error('Error loading presets:', error);
            }
        );
    }
    
    // Initialize presets if container exists
    if (presetContainer) {
        initializePresets();
    }
});