/**
 * Shared Auto Cycle Manager for Table Control
 * Provides auto cycle functionality that can be used across multiple pages
 */

class AutoCycleManager {
    constructor() {
        // Try to restore state from localStorage first
        this.enabled = this.loadState('enabled', false);
        this.running = false; // Always start as not running for safety
        this.direction = 'forward';
        this.timer = null;
        this.cycleCount = this.loadState('cycleCount', 0);
        this.currentDelay = this.loadState('currentDelay', 1000); // Default 1 second
        
        // Callbacks for UI updates
        this.onStateChange = null;
        this.onCycleCountChange = null;
        this.onProgressChange = null;
        
        console.log(`AutoCycleManager initialized: enabled=${this.enabled}, cycleCount=${this.cycleCount}, delay=${this.currentDelay}`);
    }
    
    /**
     * Load state from localStorage
     */
    loadState(key, defaultValue) {
        try {
            const value = localStorage.getItem(`autoCycle_${key}`);
            return value !== null ? JSON.parse(value) : defaultValue;
        } catch (e) {
            console.warn(`Failed to load auto cycle state for ${key}:`, e);
            return defaultValue;
        }
    }
    
    /**
     * Save state to localStorage
     */
    saveState(key, value) {
        try {
            localStorage.setItem(`autoCycle_${key}`, JSON.stringify(value));
        } catch (e) {
            console.warn(`Failed to save auto cycle state for ${key}:`, e);
        }
    }
    
    /**
     * Enable or disable auto cycle
     */
    setEnabled(enabled) {
        this.enabled = enabled;
        this.saveState('enabled', enabled);
        if (!enabled && this.running) {
            this.stop();
        }
        if (this.onStateChange) {
            this.onStateChange();
        }
    }
    
    /**
     * Set enabled state from server (authoritative source)
     * This will update localStorage to match server state
     */
    syncEnabledFromServer(enabled) {
        console.log(`AutoCycleManager: Syncing enabled state from server: ${this.enabled} -> ${enabled}`);
        this.enabled = enabled;
        this.saveState('enabled', enabled);
        if (!enabled && this.running) {
            this.stop();
        }
        if (this.onStateChange) {
            this.onStateChange();
        }
    }
    
    /**
     * Check if auto cycle is enabled
     */
    isEnabled() {
        return this.enabled;
    }
    
    /**
     * Check if auto cycle is currently running
     */
    isRunning() {
        return this.running;
    }
    
    /**
     * Set the delay between direction changes
     */
    setDelay(delaySeconds) {
        this.currentDelay = delaySeconds * 1000;
        this.saveState('currentDelay', this.currentDelay);
    }
    
    /**
     * Start auto cycle
     */
    start() {
        if (!this.enabled) {
            if (window.addLogMessage) {
                window.addLogMessage('Auto cycle is disabled. Enable it first.', true);
            }
            return false;
        }
        
        if (this.running) {
            return false;
        }
        
        this.running = true;
        this.direction = 'forward';
        this.cycleCount = 0;
        this.saveState('cycleCount', this.cycleCount);
        
        if (window.addLogMessage) {
            window.addLogMessage('Starting auto cycle...', false, 'action');
        }
        
        if (this.onStateChange) {
            this.onStateChange();
        }
        
        this.runStep();
        return true;
    }
    
    /**
     * Stop auto cycle
     */
    stop() {
        if (!this.running) {
            return;
        }
        
        this.running = false;
        
        if (this.timer) {
            clearTimeout(this.timer);
            this.timer = null;
        }
        
        // Stop any movement
        this.makeTableRequest('/table/forward', { state: false });
        this.makeTableRequest('/table/backward', { state: false });
        
        if (window.addLogMessage) {
            window.addLogMessage(`Auto cycle stopped. Completed ${this.cycleCount} cycles.`, false, 'success');
        }
        
        if (this.onStateChange) {
            this.onStateChange();
        }
        
        if (this.onProgressChange) {
            this.onProgressChange(0);
        }
    }
    
    /**
     * Run one step of the auto cycle
     */
    runStep() {
        if (!this.running) {
            console.log('AutoCycle: runStep called but not running');
            return;
        }
        
        console.log(`AutoCycle: Starting runStep in direction: ${this.direction}`);
        
        if (this.direction === 'forward') {
            console.log('AutoCycle: Making forward request');
            // Move forward
            this.makeTableRequest('/table/forward', { state: true }, () => {
                console.log('AutoCycle: Forward request successful');
                if (this.onProgressChange) {
                    this.onProgressChange(25);
                }
                
                // Poll table status to check for limit switch
                this.checkLimitAndContinue('forward');
            });
        } else {
            console.log('AutoCycle: Making backward request');
            // Move backward
            this.makeTableRequest('/table/backward', { state: true }, () => {
                console.log('AutoCycle: Backward request successful');
                if (this.onProgressChange) {
                    this.onProgressChange(75);
                }
                
                // Poll table status to check for limit switch
                this.checkLimitAndContinue('backward');
            });
        }
    }
    
