/**
 * Temperature Control JavaScript
 * Manages temperature monitoring and configuration
 * Uses shared temperature monitoring utilities from utility.js
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize temperature monitoring if the UI elements are present
    if (document.getElementById('temperature-status')) {
        // Access shared temperature utilities
        const {
            setupTemperatureMonitoring,
            updateTemperatureStatus,
            temperatureState
        } = window.ShopUtils || {};
        
        if (setupTemperatureMonitoring) {
            // Set up temperature monitoring with a 10-second interval
            setupTemperatureMonitoring(10000, {
                statusSelector: '#temperature-status',
                iconSelector: '#temperature-status-icon',
                logSelector: '#status-log',
                warningSelector: '#temperature-monitoring-card .card-body'
            });
        } else {
            // Fall back to direct update if ShopUtils is not available
            console.warn('ShopUtils not available, falling back to direct temperature update');
            updateTemperatureStatusLegacy();
            
            // Update temperature status every 10 seconds
            setInterval(updateTemperatureStatusLegacy, 10000);
        }
    }
    
    // Legacy function for temperature monitoring if utility.js is not loaded
    // This is a fallback implementation
    function updateTemperatureStatusLegacy() {
        console.warn('Using legacy temperature monitoring');
        fetch('/temperature/status')
            .then(response => response.json())
            .then(data => {
                const temperatureIcon = document.getElementById('temperature-status-icon');
                const temperatureStatus = document.getElementById('temperature-status');
                
                if (!temperatureIcon || !temperatureStatus) {
                    return;
                }
                
                // Use simplified temperature display for legacy mode
                if (data.sensors && Object.keys(data.sensors).length > 0) {
                    let highestTemp = -Infinity;
                    let highestTempName = "";
                    
                    for (const sensorId in data.sensors) {
                        const sensor = data.sensors[sensorId];
                        const temperature = sensor.temperature || sensor.temp;
                        
                        if (temperature > highestTemp) {
                            highestTemp = temperature;
                            highestTempName = sensor.name;
                        }
                    }
                    
                    temperatureIcon.innerHTML = `<i class="fas fa-thermometer-half fa-2x"></i>`;
                    temperatureStatus.innerText = `${highestTemp.toFixed(1)}°C (${highestTempName})`;
                    
                    if (data.simulated) {
                        temperatureStatus.innerText += ' [SIM]';
                    }
                } else {
                    temperatureIcon.innerHTML = '<i class="fas fa-thermometer-half fa-2x text-secondary"></i>';
                    temperatureStatus.className = 'badge bg-secondary';
                    temperatureStatus.innerText = '--°C';
                }
            })
            .catch(error => {
                console.error('Error updating temperature status:', error);
            });
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
            
            // Use the shared makeRequest utility if available
            const makeRequest = window.ShopUtils?.makeRequest || function(url, method, data) {
                return fetch(url, {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                }).then(response => response.json());
            };
            
            // Submit the configuration
            makeRequest('/temperature/update_config', 'POST', formData)
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
                    alert('Error: ' + (error.message || 'Unknown error'));
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
                // Use the shared makeRequest utility if available
                const makeRequest = window.ShopUtils?.makeRequest || function(url, method, data) {
                    return fetch(url, {
                        method: method,
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(data)
                    }).then(response => response.json());
                };
                
                makeRequest('/temperature/update_sensor_name', 'POST', {
                    sensor_id: sensorId,
                    name: newName.trim()
                })
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
                    alert('Error: ' + (error.message || 'Unknown error'));
                });
            }
        });
    });
});