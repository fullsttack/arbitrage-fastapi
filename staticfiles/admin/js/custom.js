// Custom JavaScript for Django Unfold Admin

document.addEventListener('DOMContentLoaded', function() {
    
    // Real-time data updates
    if (typeof updateDashboard === 'undefined') {
        window.updateDashboard = function() {
            // Fetch fresh data every 30 seconds
            fetch(window.location.href, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                // Update counters
                updateCounter('active_opportunities', data.active_opportunities);
                updateCounter('weekly_profit', data.weekly_profit);
                updateCounter('success_rate', data.success_rate);
                updateCounter('online_exchanges', data.online_exchanges);
                
                // Update status indicators
                updateExchangeStatus();
                updateSystemAlerts(data.system_alerts);
            })
            .catch(error => {
                console.warn('Dashboard update failed:', error);
            });
        };
    }
    
    // Update counter with animation
    function updateCounter(elementId, newValue) {
        const element = document.getElementById(elementId);
        if (element) {
            const currentValue = parseFloat(element.textContent) || 0;
            const difference = newValue - currentValue;
            
            if (difference !== 0) {
                element.classList.add(difference > 0 ? 'pulse-positive' : 'pulse-negative');
                
                // Animate counter change
                animateValue(element, currentValue, newValue, 500);
                
                // Remove animation class after animation
                setTimeout(() => {
                    element.classList.remove('pulse-positive', 'pulse-negative');
                }, 2000);
            }
        }
    }
    
    // Animate value changes
    function animateValue(element, start, end, duration) {
        const startTime = performance.now();
        const isFloat = end % 1 !== 0;
        
        function updateValue(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const current = start + (end - start) * progress;
            
            element.textContent = isFloat ? current.toFixed(2) : Math.round(current);
            
            if (progress < 1) {
                requestAnimationFrame(updateValue);
            }
        }
        
        requestAnimationFrame(updateValue);
    }
    
    // Update exchange status indicators
    function updateExchangeStatus() {
        const statusElements = document.querySelectorAll('[data-exchange-status]');
        statusElements.forEach(element => {
            const exchangeCode = element.dataset.exchangeStatus;
            
            // Fetch exchange status
            fetch(`/api/exchanges/${exchangeCode}/status/`)
                .then(response => response.json())
                .then(data => {
                    const statusIndicator = element.querySelector('.status-indicator');
                    if (statusIndicator) {
                        statusIndicator.className = data.is_online ? 
                            'status-indicator status-online' : 
                            'status-indicator status-offline';
                        statusIndicator.textContent = data.is_online ? 'Online' : 'Offline';
                    }
                })
                .catch(error => {
                    console.warn(`Failed to update status for ${exchangeCode}:`, error);
                });
        });
    }
    
    // Update system alerts
    function updateSystemAlerts(alerts) {
        const alertContainer = document.getElementById('system-alerts');
        if (alertContainer && alerts) {
            alertContainer.innerHTML = '';
            
            alerts.forEach(alert => {
                const alertElement = createAlertElement(alert);
                alertContainer.appendChild(alertElement);
            });
            
            if (alerts.length === 0) {
                alertContainer.innerHTML = `
                    <div class="text-center text-gray-500 py-4">
                        <svg class="w-8 h-8 mx-auto mb-2" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                        </svg>
                        All systems operational
                    </div>
                `;
            }
        }
    }
    
    // Create alert element
    function createAlertElement(alert) {
        const div = document.createElement('div');
        div.className = `flex items-start p-3 ${getAlertBgClass(alert.level)} rounded-lg mb-2`;
        
        div.innerHTML = `
            <div class="flex-shrink-0">
                ${getAlertIcon(alert.level)}
            </div>
            <div class="ml-3 flex-1">
                <h4 class="text-sm font-medium ${getAlertTextClass(alert.level)}">
                    ${alert.title}
                </h4>
                <p class="text-xs ${getAlertSubTextClass(alert.level)} mt-1">
                    ${alert.message}
                </p>
            </div>
        `;
        
        return div;
    }
    
    // Helper functions for alert styling
    function getAlertBgClass(level) {
        switch(level) {
            case 'error': return 'bg-red-50 dark:bg-red-900/20';
            case 'warning': return 'bg-yellow-50 dark:bg-yellow-900/20';
            default: return 'bg-blue-50 dark:bg-blue-900/20';
        }
    }
    
    function getAlertTextClass(level) {
        switch(level) {
            case 'error': return 'text-red-800 dark:text-red-200';
            case 'warning': return 'text-yellow-800 dark:text-yellow-200';
            default: return 'text-blue-800 dark:text-blue-200';
        }
    }
    
    function getAlertSubTextClass(level) {
        switch(level) {
            case 'error': return 'text-red-700 dark:text-red-300';
            case 'warning': return 'text-yellow-700 dark:text-yellow-300';
            default: return 'text-blue-700 dark:text-blue-300';
        }
    }
    
    function getAlertIcon(level) {
        const iconClass = "w-4 h-4 mt-0.5";
        switch(level) {
            case 'error':
                return `<svg class="${iconClass} text-red-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                </svg>`;
            case 'warning':
                return `<svg class="${iconClass} text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
                </svg>`;
            default:
                return `<svg class="${iconClass} text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
                </svg>`;
        }
    }
    
    // Initialize periodic updates
    if (window.location.pathname === '/admin/') {
        // Update dashboard every 30 seconds
        setInterval(updateDashboard, 30000);
        
        // Update exchange status every 60 seconds
        setInterval(updateExchangeStatus, 60000);
    }
    
    // Enhanced table interactions
    const tables = document.querySelectorAll('.admin-table-enhanced');
    tables.forEach(table => {
        // Add hover effects to rows
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(row => {
            row.addEventListener('mouseenter', function() {
                this.style.backgroundColor = '#f8fafc';
            });
            
            row.addEventListener('mouseleave', function() {
                this.style.backgroundColor = '';
            });
        });
    });
    
    // Profit/Loss color coding
    const profitElements = document.querySelectorAll('[data-profit]');
    profitElements.forEach(element => {
        const profit = parseFloat(element.dataset.profit);
        if (profit > 0) {
            element.classList.add('profit-positive');
        } else if (profit < 0) {
            element.classList.add('profit-negative');
        }
    });
    
    // Auto-hide success messages
    const messages = document.querySelectorAll('.alert-success');
    messages.forEach(message => {
        setTimeout(() => {
            message.style.opacity = '0';
            setTimeout(() => {
                message.remove();
            }, 300);
        }, 5000);
    });
    
});