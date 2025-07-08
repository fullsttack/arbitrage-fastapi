// Dashboard JavaScript - save as static/admin/js/dashboard.js

document.addEventListener('DOMContentLoaded', function() {
    // Initialize dashboard
    initializeDashboard();
    
    // Set up real-time updates
    setupRealTimeUpdates();
    
    // Initialize tooltips and interactions
    initializeInteractions();
});

function initializeDashboard() {
    console.log('🚀 Crypto Arbitrage Dashboard initialized');
    
    // Animate numbers on load
    animateCounters();
    
    // Initialize charts if Chart.js is available
    if (typeof Chart !== 'undefined') {
        initializeCharts();
    }
    
    // Set up card hover effects
    setupCardEffects();
}

function animateCounters() {
    const counters = document.querySelectorAll('.quick-stat-value, .dashboard-card-value');
    
    counters.forEach(counter => {
        const target = parseFloat(counter.textContent.replace(/[^0-9.-]/g, ''));
        if (isNaN(target)) return;
        
        let current = 0;
        const increment = target / 50;
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            
            // Format the number based on original content
            if (counter.textContent.includes('$')) {
                counter.textContent = '$' + current.toFixed(2);
            } else if (counter.textContent.includes('%')) {
                counter.textContent = current.toFixed(1) + '%';
            } else {
                counter.textContent = Math.floor(current).toString();
            }
        }, 30);
    });
}

function setupCardEffects() {
    const cards = document.querySelectorAll('.dashboard-card, .quick-stat');
    
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-4px) scale(1.02)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });
}

function setupRealTimeUpdates() {
    // Update dashboard every 30 seconds
    setInterval(updateDashboardStats, 30000);
    
    // Update status indicators every 10 seconds
    setInterval(updateStatusIndicators, 10000);
    
    // Update time-sensitive elements every second
    setInterval(updateTimeSensitiveElements, 1000);
}

function updateDashboardStats() {
    fetch('/admin/api/dashboard-stats/', {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        // Update active opportunities
        const activeOppsElement = document.getElementById('active-opportunities');
        if (activeOppsElement) {
            updateValueWithAnimation(activeOppsElement, data.active_opportunities);
        }
        
        // Update weekly profit
        const weeklyProfitElement = document.getElementById('weekly-profit');
        if (weeklyProfitElement) {
            updateValueWithAnimation(weeklyProfitElement, '$' + data.weekly_profit.toFixed(2));
        }
        
        // Update active orders
        const activeOrdersElement = document.getElementById('active-orders');
        if (activeOrdersElement) {
            updateValueWithAnimation(activeOrdersElement, data.active_orders);
        }
        
        // Update last updated timestamp
        updateLastUpdated();
        
        console.log('📊 Dashboard stats updated:', data);
    })
    .catch(error => {
        console.error('❌ Error updating dashboard stats:', error);
        showNotification('Failed to update dashboard stats', 'error');
    });
}

function updateValueWithAnimation(element, newValue) {
    const oldValue = element.textContent;
    if (oldValue !== newValue.toString()) {
        element.style.transform = 'scale(1.1)';
        element.style.transition = 'transform 0.2s ease';
        
        setTimeout(() => {
            element.textContent = newValue;
            element.style.transform = 'scale(1)';
        }, 100);
    }
}

function updateStatusIndicators() {
    // Update exchange status indicators
    const statusElements = document.querySelectorAll('.status-indicator');
    statusElements.forEach(element => {
        // Add pulse animation for active statuses
        if (element.classList.contains('status-online')) {
            element.style.animation = 'pulse-green 2s infinite';
        }
    });
    
    // Update opportunity rows with latest data
    updateOpportunityRows();
}

function updateOpportunityRows() {
    const opportunityRows = document.querySelectorAll('.opportunity-row');
    opportunityRows.forEach(row => {
        const timeCell = row.querySelector('[data-time-remaining]');
        if (timeCell) {
            const expiresAt = new Date(timeCell.dataset.expiresAt);
            const now = new Date();
            const remaining = Math.max(0, expiresAt - now);
            
            if (remaining > 0) {
                const minutes = Math.floor(remaining / 60000);
                const seconds = Math.floor((remaining % 60000) / 1000);
                timeCell.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
                
                // Update color based on remaining time
                if (minutes < 1) {
                    timeCell.className = 'text-red-600 font-mono text-sm';
                } else if (minutes < 2) {
                    timeCell.className = 'text-yellow-600 font-mono text-sm';
                } else {
                    timeCell.className = 'text-green-600 font-mono text-sm';
                }
            } else {
                timeCell.textContent = 'Expired';
                timeCell.className = 'text-red-600 font-mono text-sm';
            }
        }
    });
}

function updateTimeSensitiveElements() {
    // Update relative timestamps
    const timeElements = document.querySelectorAll('[data-timestamp]');
    timeElements.forEach(element => {
        const timestamp = new Date(element.dataset.timestamp);
        const now = new Date();
        const diff = now - timestamp;
        
        element.textContent = formatRelativeTime(diff);
    });
}

