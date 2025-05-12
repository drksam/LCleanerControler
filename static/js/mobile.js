/**
 * mobile.js - Enhanced mobile device support for LCleanerController
 * 
 * This file adds mobile-specific functionality to improve the user experience on smaller screens.
 * It handles touch events, optimized controls, and responsive layout adjustments.
 */

// Global mobile state
const mobileState = {
    isPortrait: window.innerHeight > window.innerWidth,
    isMobile: /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) 
              || (window.innerWidth <= 768),
    lastOrientation: window.innerHeight > window.innerWidth ? 'portrait' : 'landscape',
    offlineMode: false,
    batteryLevel: null,
    lastTouchPosition: { x: 0, y: 0 },
    swipeThreshold: 50,
    hapticFeedbackEnabled: true,
    bottomNavVisible: true,
    quickActionsVisible: false
};

document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on a mobile device
    if (mobileState.isMobile) {
        document.body.classList.add('mobile-device');
        console.log('Mobile device detected, enabling mobile optimizations');
        initMobileOptimizations();
    }
});

/**
 * Initialize mobile-specific optimizations
 */
function initMobileOptimizations() {
    // Optimize controls for touch
    optimizeControlsForTouch();
    
    // Add mobile-specific navigation
    setupMobileNavigation();
    
    // Setup mobile-friendly control panels
    setupMobileControlPanels();
    
    // Add pinch zoom for specific elements if needed
    setupPinchZoom();
    
    // Setup stepper distance adjustment controls
    setupStepperDistanceControls();
    
    // Setup servo angle slider optimizations
    setupServoSliderOptimizations();
    
    // Optimize sequence selection interface
    optimizeSequenceSelection();
    
    // Add haptic feedback support
    setupHapticFeedback();
    
    // Add gesture detection
    setupGestureControls();
    
    // Add pull-to-refresh functionality
    setupPullToRefresh();
    
    // Add floating action button
    setupFloatingActionButton();
    
    // Monitor and handle connectivity changes
    setupOfflineDetection();
    
    // Add orientation change handler
    setupOrientationHandler();
    
    // Initialize all mobile-specific features
    initMobileFeatures();
}

/**
 * Optimize controls for touch events
 */
function optimizeControlsForTouch() {
    // Increase button sizes for easier touch
    const actionButtons = document.querySelectorAll('.btn-primary, .btn-danger, .btn-warning, .btn-success');
    actionButtons.forEach(button => {
        button.classList.add('btn-lg', 'touch-friendly');
    });

    // Add specific touch events to control buttons
    document.querySelectorAll('[data-mobile-control="true"]').forEach(element => {
        // Prevent double tap zoom on mobile devices
        element.addEventListener('touchend', function(e) {
            e.preventDefault();
        });
    });
    
    // Make sliders larger for better touch control
    document.querySelectorAll('input[type="range"]').forEach(slider => {
        slider.classList.add('mobile-slider');
    });

    // Fix 300ms delay issue on mobile
    // This attaches fast-click behavior to all interactive elements
    document.querySelectorAll('button, a, input, .interactive').forEach(el => {
        el.addEventListener('touchstart', function() {
            this.classList.add('active-touch');
        });
        
        el.addEventListener('touchend', function() {
            this.classList.remove('active-touch');
        });
    });
}

/**
 * Setup mobile-friendly navigation
 */
function setupMobileNavigation() {
    // Create mobile bottom navigation bar if it doesn't exist
    if (!document.getElementById('mobile-nav-bar')) {
        const navBar = document.createElement('div');
        navBar.id = 'mobile-nav-bar';
        navBar.className = 'mobile-nav-bar d-md-none';
        
        // Add quick access buttons for common functions
        navBar.innerHTML = `
            <div class="btn-group mobile-nav-group">
                <button class="btn btn-primary nav-btn" data-target="table">
                    <i class="fas fa-arrows-alt"></i>
                    <span>Table</span>
                </button>
                <button class="btn btn-primary nav-btn" data-target="servo">
                    <i class="fas fa-sliders-h"></i>
                    <span>Servo</span>
                </button>
                <button class="btn btn-primary nav-btn" data-target="stepper">
                    <i class="fas fa-step-forward"></i>
                    <span>Stepper</span>
                </button>
                <button class="btn btn-primary nav-btn" data-target="sequence">
                    <i class="fas fa-play"></i>
                    <span>Sequence</span>
                </button>
            </div>
        `;
        
        document.body.appendChild(navBar);
        
        // Add event listeners to navigation buttons
        navBar.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const target = this.getAttribute('data-target');
                showControlPanel(target);
            });
        });
    }
}

/**
 * Setup mobile control panels for different functions
 */
