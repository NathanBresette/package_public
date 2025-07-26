// Dashboard functionality
let userData = null;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    loadUserData();
    setupEventListeners();
});

// Load user data from session or API
async function loadUserData() {
    const sessionId = localStorage.getItem('paymentSessionId');
    
    if (!sessionId) {
        // No session found, redirect to pricing
        window.location.href = '/index.html';
        return;
    }

    try {
        // In a real app, you'd fetch user data from your backend
        // For now, we'll simulate the data
        userData = await fetchUserData(sessionId);
        updateDashboard(userData);
    } catch (error) {
        console.error('Error loading user data:', error);
        showError('Failed to load user data. Please try again.');
    }
}

// Simulate fetching user data from backend
async function fetchUserData(sessionId) {
    // In production, this would be a real API call
    // For now, return mock data
    return {
        accessCode: generateAccessCode(),
        plan: {
            name: 'Professional',
            type: 'professional',
            requests: 500,
            price: 29
        },
        usage: {
            used: 0,
            remaining: 500,
            daysLeft: 30
        },
        user: {
            email: 'user@example.com',
            name: 'John Doe'
        }
    };
}

// Generate a random access code
function generateAccessCode() {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    let code = 'RGENT-';
    
    for (let i = 0; i < 3; i++) {
        for (let j = 0; j < 4; j++) {
            code += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        if (i < 2) code += '-';
    }
    
    return code;
}

// Update dashboard with user data
function updateDashboard(data) {
    // Update access code
    document.getElementById('accessCode').textContent = data.accessCode;
    
    // Update plan info
    document.getElementById('planName').textContent = data.plan.name + ' Plan';
    document.getElementById('planDetails').textContent = 
        data.plan.requests === -1 ? 'Unlimited requests per month' : 
        `${data.plan.requests} requests per month`;
    
    // Update usage stats
    document.getElementById('requestsUsed').textContent = data.usage.used;
    document.getElementById('requestsRemaining').textContent = data.usage.remaining;
    document.getElementById('daysLeft').textContent = data.usage.daysLeft;
    
    // Update progress bar
    const progressPercent = data.plan.requests === -1 ? 0 : 
        ((data.usage.used / data.plan.requests) * 100);
    document.getElementById('progressFill').style.width = `${Math.min(progressPercent, 100)}%`;
    
    // Update progress bar color based on usage
    const progressFill = document.getElementById('progressFill');
    if (progressPercent > 80) {
        progressFill.style.background = '#e74c3c';
    } else if (progressPercent > 60) {
        progressFill.style.background = '#f39c12';
    } else {
        progressFill.style.background = '#667eea';
    }
}

// Copy access code to clipboard
async function copyAccessCode() {
    const accessCode = document.getElementById('accessCode').textContent;
    const copyBtn = document.querySelector('.copy-btn');
    
    try {
        await navigator.clipboard.writeText(accessCode);
        
        // Update button appearance
        copyBtn.textContent = 'Copied!';
        copyBtn.classList.add('copied');
        
        // Reset button after 2 seconds
        setTimeout(() => {
            copyBtn.textContent = 'Copy Access Code';
            copyBtn.classList.remove('copied');
        }, 2000);
        
        showSuccess('Access code copied to clipboard!');
    } catch (error) {
        console.error('Failed to copy:', error);
        showError('Failed to copy access code. Please copy it manually.');
    }
}

// Account management functions
function updateBilling() {
    // In production, this would redirect to Stripe Customer Portal
    alert('Billing management will be available soon!');
}

function downloadInvoice() {
    // In production, this would generate and download an invoice
    alert('Invoice download will be available soon!');
}

function cancelSubscription() {
    if (confirm('Are you sure you want to cancel your subscription? You will lose access to RgentAI at the end of your current billing period.')) {
        // In production, this would cancel the subscription via Stripe
        alert('Subscription cancellation will be available soon!');
    }
}

// Setup event listeners
function setupEventListeners() {
    // Add any additional event listeners here
    document.addEventListener('keydown', function(e) {
        // Allow copying access code with Ctrl+C when focused
        if (e.ctrlKey && e.key === 'c') {
            const activeElement = document.activeElement;
            if (activeElement.id === 'accessCode') {
                copyAccessCode();
            }
        }
    });
}

// Utility functions
function showSuccess(message) {
    // Create a temporary success message
    const successDiv = document.createElement('div');
    successDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #27ae60;
        color: white;
        padding: 15px 20px;
        border-radius: 10px;
        z-index: 1000;
        animation: slideIn 0.3s ease;
    `;
    successDiv.textContent = message;
    
    document.body.appendChild(successDiv);
    
    // Remove after 3 seconds
    setTimeout(() => {
        successDiv.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            document.body.removeChild(successDiv);
        }, 300);
    }, 3000);
}

function showError(message) {
    // Create a temporary error message
    const errorDiv = document.createElement('div');
    errorDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #e74c3c;
        color: white;
        padding: 15px 20px;
        border-radius: 10px;
        z-index: 1000;
        animation: slideIn 0.3s ease;
    `;
    errorDiv.textContent = message;
    
    document.body.appendChild(errorDiv);
    
    // Remove after 5 seconds
    setTimeout(() => {
        errorDiv.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            document.body.removeChild(errorDiv);
        }, 300);
    }, 5000);
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Analytics tracking
function trackEvent(eventName, properties = {}) {
    // Add your analytics tracking here
    console.log('Dashboard event:', eventName, properties);
}

// Track dashboard interactions
trackEvent('dashboard_loaded', {
    timestamp: new Date().toISOString()
});

// Track copy access code
const originalCopyAccessCode = copyAccessCode;
copyAccessCode = function() {
    trackEvent('access_code_copied');
    return originalCopyAccessCode.apply(this, arguments);
}; 