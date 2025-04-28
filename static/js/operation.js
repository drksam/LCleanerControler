/**
 * Operation Page JavaScript
 * Handles fire, fire fiber, and index operations on the main operation page
 */

document.addEventListener('DOMContentLoaded', function() {
    // Check if we have access to the unified logging system
    if (typeof window.addLogMessage !== 'function') {
        console.error('window.addLogMessage function not available - global logging will not work');
        
        // This should never happen with our current implementation, but just in case
        // the base template changes, we'll add a console-only fallback
        window.addLogMessage = function(message, isError = false, logType = 'info') {
            console.log(`Log message (${logType}): ${message}`);
        };
    } else {
        // Log that we're using the main logging function
        console.log("Using addLogMessage function from base.html");
    }
    
    // Add initialization log message
    window.addLogMessage('Operation controls initialized', false, 'info');
    
    // Fire and Fiber buttons
    const fireButton = document.getElementById('fire-button');
    const fireFiberButton = document.getElementById('fire-fiber-button');
    const stopFireButton = document.getElementById('stop-fire-button');
    
    // Index buttons
    const indexButton = document.getElementById('index-button');
    const indexBackButton = document.getElementById('index-back-button');
    
    // Home and stop cleaning head buttons
    const homeCleaningHeadButton = document.getElementById('home-cleaning-head');
    const stopCleaningHeadButton = document.getElementById('stop-cleaning-head');
    
    // Table control buttons
    const runTableButton = document.getElementById('run-table-button');
    const stopTableButton = document.getElementById('stop-table-button');
    
    // Status indicators
    const firingStatus = document.getElementById('firing-status');
    const firingProgress = document.getElementById('firing-progress');
    const firingTimeDisplay = document.getElementById('firing-time-display');
    const cleaningHeadStatus = document.getElementById('cleaning-head-status');
    
    // Regular Fire Buttons (both toggle and momentary)
    const fireToggleButton = document.getElementById('fire-toggle-button');
    
    // Momentary Fire button (original behavior)
    if (fireButton && stopFireButton) {
        console.log("Fire button found and event listener attached");
        fireButton.addEventListener('click', function() {
            console.log("Fire button (momentary) clicked");
            window.addLogMessage('FIRING (momentary) - Moving servo to position B...', false, 'action');
            
            // Disable all fire buttons and enable stop button
            fireButton.disabled = true;
            if (fireToggleButton) fireToggleButton.disabled = true;
            if (fireFiberButton) fireFiberButton.disabled = true;
            if (fireFiberToggleButton) fireFiberToggleButton.disabled = true;
            stopFireButton.disabled = false;
            
            // Update status
            if (firingStatus) {
                firingStatus.textContent = 'Firing';
                firingStatus.className = 'badge bg-danger';
            }
            
            fetch('/fire', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    mode: 'momentary'
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    window.addLogMessage('Firing initiated', false, 'success');
                } else {
                    window.addLogMessage(`Error initiating firing: ${data.message}`, true);
                    // Reset button states on error
                    fireButton.disabled = false;
                    if (fireToggleButton) fireToggleButton.disabled = false;
                    if (fireFiberButton) fireFiberButton.disabled = false;
                    if (fireFiberToggleButton) fireFiberToggleButton.disabled = false;
                    stopFireButton.disabled = true;
                    
                    // Reset status
                    if (firingStatus) {
                        firingStatus.textContent = 'Not Firing';
                        firingStatus.className = 'badge bg-secondary';
                    }
                }
            })
            .catch(error => {
                window.addLogMessage(`Error: ${error.message}`, true);
                // Reset button states on error
                fireButton.disabled = false;
                if (fireToggleButton) fireToggleButton.disabled = false;
                if (fireFiberButton) fireFiberButton.disabled = false;
                if (fireFiberToggleButton) fireFiberToggleButton.disabled = false;
                stopFireButton.disabled = true;
                
                // Reset status
                if (firingStatus) {
                    firingStatus.textContent = 'Not Firing';
                    firingStatus.className = 'badge bg-secondary';
                }
            });
        });
    }
    
    // Toggle Fire button (new behavior)
    if (fireToggleButton && stopFireButton) {
        console.log("Fire toggle button found and event listener attached");
        fireToggleButton.addEventListener('click', function() {
            console.log("Fire toggle button clicked");
            window.addLogMessage('FIRING (toggle) - Moving servo to position B...', false, 'action');
            
            // Disable all fire buttons and enable stop button
            fireButton.disabled = true;
            fireToggleButton.disabled = true;
            if (fireFiberButton) fireFiberButton.disabled = true;
            if (fireFiberToggleButton) fireFiberToggleButton.disabled = true;
            stopFireButton.disabled = false;
            
            // Update status
            if (firingStatus) {
                firingStatus.textContent = 'Firing (Toggle)';
                firingStatus.className = 'badge bg-danger';
            }
            
            fetch('/fire', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    mode: 'toggle'
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    window.addLogMessage('Firing (toggle mode) initiated', false, 'success');
                } else {
                    window.addLogMessage(`Error initiating toggle firing: ${data.message}`, true);
                    // Reset button states on error
                    fireButton.disabled = false;
                    fireToggleButton.disabled = false;
                    if (fireFiberButton) fireFiberButton.disabled = false;
                    if (fireFiberToggleButton) fireFiberToggleButton.disabled = false;
                    stopFireButton.disabled = true;
                    
                    // Reset status
                    if (firingStatus) {
                        firingStatus.textContent = 'Not Firing';
                        firingStatus.className = 'badge bg-secondary';
                    }
                }
            })
            .catch(error => {
                window.addLogMessage(`Error: ${error.message}`, true);
                // Reset button states on error
                fireButton.disabled = false;
                fireToggleButton.disabled = false;
                if (fireFiberButton) fireFiberButton.disabled = false;
                if (fireFiberToggleButton) fireFiberToggleButton.disabled = false;
                stopFireButton.disabled = true;
                
                // Reset status
                if (firingStatus) {
                    firingStatus.textContent = 'Not Firing';
                    firingStatus.className = 'badge bg-secondary';
                }
            });
        });
        
        console.log("Stop fire button listener attached");
        stopFireButton.addEventListener('click', function() {
            console.log("Stop fire button clicked");
            window.addLogMessage('STOPPING FIRE - Moving servo to position A...', false, 'action');
            
            // Disable stop button
            stopFireButton.disabled = true;
            
            fetch('/stop_fire', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    window.addLogMessage('Firing stopped', false, 'success');
                    
                    // Reset status
                    if (firingStatus) {
                        firingStatus.textContent = 'Not Firing';
                        firingStatus.className = 'badge bg-secondary';
                    }
                } else {
                    window.addLogMessage(`Error stopping firing: ${data.message}`, true);
                }
                
                // Always re-enable all fire buttons after stop operation
                if (fireButton) fireButton.disabled = false;
                if (fireToggleButton) fireToggleButton.disabled = false;
                if (fireFiberButton) fireFiberButton.disabled = false;
                if (fireFiberToggleButton) fireFiberToggleButton.disabled = false;
            })
            .catch(error => {
                window.addLogMessage(`Error: ${error.message}`, true);
                
                // Always re-enable all fire buttons after stop operation
                if (fireButton) fireButton.disabled = false;
                if (fireToggleButton) fireToggleButton.disabled = false;
                if (fireFiberButton) fireFiberButton.disabled = false;
                if (fireFiberToggleButton) fireFiberToggleButton.disabled = false;
            });
        });
    }
    
    // Add fiber toggle button reference
    const fireFiberToggleButton = document.getElementById('fire-fiber-toggle-button');
    
    // Fire Fiber button (momentary) event 
    if (fireFiberButton) {
        console.log("Fiber fire button found and event listener attached");
        fireFiberButton.addEventListener('click', function() {
            window.addLogMessage('Starting FIBER sequence (momentary)...', false, 'action');
            
            // Disable all fire buttons but ENABLE stop button
            if (fireButton) fireButton.disabled = true;
            if (fireToggleButton) fireToggleButton.disabled = true;
            fireFiberButton.disabled = true;
            if (fireFiberToggleButton) fireFiberToggleButton.disabled = true;
            stopFireButton.disabled = false;  // Enable stop button
            
            // Update status
            if (firingStatus) {
                firingStatus.textContent = 'Fiber Sequence';
                firingStatus.className = 'badge bg-warning text-dark';
            }
            
            fetch('/fire_fiber', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    mode: 'momentary'
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    window.addLogMessage('Fiber sequence started', false, 'success');
                } else {
                    window.addLogMessage(`Error starting fiber sequence: ${data.message}`, true);
                    
                    // Reset status and buttons
                    if (firingStatus) {
                        firingStatus.textContent = 'Not Firing';
                        firingStatus.className = 'badge bg-secondary';
                    }
                    
                    // Reset all buttons on error
                    if (fireButton) fireButton.disabled = false;
                    if (fireToggleButton) fireToggleButton.disabled = false;
                    fireFiberButton.disabled = false;
                    if (fireFiberToggleButton) fireFiberToggleButton.disabled = false;
                    stopFireButton.disabled = true;
                }
            })
            .catch(error => {
                window.addLogMessage(`Error in fiber sequence: ${error.message}`, true);
                
                // Reset all buttons on error
                if (fireButton) fireButton.disabled = false;
                if (fireToggleButton) fireToggleButton.disabled = false;
                fireFiberButton.disabled = false;
                if (fireFiberToggleButton) fireFiberToggleButton.disabled = false;
                stopFireButton.disabled = true;
                
                // Reset status
                if (firingStatus) {
                    firingStatus.textContent = 'Not Firing';
                    firingStatus.className = 'badge bg-secondary';
                }
            });
        });
    }
    
    // Fire Fiber Toggle button event
    if (fireFiberToggleButton) {
        console.log("Fiber fire toggle button found and event listener attached");
        fireFiberToggleButton.addEventListener('click', function() {
            window.addLogMessage('Starting FIBER sequence (toggle mode)...', false, 'action');
            
            // Disable all fire buttons but ENABLE stop button
            if (fireButton) fireButton.disabled = true;
            if (fireToggleButton) fireToggleButton.disabled = true;
            if (fireFiberButton) fireFiberButton.disabled = true;
            fireFiberToggleButton.disabled = true;
            stopFireButton.disabled = false;  // Enable stop button
            
            // Update status
            if (firingStatus) {
                firingStatus.textContent = 'Fiber Sequence (Toggle)';
                firingStatus.className = 'badge bg-warning text-dark';
            }
            
            fetch('/fire_fiber', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    mode: 'toggle'
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    window.addLogMessage('Fiber sequence started (toggle mode)', false, 'success');
                } else {
                    window.addLogMessage(`Error starting fiber sequence: ${data.message}`, true);
                    
                    // Reset status and buttons
                    if (firingStatus) {
                        firingStatus.textContent = 'Not Firing';
                        firingStatus.className = 'badge bg-secondary';
                    }
                    
                    // Reset all buttons on error
                    if (fireButton) fireButton.disabled = false;
                    if (fireToggleButton) fireToggleButton.disabled = false;
                    if (fireFiberButton) fireFiberButton.disabled = false;
                    fireFiberToggleButton.disabled = false;
                    stopFireButton.disabled = true;
                }
            })
            .catch(error => {
                window.addLogMessage(`Error in fiber toggle sequence: ${error.message}`, true);
                
                // Reset all buttons on error
                if (fireButton) fireButton.disabled = false;
                if (fireToggleButton) fireToggleButton.disabled = false;
                if (fireFiberButton) fireFiberButton.disabled = false;
                fireFiberToggleButton.disabled = false;
                stopFireButton.disabled = true;
                
                // Reset status
                if (firingStatus) {
                    firingStatus.textContent = 'Not Firing';
                    firingStatus.className = 'badge bg-secondary';
                }
            });
        });
    }
    
    // Track cleaning head movement state
    let cleaningHeadBusy = false;
    
    // Function to disable all cleaning head buttons
    function disableCleaningHeadButtons() {
        if (indexButton) indexButton.disabled = true;
        if (indexBackButton) indexBackButton.disabled = true;
        if (homeCleaningHeadButton) homeCleaningHeadButton.disabled = true;
        // Keep stop button enabled
        cleaningHeadBusy = true;
    }
    
    // Function to enable all cleaning head buttons
    function enableCleaningHeadButtons() {
        if (indexButton) indexButton.disabled = false;
        if (indexBackButton) indexBackButton.disabled = false;
        if (homeCleaningHeadButton) homeCleaningHeadButton.disabled = false;
        cleaningHeadBusy = false;
    }
    
    // Index Forward button
    if (indexButton) {
        console.log("Index button found and event listener attached");
        indexButton.addEventListener('click', function() {
            // Don't allow multiple operations at once
            if (cleaningHeadBusy) {
                window.addLogMessage('Cannot index forward: cleaning head is busy. Stop current operation first.', true);
                return;
            }
            
            console.log("Index button clicked");
            window.addLogMessage('Indexing forward...', false, 'action');
            
            // Disable all cleaning head buttons
            disableCleaningHeadButtons();
            
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
                    
                    // Update position display
                    if (cleaningHeadStatus) {
                        cleaningHeadStatus.textContent = `Position: ${currentPosition}`;
                    }
                    
                    window.addLogMessage(`Index forward complete! Position: ${currentPosition}`, false, 'success');
                } else {
                    window.addLogMessage(`Error: ${data.message}`, true);
                }
            })
            .catch(error => {
                window.addLogMessage(`Error: ${error.message}`, true);
            })
            .finally(() => {
                // Re-enable all buttons
                enableCleaningHeadButtons();
            });
        });
    }
    
    // Index Backward button
    if (indexBackButton) {
        indexBackButton.addEventListener('click', function() {
            // Don't allow multiple operations at once
            if (cleaningHeadBusy) {
                window.addLogMessage('Cannot index backward: cleaning head is busy. Stop current operation first.', true);
                return;
            }
            
            window.addLogMessage('Indexing backward...', false, 'action');
            
            // Disable all cleaning head buttons
            disableCleaningHeadButtons();
            
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
                    
                    // Update position display
                    if (cleaningHeadStatus) {
                        cleaningHeadStatus.textContent = `Position: ${currentPosition}`;
                    }
                    
                    window.addLogMessage(`Index backward complete! Position: ${currentPosition}`, false, 'success');
                } else {
                    window.addLogMessage(`Error: ${data.message}`, true);
                }
            })
            .catch(error => {
                window.addLogMessage(`Error: ${error.message}`, true);
            })
            .finally(() => {
                // Re-enable all buttons
                enableCleaningHeadButtons();
            });
        });
    }
    
    // Home Cleaning Head button
    if (homeCleaningHeadButton) {
        homeCleaningHeadButton.addEventListener('click', function() {
            // Don't allow multiple operations at once
            if (cleaningHeadBusy) {
                window.addLogMessage('Cannot home cleaning head: cleaning head is busy. Stop current operation first.', true);
                return;
            }
            
            window.addLogMessage('Homing cleaning head...', false, 'action');
            
            // Disable all cleaning head buttons
            disableCleaningHeadButtons();
            
            fetch('/home', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Update position display
                    if (cleaningHeadStatus) {
                        cleaningHeadStatus.textContent = 'Position: 0';
                    }
                    
                    window.addLogMessage('Cleaning head homed successfully', false, 'success');
                } else {
                    window.addLogMessage(`Error homing cleaning head: ${data.message}`, true);
                }
            })
            .catch(error => {
                window.addLogMessage(`Error: ${error.message}`, true);
            })
            .finally(() => {
                // Re-enable all buttons
                enableCleaningHeadButtons();
            });
        });
    }
    
    // Stop Cleaning Head button
    if (stopCleaningHeadButton) {
        console.log("Stop cleaning head button listener attached");
        stopCleaningHeadButton.addEventListener('click', function() {
            console.log("Stop cleaning head button clicked");
            window.addLogMessage('STOPPING CLEANING HEAD...', false, 'action');
            
            fetch('/stop_motor', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const currentPosition = data.position || 'unknown';
                    window.addLogMessage(`Cleaning head stopped at position: ${currentPosition}`, false, 'success');
                    
                    // Update position display if available
                    if (cleaningHeadStatus && data.position) {
                        cleaningHeadStatus.textContent = `Position: ${currentPosition}`;
                    }
                    
                    // Re-enable all buttons after stopping
                    enableCleaningHeadButtons();
                } else {
                    window.addLogMessage(`Error stopping cleaning head: ${data.message}`, true);
                    // Still try to re-enable buttons
                    enableCleaningHeadButtons();
                }
            })
            .catch(error => {
                window.addLogMessage(`Error: ${error.message}`, true);
                // Make sure to re-enable buttons even on error
                enableCleaningHeadButtons();
            });
        });
    }
    
    // Run Table button
    if (runTableButton) {
        runTableButton.addEventListener('click', function() {
            window.addLogMessage('Running table sequence...', false, 'action');
            
            // Disable run button and enable stop button
            runTableButton.disabled = true;
            stopTableButton.disabled = false;
            
            // Start table forward movement
            fetch('/table/forward', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    state: true
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status !== 'success') {
                    window.addLogMessage(`Error starting table: ${data.message || 'Unknown error'}`, true);
                    // Reset buttons on error
                    runTableButton.disabled = false;
                    stopTableButton.disabled = true;
                }
            })
            .catch(error => {
                window.addLogMessage(`Error: ${error.message}`, true);
                // Reset buttons on error
                runTableButton.disabled = false;
                stopTableButton.disabled = true;
            });
        });
    }
    
    // Stop Table button
    if (stopTableButton) {
        stopTableButton.addEventListener('click', function() {
            window.addLogMessage('Stopping table...', false, 'action');
            
            // Stop both directions
            Promise.all([
                fetch('/table/forward', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        state: false
                    })
                }),
                fetch('/table/backward', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        state: false
                    })
                })
            ])
            .then(() => {
                window.addLogMessage('Table stopped', false, 'success');
                
                // Reset buttons
                runTableButton.disabled = false;
                stopTableButton.disabled = true;
            })
            .catch(error => {
                window.addLogMessage(`Error stopping table: ${error.message}`, true);
                
                // Still reset buttons even on error
                runTableButton.disabled = false;
                stopTableButton.disabled = true;
            });
        });
    }
});