function setupMobileControlPanels() {
    // Create a mobile control panel container if it doesn't exist
    if (!document.getElementById('mobile-control-panels')) {
        const panelsContainer = document.createElement('div');
        panelsContainer.id = 'mobile-control-panels';
        panelsContainer.className = 'mobile-control-panels d-md-none';
        
        // Add control panels for each function
        panelsContainer.innerHTML = `
            <div id="table-control-panel" class="control-panel">
                <h3>Table Control</h3>
                <div class="mobile-control-buttons">
                    <button id="mobile-table-backward" class="btn btn-lg btn-primary mobile-control-btn">
                        <i class="fas fa-arrow-left"></i> Backward
                    </button>
                    <button id="mobile-table-stop" class="btn btn-lg btn-danger mobile-control-btn">
                        <i class="fas fa-stop"></i> Stop
                    </button>
                    <button id="mobile-table-forward" class="btn btn-lg btn-primary mobile-control-btn">
                        <i class="fas fa-arrow-right"></i> Forward
                    </button>
                </div>
                <div class="status-indicators mt-3">
                    <div class="row">
                        <div class="col-6">
                            <span>Status: </span>
                            <span id="mobile-table-status" class="badge bg-secondary">Unknown</span>
                        </div>
                        <div class="col-6">
                            <span>Back Limit: </span>
                            <span id="mobile-back-limit" class="badge bg-secondary">Unknown</span>
                        </div>
                    </div>
                    <div class="row mt-2">
                        <div class="col-6">
                            <span>Front Limit: </span>
                            <span id="mobile-front-limit" class="badge bg-secondary">Unknown</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <div id="stepper-control-panel" class="control-panel" style="display:none;">
                <h3>Stepper Control</h3>
                <div class="mobile-control-buttons">
                    <button id="mobile-stepper-backward" class="btn btn-lg btn-primary mobile-control-btn">
                        <i class="fas fa-arrow-left"></i> Backward
                    </button>
                    <button id="mobile-stepper-stop" class="btn btn-lg btn-danger mobile-control-btn">
                        <i class="fas fa-stop"></i> Stop
                    </button>
                    <button id="mobile-stepper-forward" class="btn btn-lg btn-primary mobile-control-btn">
                        <i class="fas fa-arrow-right"></i> Forward
                    </button>
                </div>
                <div class="mt-3">
                    <label for="mobile-stepper-distance" class="form-label">Distance (mm): <span id="mobile-stepper-distance-value">10</span></label>
                    <input type="range" class="form-range mobile-slider" id="mobile-stepper-distance" min="1" max="100" step="1" value="10">
                </div>
                <div class="mt-2">
                    <label for="mobile-stepper-speed" class="form-label">Speed: <span id="mobile-stepper-speed-value">50%</span></label>
                    <input type="range" class="form-range mobile-slider" id="mobile-stepper-speed" min="10" max="100" step="5" value="50">
                </div>
                <div class="status-indicators mt-3">
                    <div class="row">
                        <div class="col-12">
                            <span>Position: </span>
                            <span id="mobile-stepper-position" class="badge bg-info">0.00 mm</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <div id="servo-control-panel" class="control-panel" style="display:none;">
                <h3>Servo Control</h3>
                <div class="mt-3">
                    <label for="mobile-servo-angle" class="form-label">Angle: <span id="mobile-servo-angle-value">90°</span></label>
                    <input type="range" class="form-range mobile-slider" id="mobile-servo-angle" min="0" max="180" step="1" value="90">
                </div>
                <div class="mobile-control-buttons mt-3">
                    <button id="mobile-servo-min" class="btn btn-lg btn-primary mobile-control-btn">Min (0°)</button>
                    <button id="mobile-servo-center" class="btn btn-lg btn-primary mobile-control-btn">Center (90°)</button>
                    <button id="mobile-servo-max" class="btn btn-lg btn-primary mobile-control-btn">Max (180°)</button>
                </div>
            </div>
            
            <div id="sequence-control-panel" class="control-panel" style="display:none;">
                <h3>Sequence Control</h3>
                <div class="form-group mt-3">
                    <label for="mobile-sequence-select">Select Sequence:</label>
                    <select class="form-control" id="mobile-sequence-select">
                        <option value="">-- Select Sequence --</option>
                    </select>
                </div>
                <div class="mobile-control-buttons mt-3">
                    <button id="mobile-sequence-start" class="btn btn-lg btn-success mobile-control-btn">
                        <i class="fas fa-play"></i> Start
                    </button>
                    <button id="mobile-sequence-pause" class="btn btn-lg btn-warning mobile-control-btn" disabled>
                        <i class="fas fa-pause"></i> Pause
                    </button>
                    <button id="mobile-sequence-stop" class="btn btn-lg btn-danger mobile-control-btn" disabled>
                        <i class="fas fa-stop"></i> Stop
                    </button>
                </div>
                <div class="progress mt-3">
                    <div id="mobile-sequence-progress" class="progress-bar" role="progressbar" style="width: 0%;" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">0%</div>
                </div>
                <div class="mt-3">
                    <span>Status: </span>
                    <span id="mobile-sequence-status" class="badge bg-secondary">Not Running</span>
                </div>
            </div>
        `;
        
        document.body.appendChild(panelsContainer);
        
        // Initialize panel controls
        initTableControls();
        initStepperControls();
        initServoControls();
        initSequenceControls();
    }
}

/**
 * Show a specific control panel and hide others
 * @param {string} panelName - Name of the panel to show
 */
function showControlPanel(panelName) {
    // Hide all panels first
    document.querySelectorAll('.control-panel').forEach(panel => {
        panel.style.display = 'none';
    });
    
    // Show the selected panel
    const targetPanel = document.getElementById(`${panelName}-control-panel`);
    if (targetPanel) {
        targetPanel.style.display = 'block';
        
        // Update active state in navigation
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.getAttribute('data-target') === panelName) {
                btn.classList.add('active');
            }
        });
        
        // Refresh panel data
        switch(panelName) {
            case 'table':
                updateTableStatus();
                break;
            case 'stepper':
                updateStepperStatus();
                break;
            case 'sequence':
                updateSequenceList();
                updateSequenceStatus();
                break;
        }
    }
}

/**
 * Initialize table control buttons
 */
function initTableControls() {
    const forwardBtn = document.getElementById('mobile-table-forward');
    const backwardBtn = document.getElementById('mobile-table-backward');
    const stopBtn = document.getElementById('mobile-table-stop');
    
    if (forwardBtn && backwardBtn && stopBtn) {
        // Forward button
        forwardBtn.addEventListener('touchstart', function(e) {
            e.preventDefault();
            moveTableForward(true);
        });
        
        forwardBtn.addEventListener('touchend', function() {
            stopTable();
        });
        
        // Backward button
        backwardBtn.addEventListener('touchstart', function(e) {
            e.preventDefault();
            moveTableBackward(true);
        });
        
        backwardBtn.addEventListener('touchend', function() {
            stopTable();
        });
        
        // Stop button
        stopBtn.addEventListener('touchstart', function(e) {
            e.preventDefault();
            stopTable();
        });
        
        // Start with table panel visible
        showControlPanel('table');
        
        // Poll table status
        setInterval(updateTableStatus, 2000);
    }
}

/**
 * Move table forward (calls main table_control.js function if available)
 */
function moveTableForward(touch = true) {
    if (window.moveTableForward) {
        window.moveTableForward(touch);
    } else {
        fetch('/table/forward', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ state: true })
        })
        .then(response => response.json())
        .then(data => {
            console.log('Moving table forward');
            updateTableStatus();
        })
        .catch(error => {
            console.error('Error moving table forward:', error);
        });
    }
}

/**
 * Move table backward (calls main table_control.js function if available)
 */
function moveTableBackward(touch = true) {
    if (window.moveTableBackward) {
        window.moveTableBackward(touch);
    } else {
        fetch('/table/backward', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ state: true })
        })
        .then(response => response.json())
        .then(data => {
            console.log('Moving table backward');
            updateTableStatus();
        })
        .catch(error => {
            console.error('Error moving table backward:', error);
        });
    }
}

/**
 * Stop table movement (calls main table_control.js function if available)
 */