function formatRelativeTime(milliseconds) {
    const seconds = Math.floor(milliseconds / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (days > 0) return `${days}d ago`;
    if (hours > 0) return `${hours}h ago`;
    if (minutes > 0) return `${minutes}m ago`;
    return `${seconds}s ago`;
}

function updateLastUpdated() {
    const lastUpdatedElement = document.querySelector('.last-updated');
    if (lastUpdatedElement) {
        const now = new Date();
        lastUpdatedElement.textContent = `Last updated: ${now.toLocaleTimeString()}`;
    }
}

function initializeCharts() {
    // Initialize profit trend chart
    const profitCtx = document.getElementById('profitChart');
    if (profitCtx) {
        initializeProfitChart(profitCtx);
    }
    
    // Initialize exchange performance chart
    const exchangeCtx = document.getElementById('exchangeChart');
    if (exchangeCtx) {
        initializeExchangeChart(exchangeCtx);
    }
}

function initializeProfitChart(ctx) {
    const profitChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: window.profitChartLabels || [],
            datasets: [{
                label: 'Daily Profit',
                data: window.profitChartData || [],
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                tension: 0.4,
                fill: true,
                pointBackgroundColor: '#10b981',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 6,
                pointHoverRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#ffffff',
                    bodyColor: '#ffffff',
                    borderColor: '#10b981',
                    borderWidth: 1,
                    cornerRadius: 8,
                    displayColors: false,
                    callbacks: {
                        label: function(context) {
                            return `Profit: $${context.parsed.y.toFixed(2)}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.1)',
                        drawBorder: false
                    },
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toFixed(0);
                        },
                        color: '#6b7280'
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: '#6b7280'
                    }
                }
            },
            elements: {
                point: {
                    hoverBackgroundColor: '#10b981'
                }
            }
        }
    });
    
    // Store chart reference for updates
    window.profitChart = profitChart;
}

function initializeExchangeChart(ctx) {
    const exchangeChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: window.exchangeChartLabels || [],
            datasets: [{
                data: window.exchangeChartData || [],
                backgroundColor: [
                    '#10b981', // Green
                    '#f59e0b', // Yellow
                    '#ef4444', // Red
                    '#6366f1', // Indigo
                    '#8b5cf6', // Violet
                    '#ec4899', // Pink
                    '#14b8a6', // Teal
                ],
                borderWidth: 2,
                borderColor: '#ffffff',
                hoverBorderWidth: 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true,
                        pointStyle: 'circle',
                        color: '#374151'
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#ffffff',
                    bodyColor: '#ffffff',
                    borderColor: '#6366f1',
                    borderWidth: 1,
                    cornerRadius: 8,
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            return `${label}: ${value.toFixed(1)}%`;
                        }
                    }
                }
            },
            cutout: '60%',
            elements: {
                arc: {
                    hoverOffset: 10
                }
            }
        }
    });
    
    // Store chart reference for updates
    window.exchangeChart = exchangeChart;
}

// Opportunity management functions
function executeOpportunity(opportunityId) {
    if (confirm('Are you sure you want to execute this opportunity?')) {
        showNotification('Executing opportunity...', 'info');
        
        fetch(`/admin/api/opportunities/${opportunityId}/execute/`, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({})
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Opportunity execution started!', 'success');
                setTimeout(updateDashboardStats, 2000);
            } else {
                showNotification('Failed to execute opportunity: ' + data.error, 'error');
            }
        })
        .catch(error => {
            console.error('Error executing opportunity:', error);
            showNotification('Error executing opportunity', 'error');
        });
    }
}

function viewDetails(opportunityId) {
    // Open opportunity details in a modal or new tab
    window.open(`/admin/arbitrage/arbitrageopportunity/${opportunityId}/change/`, '_blank');
}

// Notification system
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 transition-all duration-300 transform translate-x-full`;
    
    const colors = {
        success: 'bg-green-500 text-white',
        error: 'bg-red-500 text-white',
        warning: 'bg-yellow-500 text-white',
        info: 'bg-blue-500 text-white'
    };
    
    notification.className += ` ${colors[type] || colors.info}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => {
        notification.style.transform = 'translateX(0)';
    }, 100);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        notification.style.transform = 'translateX(full)';
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 5000);
}

// Utility functions
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function initializeInteractions() {
    // Add keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + R: Refresh dashboard
        if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
            e.preventDefault();
            updateDashboardStats();
            showNotification('Dashboard refreshed', 'info');
        }
        
        // Escape: Close any open modals
        if (e.key === 'Escape') {
            closeModals();
        }
    });
    
    // Add click handlers for interactive elements
    const interactiveElements = document.querySelectorAll('[data-action]');
    interactiveElements.forEach(element => {
        element.addEventListener('click', function(e) {
            e.preventDefault();
            const action = this.dataset.action;
            const target = this.dataset.target;
            
            switch (action) {
                case 'execute':
                    executeOpportunity(target);
                    break;
                case 'view':
                    viewDetails(target);
                    break;
                case 'refresh':
                    updateDashboardStats();
                    break;
            }
        });
    });
}

function closeModals() {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.style.display = 'none';
    });
}

// Performance monitoring
let performanceMetrics = {
    dashboardLoads: 0,
    apiCalls: 0,
    errors: 0,
    startTime: Date.now()
};

function trackPerformance(metric) {
    performanceMetrics[metric]++;
    
    // Log performance every 10 minutes
    if (performanceMetrics.dashboardLoads % 20 === 0) {
        console.log('📈 Dashboard Performance Metrics:', performanceMetrics);
    }
}

// Initialize performance tracking
trackPerformance('dashboardLoads');

// Export functions for global access
window.dashboard = {
    updateStats: updateDashboardStats,
    executeOpportunity: executeOpportunity,
    viewDetails: viewDetails,
    showNotification: showNotification,
    metrics: performanceMetrics
};

console.log('✅ Dashboard JavaScript fully loaded and initialized');