    /**
     * Check for limit switch and continue the cycle
     */
    checkLimitAndContinue(direction) {
        if (!this.running) {
            console.log('AutoCycle: checkLimitAndContinue called but not running');
            return;
        }
        
        console.log(`AutoCycle: Checking limit for direction: ${direction}`);
        
        // Check table status every 100ms
        fetch('/table/status')
            .then(response => response.json())
            .then(data => {
                if (!this.running) {
                    console.log('AutoCycle: Status received but not running anymore');
                    return;
                }
                
                console.log('AutoCycle: Table status:', data);
                
                let limitReached = false;
                
                if (direction === 'forward' && data.table_at_front_limit) {
                    console.log('AutoCycle: Front limit reached!');
                    limitReached = true;
                    if (this.onProgressChange) {
                        this.onProgressChange(50);
                    }
                } else if (direction === 'backward' && data.table_at_back_limit) {
                    console.log('AutoCycle: Back limit reached!');
                    limitReached = true;
                    if (this.onProgressChange) {
                        this.onProgressChange(100);
                    }
                }
                
                if (limitReached) {
                    console.log(`AutoCycle: Limit reached, stopping ${direction} movement`);
                    // Stop movement
                    this.makeTableRequest(`/table/${direction}`, { state: false }, () => {
                        console.log(`AutoCycle: ${direction} stopped, switching direction`);
                        if (this.running) {
                            if (direction === 'forward') {
                                console.log('AutoCycle: Switching to backward direction');
                                this.direction = 'backward';
                            } else {
                                console.log('AutoCycle: Completed a full cycle');
                                // Completed a full cycle
                                this.cycleCount++;
                                this.saveState('cycleCount', this.cycleCount);
                                this.direction = 'forward';
                                
                                // Update session table cycles for performance tracking
                                this.updateSessionTableCycles(1);
                                
                                if (this.onCycleCountChange) {
                                    this.onCycleCountChange(this.cycleCount);
                                }
                                
                                if (this.onProgressChange) {
                                    this.onProgressChange(0);
                                }
                            }
                            
                            console.log(`AutoCycle: Waiting ${this.currentDelay}ms before continuing with ${this.direction}`);
                            // Wait for dwell time, then continue
                            this.timer = setTimeout(() => {
                                console.log(`AutoCycle: Dwell time complete, starting ${this.direction} step`);
                                this.runStep();
                            }, this.currentDelay);
                        }
                    });
                } else {
                    // Limit not reached yet, check again
                    this.timer = setTimeout(() => this.checkLimitAndContinue(direction), 100);
                }
            })
            .catch(error => {
                console.error('AutoCycle: Error checking table status:', error);
                if (window.addLogMessage) {
                    window.addLogMessage('Error checking table status: ' + error.message, true);
                }
                this.stop();
            });
    }
    
    /**
     * Make a table control request with AutoCycle identifier
     */
    makeTableRequest(url, data, callback) {
        console.log(`AutoCycle: Making request to ${url} with data:`, data);
        
        // Add a flag to identify this as an auto cycle request
        const requestData = {
            ...data,
            source: 'auto_cycle'  // Identify this request as coming from auto cycle
        };
        
        const options = {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        };
        
        fetch(url, options)
            .then(response => response.json())
            .then(responseData => {
                console.log(`AutoCycle: Response from ${url}:`, responseData);
                if (responseData.status === 'success') {
                    if (callback) {
                        callback(responseData);
                    }
                } else {
                    console.error(`AutoCycle: Request to ${url} failed:`, responseData);
                    if (window.addLogMessage) {
                        window.addLogMessage(`Request to ${url} failed: ${responseData.message || 'Unknown error'}`, true);
                    }
                }
            })
            .catch(error => {
                console.error('Auto cycle request error:', error);
                if (window.addLogMessage) {
                    window.addLogMessage(`Auto cycle error: ${error.message}`, true);
                }
            });
    }
    
    /**
     * Update session table cycles for performance tracking
     */
    updateSessionTableCycles(increment = 1) {
        fetch('/api/sessions/table-cycle', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                increment: increment
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log(`AutoCycle: Session table cycles updated by ${increment}`);
            } else {
                console.warn('AutoCycle: Failed to update session table cycles:', data.error);
            }
        })
        .catch(error => {
            console.error('AutoCycle: Error updating session table cycles:', error);
        });
    }
    
    /**
     * Get current state
     */
    getState() {
        return {
            enabled: this.enabled,
            running: this.running,
            direction: this.direction,
            cycleCount: this.cycleCount
        };
    }
}

// Create global instance
window.AutoCycleManager = window.AutoCycleManager || new AutoCycleManager();