function stopTable() {
    if (window.stopTable) {
        window.stopTable();
    } else {
        // Stop forward movement
        fetch('/table/forward', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ state: false })
        })
        .then(response => response.json())
        .then(() => {
            // Then stop backward movement
            return fetch('/table/backward', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ state: false })
            });
        })
        .then(response => response.json())
        .then(data => {
            console.log('Table stopped');
            updateTableStatus();
        })
        .catch(error => {
            console.error('Error stopping table:', error);
        });
    }
}

/**
 * Update table status display on mobile interface
 */
function updateTableStatus() {
    fetch('/table/status', {
        method: 'GET'
    })
    .then(response => response.json())
    .then(data => {
        // Update mobile status indicators
        const mobileStatus = document.getElementById('mobile-table-status');
        const mobileFrontLimit = document.getElementById('mobile-front-limit');
        const mobileBackLimit = document.getElementById('mobile-back-limit');
        
        if (mobileStatus) {
            if (data.table_forward_state) {
                mobileStatus.textContent = 'Moving Forward';
                mobileStatus.className = 'badge bg-success';
            } else if (data.table_backward_state) {
                mobileStatus.textContent = 'Moving Backward';
                mobileStatus.className = 'badge bg-success';
            } else {
                mobileStatus.textContent = 'Stopped';
                mobileStatus.className = 'badge bg-secondary';
            }
        }
        
        if (mobileFrontLimit) {
            if (data.table_front_switch_state) {
                mobileFrontLimit.textContent = 'Activated';
                mobileFrontLimit.className = 'badge bg-danger';
            } else {
                mobileFrontLimit.textContent = 'Not Active';
                mobileFrontLimit.className = 'badge bg-secondary';
            }
        }
        
        if (mobileBackLimit) {
            if (data.table_back_switch_state) {
                mobileBackLimit.textContent = 'Activated';
                mobileBackLimit.className = 'badge bg-danger';
            } else {
                mobileBackLimit.textContent = 'Not Active';
                mobileBackLimit.className = 'badge bg-secondary';
            }
        }
    })
    .catch(error => {
        console.error('Error fetching table status:', error);
    });
}

/**
 * Initialize stepper control functions
 */
function initStepperControls() {
    const forwardBtn = document.getElementById('mobile-stepper-forward');
    const backwardBtn = document.getElementById('mobile-stepper-backward');
    const stopBtn = document.getElementById('mobile-stepper-stop');
    const distanceSlider = document.getElementById('mobile-stepper-distance');
    const speedSlider = document.getElementById('mobile-stepper-speed');
    
    if (forwardBtn && backwardBtn && stopBtn) {
        // Forward button
        forwardBtn.addEventListener('click', function() {
            moveStepperForward();
        });
        
        // Backward button
        backwardBtn.addEventListener('click', function() {
            moveStepperBackward();
        });
        
        // Stop button
        stopBtn.addEventListener('click', function() {
            stopStepper();
        });
        
        // Distance slider
        if (distanceSlider) {
            distanceSlider.addEventListener('input', function() {
                document.getElementById('mobile-stepper-distance-value').textContent = this.value;
            });
        }
        
        // Speed slider
        if (speedSlider) {
            speedSlider.addEventListener('input', function() {
                document.getElementById('mobile-stepper-speed-value').textContent = this.value + '%';
            });
        }
        
        // Poll stepper status
        setInterval(updateStepperStatus, 2000);
    }
}

/**
 * Move stepper forward
 */
function moveStepperForward() {
    const distance = document.getElementById('mobile-stepper-distance').value;
    const speed = document.getElementById('mobile-stepper-speed').value;
    
    fetch('/stepper/move', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            direction: 'forward',
            distance: parseFloat(distance),
            speed_percent: parseInt(speed)
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Moving stepper forward');
        updateStepperStatus();
    })
    .catch(error => {
        console.error('Error moving stepper forward:', error);
    });
}

/**
 * Move stepper backward
 */
function moveStepperBackward() {
    const distance = document.getElementById('mobile-stepper-distance').value;
    const speed = document.getElementById('mobile-stepper-speed').value;
    
    fetch('/stepper/move', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            direction: 'backward',
            distance: parseFloat(distance),
            speed_percent: parseInt(speed)
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Moving stepper backward');
        updateStepperStatus();
    })
    .catch(error => {
        console.error('Error moving stepper backward:', error);
    });
}

/**
 * Stop stepper movement
 */
function stopStepper() {
    fetch('/stepper/stop', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        console.log('Stepper stopped');
        updateStepperStatus();
    })
    .catch(error => {
        console.error('Error stopping stepper:', error);
    });
}

/**
 * Update stepper status display
 */
function updateStepperStatus() {
    fetch('/stepper/status', {
        method: 'GET'
    })
    .then(response => response.json())
    .then(data => {
        // Update mobile status indicators
        const positionDisplay = document.getElementById('mobile-stepper-position');
        
        if (positionDisplay && data.position !== undefined) {
            positionDisplay.textContent = data.position.toFixed(2) + ' mm';
        }
    })
    .catch(error => {
        console.error('Error fetching stepper status:', error);
    });
}

/**
 * Initialize servo control functions
 */
function initServoControls() {
    const servoAngleSlider = document.getElementById('mobile-servo-angle');
    const servoMinBtn = document.getElementById('mobile-servo-min');
    const servoCenterBtn = document.getElementById('mobile-servo-center');
    const servoMaxBtn = document.getElementById('mobile-servo-max');
    
    if (servoAngleSlider) {
        servoAngleSlider.addEventListener('input', function() {
            document.getElementById('mobile-servo-angle-value').textContent = this.value + '°';
        });
        
        servoAngleSlider.addEventListener('change', function() {
            setServoAngle(parseInt(this.value));
        });
    }
    
    if (servoMinBtn) {
        servoMinBtn.addEventListener('click', function() {
            setServoAngle(0);
            servoAngleSlider.value = 0;
            document.getElementById('mobile-servo-angle-value').textContent = '0°';
        });
    }
    
    if (servoCenterBtn) {
        servoCenterBtn.addEventListener('click', function() {
            setServoAngle(90);
            servoAngleSlider.value = 90;
            document.getElementById('mobile-servo-angle-value').textContent = '90°';
        });
    }
    
    if (servoMaxBtn) {
        servoMaxBtn.addEventListener('click', function() {
            setServoAngle(180);
            servoAngleSlider.value = 180;
            document.getElementById('mobile-servo-angle-value').textContent = '180°';
        });
    }
}

/**
 * Set servo angle
 * @param {number} angle - Angle for servo in degrees (0-180)
 */
