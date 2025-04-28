/**
 * Statistics JavaScript
 * Manages the display and control of laser usage statistics
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
    updateStatistics();
    
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
    
    // Helper function to format time as HH:MM:SS
    function formatTime(timeMs) {
        const totalSeconds = Math.floor(timeMs / 1000);
        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const seconds = totalSeconds % 60;
        
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
    
    // Function to update firing timer display while actively firing
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
    
    // Function to start firing timer
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
    
    // Function to stop firing timer
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
    
    // Function to check servo status
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
            .catch(error => {
                console.error('Error checking servo status:', error);
            });
    }
    
    // Function to update statistics from server
    function updateStatistics() {
        fetch('/statistics/data')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Update the statistics displays
                    laserFireCount.textContent = data.laser_fire_count;
                    totalFireTime.textContent = formatTime(data.total_laser_fire_time);
                    totalFireTimeMs.textContent = `${data.total_laser_fire_time} ms`;
                }
            })
            .catch(error => {
                console.error('Error updating statistics:', error);
                addLogMessage(`Error updating statistics: ${error.message}`, true);
            });
    }
    
    // Function to reset counter
    function resetCounter() {
        fetch('/statistics/reset_counter', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    laserFireCount.textContent = '0';
                    addLogMessage('Laser fire counter reset to zero');
                } else {
                    addLogMessage(`Error: ${data.message}`, true);
                }
            })
            .catch(error => {
                console.error('Error resetting counter:', error);
                addLogMessage(`Error resetting counter: ${error.message}`, true);
            });
    }
    
    // Function to reset timer
    function resetTimer() {
        fetch('/statistics/reset_timer', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    totalFireTime.textContent = '00:00:00';
                    totalFireTimeMs.textContent = '0 ms';
                    addLogMessage('Laser fire timer reset to zero');
                } else {
                    addLogMessage(`Error: ${data.message}`, true);
                }
            })
            .catch(error => {
                console.error('Error resetting timer:', error);
                addLogMessage(`Error resetting timer: ${error.message}`, true);
            });
    }
    
    // Function to reset all statistics
    function resetAllStats() {
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
                    addLogMessage('All laser statistics reset to zero');
                } else {
                    addLogMessage(`Error: ${data.message}`, true);
                }
            })
            .catch(error => {
                console.error('Error resetting all statistics:', error);
                addLogMessage(`Error resetting all statistics: ${error.message}`, true);
            });
    }
    
    // Add a message to the log
    function addLogMessage(message, isError = false) {
        const logContainer = document.getElementById('log-container');
        if (logContainer) {
            const logEntry = document.createElement('div');
            logEntry.className = isError ? 'log-entry text-danger' : 'log-entry';
            
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