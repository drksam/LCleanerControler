/**
 * Temperature Control JavaScript
 * Manages temperature monitoring and configuration
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize temperature monitoring
    window.lastHighTempAlert = 0; // Timestamp to prevent log spam
    window.lastTemperatureData = null; // Cache temperature data to prevent flickering
    
    // Update temperature status on load
    if (document.getElementById('temperature-status')) {
        updateTemperatureStatus();
        
        // Update temperature status every 10 seconds (increased from 5 to reduce flickering)
        setInterval(updateTemperatureStatus, 10000);
    }
    
    // Temperature monitoring function for main interface
    function updateTemperatureStatus() {
        fetch('/temperature/status')
            .then(response => response.json())
            .then(data => {
                const temperatureIcon = document.getElementById('temperature-status-icon');
                const temperatureStatus = document.getElementById('temperature-status');
                
                if (!temperatureIcon || !temperatureStatus) {
                    return; // Elements not found in the current page
                }
                
                // Cache the data for use between updates
                window.lastTemperatureData = data;
                
                // Check for the correct data structure (could be sensors or temperatures)
                const sensors = data.sensors || data.temperatures || {};
                
                // Check if we have temperature data
                if (Object.keys(sensors).length > 0) {
                    // Find the highest temperature
                    let highestTemp = -Infinity;
                    let highestTempName = "";
                    
                    for (const sensorId in sensors) {
                        const sensor = sensors[sensorId];
                        // Handle different API response formats (temp vs temperature)
                        const temperature = sensor.temperature !== undefined ? sensor.temperature : sensor.temp;
                        
                        if (temperature > highestTemp) {
                            highestTemp = temperature;
                            highestTempName = sensor.name;
                        }
                    }
                    
                    // Determine status color based on highest temperature
                    let statusClass = 'bg-success';
                    let iconClass = 'text-success';
                    
                    if (data.high_temp_condition) {
                        // High temperature alert
                        statusClass = 'bg-danger';
                        iconClass = 'text-danger';
                    } else if (highestTemp > data.high_limit - 10) {
                        // Approaching high temperature
                        statusClass = 'bg-warning';
                        iconClass = 'text-warning';
                    }
                    
                    // Update the UI
                    temperatureIcon.innerHTML = `<i class="fas fa-thermometer-half fa-2x ${iconClass}"></i>`;
                    temperatureStatus.className = `badge ${statusClass}`;
                    temperatureStatus.innerText = `${highestTemp.toFixed(1)}°C (${highestTempName})`;
                    
                    // Dispatch event for any components that need temperature updates
                    document.dispatchEvent(new CustomEvent('temperature-update', {
                        detail: {
                            temperature: highestTemp,
                            sensorName: highestTempName,
                            isHighTemp: data.high_temp_condition
                        }
                    }));
                    
                    // Add to status log
                    const log = document.getElementById('status-log');
                    
                    // Add a warning to the log if there's a high temperature condition
                    if (data.high_temp_condition && (!window.lastHighTempAlert || 
                        (Date.now() - window.lastHighTempAlert) > 60000)) {
                        window.lastHighTempAlert = Date.now();
                        
                        // If status log exists, add message
                        if (log) {
                            const now = new Date();
                            const timeString = now.toLocaleTimeString();
                            
                            const logEntry = document.createElement('p');
                            logEntry.classList.add('mb-1', 'text-danger');
                            logEntry.innerHTML = `<strong>${timeString}:</strong> HIGH TEMPERATURE ALERT: ${highestTemp.toFixed(1)}°C on ${highestTempName}`;
                            
                            log.appendChild(logEntry);
                            log.scrollTop = log.scrollHeight;
                            
                            // Also add normal log entry for temperature update
                            addTemperatureLogEntry(log, highestTemp, highestTempName);
                        }
                    } else {
                        // Add regular temperature update to log every 30 seconds
                        if (log && (!window.lastTempLog || (Date.now() - window.lastTempLog) > 30000)) {
                            addTemperatureLogEntry(log, highestTemp, highestTempName);
                        }
                    }
                } else {
                    // No temperature data, but don't change display if we had data before (prevents flickering)
                    if (!window.lastTemperatureData || !window.lastTemperatureData.sensors) {
                        temperatureIcon.innerHTML = '<i class="fas fa-thermometer-half fa-2x text-secondary"></i>';
                        temperatureStatus.className = 'badge bg-secondary';
                        temperatureStatus.innerText = '--°C';
                    }
                    
                    // Log the error
                    const log = document.getElementById('status-log');
                    if (log && (!window.lastTempError || (Date.now() - window.lastTempError) > 60000)) {
                        window.lastTempError = Date.now();
                        const now = new Date();
                        const timeString = now.toLocaleTimeString();
                        
                        const logEntry = document.createElement('p');
                        logEntry.classList.add('mb-1', 'text-warning');
                        logEntry.innerHTML = `<strong>${timeString}:</strong> Could not retrieve temperature data`;
                        
                        log.appendChild(logEntry);
                        log.scrollTop = log.scrollHeight;
                    }
                }
            })
            .catch(error => {
                console.error('Error updating temperature status:', error);
                
                // If we have cached data, don't change the display (prevent flickering)
                if (!window.lastTemperatureData) {
                    const temperatureIcon = document.getElementById('temperature-status-icon');
                    const temperatureStatus = document.getElementById('temperature-status');
                    
                    if (temperatureIcon && temperatureStatus) {
                        temperatureIcon.innerHTML = '<i class="fas fa-thermometer-half fa-2x text-danger"></i>';
                        temperatureStatus.className = 'badge bg-danger';
                        temperatureStatus.innerText = 'Error';
                    }
                }
                
                // Log the error
                const log = document.getElementById('status-log');
                if (log && (!window.lastTempError || (Date.now() - window.lastTempError) > 60000)) {
                    window.lastTempError = Date.now();
                    const now = new Date();
                    const timeString = now.toLocaleTimeString();
                    
                    const logEntry = document.createElement('p');
                    logEntry.classList.add('mb-1', 'text-danger');
                    logEntry.innerHTML = `<strong>${timeString}:</strong> Error retrieving temperature data: ${error.message}`;
                    
                    log.appendChild(logEntry);
                    log.scrollTop = log.scrollHeight;
                }
            });
    }
    
    // Helper function to add temperature update to log
    function addTemperatureLogEntry(log, temperature, sensorName) {
        window.lastTempLog = Date.now();
        const now = new Date();
        const timeString = now.toLocaleTimeString();
        
        const logEntry = document.createElement('p');
        logEntry.classList.add('mb-1', 'text-light');
        logEntry.innerHTML = `<strong>${timeString}:</strong> Temperature: ${temperature.toFixed(1)}°C (${sensorName})`;
        
        log.appendChild(logEntry);
        log.scrollTop = log.scrollHeight;
    }
});