function setServoAngle(angle) {
    fetch('/servo/set_angle', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            angle: angle
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log(`Servo angle set to ${angle}°`);
    })
    .catch(error => {
        console.error('Error setting servo angle:', error);
    });
}

/**
 * Initialize sequence controls
 */
function initSequenceControls() {
    const sequenceSelect = document.getElementById('mobile-sequence-select');
    const startBtn = document.getElementById('mobile-sequence-start');
    const pauseBtn = document.getElementById('mobile-sequence-pause');
    const stopBtn = document.getElementById('mobile-sequence-stop');
    
    if (sequenceSelect && startBtn && pauseBtn && stopBtn) {
        // Initial sequence list
        updateSequenceList();
        
        // Start button
        startBtn.addEventListener('click', function() {
            const selectedSequence = sequenceSelect.value;
            if (selectedSequence) {
                startSequence(selectedSequence);
            } else {
                alert('Please select a sequence first.');
            }
        });
        
        // Pause button
        pauseBtn.addEventListener('click', function() {
            pauseSequence();
        });
        
        // Stop button
        stopBtn.addEventListener('click', function() {
            stopSequence();
        });
        
        // Poll sequence status
        setInterval(updateSequenceStatus, 2000);
    }
}

/**
 * Update the list of available sequences
 */
function updateSequenceList() {
    fetch('/api/sequences/list', {
        method: 'GET'
    })
    .then(response => response.json())
    .then(data => {
        const sequenceSelect = document.getElementById('mobile-sequence-select');
        if (sequenceSelect) {
            // Clear existing options (except the default)
            while (sequenceSelect.options.length > 1) {
                sequenceSelect.remove(1);
            }
            
            // Add sequences to dropdown
            if (data.sequences && data.sequences.length > 0) {
                data.sequences.forEach(sequence => {
                    const option = document.createElement('option');
                    option.value = sequence.id;
                    option.textContent = sequence.name;
                    sequenceSelect.appendChild(option);
                });
            }
        }
    })
    .catch(error => {
        console.error('Error fetching sequences:', error);
    });
}

/**
 * Start a sequence
 * @param {string} sequenceId - ID of sequence to start
 */
function startSequence(sequenceId) {
    fetch('/api/sequences/start', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            sequence_id: sequenceId
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Sequence started');
        updateSequenceStatus();
    })
    .catch(error => {
        console.error('Error starting sequence:', error);
    });
}

/**
 * Pause currently running sequence
 */
function pauseSequence() {
    fetch('/api/sequences/pause', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        console.log('Sequence paused');
        updateSequenceStatus();
    })
    .catch(error => {
        console.error('Error pausing sequence:', error);
    });
}

/**
 * Stop currently running sequence
 */
function stopSequence() {
    fetch('/api/sequences/stop', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        console.log('Sequence stopped');
        updateSequenceStatus();
    })
    .catch(error => {
        console.error('Error stopping sequence:', error);
    });
}

/**
 * Update sequence status display
 */
function updateSequenceStatus() {
    fetch('/api/sequences/status', {
        method: 'GET'
    })
    .then(response => response.json())
    .then(data => {
        const statusElement = document.getElementById('mobile-sequence-status');
        const progressBar = document.getElementById('mobile-sequence-progress');
        const pauseBtn = document.getElementById('mobile-sequence-pause');
        const stopBtn = document.getElementById('mobile-sequence-stop');
        
        if (statusElement && progressBar && pauseBtn && stopBtn) {
            // Update status badge
            if (data.running && !data.paused) {
                statusElement.textContent = 'Running';
                statusElement.className = 'badge bg-success';
                pauseBtn.disabled = false;
                stopBtn.disabled = false;
            } else if (data.running && data.paused) {
                statusElement.textContent = 'Paused';
                statusElement.className = 'badge bg-warning';
                pauseBtn.disabled = false;
                stopBtn.disabled = false;
            } else {
                statusElement.textContent = 'Not Running';
                statusElement.className = 'badge bg-secondary';
                pauseBtn.disabled = true;
                stopBtn.disabled = true;
            }
            
            // Update progress bar
            const progress = data.progress_percent || 0;
            progressBar.style.width = progress + '%';
            progressBar.textContent = progress + '%';
            progressBar.setAttribute('aria-valuenow', progress);
        }
    })
    .catch(error => {
        console.error('Error fetching sequence status:', error);
    });
}

/**
 * Setup stepper distance adjustment controls
 */
function setupStepperDistanceControls() {
    const distanceSlider = document.getElementById('mobile-stepper-distance');
    
    if (distanceSlider) {
        // Add increment/decrement buttons for fine control
        const stepperControlWrapper = distanceSlider.parentNode;
        
        if (stepperControlWrapper) {
            const controlsDiv = document.createElement('div');
            controlsDiv.className = 'mt-2 d-flex justify-content-between';
            controlsDiv.innerHTML = `
                <button class="btn btn-sm btn-secondary" id="mobile-distance-dec">-</button>
                <button class="btn btn-sm btn-secondary" id="mobile-distance-reset">Reset</button>
                <button class="btn btn-sm btn-secondary" id="mobile-distance-inc">+</button>
            `;
            
            stepperControlWrapper.appendChild(controlsDiv);
            
            // Add event listeners to buttons
            document.getElementById('mobile-distance-dec').addEventListener('click', function() {
                const currentValue = parseInt(distanceSlider.value);
                const newValue = Math.max(parseInt(distanceSlider.min), currentValue - 1);
                distanceSlider.value = newValue;
                document.getElementById('mobile-stepper-distance-value').textContent = newValue;
            });
            
            document.getElementById('mobile-distance-inc').addEventListener('click', function() {
                const currentValue = parseInt(distanceSlider.value);
                const newValue = Math.min(parseInt(distanceSlider.max), currentValue + 1);
                distanceSlider.value = newValue;
                document.getElementById('mobile-stepper-distance-value').textContent = newValue;
            });
            
            document.getElementById('mobile-distance-reset').addEventListener('click', function() {
                distanceSlider.value = 10; // Default value
                document.getElementById('mobile-stepper-distance-value').textContent = 10;
            });
        }
    }
}

/**
 * Setup pinch zoom for diagrams or sequence visualizations
 */
