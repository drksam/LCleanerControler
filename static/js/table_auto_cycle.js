/**
 * Shared Table Auto Cycle Management
 * This module provides consistent auto cycle functionality across pages
 */

// Global table auto cycle state
window.TableAutoCycle = (function() {
    let autoCycleEnabled = false;
    let autoCycleRunning = false;
    let currentCycleCount = 0;
    let cycleDirection = 'forward';
    let cycleTimeout = null;
    let cycleDelay = 1000;
    
    // Get auto cycle enable state from table page switch if available
    function getAutoCycleEnabledState() {
        const switch_ = document.getElementById('auto-cycle-enable-switch');
        return switch_ ? switch_.checked : true; // Default to enabled if no switch
    }
    
    function startAutoCycle() {
        const enabledState = getAutoCycleEnabledState();
        
        if (!enabledState) {
            if (window.addLogMessage) {
                window.addLogMessage('Auto cycle is disabled. Enable it first on the Table page.', true);
            }
            return false;
        }
        
        if (autoCycleRunning) {
            if (window.addLogMessage) {
                window.addLogMessage('Auto cycle is already running', false, 'warning');
            }
            return false;
        }
        
        autoCycleRunning = true;
        currentCycleCount = 0;
        cycleDirection = 'forward';
        
        if (window.addLogMessage) {
            window.addLogMessage('Starting automatic table cycling', false, 'info');
        }
        
        updateButtonStates();
        runCycleStep();
        return true;
    }
    
    function stopAutoCycle() {
        if (!autoCycleRunning) {
            return false;
        }
        
        autoCycleRunning = false;
        
        if (cycleTimeout) {
            clearTimeout(cycleTimeout);
            cycleTimeout = null;
        }
        
        // Stop the table
        stopTable();
        
        if (window.addLogMessage) {
            window.addLogMessage('Automatic table cycling stopped', false, 'info');
        }
        
        updateButtonStates();
        return true;
    }
    
    function stopTable() {
        // Use the utility function if available, otherwise make direct requests
        if (window.ShopUtils && window.ShopUtils.makeRequest) {
            const makeRequest = window.ShopUtils.makeRequest;
            
            makeRequest('/table/forward', 'POST', { state: false }, console.log, function() {
                makeRequest('/table/backward', 'POST', { state: false });
            });
        } else {
            // Fallback to direct fetch
            fetch('/table/forward', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ state: false })
            }).then(() => {
                return fetch('/table/backward', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ state: false })
                });
            });
        }
    }
    
    function runCycleStep() {
        if (!autoCycleRunning || !getAutoCycleEnabledState()) {
            return;
        }
        
        const makeRequest = window.ShopUtils?.makeRequest || defaultMakeRequest;
        
        if (cycleDirection === 'forward') {
            makeRequest('/table/forward', 'POST', { state: true }, console.log, function(data) {
                if (data.status === 'success') {
                    setTimeout(checkForwardLimit, 500);
                } else {
                    stopAutoCycle();
                }
            });
        } else {
            makeRequest('/table/backward', 'POST', { state: true }, console.log, function(data) {
                if (data.status === 'success') {
                    setTimeout(checkBackwardLimit, 500);
                } else {
                    stopAutoCycle();
                }
            });
        }
    }
    
    function checkForwardLimit() {
        if (!autoCycleRunning) return;
        
        const makeRequest = window.ShopUtils?.makeRequest || defaultMakeRequest;
        
        makeRequest('/table/status', 'GET', null, console.log, function(data) {
            if (data.table_at_front_limit) {
                makeRequest('/table/forward', 'POST', { state: false }, console.log, function() {
                    cycleTimeout = setTimeout(() => {
                        if (autoCycleRunning) {
                            cycleDirection = 'backward';
                            runCycleStep();
                        }
                    }, cycleDelay);
                });
            } else {
                setTimeout(checkForwardLimit, 200);
            }
        });
    }
    
    function checkBackwardLimit() {
        if (!autoCycleRunning) return;
        
        const makeRequest = window.ShopUtils?.makeRequest || defaultMakeRequest;
        
        makeRequest('/table/status', 'GET', null, console.log, function(data) {
            if (data.table_at_back_limit) {
                makeRequest('/table/backward', 'POST', { state: false }, console.log, function() {
                    currentCycleCount++;
                    updateCycleDisplay();
                    
                    cycleTimeout = setTimeout(() => {
                        if (autoCycleRunning) {
                            cycleDirection = 'forward';
                            runCycleStep();
                        }
                    }, cycleDelay);
                });
            } else {
                setTimeout(checkBackwardLimit, 200);
            }
        });
    }
    
    function updateButtonStates() {
        // Update run table buttons on all pages
        const runTableButtons = document.querySelectorAll('#run-table-button');
        const stopTableButtons = document.querySelectorAll('#stop-table-button');
        
        runTableButtons.forEach(btn => {
            if (autoCycleRunning) {
                btn.classList.add('btn-running');
                btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Running...';
                btn.disabled = true;
            } else {
                btn.classList.remove('btn-running');
                btn.innerHTML = '<i class="fas fa-play-circle me-2"></i> Run Table';
                btn.disabled = !getAutoCycleEnabledState();
            }
        });
        
        stopTableButtons.forEach(btn => {
            btn.disabled = false; // Stop should always be available
        });
    }
    
    function updateCycleDisplay() {
        const cycleCount = document.getElementById('cycle-count');
        if (cycleCount) {
            cycleCount.textContent = `${currentCycleCount} cycles completed`;
        }
    }
    
    // Default makeRequest fallback
    function defaultMakeRequest(url, method, data, successCallback, errorCallback) {
        const options = {
            method: method,
            headers: { 'Content-Type': 'application/json' }
        };
        
        if (data && (method === 'POST' || method === 'PUT')) {
            options.body = JSON.stringify(data);
        }
        
        fetch(url, options)
            .then(response => response.json())
            .then(data => {
                if (successCallback) successCallback(data);
            })
            .catch(error => {
                if (errorCallback) errorCallback(error);
            });
    }
    
    // Public API
    return {
        start: startAutoCycle,
        stop: stopAutoCycle,
        stopTable: stopTable,
        isRunning: () => autoCycleRunning,
        isEnabled: getAutoCycleEnabledState,
        updateButtonStates: updateButtonStates,
        setCycleDelay: (delay) => { cycleDelay = delay * 1000; }
    };
})();

