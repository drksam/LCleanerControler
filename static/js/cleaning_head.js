// Get steps per mm conversion factor
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

document.addEventListener('DOMContentLoaded', function() {
    // Use the global addLogMessage function from main.js
    // No need to define it here anymore

    // Current position update function
    function updatePositionDisplay(position) {
        const positionDisplay = document.getElementById('position-display');
        const positionProgress = document.getElementById('position-progress');
        
        if (positionDisplay) {
            positionDisplay.textContent = position;
        }
        
        if (positionProgress) {
            // Calculate percentage for progress bar (scale to MAX_POSITION)
            const MAX_POSITION = 1000;
            let percentage = (position / MAX_POSITION) * 100;
            
            // Ensure percentage is between 0 and 100
            percentage = Math.max(0, Math.min(100, percentage));
            
            positionProgress.style.width = `${percentage}%`;
            positionProgress.setAttribute('aria-valuenow', percentage);
        }
    }

    // Index Distance Update button
    const updateIndexDistanceBtn = document.getElementById('update-index-distance');
    const indexDistanceMmInput = document.getElementById('index-distance-mm');
    const indexDistanceStepsDisplay = document.getElementById('index-distance-steps-display');
    
    if (updateIndexDistanceBtn && indexDistanceMmInput) {
        updateIndexDistanceBtn.addEventListener('click', function() {
            const indexDistanceMm = parseFloat(indexDistanceMmInput.value);
            
            if (isNaN(indexDistanceMm) || indexDistanceMm <= 0) {
                addLogMessage('Please enter a valid index distance in millimeters.', true);
                return;
            }
            
            // Convert mm to steps
            const stepsPerMm = getStepsPerMm();
            const indexDistanceSteps = Math.round(indexDistanceMm * stepsPerMm);
            
            // Log the action
            addLogMessage(`Updating index distance to ${indexDistanceMm.toFixed(2)} mm...`, false, 'config');
            
            // Update the index distance using the config API
            fetch('/update_config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    section: 'stepper',
                    key: 'index_distance',
                    value: indexDistanceSteps
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    addLogMessage(`Index distance updated to ${indexDistanceMm.toFixed(2)} mm (${indexDistanceSteps} steps).`, false, 'success');
                    
                    // Update the display
                    if (indexDistanceStepsDisplay) {
                        indexDistanceStepsDisplay.textContent = indexDistanceSteps;
                    }
                } else {
                    addLogMessage('Error: ' + data.message, true);
                }
            })
            .catch(error => {
                addLogMessage('Error: ' + error.message, true);
            });
        });
    }

    // Index Forward button
    const indexButton = document.getElementById('index-button');
    
    if (indexButton) {
        indexButton.addEventListener('click', function() {
            addLogMessage('Indexing forward...', false, 'action');
            indexButton.disabled = true;
            
            fetch('/index_move', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    direction: 'forward'
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const currentPosition = data.position;
                    updatePositionDisplay(currentPosition);
                    addLogMessage('Index forward complete!', false, 'success');
                } else {
                    addLogMessage('Error: ' + data.message, true);
                }
            })
            .catch(error => {
                addLogMessage('Error: ' + error.message, true);
            })
            .finally(() => {
                if (indexButton) indexButton.disabled = false;
            });
        });
    }
    
    // Index Backward button
    const indexBackButton = document.getElementById('index-back-button');
    
    if (indexBackButton) {
        indexBackButton.addEventListener('click', function() {
            addLogMessage('Indexing backward...', false, 'action');
            indexBackButton.disabled = true;
            
            fetch('/index_move', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    direction: 'backward'
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const currentPosition = data.position;
                    updatePositionDisplay(currentPosition);
                    addLogMessage('Index backward complete!', false, 'success');
                } else {
                    addLogMessage('Error: ' + data.message, true);
                }
            })
            .catch(error => {
                addLogMessage('Error: ' + error.message, true);
            })
            .finally(() => {
                if (indexBackButton) indexBackButton.disabled = false;
            });
        });
    }
});