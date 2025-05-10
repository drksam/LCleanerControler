/**
 * Temperature Control JavaScript
 * Manages temperature monitoring and configuration
 */
document.addEventListener('DOMContentLoaded', function() {
    // Track the current operation mode
    let currentOperationMode = 'unknown';
    
    // Get the system operation mode first
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
    
    // Initialize temperature monitoring
    window.lastHighTempAlert = 0; // Timestamp to prevent log spam
    window.lastTemperatureData = null; // Cache temperature data to prevent flickering
    
    // Function to add simulation warning or error
    function addSimulationWarning(message) {
        // Remove any existing warning first
        clearSimulationWarnings();
        
        // Create a new warning alert
        const warningDiv = document.createElement('div');
        warningDiv.className = 'alert alert-warning simulation-warning mt-3';
        warningDiv.innerHTML = '<i class="fas fa-exclamation-triangle me-2"></i>' + message;
        
        // Insert at the top of the temperature monitoring card
        const tempCard = document.querySelector('#temperature-monitoring-card .card-body');
        if (tempCard) {
            tempCard.insertBefore(warningDiv, tempCard.firstChild);
        }
    }
    
    function addSimulationError(message) {
        // Remove any existing warning first
        clearSimulationWarnings();
        
        // Create a new error alert
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger simulation-warning mt-3';
        errorDiv.innerHTML = '<i class="fas fa-exclamation-triangle me-2"></i>' + message;
        
        // Insert at the top of the temperature monitoring card
        const tempCard = document.querySelector('#temperature-monitoring-card .card-body');
        if (tempCard) {
            tempCard.insertBefore(errorDiv, tempCard.firstChild);
        }
    }
    
    function clearSimulationWarnings() {
        document.querySelectorAll('.simulation-warning').forEach(el => el.remove());
    }
    
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
                
                // Check if we have simulation data and handle appropriately
                if (data.simulated) {
                    // For simulation mode, this is expected
                    if (currentOperationMode === 'simulation') {
                        console.log('Temperature data is simulated (expected in simulation mode)');
                    } 
                    // For prototype mode, this should NEVER happen
                    else if (currentOperationMode === 'prototype') {
                        console.error('ERROR: Temperature simulation in PROTOTYPE MODE. Hardware is required!');
                        addSimulationError('HARDWARE ERROR: Receiving simulated temperature values in PROTOTYPE MODE. Check your hardware connections.');
                        
                        // Add to status log if available
                        const log = document.getElementById('status-log');
                        if (log) {
                            const now = new Date();
                            const timeString = now.toLocaleTimeString();
                            
                            const logEntry = document.createElement('p');
                            logEntry.classList.add('mb-1', 'text-danger');
                            logEntry.innerHTML = `<strong>${timeString}:</strong> ERROR: Temperature sensors are simulated in PROTOTYPE MODE`;
                            
                            log.appendChild(logEntry);
                            log.scrollTop = log.scrollHeight;
                        }
                    } 
                    // For normal mode, it's a warning
                    else {
                        console.warn('WARNING: Temperature data is simulated due to hardware error');
                        addSimulationWarning('Hardware error detected - showing simulated temperature values');
                        
                        // Add to status log if available
                        const log = document.getElementById('status-log');
                        if (log && (!window.lastSimWarning || (Date.now() - window.lastSimWarning) > 60000)) {
                            window.lastSimWarning = Date.now();
                            const now = new Date();
                            const timeString = now.toLocaleTimeString();
                            
                            const logEntry = document.createElement('p');
                            logEntry.classList.add('mb-1', 'text-warning');
                            logEntry.innerHTML = `<strong>${timeString}:</strong> WARNING: Using simulated temperature values due to hardware error`;
                            
                            log.appendChild(logEntry);
                            log.scrollTop = log.scrollHeight;
                        }
                    }
                } else if (data.status === 'success') {
                    // Clear any warnings if getting real hardware data
                    clearSimulationWarnings();
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
                    
                    // Add simulation indicator if data is simulated
                    if (data.simulated) {
                        temperatureStatus.innerText += ' [SIM]';
                    }
                    
                    // Dispatch event for any components that need temperature updates
                    document.dispatchEvent(new CustomEvent('temperature-update', {
                        detail: {
                            temperature: highestTemp,
                            sensorName: highestTempName,
                            isHighTemp: data.high_temp_condition,
                            isSimulated: data.simulated
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
                            logEntry.innerHTML = `<strong>${timeString}:</strong> HIGH TEMPERATURE ALERT: ${highestTemp.toFixed(1)}°C on ${highestTempName}${data.simulated ? ' [SIMULATED]' : ''}`;
                            
                            log.appendChild(logEntry);
                            log.scrollTop = log.scrollHeight;
                            
                            // Also add normal log entry for temperature update
                            addTemperatureLogEntry(log, highestTemp, highestTempName, data.simulated);
                        }
                    } else {
                        // Add regular temperature update to log every 30 seconds
                        if (log && (!window.lastTempLog || (Date.now() - window.lastTempLog) > 30000)) {
                            addTemperatureLogEntry(log, highestTemp, highestTempName, data.simulated);
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
    function addTemperatureLogEntry(log, temperature, sensorName, isSimulated) {
        window.lastTempLog = Date.now();
        const now = new Date();
        const timeString = now.toLocaleTimeString();
        
        const logEntry = document.createElement('p');
        logEntry.classList.add('mb-1', 'text-light');
        logEntry.innerHTML = `<strong>${timeString}:</strong> Temperature: ${temperature.toFixed(1)}°C (${sensorName})${isSimulated ? ' [SIMULATED]' : ''}`;
        
        log.appendChild(logEntry);
        log.scrollTop = log.scrollHeight;
    }
    
    // Temperature configuration form handling for the temperature settings page
    const tempConfigForm = document.getElementById('temperature-config-form');
    if (tempConfigForm) {
        tempConfigForm.addEventListener('submit', function(event) {
            event.preventDefault();
            
            const formData = {
                high_limit: parseFloat(document.getElementById('high-temp-limit').value),
                monitoring_interval: parseFloat(document.getElementById('monitoring-interval').value),
                enabled: document.getElementById('monitoring-enabled').checked,
                primary_sensor: document.getElementById('primary-sensor').value
            };
            
            // Check sensor-specific limits
            const sensorLimits = {};
            document.querySelectorAll('.sensor-limit-input').forEach(function(input) {
                if (input.value) {
                    sensorLimits[input.dataset.sensorId] = parseFloat(input.value);
                }
            });
            
            if (Object.keys(sensorLimits).length > 0) {
                formData.sensor_limits = sensorLimits;
            }
            
            // Submit the configuration
            fetch('/temperature/update_config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Show success message
                    const alertDiv = document.createElement('div');
                    alertDiv.className = 'alert alert-success';
                    alertDiv.textContent = 'Temperature configuration updated successfully';
                    
                    const container = document.querySelector('.container');
                    container.insertBefore(alertDiv, container.firstChild);
                    
                    // Remove the alert after 3 seconds
                    setTimeout(() => {
                        alertDiv.remove();
                    }, 3000);
                } else {
                    // Show error message
                    alert('Error: ' + data.message);
                }
            })
            .catch(error => {
                alert('Error: ' + error.message);
            });
        });
    }
    
    // Sensor name editing
    document.querySelectorAll('.edit-sensor-name').forEach(function(button) {
        button.addEventListener('click', function() {
            const sensorId = this.dataset.sensorId;
            const currentName = document.getElementById(`sensor-name-${sensorId}`).textContent;
            
            const newName = prompt('Enter new name for sensor:', currentName);
            
            if (newName && newName.trim() !== '' && newName !== currentName) {
                fetch('/temperature/update_sensor_name', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        sensor_id: sensorId,
                        name: newName.trim()
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        // Update name in UI
                        document.getElementById(`sensor-name-${sensorId}`).textContent = newName;
                        
                        // Show success message
                        const alertDiv = document.createElement('div');
                        alertDiv.className = 'alert alert-success';
                        alertDiv.textContent = `Sensor renamed to "${newName}"`;
                        
                        const container = document.querySelector('.container');
                        container.insertBefore(alertDiv, container.firstChild);
                        
                        // Remove the alert after 3 seconds
                        setTimeout(() => {
                            alertDiv.remove();
                        }, 3000);
                    } else {
                        // Show error message
                        alert('Error: ' + data.message);
                    }
                })
                .catch(error => {
                    alert('Error: ' + error.message);
                });
            }
        });
    });
});