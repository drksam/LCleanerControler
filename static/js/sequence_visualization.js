/**
 * Sequence Visualization Module
 * 
 * Provides real-time visualization of sequence execution
 * 
 * @module sequence_visualization
 * @author LCleanerControler Team
 * @version 1.0.0
 */

/**
 * Sequence Visualizer class
 * @class
 */
class SequenceVisualizer {
    /**
     * Create a new sequence visualizer
     * @param {string} containerId - The ID of the container element
     * @param {Object} options - Configuration options
     */
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error(`Container element with ID ${containerId} not found`);
            return;
        }
        
        this.options = Object.assign({
            width: 600,
            height: 250,
            stepGap: 40,
            animationSpeed: 300,
            colorMap: {
                'stepper_move': '#007bff',
                'fire': '#dc3545',
                'fire_fiber': '#fd7e14',
                'stop_fire': '#28a745',
                'wait': '#ffc107',
                'wait_input': '#17a2b8',
                'fan_on': '#6c757d',
                'fan_off': '#6c757d',
                'lights_on': '#6c757d',
                'lights_off': '#6c757d',
                'table_forward': '#343a40',
                'table_backward': '#343a40'
            }
        }, options);
        
        this.sequence = null;
        this.currentStep = -1;
        this.initCanvas();
    }
    
    /**
     * Initialize the canvas element
     * @private
     */
    initCanvas() {
        // Create canvas container with responsive wrapper
        this.container.innerHTML = `
            <div class="position-relative" style="width: 100%; height: ${this.options.height}px;">
                <canvas id="${this.container.id}_canvas" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"></canvas>
            </div>
        `;
        
        this.canvas = document.getElementById(`${this.container.id}_canvas`);
        this.ctx = this.canvas.getContext('2d');
        
        // Make canvas responsive
        this.resizeCanvas();
        window.addEventListener('resize', () => this.resizeCanvas());
    }
    
    /**
     * Resize canvas to fit container
     * @private
     */
    resizeCanvas() {
        const rect = this.container.getBoundingClientRect();
        this.canvas.width = rect.width;
        this.canvas.height = this.options.height;
        
        // Redraw if we have sequence data
        if (this.sequence) {
            this.draw();
        }
    }
    
    /**
     * Set the sequence to visualize
     * @param {Object} sequence - The sequence object
     */
    setSequence(sequence) {
        this.sequence = sequence;
        this.currentStep = -1;
        this.draw();
    }
    
    /**
     * Update the current step
     * @param {number} stepIndex - The current step index (0-based)
     */
    updateCurrentStep(stepIndex) {
        this.currentStep = stepIndex;
        this.draw();
    }
    
    /**
     * Draw the visualization
     * @private
     */
    draw() {
        if (!this.sequence || !this.sequence.steps || this.sequence.steps.length === 0) {
            this.drawEmptyState();
            return;
        }
        
        // Clear canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        const steps = this.sequence.steps;
        const totalWidth = this.canvas.width - 40; // Padding on both sides
        const stepWidth = Math.min(this.options.stepGap, totalWidth / steps.length);
        
        // Draw timeline
        this.ctx.beginPath();
        this.ctx.moveTo(20, this.canvas.height / 2);
        this.ctx.lineTo(this.canvas.width - 20, this.canvas.height / 2);
        this.ctx.strokeStyle = '#dee2e6';
        this.ctx.lineWidth = 2;
        this.ctx.stroke();
        
        // Calculate horizontal spacing
        const availableWidth = this.canvas.width - 40;
        const spacing = steps.length <= 1 ? 0 : availableWidth / (steps.length - 1);
        
        // Draw steps
        steps.forEach((step, index) => {
            const x = steps.length === 1 ? this.canvas.width / 2 : 20 + index * spacing;
            const y = this.canvas.height / 2;
            const color = this.options.colorMap[step.action] || '#6c757d';
            const isCurrent = index === this.currentStep;
            
            // Draw step node
            this.ctx.beginPath();
            this.ctx.arc(x, y, isCurrent ? 12 : 8, 0, 2 * Math.PI);
            this.ctx.fillStyle = color;
            this.ctx.fill();
            
            if (isCurrent) {
                this.ctx.beginPath();
                this.ctx.arc(x, y, 16, 0, 2 * Math.PI);
                this.ctx.strokeStyle = color;
                this.ctx.lineWidth = 2;
                this.ctx.stroke();
            }
            
            // Draw step label
            this.ctx.font = isCurrent ? 'bold 12px sans-serif' : '12px sans-serif';
            this.ctx.textAlign = 'center';
            this.ctx.fillStyle = '#212529';
            
            // Draw action name above the node
            this.ctx.fillText(this.formatActionName(step.action), x, y - 20);
            
            // Draw step number below the node
            this.ctx.fillText(`Step ${index + 1}`, x, y + 25);
            
            // Draw connection between steps
            if (index > 0) {
                const prevX = steps.length === 1 ? this.canvas.width / 2 : 20 + (index - 1) * spacing;
                this.ctx.beginPath();
                this.ctx.moveTo(prevX, y);
                this.ctx.lineTo(x, y);
                this.ctx.strokeStyle = '#dee2e6';
                this.ctx.lineWidth = 2;
                this.ctx.stroke();
            }
        });
    }
    
    /**
     * Draw empty state when no sequence is loaded
     * @private
     */
    drawEmptyState() {
        // Clear canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Draw message
        this.ctx.font = '14px sans-serif';
        this.ctx.textAlign = 'center';
        this.ctx.fillStyle = '#6c757d';
        this.ctx.fillText('No sequence loaded', this.canvas.width / 2, this.canvas.height / 2);
    }
    
    /**
     * Format action name for display
     * @param {string} action - The action name
     * @returns {string} Formatted action name
     * @private
     */
    formatActionName(action) {
        const actionMap = {
            'stepper_move': 'Move',
            'fire': 'Fire',
            'fire_fiber': 'Fire Fiber',
            'stop_fire': 'Stop Fire',
            'wait': 'Wait',
            'wait_input': 'Wait Input',
            'fan_on': 'Fan On',
            'fan_off': 'Fan Off',
            'lights_on': 'Lights On',
            'lights_off': 'Lights Off',
            'table_forward': 'Table →',
            'table_backward': 'Table ←'
        };
        
        return actionMap[action] || action;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SequenceVisualizer;
}