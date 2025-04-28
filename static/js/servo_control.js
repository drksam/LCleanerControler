/**
 * Servo Control JavaScript
 * Handles servo positioning, movement, and firing actions with proper logging
 */

document.addEventListener('DOMContentLoaded', function() {
    // Position sliders
    const servoPositionASlider = document.getElementById('servo-position-a');
    const servoPositionAValue = document.getElementById('servo-position-a-value');
    const servoPositionBSlider = document.getElementById('servo-position-b');
    const servoPositionBValue = document.getElementById('servo-position-b-value');
    const servoInvertSwitch = document.getElementById('servo-invert');
    
    // Movement buttons
    const moveToPositionABtn = document.getElementById('move-to-position-a');
    const moveToPositionBBtn = document.getElementById('move-to-position-b');
    const servoDirectAngleSlider = document.getElementById('servo-direct-angle');
    const servoDirectAngleValue = document.getElementById('servo-direct-angle-value');
    const moveToAngleBtn = document.getElementById('move-to-angle');
    const detachServoBtn = document.getElementById('detach-servo');
    const reattachServoBtn = document.getElementById('reattach-servo');
    
    // Firing test buttons
    const fireButtonTest = document.getElementById('fire-button-test');
    const stopFireButtonTest = document.getElementById('stop-fire-button-test');
    const fireFiberButtonTest = document.getElementById('fire-fiber-button-test');
    
    // addLogMessage function is now defined in base.html
    
    // Position A slider
    if (servoPositionASlider && servoPositionAValue) {
        servoPositionASlider.addEventListener('input', function() {
            servoPositionAValue.textContent = this.value;
        });
        
        servoPositionASlider.addEventListener('change', function() {
            const position = parseInt(this.value);
            addLogMessage(`Setting servo position A to ${position}°...`, false, 'config');
            
            fetch('/servo/set_position_a', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    position: position
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    addLogMessage(`Servo position A set to ${position}°`, false, 'success');
                } else {
                    addLogMessage(`Error setting position A: ${data.message}`, true);
                }
            })
            .catch(error => {
                addLogMessage(`Error: ${error.message}`, true);
            });
        });
    }
    
    // Position B slider
    if (servoPositionBSlider && servoPositionBValue) {
        servoPositionBSlider.addEventListener('input', function() {
            servoPositionBValue.textContent = this.value;
        });
        
        servoPositionBSlider.addEventListener('change', function() {
            const position = parseInt(this.value);
            addLogMessage(`Setting servo position B to ${position}°...`, false, 'config');
            
            fetch('/servo/set_position_b', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    position: position
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    addLogMessage(`Servo position B set to ${position}°`, false, 'success');
                } else {
                    addLogMessage(`Error setting position B: ${data.message}`, true);
                }
            })
            .catch(error => {
                addLogMessage(`Error: ${error.message}`, true);
            });
        });
    }
    
    // Invert switch
    if (servoInvertSwitch) {
        servoInvertSwitch.addEventListener('change', function() {
            const inverted = this.checked;
            addLogMessage(`${inverted ? 'Enabling' : 'Disabling'} servo inversion...`, false, 'config');
            
            fetch('/servo/set_inverted', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    inverted: inverted
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    addLogMessage(`Servo inversion ${inverted ? 'enabled' : 'disabled'}`, false, 'success');
                } else {
                    addLogMessage(`Error setting inversion: ${data.message}`, true);
                    // Revert switch state on error
                    this.checked = !inverted;
                }
            })
            .catch(error => {
                addLogMessage(`Error: ${error.message}`, true);
                // Revert switch state on error
                this.checked = !inverted;
            });
        });
    }
    
    // Move to Position A button
    if (moveToPositionABtn) {
        moveToPositionABtn.addEventListener('click', function() {
            addLogMessage('Moving servo to position A...', false, 'action');
            
            fetch('/servo/move_to_a', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    addLogMessage(`Servo moved to position A (${data.angle}°)`, false, 'success');
                } else {
                    addLogMessage(`Error moving to position A: ${data.message}`, true);
                }
            })
            .catch(error => {
                addLogMessage(`Error: ${error.message}`, true);
            });
        });
    }
    
    // Move to Position B button
    if (moveToPositionBBtn) {
        moveToPositionBBtn.addEventListener('click', function() {
            addLogMessage('Moving servo to position B...', false, 'action');
            
            fetch('/servo/move_to_b', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    addLogMessage(`Servo moved to position B (${data.angle}°)`, false, 'success');
                } else {
                    addLogMessage(`Error moving to position B: ${data.message}`, true);
                }
            })
            .catch(error => {
                addLogMessage(`Error: ${error.message}`, true);
            });
        });
    }
    
    // Direct angle slider
    if (servoDirectAngleSlider && servoDirectAngleValue) {
        servoDirectAngleSlider.addEventListener('input', function() {
            servoDirectAngleValue.textContent = this.value;
        });
    }
    
    // Move to Angle button
    if (moveToAngleBtn && servoDirectAngleSlider) {
        moveToAngleBtn.addEventListener('click', function() {
            const angle = parseInt(servoDirectAngleSlider.value);
            addLogMessage(`Moving servo to ${angle}°...`, false, 'action');
            
            fetch('/servo/move_to_angle', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    angle: angle
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    addLogMessage(`Servo moved to ${angle}°`, false, 'success');
                } else {
                    addLogMessage(`Error moving to angle: ${data.message}`, true);
                }
            })
            .catch(error => {
                addLogMessage(`Error: ${error.message}`, true);
            });
        });
    }
    
    // Detach servo button
    if (detachServoBtn) {
        detachServoBtn.addEventListener('click', function() {
            addLogMessage('Detaching servo...', false, 'action');
            
            fetch('/servo/detach', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    addLogMessage('Servo detached', false, 'success');
                } else {
                    addLogMessage(`Error detaching servo: ${data.message}`, true);
                }
            })
            .catch(error => {
                addLogMessage(`Error: ${error.message}`, true);
            });
        });
    }
    
    // Reattach servo button
    if (reattachServoBtn) {
        reattachServoBtn.addEventListener('click', function() {
            addLogMessage('Reattaching servo...', false, 'action');
            
            fetch('/servo/reattach', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    addLogMessage('Servo reattached', false, 'success');
                } else {
                    addLogMessage(`Error reattaching servo: ${data.message}`, true);
                }
            })
            .catch(error => {
                addLogMessage(`Error: ${error.message}`, true);
            });
        });
    }
    
    // Fire test button
    if (fireButtonTest && stopFireButtonTest) {
        fireButtonTest.addEventListener('click', function() {
            addLogMessage('FIRING (TEST) - Moving servo to position B...', false, 'action');
            
            // Disable fire button and enable stop button
            fireButtonTest.disabled = true;
            stopFireButtonTest.disabled = false;
            
            fetch('/fire', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    addLogMessage('Firing initiated (Test mode)', false, 'success');
                } else {
                    addLogMessage(`Error initiating firing: ${data.message}`, true);
                    // Reset button states on error
                    fireButtonTest.disabled = false;
                    stopFireButtonTest.disabled = true;
                }
            })
            .catch(error => {
                addLogMessage(`Error: ${error.message}`, true);
                // Reset button states on error
                fireButtonTest.disabled = false;
                stopFireButtonTest.disabled = true;
            });
        });
        
        stopFireButtonTest.addEventListener('click', function() {
            addLogMessage('STOPPING FIRE (TEST) - Moving servo to position A...', false, 'action');
            
            // Disable stop button and enable fire button
            stopFireButtonTest.disabled = true;
            fireButtonTest.disabled = false;
            
            fetch('/stop_fire', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    addLogMessage('Firing stopped (Test mode)', false, 'success');
                } else {
                    addLogMessage(`Error stopping firing: ${data.message}`, true);
                    // Reset button states on error
                    stopFireButtonTest.disabled = false;
                    fireButtonTest.disabled = true;
                }
            })
            .catch(error => {
                addLogMessage(`Error: ${error.message}`, true);
                // Reset button states on error
                stopFireButtonTest.disabled = false;
                fireButtonTest.disabled = true;
            });
        });
    }
    
    // Fiber sequence test button
    if (fireFiberButtonTest) {
        fireFiberButtonTest.addEventListener('click', function() {
            addLogMessage('Starting FIBER sequence (TEST)...', false, 'action');
            
            fireFiberButtonTest.disabled = true;
            
            fetch('/fire_fiber', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    addLogMessage('Fiber sequence started (Test mode)', false, 'success');
                } else {
                    addLogMessage(`Error starting fiber sequence: ${data.message}`, true);
                }
            })
            .catch(error => {
                addLogMessage(`Error: ${error.message}`, true);
            })
            .finally(() => {
                // Re-enable button after a short delay
                setTimeout(() => {
                    fireFiberButtonTest.disabled = false;
                }, 2000);
            });
        });
    }
});