function setupPinchZoom() {
    // Find any elements that might benefit from pinch zoom (diagrams, sequence visualizations)
    const zoomableElements = document.querySelectorAll('.diagram-container, .sequence-visualization');
    
    zoomableElements.forEach(element => {
        // Set initial transform values
        let currentScale = 1;
        let lastScale = 1;
        let lastX = 0;
        let lastY = 0;
        
        // Add the zoomable class to apply CSS styles
        element.classList.add('zoomable');
        
        // Handle pinch zoom gesture
        element.addEventListener('touchstart', function(event) {
            if (event.touches.length === 2) {
                event.preventDefault();
            }
        }, { passive: false });
        
        element.addEventListener('touchmove', function(event) {
            if (event.touches.length === 2) {
                event.preventDefault();
                
                // Calculate distance between touch points
                const touch1 = event.touches[0];
                const touch2 = event.touches[1];
                const dist = Math.hypot(
                    touch2.pageX - touch1.pageX,
                    touch2.pageY - touch1.pageY
                );
                
                // Calculate scale change
                if (lastScale !== 1) {
                    currentScale = Math.min(Math.max(0.5, dist / lastScale), 3);
                }
                
                // Apply scale transform
                element.style.transform = `scale(${currentScale})`;
                
                lastScale = dist;
            }
        }, { passive: false });
        
        element.addEventListener('touchend', function() {
            lastScale = 1;
            // Remember the current scale, don't reset to 1
        });
    });
}

/**
 * Setup servo slider optimizations for mobile
 */
function setupServoSliderOptimizations() {
    const servoSlider = document.getElementById('mobile-servo-angle');
    
    if (servoSlider) {
        // Add preset buttons for common angles
        const presets = [
            { name: '0°', value: 0 },
            { name: '45°', value: 45 },
            { name: '90°', value: 90 },
            { name: '135°', value: 135 },
            { name: '180°', value: 180 }
        ];
        
        const presetContainer = document.createElement('div');
        presetContainer.className = 'servo-presets mt-2 d-flex justify-content-between';
        
        presets.forEach(preset => {
            const presetBtn = document.createElement('button');
            presetBtn.className = 'btn btn-sm btn-outline-primary';
            presetBtn.textContent = preset.name;
            presetBtn.addEventListener('click', function() {
                servoSlider.value = preset.value;
                document.getElementById('mobile-servo-angle-value').textContent = preset.value + '°';
                setServoAngle(preset.value);
            });
            presetContainer.appendChild(presetBtn);
        });
        
        // Insert after the slider
        const parent = servoSlider.parentNode;
        parent.insertBefore(presetContainer, servoSlider.nextSibling);
    }
}

/**
 * Optimize sequence selection interface
 */
function optimizeSequenceSelection() {
    const sequenceSelect = document.getElementById('mobile-sequence-select');
    
    if (sequenceSelect) {
        // Make the select element larger for easier touch
        sequenceSelect.classList.add('form-control-lg');
        
        // Add a refresh button
        const refreshBtn = document.createElement('button');
        refreshBtn.className = 'btn btn-sm btn-outline-secondary mt-2';
        refreshBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Refresh Sequences';
        refreshBtn.addEventListener('click', function() {
            updateSequenceList();
        });
        
        // Insert after the select element
        const parent = sequenceSelect.parentNode;
        parent.appendChild(refreshBtn);
    }
}

/**
 * Setup haptic feedback for touch controls
 */
function setupHapticFeedback() {
    // Check if device supports vibration API
    const hasVibration = 'vibrate' in navigator;
    
    // Add haptic feedback to all interactive controls
    document.querySelectorAll('.btn, .mobile-control-btn, input[type="range"], .mobile-toggle-switch, [data-haptic="true"]')
        .forEach(element => {
            element.addEventListener('touchstart', function() {
                // Add visual feedback
                this.classList.add('haptic-feedback');
                
                // Provide haptic feedback if supported
                if (hasVibration) {
                    navigator.vibrate(15); // Short 15ms vibration
                }
                
                // Remove class after animation completes
                setTimeout(() => {
                    this.classList.remove('haptic-feedback');
                }, 150);
            });
        });
}

/**
 * Setup advanced gesture controls
 */
function setupGestureControls() {
    // Track touch positions for gesture detection
    let touchStartX = 0;
    let touchStartY = 0;
    let touchEndX = 0;
    let touchEndY = 0;
    let minSwipeDistance = 50; // Minimum distance to register as swipe
    
    // Add event listeners to detect swipes
    document.addEventListener('touchstart', function(e) {
        touchStartX = e.changedTouches[0].screenX;
        touchStartY = e.changedTouches[0].screenY;
    }, false);
    
    document.addEventListener('touchend', function(e) {
        touchEndX = e.changedTouches[0].screenX;
        touchEndY = e.changedTouches[0].screenY;
        handleSwipe();
    }, false);
    
    // Handle swipe gestures
    function handleSwipe() {
        const deltaX = touchEndX - touchStartX;
        const deltaY = touchEndY - touchStartY;
        
        // Determine if it was a horizontal or vertical swipe
        if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > minSwipeDistance) {
            // Horizontal swipe
            if (deltaX > 0) {
                // Right swipe - navigate to previous panel
                handleSwipeRight();
            } else {
                // Left swipe - navigate to next panel
                handleSwipeLeft();
            }
        }
    }
    
    // Handle right swipe (previous panel)
    function handleSwipeRight() {
        const panels = ['table', 'stepper', 'servo', 'sequence'];
        const activePanelId = document.querySelector('.control-panel[style*="display: block"]')?.id?.replace('-control-panel', '') || 'table';
        const currentIndex = panels.indexOf(activePanelId);
        
        if (currentIndex > 0) {
            showControlPanel(panels[currentIndex - 1]);
        }
    }
    
    // Handle left swipe (next panel)
    function handleSwipeLeft() {
        const panels = ['table', 'stepper', 'servo', 'sequence'];
        const activePanelId = document.querySelector('.control-panel[style*="display: block"]')?.id?.replace('-control-panel', '') || 'table';
        const currentIndex = panels.indexOf(activePanelId);
        
        if (currentIndex < panels.length - 1) {
            showControlPanel(panels[currentIndex + 1]);
        }
    }
}

/**
 * Setup pull-to-refresh functionality
 */
