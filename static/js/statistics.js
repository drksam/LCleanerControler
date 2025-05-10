/**
 * Statistics JavaScript
 * 
 * Manages the display and control of laser usage statistics.
 * Tracks firing counts, timing, and provides reset functionality.
 * @module statistics
 */
document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const laserFireCount = document.getElementById('laser-fire-count');
    const totalFireTime = document.getElementById('total-fire-time');
    const totalFireTimeMs = document.getElementById('total-fire-time-ms');
    const sessionFireCount = document.getElementById('session-fire-count');
    const sessionFireTime = document.getElementById('session-fire-time');
    
    // Reset buttons
    const resetCounterBtn = document.getElementById('reset-counter-btn');
    const resetTimerBtn = document.getElementById('reset-timer-btn');
    const resetCounterBtnLarge = document.getElementById('reset-counter-btn-large');
    const resetTimerBtnLarge = document.getElementById('reset-timer-btn-large');
    const resetAllBtn = document.getElementById('reset-all-btn');
    
    // Session variables
    let sessionFiringCount = 0;
    let sessionFiringTimeMs = 0;
    let firingTimerActive = false;
    let firingStartTime = 0;
    let currentFiringTime = 0;
    let firingTimerInterval = null;
    
    // Initialize
    initializeUtilities().then(() => {
        updateStatistics();
    });
    
    // Add event listeners for reset buttons
    if (resetCounterBtn) {
        resetCounterBtn.addEventListener('click', function() {
            resetCounter();
        });
    }
    
    if (resetTimerBtn) {
        resetTimerBtn.addEventListener('click', function() {
            resetTimer();
        });
    }
    
    if (resetCounterBtnLarge) {
        resetCounterBtnLarge.addEventListener('click', function() {
            resetCounter();
        });
    }
    
    if (resetTimerBtnLarge) {
        resetTimerBtnLarge.addEventListener('click', function() {
            resetTimer();
        });
    }
    
    if (resetAllBtn) {
        resetAllBtn.addEventListener('click', function() {
            resetAllStats();
        });
    }
    
    /**
     * Helper function to format time as HH:MM:SS
     * 
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
     * Updates the timer display and progress bar if they exist
     * 
     * @returns {void}
     */
    function updateFiringTimer() {
        if (firingTimerActive) {
            const currentTime = Date.now();
            currentFiringTime = currentTime - firingStartTime;
            const formattedTime = formatTime(currentFiringTime);
            
            if (document.getElementById('firing-time-display')) {
                document.getElementById('firing-time-display').textContent = formattedTime;
            }
            
            // Update progress bar if it exists
            if (document.getElementById('firing-progress')) {
                // Limit progress bar to 100% after 5 minutes (300000ms)
                const progressPercent = Math.min(100, (currentFiringTime / 300000) * 100);
                document.getElementById('firing-progress').style.width = `${progressPercent}%`;
            }
        }
    }
    
    /**
     * Start the firing timer and update UI elements
     * 
     * @returns {void}
     */
    function startFiringTimer() {
        firingTimerActive = true;
        firingStartTime = Date.now();
        
        // Update firing status elements
        if (document.getElementById('firing-status')) {
            document.getElementById('firing-status').textContent = 'Firing';
        }
        
        if (document.getElementById('firing-status-icon')) {
            const icon = document.getElementById('firing-status-icon').querySelector('i');
            if (icon) {
                icon.className = 'fas fa-fire-alt text-danger fa-2x';
            }
        }
        
        // Start the timer interval
        firingTimerInterval = setInterval(updateFiringTimer, 100);
    }
    
    /**
     * Stop the firing timer and update statistics
     * 
     * @returns {void}
     */
    function stopFiringTimer() {
        if (firingTimerActive) {
            firingTimerActive = false;
            clearInterval(firingTimerInterval);
            
            // Update session counters
            const firingDuration = currentFiringTime;
            if (firingDuration >= 2000) {  // Only count if over 2 seconds
                sessionFiringCount++;
                sessionFiringTimeMs += firingDuration;
                
                // Update session displays
                sessionFireCount.textContent = sessionFiringCount;
                sessionFireTime.textContent = formatTime(sessionFiringTimeMs);
                
                // Add to log
                addLogMessage(`Firing completed: ${formatTime(firingDuration)} duration`);
            }
            
            // Reset the timer display
            if (document.getElementById('firing-time-display')) {
                document.getElementById('firing-time-display').textContent = '00:00:00';
            }
            
            // Reset progress bar
            if (document.getElementById('firing-progress')) {
                document.getElementById('firing-progress').style.width = '0%';
            }
            
            // Update firing status elements
            if (document.getElementById('firing-status')) {
                document.getElementById('firing-status').textContent = 'Not Firing';
            }
            
            if (document.getElementById('firing-status-icon')) {
                const icon = document.getElementById('firing-status-icon').querySelector('i');
                if (icon) {
                    icon.className = 'fas fa-fire-alt text-secondary fa-2x';
                }
            }
            
            // Update the statistics from the server to get the latest values
            updateStatistics();
        }
    }
    
    /**
     * Check servo status and update firing timer accordingly
     * 
     * @returns {void}
     */
    function updateServoStatus() {
        fetch('/servo/status')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Check if the servo is at position B (firing position)
                    const isFiring = (data.current_position === data.position_b);
                    
                    // Update the firing timer
                    if (isFiring && !firingTimerActive) {
                        startFiringTimer();
                    } else if (!isFiring && firingTimerActive) {
                        stopFiringTimer();
                    }
                }
            })
            .catch(error => handleError(error, addLogMessage));
    }
    
    /**
     * Update statistics from server
     * 
     * @returns {void}
     */
    function updateStatistics() {
        fetch('/statistics/data')
            .then(response => response.json())
            .then(data => {
                // Handle simulated response
                if (data.simulated) {
                    handleSimulationResponse(
                        data, 
                        'Statistics update', 
                        addLogMessage,
                        addSimulationWarning,
                        addSimulationError,
                        clearSimulationWarnings
                    );
                }
                
                if (data.status === 'success') {
                    // Update the statistics displays
                    laserFireCount.textContent = data.laser_fire_count;
                    totalFireTime.textContent = formatTime(data.total_laser_fire_time);
                    totalFireTimeMs.textContent = `${data.total_laser_fire_time} ms`;
                }
            })
            .catch(error => handleError(error, addLogMessage));
    }
    
    /**
     * Reset the laser fire counter
     * 
     * @returns {void}
     */
    function resetCounter() {
        setButtonsState(false, resetCounterBtn, resetCounterBtnLarge, resetAllBtn);
        
        fetch('/statistics/reset_counter', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    laserFireCount.textContent = '0';
                    addLogMessage('Laser fire counter reset to zero', false, 'success');
                } else {
                    addLogMessage(`Error: ${data.message}`, true);
                }
                setButtonsState(true, resetCounterBtn, resetCounterBtnLarge, resetAllBtn);
            })
            .catch(error => {
                handleError(error, addLogMessage, () => {
                    setButtonsState(true, resetCounterBtn, resetCounterBtnLarge, resetAllBtn);
                });
            });
    }
    
    /**
     * Reset the laser fire timer
     * 
     * @returns {void}
     */
    function resetTimer() {
        setButtonsState(false, resetTimerBtn, resetTimerBtnLarge, resetAllBtn);
        
        fetch('/statistics/reset_timer', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    totalFireTime.textContent = '00:00:00';
                    totalFireTimeMs.textContent = '0 ms';
                    addLogMessage('Laser fire timer reset to zero', false, 'success');
                } else {
                    addLogMessage(`Error: ${data.message}`, true);
                }
                setButtonsState(true, resetTimerBtn, resetTimerBtnLarge, resetAllBtn);
            })
            .catch(error => {
                handleError(error, addLogMessage, () => {
                    setButtonsState(true, resetTimerBtn, resetTimerBtnLarge, resetAllBtn);
                });
            });
    }
    
    /**
     * Reset all statistics (counter, timer, and session data)
     * 
     * @returns {void}
     */
    function resetAllStats() {
        setButtonsState(false, resetCounterBtn, resetTimerBtn, resetCounterBtnLarge, resetTimerBtnLarge, resetAllBtn);
        
        fetch('/statistics/reset_all', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    laserFireCount.textContent = '0';
                    totalFireTime.textContent = '00:00:00';
                    totalFireTimeMs.textContent = '0 ms';
                    sessionFiringCount = 0;
                    sessionFiringTimeMs = 0;
                    sessionFireCount.textContent = '0';
                    sessionFireTime.textContent = '00:00:00';
                    addLogMessage('All laser statistics reset to zero', false, 'success');
                } else {
                    addLogMessage(`Error: ${data.message}`, true);
                }
                setButtonsState(true, resetCounterBtn, resetTimerBtn, resetCounterBtnLarge, resetTimerBtnLarge, resetAllBtn);
            })
            .catch(error => {
                handleError(error, addLogMessage, () => {
                    setButtonsState(true, resetCounterBtn, resetTimerBtn, resetCounterBtnLarge, resetTimerBtnLarge, resetAllBtn);
                });
            });
    }
    
    /**
     * Add simulation warning to the UI
     * 
     * @param {string} message - The warning message 
     * @returns {void}
     */
    function addSimulationWarning(message) {
        const warningContainer = document.getElementById('simulation-warnings');
        if (warningContainer) {
            if (warningContainer.querySelector('.sim-warning[data-message="' + message + '"]')) {
                return; // Warning already exists
            }
            
            const warningElement = document.createElement('div');
            warningElement.className = 'alert alert-warning sim-warning';
            warningElement.dataset.message = message;
            warningElement.textContent = message;
            warningContainer.appendChild(warningElement);
            warningContainer.style.display = 'block';
        }
    }
    
    /**
     * Add simulation error to the UI
     * 
     * @param {string} message - The error message
     * @returns {void}
     */
    function addSimulationError(message) {
        const warningContainer = document.getElementById('simulation-warnings');
        if (warningContainer) {
            if (warningContainer.querySelector('.sim-error[data-message="' + message + '"]')) {
                return; // Error already exists
            }
            
            const errorElement = document.createElement('div');
            errorElement.className = 'alert alert-danger sim-error';
            errorElement.dataset.message = message;
            errorElement.textContent = message;
            warningContainer.appendChild(errorElement);
            warningContainer.style.display = 'block';
        }
    }
    
    /**
     * Clear all simulation warnings in the UI
     * 
     * @returns {void}
     */
    function clearSimulationWarnings() {
        const warningContainer = document.getElementById('simulation-warnings');
        if (warningContainer) {
            warningContainer.innerHTML = '';
            warningContainer.style.display = 'none';
        }
    }
    
    /**
     * Add a message to the log
     * 
     * @param {string} message - The message to log
     * @param {boolean} isError - Whether this is an error message
     * @param {string} [type='info'] - Type of message (info, success, warning, danger)
     * @returns {void}
     */
    function addLogMessage(message, isError = false, type = 'info') {
        const logContainer = document.getElementById('log-container');
        if (logContainer) {
            const logEntry = document.createElement('div');
            
            // Set classes based on message type
            let className = 'log-entry';
            if (isError || type === 'danger') {
                className += ' text-danger';
            } else if (type === 'warning') {
                className += ' text-warning';
            } else if (type === 'success') {
                className += ' text-success';
            }
            
            logEntry.className = className;
            
            const timestamp = new Date().toLocaleTimeString();
            logEntry.innerHTML = `<small>${timestamp}</small> ${message}`;
            
            logContainer.appendChild(logEntry);
            logContainer.scrollTop = logContainer.scrollHeight;
            
            // Limit the number of log entries
            while (logContainer.children.length > 100) {
                logContainer.removeChild(logContainer.firstChild);
            }
        }
    }
    
    // Check for firing status periodically
    setInterval(updateServoStatus, 500);
    
    // Update statistics periodically
    setInterval(updateStatistics, 5000);
});