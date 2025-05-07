/**
 * GPIO Test Panel JavaScript
 * Handles the functionality for GPIO input monitoring and output control
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize status toast
    const statusToast = {
        element: document.getElementById('statusToast') || createStatusToast(),
        bodyElement: document.getElementById('statusToastBody'),
        
        show: function(message, isError = false) {
            // Set the toast content and styles
            this.bodyElement.textContent = message;
            
            if (isError) {
                this.element.classList.remove('bg-success');
                this.element.classList.add('bg-danger');
            } else {
                this.element.classList.remove('bg-danger');
                this.element.classList.add('bg-success');
            }
            
            // Show the toast using Bootstrap
            const bsToast = new bootstrap.Toast(this.element);
            bsToast.show();
        }
    };
    
    // Create a toast if it doesn't exist
    function createStatusToast() {
        const toast = document.createElement('div');
        toast.id = 'statusToast';
        toast.className = 'toast align-items-center text-white bg-success border-0 position-fixed bottom-0 end-0 m-3';
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        const flexDiv = document.createElement('div');
        flexDiv.className = 'd-flex';
        
        const body = document.createElement('div');
        body.id = 'statusToastBody';
        body.className = 'toast-body';
        
        const closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'btn-close btn-close-white me-2 m-auto';
        closeBtn.setAttribute('data-bs-dismiss', 'toast');
        closeBtn.setAttribute('aria-label', 'Close');
        
        flexDiv.appendChild(body);
        flexDiv.appendChild(closeBtn);
        toast.appendChild(flexDiv);
        
        document.body.appendChild(toast);
        return toast;
    }
    
    // Get references to all input and output buttons
    const refreshInputsButton = document.getElementById('refresh-inputs');
    
    // Fan control buttons
    const fanOnButton = document.getElementById('fan-on');
    const fanOffButton = document.getElementById('fan-off');
    
    // Lights control buttons
    const lightsOnButton = document.getElementById('lights-on');
    const lightsOffButton = document.getElementById('lights-off');
    
    // Table forward control buttons
    const tableForwardOnButton = document.getElementById('table-forward-on');
    const tableForwardOffButton = document.getElementById('table-forward-off');
    
    // Table backward control buttons
    const tableBackwardOnButton = document.getElementById('table-backward-on');
    const tableBackwardOffButton = document.getElementById('table-backward-off');
    
    // Attach event listeners to buttons if they exist
    if (refreshInputsButton) {
        refreshInputsButton.addEventListener('click', refreshInputStates);
    }
    
    // Fan control
    if (fanOnButton) {
        fanOnButton.addEventListener('click', function() {
            setOutput('fan', true);
        });
    }
    
    if (fanOffButton) {
        fanOffButton.addEventListener('click', function() {
            setOutput('fan', false);
        });
    }
    
    // Lights control
    if (lightsOnButton) {
        lightsOnButton.addEventListener('click', function() {
            setOutput('red_lights', true);
        });
    }
    
    if (lightsOffButton) {
        lightsOffButton.addEventListener('click', function() {
            setOutput('red_lights', false);
        });
    }
    
    // Table forward control
    if (tableForwardOnButton) {
        tableForwardOnButton.addEventListener('click', function() {
            setOutput('table_forward', true);
        });
    }
    
    if (tableForwardOffButton) {
        tableForwardOffButton.addEventListener('click', function() {
            setOutput('table_forward', false);
        });
    }
    
    // Table backward control
    if (tableBackwardOnButton) {
        tableBackwardOnButton.addEventListener('click', function() {
            setOutput('table_backward', true);
        });
    }
    
    if (tableBackwardOffButton) {
        tableBackwardOffButton.addEventListener('click', function() {
            setOutput('table_backward', false);
        });
    }
    
    // Function to refresh input states
    function refreshInputStates() {
        // Show loading indicator
        const refreshButton = document.getElementById('refresh-inputs');
        if (refreshButton) {
            refreshButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Refreshing...';
            refreshButton.disabled = true;
        }
        
        fetch('/api/gpio/inputs')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Update all GPIO input states by their pin number
                    Object.keys(data).forEach(key => {
                        if (key.startsWith('gpio') && key !== 'status' && key !== 'simulated') {
                            updateInputState(key + '-state', data[key]);
                        }
                    });
                    
                    // Show whether these are simulated values
                    if (data.simulated) {
                        statusToast.show('Input states refreshed (simulated values)', false);
                    } else {
                        statusToast.show('Input states refreshed from hardware pins', false);
                    }
                } else {
                    statusToast.show('Error refreshing inputs: ' + (data.message || 'Unknown error'), true);
                }
            })
            .catch(error => {
                console.error('Error fetching input states:', error);
                statusToast.show('Network error while refreshing inputs', true);
            })
            .finally(() => {
                // Restore button state
                if (refreshButton) {
                    refreshButton.innerHTML = '<i class="fas fa-sync-alt me-1"></i> Refresh Inputs';
                    refreshButton.disabled = false;
                }
            });
    }
    
    // Function to update a single input state
    function updateInputState(elementId, state) {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        if (state === null) {
            element.className = 'badge bg-dark';
            element.textContent = 'Unknown';
        } else if (state === true) {
            element.className = 'badge bg-success';
            element.textContent = 'HIGH';
        } else if (state === false) {
            element.className = 'badge bg-danger';
            element.textContent = 'LOW';
        }
    }
    
    // Function to set an output
    function setOutput(device, state) {
        fetch('/api/gpio/outputs', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                device: device,
                state: state
            }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                const deviceName = getDeviceDisplayName(device);
                const stateText = state ? 'ON' : 'OFF';
                statusToast.show(`${deviceName} set to ${stateText}${data.simulated ? ' (simulated)' : ''}`, false);
            } else {
                statusToast.show('Error: ' + (data.message || 'Unknown error'), true);
            }
        })
        .catch(error => {
            console.error('Error setting output:', error);
            statusToast.show('Network error while setting output', true);
        });
    }
    
    // Helper to get a nice display name for a device
    function getDeviceDisplayName(device) {
        const deviceNames = {
            'fan': 'Fan',
            'red_lights': 'Red Lights',
            'table_forward': 'Table Forward',
            'table_backward': 'Table Backward'
        };
        
        return deviceNames[device] || device;
    }
    
    // Initial state refresh when page loads
    refreshInputStates();
    
    // Set up automatic refresh every 3 seconds
    const autoRefreshInterval = setInterval(refreshInputStates, 3000);
    
    // Clean up on page unload
    window.addEventListener('beforeunload', function() {
        clearInterval(autoRefreshInterval);
    });
});