// Initialize button handlers when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Handle all Run Table buttons
    document.querySelectorAll('#run-table-button').forEach(btn => {
        btn.addEventListener('click', function() {
            window.TableAutoCycle.start();
        });
    });
    
    // Handle all Stop Table buttons
    document.querySelectorAll('#stop-table-button').forEach(btn => {
        btn.addEventListener('click', function() {
            window.TableAutoCycle.stop();
        });
    });
    
    // Handle auto cycle enable switch if present
    const autoCycleSwitch = document.getElementById('auto-cycle-enable-switch');
    if (autoCycleSwitch) {
        autoCycleSwitch.addEventListener('change', function() {
            window.TableAutoCycle.updateButtonStates();
            if (!this.checked && window.TableAutoCycle.isRunning()) {
                window.TableAutoCycle.stop();
            }
        });
    }
    
    // Handle cycle delay slider if present
    const cycleDelaySlider = document.getElementById('cycle-delay');
    const cycleDelayValue = document.getElementById('cycle-delay-value');
    if (cycleDelaySlider && cycleDelayValue) {
        cycleDelaySlider.addEventListener('input', function() {
            window.TableAutoCycle.setCycleDelay(parseFloat(this.value));
            cycleDelayValue.textContent = this.value + 's';
        });
        
        // Initialize
        window.TableAutoCycle.setCycleDelay(parseFloat(cycleDelaySlider.value));
        cycleDelayValue.textContent = cycleDelaySlider.value + 's';
    }
    
    // Initial button state update
    setTimeout(window.TableAutoCycle.updateButtonStates, 100);
});