function setupPullToRefresh() {
    let touchStartY = 0;
    let pullDistance = 0;
    const pullThreshold = 100; // Minimum pull distance to trigger refresh
    const maxPullDistance = 150;
    let isPulling = false;
    
    // Create pull indicator element if it doesn't exist
    if (!document.getElementById('pull-indicator')) {
        const indicator = document.createElement('div');
        indicator.id = 'pull-indicator';
        indicator.className = 'pull-indicator';
        indicator.innerHTML = `
            <div class="pull-spinner">
                <i class="fas fa-sync-alt"></i>
            </div>
            <div class="pull-text">Pull down to refresh</div>
        `;
        document.body.insertBefore(indicator, document.body.firstChild);
        
        // Style the indicator
        indicator.style.position = 'fixed';
        indicator.style.top = '-60px';
        indicator.style.left = '0';
        indicator.style.right = '0';
        indicator.style.height = '60px';
        indicator.style.backgroundColor = 'var(--bs-primary)';
        indicator.style.color = 'white';
        indicator.style.zIndex = '999';
        indicator.style.display = 'flex';
        indicator.style.alignItems = 'center';
        indicator.style.justifyContent = 'center';
        indicator.style.transition = 'transform 0.2s ease';
        indicator.style.transform = 'translateY(0)';
    }
    
    // Track touch start position
    document.addEventListener('touchstart', function(e) {
        // Only enable pull to refresh at the top of the page
        if (window.scrollY === 0) {
            touchStartY = e.touches[0].clientY;
            isPulling = true;
        }
    }, false);
    
    // Track touch move to show pull indicator
    document.addEventListener('touchmove', function(e) {
        if (!isPulling) return;
        
        const touchY = e.touches[0].clientY;
        pullDistance = touchY - touchStartY;
        
        // Only activate when pulling down from the top
        if (pullDistance > 0 && window.scrollY === 0) {
            const pullIndicator = document.getElementById('pull-indicator');
            const pullProgress = Math.min(1, pullDistance / pullThreshold);
            const cappedDistance = Math.min(pullDistance * 0.5, maxPullDistance); // Apply resistance
            
            pullIndicator.style.transform = `translateY(${cappedDistance}px)`;
            
            // Update indicator text based on distance
            const pullText = pullIndicator.querySelector('.pull-text');
            if (pullText) {
                pullText.textContent = pullDistance > pullThreshold ? 
                    'Release to refresh' : 'Pull down to refresh';
            }
            
            // Rotate spinner based on pull distance
            const pullSpinner = pullIndicator.querySelector('.pull-spinner i');
            if (pullSpinner) {
                pullSpinner.style.transform = `rotate(${pullProgress * 360}deg)`;
            }
            
            // Prevent default scrolling behavior when pulling
            e.preventDefault();
        }
    }, { passive: false });
    
    // Handle touch end to trigger refresh
    document.addEventListener('touchend', function() {
        if (!isPulling) return;
        
        const pullIndicator = document.getElementById('pull-indicator');
        
        if (pullDistance > pullThreshold) {
            // Show loading state
            pullIndicator.querySelector('.pull-text').textContent = 'Refreshing...';
            pullIndicator.querySelector('.pull-spinner i').classList.add('fa-spin');
            
            // Perform refresh
            refreshCurrentView().then(() => {
                // Reset indicator after refresh
                setTimeout(() => {
                    pullIndicator.style.transform = 'translateY(0)';
                    pullIndicator.querySelector('.pull-spinner i').classList.remove('fa-spin');
                }, 500);
            });
        } else {
            // Reset indicator immediately if threshold wasn't reached
            pullIndicator.style.transform = 'translateY(0)';
        }
        
        // Reset tracking variables
        isPulling = false;
        pullDistance = 0;
    }, false);
}

/**
 * Refresh the current control panel data
 * @returns {Promise} Promise that resolves when refresh is complete
 */
function refreshCurrentView() {
    return new Promise((resolve) => {
        const activePanelId = document.querySelector('.control-panel[style*="display: block"]')?.id?.replace('-control-panel', '') || 'table';
        
        switch(activePanelId) {
            case 'table':
                updateTableStatus();
                break;
            case 'stepper':
                updateStepperStatus();
                break;
            case 'servo':
                // Refresh servo status if applicable
                break;
            case 'sequence':
                updateSequenceList();
                updateSequenceStatus();
                break;
        }
        
        // Simulate a short delay before resolving the promise
        setTimeout(resolve, 500);
    });
}

/**
 * Setup floating action button for quick actions
 */
