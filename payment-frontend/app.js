// Initialize Stripe
const stripe = Stripe('pk_test_51Rp76V075QJxEpaQKmYsfObmwGt7i3SKY9FYv5cR5uZpF3CftDAkFrah43DfIvXiQz9zkkbx8fDmPi1Jkbo4RN8M00Dl1K5jQx'); // Test Stripe publishable key

// Backend API URL
const BACKEND_URL = 'https://rgent.onrender.com';

// Purchase plan function - redirect to signin
async function purchasePlan(planType) {
    // Redirect to signin page with plan type
    window.location.href = `signin.html?plan=${planType}`;
}

// Helper function to get plan name
function getPlanName(planType) {
    const planNames = {
        'free': 'Free',
        'pro_haiku': 'Pro (Haiku)',
        'pro_sonnet': 'Pro (Sonnet)',
        'enterprise': 'Enterprise'
    };
    return planNames[planType] || planType;
}

// Handle successful payment (called from success page)
function handlePaymentSuccess(sessionId) {
    showSuccess('Payment successful! Your access code has been sent to your email.');
    
    // Store session info for verification
    localStorage.setItem('paymentSessionId', sessionId);
    
    // Redirect to dashboard or show access code
    setTimeout(() => {
        window.location.href = '/dashboard.html';
    }, 2000);
}

// Handle payment cancellation
function handlePaymentCancelled() {
    showError('Payment was cancelled. Please try again.');
}

// Utility functions
function showLoading(show) {
    const loading = document.getElementById('loading');
    loading.style.display = show ? 'block' : 'none';
}

function showError(message) {
    const error = document.getElementById('error');
    error.textContent = message;
    error.style.display = 'block';
}

function showSuccess(message) {
    const success = document.getElementById('success');
    success.textContent = message;
    success.style.display = 'block';
}

function hideMessages() {
    document.getElementById('error').style.display = 'none';
    document.getElementById('success').style.display = 'none';
}

// Check for payment success/cancel parameters in URL
document.addEventListener('DOMContentLoaded', function() {
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session_id');
    const cancelled = urlParams.get('cancelled');

    if (sessionId) {
        handlePaymentSuccess(sessionId);
    } else if (cancelled) {
        handlePaymentCancelled();
    }
});

// Add smooth scrolling for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Add hover effects for pricing cards
document.querySelectorAll('.pricing-card').forEach(card => {
    card.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-10px) scale(1.02)';
    });
    
    card.addEventListener('mouseleave', function() {
        this.style.transform = 'translateY(0) scale(1)';
    });
});

// Form validation for email signup (if added later)
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

// Analytics tracking (optional)
function trackEvent(eventName, properties = {}) {
    // Add your analytics tracking here (Google Analytics, Mixpanel, etc.)
    console.log('Event tracked:', eventName, properties);
}

// Track page views
trackEvent('page_view', {
    page: 'pricing',
    timestamp: new Date().toISOString()
});

// Track button clicks
document.querySelectorAll('.btn').forEach(button => {
    button.addEventListener('click', function() {
        const planType = this.getAttribute('onclick')?.match(/purchasePlan\('(.+?)'\)/)?.[1];
        if (planType) {
            trackEvent('purchase_button_clicked', {
                plan_type: planType,
                plan_name: getPlanName(planType)
            });
        }
    });
}); 