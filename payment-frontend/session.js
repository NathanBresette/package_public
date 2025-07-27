// Session Management using HTTP-only cookies
// BACKEND_URL is defined in app.js

// Check if user is logged in by calling the session endpoint
async function checkSession() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/session`, {
            method: 'GET',
            credentials: 'include' // Include cookies
        });
        
        if (response.ok) {
            const data = await response.json();
            return data.user;
        } else {
            return null;
        }
    } catch (error) {
        console.error('Session check failed:', error);
        return null;
    }
}

// Logout user
async function logout() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/logout`, {
            method: 'POST',
            credentials: 'include' // Include cookies
        });
        
        if (response.ok) {
            // Clear any remaining localStorage data
            localStorage.removeItem('user');
            localStorage.removeItem('selectedPlan');
            
            // Redirect to signin page
            window.location.href = 'signin.html';
        }
    } catch (error) {
        console.error('Logout failed:', error);
        // Still redirect even if logout fails
        window.location.href = 'signin.html';
    }
}

// Update navigation based on session status
async function updateNavigation() {
    const signinLink = document.getElementById('signinLink');
    const dashboardLink = document.getElementById('dashboardLink');
    const logoutLink = document.getElementById('logoutLink');
    
    if (signinLink && dashboardLink) {
        const user = await checkSession();
        
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
async function redirectIfLoggedIn() {
    const user = await checkSession();
    if (user) {
        window.location.href = 'dashboard.html';
    }
}

// Redirect to signin if not logged in
async function redirectIfNotLoggedIn() {
    const user = await checkSession();
    if (!user) {
        window.location.href = 'signin.html';
    }
    return user;
}

// Get current user data
async function getCurrentUser() {
    return await checkSession();
} 