function setupFloatingActionButton() {
    // Create FAB element if it doesn't exist
    if (!document.getElementById('mobile-fab')) {
        const fab = document.createElement('div');
        fab.id = 'mobile-fab';
        fab.className = 'mobile-fab';
        fab.innerHTML = '<i class="fas fa-plus"></i>';
        
        // Add click event for action menu
        fab.addEventListener('click', function() {
            toggleFabMenu();
        });
        
        document.body.appendChild(fab);
    }
    
    // Function to toggle the FAB action menu
    function toggleFabMenu() {
        // Get or create the action menu
        let fabMenu = document.getElementById('fab-menu');
        
        if (!fabMenu) {
            fabMenu = document.createElement('div');
            fabMenu.id = 'fab-menu';
            fabMenu.className = 'fab-menu';
            fabMenu.style.position = 'fixed';
            fabMenu.style.right = '20px';
            fabMenu.style.bottom = '160px';
            fabMenu.style.zIndex = '998';
            fabMenu.style.display = 'flex';
            fabMenu.style.flexDirection = 'column';
            fabMenu.style.alignItems = 'flex-end';
            fabMenu.style.gap = '10px';
            fabMenu.style.transition = 'transform 0.3s ease';
            fabMenu.style.transform = 'scale(0)';
            fabMenu.style.transformOrigin = 'bottom right';
            
            // Add action buttons
            fabMenu.innerHTML = `
                <div class="fab-action" data-action="home">
                    <span class="fab-label">Home</span>
                    <button class="btn btn-info btn-fab"><i class="fas fa-home"></i></button>
                </div>
                <div class="fab-action" data-action="refresh">
                    <span class="fab-label">Refresh</span>
                    <button class="btn btn-info btn-fab"><i class="fas fa-sync-alt"></i></button>
                </div>
                <div class="fab-action" data-action="emergency">
                    <span class="fab-label">Emergency Stop</span>
                    <button class="btn btn-danger btn-fab"><i class="fas fa-power-off"></i></button>
                </div>
            `;
            
            document.body.appendChild(fabMenu);
            
            // Style the action buttons
            document.querySelectorAll('.fab-action').forEach(action => {
                action.style.display = 'flex';
                action.style.alignItems = 'center';
                action.style.gap = '10px';
                
                // Add click handlers
                action.addEventListener('click', function(e) {
                    const actionType = this.getAttribute('data-action');
                    handleFabAction(actionType);
                    toggleFabMenu(); // Close the menu after action
                });
            });
            
            document.querySelectorAll('.btn-fab').forEach(btn => {
                btn.style.width = '45px';
                btn.style.height = '45px';
                btn.style.borderRadius = '50%';
                btn.style.display = 'flex';
                btn.style.alignItems = 'center';
                btn.style.justifyContent = 'center';
                btn.style.boxShadow = '0 2px 5px rgba(0,0,0,0.3)';
            });
            
            document.querySelectorAll('.fab-label').forEach(label => {
                label.style.backgroundColor = 'rgba(0,0,0,0.7)';
                label.style.color = 'white';
                label.style.padding = '5px 10px';
                label.style.borderRadius = '4px';
                label.style.fontSize = '14px';
                label.style.whiteSpace = 'nowrap';
            });
        }
        
        // Toggle the menu visibility
        const isVisible = fabMenu.style.transform === 'scale(1)';
        fabMenu.style.transform = isVisible ? 'scale(0)' : 'scale(1)';
        
        // Rotate the FAB icon
        const fabIcon = document.querySelector('#mobile-fab i');
        fabIcon.style.transform = isVisible ? 'rotate(0deg)' : 'rotate(45deg)';
        fabIcon.style.transition = 'transform 0.3s ease';
    }
    
    // Handle actions from the FAB menu
    function handleFabAction(action) {
        switch(action) {
            case 'home':
                window.location.href = '/';
                break;
            case 'refresh':
                refreshCurrentView();
                break;
            case 'emergency':
                emergencyStop();
                break;
        }
    }
    
    // Emergency stop function
    function emergencyStop() {
        // Show confirmation dialog
        if (confirm('Are you sure you want to trigger emergency stop?')) {
            // Visual indication
            document.body.classList.add('emergency');
            
            // Trigger haptic feedback if available
            if ('vibrate' in navigator) {
                navigator.vibrate([100, 50, 100, 50, 100]);
            }
            
            // Send emergency stop command to all systems
            fetch('/emergency/stop', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                console.log('Emergency stop triggered');
                alert('Emergency stop triggered successfully');
                
                // Remove visual indication after delay
                setTimeout(() => {
                    document.body.classList.remove('emergency');
                }, 2000);
                
                // Update all status displays
                updateTableStatus();
                updateStepperStatus();
                updateSequenceStatus();
            })
            .catch(error => {
                console.error('Error triggering emergency stop:', error);
                alert('Failed to trigger emergency stop: ' + error);
            });
        }
    }
}

/**
 * Setup offline detection and handling
 */
function setupOfflineDetection() {
    // Create offline indicator if it doesn't exist
    if (!document.getElementById('offline-indicator')) {
        const indicator = document.createElement('div');
        indicator.id = 'offline-indicator';
        indicator.className = 'offline-indicator';
        indicator.textContent = 'You are currently offline';
        document.body.appendChild(indicator);
    }
    
    // Update online/offline status
    function updateOnlineStatus() {
        const indicator = document.getElementById('offline-indicator');
        if (navigator.onLine) {
            indicator.style.display = 'none';
            // Try to reconnect to any disconnected services
            attemptReconnect();
        } else {
            indicator.style.display = 'block';
        }
    }
    
    // Try to reconnect when coming back online
    function attemptReconnect() {
        // Attempt to reconnect any websockets or fetch latest status
        refreshCurrentView();
    }
    
    // Listen for online/offline events
    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
    
    // Initial check
    updateOnlineStatus();
}

/**
 * Handle device orientation changes
 */
