// Session Management using Bearer Tokens
// BACKEND_URL is defined in app.js

// Check if user is logged in by checking localStorage
function checkSession() {
    try {
        const userData = localStorage.getItem('user');
        const token = localStorage.getItem('auth_token');
        if (userData && token) {
            return JSON.parse(userData);
        }
        return null;
    } catch (error) {
        console.error('Session check failed:', error);
        return null;
    }
}

// Get auth headers for API requests
function getAuthHeaders() {
    const token = localStorage.getItem('auth_token');
    if (token) {
        return {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        };
    }
    return {
        'Content-Type': 'application/json'
    };
}

// Logout user
async function logout() {
    try {
        // Clear localStorage data
        localStorage.removeItem('user');
        localStorage.removeItem('auth_token');
        localStorage.removeItem('selectedPlan');
        
        // Call backend logout (optional - for server-side cleanup)
        try {
            await fetch(`${BACKEND_URL}/api/logout`, {
                method: 'POST',
                headers: getAuthHeaders()
            });
        } catch (e) {
            // Ignore backend logout errors
        }
        
        // Redirect to signin page
        window.location.href = 'signin.html';
    } catch (error) {
        console.error('Logout failed:', error);
        // Still redirect even if logout fails
        window.location.href = 'signin.html';
    }
}

// Update navigation based on session status
function updateNavigation() {
    const signinLink = document.getElementById('signinLink');
    const dashboardLink = document.getElementById('dashboardLink');
    const logoutLink = document.getElementById('logoutLink');
    
    if (signinLink && dashboardLink) {
        const user = checkSession();
        
        if (user) {
            // User is logged in
            signinLink.style.display = 'none';
            dashboardLink.style.display = 'inline';
            if (logoutLink) logoutLink.style.display = 'inline';
        } else {
            // User is not logged in
            signinLink.style.display = 'inline';
            dashboardLink.style.display = 'none';
            if (logoutLink) logoutLink.style.display = 'none';
        }
    }
}

// Redirect to dashboard if already logged in
function redirectIfLoggedIn() {
    const user = checkSession();
    if (user) {
        window.location.href = 'dashboard.html';
    }
}

// Redirect to signin if not logged in
function redirectIfNotLoggedIn() {
    const user = checkSession();
    if (!user) {
        window.location.href = 'signin.html';
    }
    return user;
}

// Get current user data
function getCurrentUser() {
    return checkSession();
} 