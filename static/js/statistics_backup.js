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
    
    // Session variables (for tracking current browser session)
    let sessionFiringCount = 0;
    let sessionFiringTimeMs = 0;
    
    // Debug: Check if session elements are found
    console.log('Session elements found:');
    console.log('sessionFireCount:', sessionFireCount ? 'YES' : 'NO');
    console.log('sessionFireTime:', sessionFireTime ? 'YES' : 'NO');
    
    // Initialize
    initializeUtilities().then(() => {
        updateStatistics();
        
        // Test session display update
        console.log('Testing session display update...');
        if (sessionFireCount && sessionFireTime) {
            // Add a test function to window for manual testing
            window.testSessionUpdate = function(count, timeMs) {
                sessionFiringCount = count || 1;
                sessionFiringTimeMs = timeMs || 5000;
                sessionFireCount.textContent = sessionFiringCount;
                sessionFireTime.textContent = formatTime(sessionFiringTimeMs);
                console.log('Test session update applied:', sessionFiringCount, formatTime(sessionFiringTimeMs));
            };
            console.log('Test function added: window.testSessionUpdate(count, timeMs)');
        } else {
            console.error('Session elements not found for testing');
        }
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
     * Reset the laser fire counter
     * 
     * @returns {void}
     */
    function resetCounter() {    /**
     * Update statistics from server and handle session tracking
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
                    
                    // Track session statistics based on changes in total statistics
                    trackSessionFromTotalStats(data.laser_fire_count, data.total_laser_fire_time);
                }
            })
            .catch(error => handleError(error, addLogMessage));
    }
    
    // Variables to track previous values for session calculation
    let lastKnownCount = 0;
    let lastKnownTime = 0;
    let sessionInitialized = false;
    
    /**
     * Track session statistics by monitoring changes in total statistics
     * This is more reliable than servo position detection
     */
    function trackSessionFromTotalStats(currentCount, currentTime) {
        if (!sessionInitialized) {
            // Initialize session tracking with current values
            lastKnownCount = currentCount;
            lastKnownTime = currentTime;
            sessionInitialized = true;
            console.log('Session tracking initialized:', { count: currentCount, time: currentTime });
            return;
        }
        
        // Check for increases in count or time
        const countIncrease = currentCount - lastKnownCount;
        const timeIncrease = currentTime - lastKnownTime;
        
        if (countIncrease > 0) {
            sessionFiringCount += countIncrease;
            console.log('Session count increased by:', countIncrease, 'Total session count:', sessionFiringCount);
            
            if (sessionFireCount) {
                sessionFireCount.textContent = sessionFiringCount;
            }
            
            addLogMessage(`Session: +${countIncrease} firing(s) detected (total: ${sessionFiringCount})`, false, 'info');
        }
        
        if (timeIncrease > 0) {
            sessionFiringTimeMs += timeIncrease;
            console.log('Session time increased by:', timeIncrease, 'ms. Total session time:', sessionFiringTimeMs, 'ms');
            
            if (sessionFireTime) {
                sessionFireTime.textContent = formatTime(sessionFiringTimeMs);
            }
            
            addLogMessage(`Session: +${formatTime(timeIncrease)} firing time (total: ${formatTime(sessionFiringTimeMs)})`, false, 'info');
        }
        
        // Update last known values
        lastKnownCount = currentCount;
        lastKnownTime = currentTime;
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
    
    // Make addLogMessage available globally
    window.addLogMessage = addLogMessage;
    
    // Update statistics periodically (more frequently to catch session changes)
    setInterval(updateStatisticsFromServer, 2000);
    
    // Add debugging functions to window for manual testing
    window.debugStatistics = {
        testSessionUpdate: function(count, timeMs) {
            if (sessionFireCount && sessionFireTime) {
                sessionFiringCount = count || 1;
                sessionFiringTimeMs = timeMs || 5000;
                sessionFireCount.textContent = sessionFiringCount;
                sessionFireTime.textContent = formatTime(sessionFiringTimeMs);
                console.log('Manual session update:', sessionFiringCount, formatTime(sessionFiringTimeMs));
                return true;
            } else {
                console.error('Session elements not found');
                return false;
            }
        },
        getCurrentSession: function() {
            return {
                count: sessionFiringCount,
                timeMs: sessionFiringTimeMs,
                initialized: sessionInitialized
            };
        },
        resetSession: function() {
            sessionFiringCount = 0;
            sessionFiringTimeMs = 0;
            if (sessionFireCount) sessionFireCount.textContent = '0';
            if (sessionFireTime) sessionFireTime.textContent = '00:00:00';
            console.log('Session reset manually');
        },
        forceUpdate: function() {
            updateStatisticsFromServer();
            console.log('Forced statistics update');
        }
    };
    
    console.log('Debug functions available: window.debugStatistics');
});