function setupOrientationHandler() {
    // Add orientation classes to body initially
    updateOrientationClass();
    
    // Listen for orientation changes
    window.addEventListener('orientationchange', function() {
        setTimeout(updateOrientationClass, 300); // Short delay to let rotation complete
    });
    
    window.addEventListener('resize', function() {
        updateOrientationClass();
    });
    
    function updateOrientationClass() {
        const isPortrait = window.innerHeight > window.innerWidth;
        document.body.classList.remove('landscape-mode', 'portrait-mode');
        document.body.classList.add(isPortrait ? 'portrait-mode' : 'landscape-mode');
        
        // Get active panel
        const activePanel = document.querySelector('.control-panel[style*="display: block"]');
        if (activePanel) {
            optimizeLayoutForOrientation(activePanel.id, isPortrait);
        }
        
        // Display a tip for first-time landscape mode users
        const hasSeenLandscapeTip = localStorage.getItem('hasSeenLandscapeTip');
        if (!isPortrait && !hasSeenLandscapeTip) {
            showLandscapeModeTip();
            localStorage.setItem('hasSeenLandscapeTip', 'true');
        }
    }
    
    function optimizeLayoutForOrientation(panelId, isPortrait) {
        switch(panelId) {
            case 'table-control-panel':
                // In landscape, show more controls side by side
                const tableButtons = document.querySelector('#table-control-panel .mobile-control-buttons');
                if (tableButtons) {
                    tableButtons.classList.toggle('flex-row', !isPortrait);
                    tableButtons.classList.toggle('justify-content-around', !isPortrait);
                }
                break;
                
            case 'stepper-control-panel':
                // In landscape, show controls and status side by side
                const stepperPanel = document.getElementById('stepper-control-panel');
                if (stepperPanel) {
                    stepperPanel.classList.toggle('landscape-layout', !isPortrait);
                }
                break;
                
            case 'sequence-control-panel':
                // In landscape, show more detailed sequence information
                const sequenceDetails = document.querySelector('#sequence-control-panel .sequence-details');
                if (sequenceDetails) {
                    sequenceDetails.classList.toggle('d-none', isPortrait);
                }
                break;
        }
    }
    
    function showLandscapeModeTip() {
        // Create a tip modal if it doesn't exist
        if (!document.getElementById('landscape-tip-modal')) {
            const modal = document.createElement('div');
            modal.id = 'landscape-tip-modal';
            modal.className = 'orientation-tip-modal';
            modal.innerHTML = `
                <div class="tip-content">
                    <h4>Landscape Mode Enabled</h4>
                    <p>This view provides expanded controls and additional information.</p>
                    <button class="btn btn-primary" id="tip-dismiss-btn">Got it</button>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            // Style the modal
            modal.style.position = 'fixed';
            modal.style.top = '0';
            modal.style.left = '0';
            modal.style.right = '0';
            modal.style.bottom = '0';
            modal.style.backgroundColor = 'rgba(0,0,0,0.8)';
            modal.style.zIndex = '9999';
            modal.style.display = 'flex';
            modal.style.alignItems = 'center';
            modal.style.justifyContent = 'center';
            
            // Style the content
            const content = modal.querySelector('.tip-content');
            content.style.backgroundColor = 'var(--bs-dark)';
            content.style.color = 'var(--bs-light)';
            content.style.padding = '20px';
            content.style.borderRadius = '8px';
            content.style.maxWidth = '80%';
            content.style.textAlign = 'center';
            
            // Add dismiss button event
            document.getElementById('tip-dismiss-btn').addEventListener('click', function() {
                modal.remove();
            });
        }
    }
}

/**
 * Initialize all mobile-specific features
 */
function initMobileFeatures() {
    setupOrientationHandling();
    setupBottomNavigation();
    setupOfflineDetection();
    setupTouchControls();
    setupPullToRefresh();
    setupQuickActions();
    setupBatteryStatus();
    setupEmergencyStop();
    setupFullscreenMode();
    
    // Add class to body for mobile-specific CSS
    document.body.classList.add('mobile-device');
    if (mobileState.isPortrait) {
        document.body.classList.add('portrait-mode');
    } else {
        document.body.classList.add('landscape-mode');
    }
    
    // Inform user about mobile optimizations
    showMobileWelcomeToast();
}

/**
 * Setup full-screen mode for mobile
 */
function setupFullscreenMode() {
    // Add fullscreen toggle button
    const controlPanel = document.querySelector('.control-panel');
    if (controlPanel) {
        const fullscreenBtn = document.createElement('button');
        fullscreenBtn.className = 'btn btn-sm btn-outline-secondary fullscreen-toggle';
        fullscreenBtn.innerHTML = '<i class="fas fa-expand"></i>';
        fullscreenBtn.title = 'Toggle Fullscreen';
        
        fullscreenBtn.addEventListener('click', toggleFullscreen);
        
        // Add to control panel header if exists, otherwise to the panel itself
        const panelHeader = controlPanel.querySelector('.panel-header') || controlPanel;
        panelHeader.appendChild(fullscreenBtn);
    }
}

/**
 * Toggle fullscreen mode
 */
function toggleFullscreen() {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(err => {
            console.error(`Error attempting to enable fullscreen: ${err.message}`);
        });
        
        // Change button icon
        document.querySelector('.fullscreen-toggle').innerHTML = '<i class="fas fa-compress"></i>';
        
        // Haptic feedback
        if (window.navigator && window.navigator.vibrate && mobileState.hapticFeedbackEnabled) {
            window.navigator.vibrate(30);
        }
    } else {
        if (document.exitFullscreen) {
            document.exitFullscreen();
            
            // Change button icon back
            document.querySelector('.fullscreen-toggle').innerHTML = '<i class="fas fa-expand"></i>';
            
            // Haptic feedback
            if (window.navigator && window.navigator.vibrate && mobileState.hapticFeedbackEnabled) {
                window.navigator.vibrate([10, 20, 10]);
            }
        }
    }
}

/**
 * Setup battery status monitoring if available
 */
function setupBatteryStatus() {
    if ('getBattery' in navigator) {
        navigator.getBattery().then(function(battery) {
            updateBatteryStatus(battery);
            
            // Listen for battery changes
            battery.addEventListener('levelchange', () => {
                updateBatteryStatus(battery);
            });
            
            battery.addEventListener('chargingchange', () => {
                updateBatteryStatus(battery);
            });
        });
    }
}

/**
 * Update battery status indicator
 */
function updateBatteryStatus(battery) {
    mobileState.batteryLevel = Math.round(battery.level * 100);
    
    // Create status element if it doesn't exist
    let batteryStatus = document.getElementById('battery-status');
    if (!batteryStatus) {
        batteryStatus = document.createElement('div');
        batteryStatus.id = 'battery-status';
        batteryStatus.className = 'battery-status';
        document.body.appendChild(batteryStatus);
    }
    
    // Update battery indicator
    let batteryIcon = 'fa-battery-empty';
    if (mobileState.batteryLevel > 87) {
        batteryIcon = 'fa-battery-full';
    } else if (mobileState.batteryLevel > 62) {
        batteryIcon = 'fa-battery-three-quarters';
    } else if (mobileState.batteryLevel > 37) {
        batteryIcon = 'fa-battery-half';
    } else if (mobileState.batteryLevel > 12) {
        batteryIcon = 'fa-battery-quarter';
    }
    
    // Add charging indicator if applicable
    let chargingIcon = battery.charging ? '<i class="fas fa-bolt charging-icon"></i>' : '';
    
    batteryStatus.innerHTML = `
        <i class="fas ${batteryIcon}"></i> ${chargingIcon} ${mobileState.batteryLevel}%
    `;
    
    // Warning for low battery
    if (mobileState.batteryLevel <= 15 && !battery.charging) {
        batteryStatus.classList.add('battery-low');
        
        // Only show warning once per session when battery gets low
        if (!sessionStorage.getItem('lowBatteryWarningShown') && mobileState.batteryLevel <= 15) {
            showToast('Battery level low. Please connect charger.', 'warning');
            sessionStorage.setItem('lowBatteryWarningShown', 'true');
        }
    } else {
        batteryStatus.classList.remove('battery-low');
    }
}

/**
 * Welcome toast for mobile users
 */
function showMobileWelcomeToast() {
    // Only show once per session
    if (!sessionStorage.getItem('mobileWelcomeShown')) {
        setTimeout(() => {
            showToast('Mobile interface active. Swipe for navigation.', 'info', 5000);
            sessionStorage.setItem('mobileWelcomeShown', 'true');
        }, 1500);
    }
}

/**
 * Display toast notification
 */
function showToast(message, type = 'info', duration = 3000) {
    // Create toast container if it doesn't exist
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast toast-${type} show`;
    toast.innerHTML = `<div class="toast-content">${message}</div>`;
    
    // Add to container
    toastContainer.appendChild(toast);
    
    // Haptic feedback based on toast type
    if (window.navigator && window.navigator.vibrate && mobileState.hapticFeedbackEnabled) {
        switch (type) {
            case 'error':
                window.navigator.vibrate([50, 100, 50]);
                break;
            case 'warning':
                window.navigator.vibrate([20, 40, 20]);
                break;
            case 'success':
                window.navigator.vibrate(40);
                break;
            default:
                window.navigator.vibrate(20);
        }
    }
    
    // Remove after duration
    setTimeout(() => {
        toast.classList.add('hide');
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, duration);
}