// Dashboard functionality
let userData = null;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    loadUserData();
    setupEventListeners();
});

// Load user data from localStorage
function loadUserData() {
    try {
        userData = getCurrentUser();
        
        if (!userData) {
            // No valid session, redirect to signin
            window.location.href = 'signin.html';
            return;
        }
        
        updateDashboard(userData);
    } catch (error) {
        console.error('Error loading user data:', error);
        window.location.href = 'signin.html';
    }
}

// Update dashboard with user data
function updateDashboard(data) {
    // Update access code
    document.getElementById('accessCode').textContent = data.access_code;
    
    // Update user info (PII-free - use access code and email from session)
    document.getElementById('userName').textContent = 'User';
    document.getElementById('userEmail').textContent = data.email || 'user@example.com';
    
    // Update plan info (PII-free - use plan type to determine limits)
    let planType = 'Free Trial';
    let planDetails = '25 requests (one-time trial)';
    let dailyLimit = 25;
    
    if (data.plan_type === 'pro_haiku') {
        planType = 'Pro (Haiku)';
        planDetails = '$10/month + pay per token';
        dailyLimit = 10000; // Very high limit for pay-per-token
    } else if (data.plan_type === 'pro_sonnet') {
        planType = 'Pro (Sonnet)';
        planDetails = '$10/month + pay per token';
        dailyLimit = 10000; // Very high limit for pay-per-token
    } else if (data.plan_type === 'free_trial') {
        planType = 'Free Trial';
        planDetails = '25 requests (one-time trial)';
        dailyLimit = 25;
    }
    
    document.getElementById('planName').textContent = planType + ' Plan';
    document.getElementById('planDetails').textContent = planDetails;
    
    // Update usage stats based on plan type
    let requestsUsed = Math.floor(Math.random() * 10); // Mock data
    let requestsRemaining = 0;
    let daysLeft = '30';
    
    if (data.plan_type === 'free_trial') {
        requestsRemaining = Math.max(0, dailyLimit - requestsUsed);
        daysLeft = 'Trial';
    } else if (data.plan_type === 'pro_haiku' || data.plan_type === 'pro_sonnet') {
        requestsUsed = 'Unlimited';
        requestsRemaining = 'Unlimited';
        daysLeft = 'Monthly';
    } else {
        requestsRemaining = Math.max(0, dailyLimit - requestsUsed);
        daysLeft = '30';
    }
    
    document.getElementById('requestsUsed').textContent = requestsUsed;
    document.getElementById('requestsRemaining').textContent = requestsRemaining;
    document.getElementById('daysLeft').textContent = daysLeft;
    
    // Update progress bar based on plan type
    const progressFill = document.getElementById('progressFill');
    
    if (data.plan_type === 'pro_haiku' || data.plan_type === 'pro_sonnet') {
        // Unlimited plans - show full progress bar in green
        progressFill.style.width = '100%';
        progressFill.style.background = '#27ae60';
    } else {
        // Limited plans - show actual usage
        const progressPercent = (requestsUsed / dailyLimit) * 100;
        progressFill.style.width = `${Math.min(progressPercent, 100)}%`;
        
        // Update progress bar color based on usage
        if (progressPercent > 80) {
            progressFill.style.background = '#e74c3c';
        } else if (progressPercent > 60) {
            progressFill.style.background = '#f39c12';
        } else {
            progressFill.style.background = '#667eea';
        }
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

// Sign out function
function signOut() {
    logout();
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