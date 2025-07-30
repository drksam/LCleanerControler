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
    const laserFireTime = document.getElementById('total-fire-time');
    const sessionFireCount = document.getElementById('session-fire-count');
    const sessionFireTime = document.getElementById('session-fire-time');
    const resetCountButton = document.getElementById('reset-counter-btn-large');
    const resetTimeButton = document.getElementById('reset-timer-btn-large');
    const resetAllButton = document.getElementById('reset-all-btn');

    // Session tracking variables
    let sessionFiringCount = 0;
    let sessionFiringTimeMs = 0;
    let lastTotalCount = 0;
    let lastTotalTimeMs = 0;
    let sessionInitialized = false;

    /**
     * Format milliseconds to HH:MM:SS format
     * 
     * @param {number} ms - Milliseconds to format
     * @returns {string} - Formatted time string
     */
    function formatTime(ms) {
        console.log('formatTime called with ms:', ms, 'type:', typeof ms);
        
        // Ensure ms is a number
        const msNum = Number(ms);
        if (isNaN(msNum)) {
            console.error('formatTime received invalid number:', ms);
            return '00:00:00';
        }
        
        const seconds = Math.floor(msNum / 1000);
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        
        const result = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        console.log('formatTime result:', result, 'from', msNum, 'ms =>', seconds, 'seconds');
        
        return result;
    }

    /**
     * Update statistics display from server data
     * 
     * @returns {void}
     */
    function updateStatisticsFromServer() {
        fetch('/statistics/data')
            .then(response => response.json())
            .then(data => {
                console.log('Statistics data received:', data);
                
                // Update total statistics display
                if (laserFireCount) {
                    laserFireCount.textContent = data.laser_fire_count || 0;
                    console.log('Updated laser fire count to:', data.laser_fire_count);
                }
                if (laserFireTime) {
                    const totalTimeMs = data.total_laser_fire_time || 0;
                    console.log('Processing laser fire time:', {
                        rawValue: data.total_laser_fire_time,
                        processedValue: totalTimeMs,
                        type: typeof totalTimeMs
                    });
                    
                    const formattedTime = formatTime(totalTimeMs);
                    laserFireTime.textContent = formattedTime;
                    console.log('Updated laser fire time to:', formattedTime, '(from', totalTimeMs, 'ms)');
                    console.log('laserFireTime element:', laserFireTime, 'innerHTML:', laserFireTime.innerHTML);
                } else {
                    console.error('laserFireTime element not found!');
                }

                // Track session statistics using backend changes AND fetch real session data
                trackSessionFromTotalStats(data.laser_fire_count || 0, data.total_laser_fire_time || 0);
                fetchCurrentSessionStats();
            })
            .catch(error => {
                console.error('Error fetching statistics:', error);
                displaySimulationWarning('Failed to fetch statistics from server');
            });
    }

    /**
     * Track session statistics by monitoring changes in total statistics
     * This replaces the previous servo-dependent approach
     * 
     * @param {number} currentTotalCount - Current total fire count from server
     * @param {number} currentTotalTimeMs - Current total fire time in milliseconds
     * @returns {void}
     */
    function trackSessionFromTotalStats(currentTotalCount, currentTotalTimeMs) {
        if (!sessionInitialized) {
            // Initialize session tracking with current totals
            lastTotalCount = currentTotalCount;
            lastTotalTimeMs = currentTotalTimeMs;
            sessionInitialized = true;
            console.log('Session tracking initialized:', { lastTotalCount, lastTotalTimeMs });
            return;
        }

        // Check for increases in total statistics (indicates new firing activity)
        const countIncrease = currentTotalCount - lastTotalCount;
        const timeIncrease = currentTotalTimeMs - lastTotalTimeMs;

        if (countIncrease > 0 || timeIncrease > 0) {
            // Add increases to session totals
            sessionFiringCount += countIncrease;
            sessionFiringTimeMs += timeIncrease;

            console.log('Session updated:', {
                countIncrease,
                timeIncrease,
                newSessionCount: sessionFiringCount,
                newSessionTime: formatTime(sessionFiringTimeMs)
            });

            // Update session display
            if (sessionFireCount) {
                sessionFireCount.textContent = sessionFiringCount;
                console.log('Updated session fire count display to:', sessionFiringCount);
            }
            if (sessionFireTime) {
                const formattedSessionTime = formatTime(sessionFiringTimeMs);
                sessionFireTime.textContent = formattedSessionTime;
                console.log('Updated session fire time display to:', formattedSessionTime);
            }

            // Update last known totals
            lastTotalCount = currentTotalCount;
            lastTotalTimeMs = currentTotalTimeMs;
        }
    }

    /**
     * Fetch current session statistics from the server (real session data)
     * This replaces the local tracking when available
     */
    function fetchCurrentSessionStats() {
        fetch('/api/sessions/current')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.session) {
                    const session = data.session;
                    
                    // Update session display with real data
                    if (sessionFireCount) {
                        sessionFireCount.textContent = session.session_fire_count || 0;
                        console.log('Updated session fire count from server:', session.session_fire_count);
                    }
                    if (sessionFireTime) {
                        const sessionTimeMs = session.session_fire_time_ms || 0;
                        sessionFireTime.textContent = formatTime(sessionTimeMs);
                        console.log('Updated session fire time from server:', formatTime(sessionTimeMs));
                    }
                    
                    // Update local tracking to match server (prevents drift)
                    sessionFiringCount = session.session_fire_count || 0;
                    sessionFiringTimeMs = session.session_fire_time_ms || 0;
                    
                    console.log('Session stats synced with server:', {
                        count: sessionFiringCount,
                        time: formatTime(sessionFiringTimeMs)
                    });
                } else {
                    console.log('No active session found on server');
                }
            })
            .catch(error => {
                console.warn('Could not fetch current session stats:', error);
            });
    }

    /**
     * Reset the laser fire counter
     * 
     * @returns {void}
     */
    function resetCounter() {
        fetch('/statistics/reset_counter', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                console.log('Counter reset successfully');
                updateStatisticsFromServer(); // Refresh display
            } else {
                console.error('Failed to reset counter:', data.message);
            }
        })
        .catch(error => {
            console.error('Error resetting counter:', error);
        });
    }

    /**
     * Reset the laser fire timer
     * 
     * @returns {void}
     */
    function resetTimer() {
        fetch('/statistics/reset_timer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                console.log('Timer reset successfully');
                updateStatisticsFromServer(); // Refresh display
            } else {
                console.error('Failed to reset timer:', data.message);
            }
        })
        .catch(error => {
            console.error('Error resetting timer:', error);
        });
    }

    /**
     * Reset all statistics
     * 
     * @returns {void}
     */
    function resetAll() {
        fetch('/statistics/reset_all', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                console.log('All statistics reset successfully');
                // Reset session tracking as well
                sessionFiringCount = 0;
                sessionFiringTimeMs = 0;
                sessionInitialized = false;
                updateStatisticsFromServer(); // Refresh display
            } else {
                console.error('Failed to reset all statistics:', data.message);
            }
        })
        .catch(error => {
            console.error('Error resetting all statistics:', error);
        });
    }

    // Event listeners for reset buttons
    if (resetCountButton) {
        resetCountButton.addEventListener('click', function() {
            if (confirm('Are you sure you want to reset the laser fire counter?')) {
                resetCounter();
            }
        });
    }

    if (resetTimeButton) {
        resetTimeButton.addEventListener('click', function() {
            if (confirm('Are you sure you want to reset the laser fire timer?')) {
                resetTimer();
            }
        });
    }

    if (resetAllButton) {
        resetAllButton.addEventListener('click', function() {
            if (confirm('Are you sure you want to reset ALL statistics? This cannot be undone.')) {
                resetAll();
            }
        });
    }

    // Add event listeners for small reset buttons too
    const resetCountSmall = document.getElementById('reset-counter-btn');
    const resetTimeSmall = document.getElementById('reset-timer-btn');
    
    if (resetCountSmall) {
        resetCountSmall.addEventListener('click', function() {
            if (confirm('Are you sure you want to reset the laser fire counter?')) {
                resetCounter();
            }
        });
    }

    if (resetTimeSmall) {
        resetTimeSmall.addEventListener('click', function() {
            if (confirm('Are you sure you want to reset the laser fire timer?')) {
                resetTimer();
            }
        });
    }

    /**
     * Display a simulation warning in the UI
     * 
     * @param {string} message - Warning message to display
     * @returns {void}
     */
    function displaySimulationWarning(message) {
        const warningContainer = document.getElementById('simulation-warnings');
        if (warningContainer) {
            const errorElement = document.createElement('div');
            errorElement.className = 'alert alert-warning alert-dismissible fade show';
            errorElement.setAttribute('role', 'alert');
            errorElement.dataset.message = message;
            errorElement.innerHTML = `
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            `;
            
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

    // Update statistics periodically (reduced frequency to avoid server load)
    setInterval(updateStatisticsFromServer, 5000); // Changed from 2000ms to 5000ms (5 seconds)

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

    // Initial load
    updateStatisticsFromServer();
});
