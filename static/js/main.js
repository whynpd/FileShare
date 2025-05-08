// Main JavaScript file for Secure File Sharing System

document.addEventListener('DOMContentLoaded', function() {
    // Handle user authentication state
    updateAuthState();
    
    // Setup logout functionality
    setupLogout();
});

// Update UI based on authentication state
function updateAuthState() {
    const token = localStorage.getItem('token');
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    
    if (token && user) {
        // Show authenticated user elements
        document.querySelectorAll('.user-auth').forEach(el => el.classList.remove('d-none'));
        document.querySelectorAll('.user-no-auth').forEach(el => el.classList.add('d-none'));
        
        // Show elements based on user role
        if (user.role === 'operations') {
            document.querySelectorAll('.user-ops').forEach(el => el.classList.remove('d-none'));
            document.querySelectorAll('.user-client').forEach(el => el.classList.add('d-none'));
        } else if (user.role === 'client') {
            document.querySelectorAll('.user-client').forEach(el => el.classList.remove('d-none'));
            document.querySelectorAll('.user-ops').forEach(el => el.classList.add('d-none'));
        }
    } else {
        // Show non-authenticated user elements
        document.querySelectorAll('.user-auth').forEach(el => el.classList.add('d-none'));
        document.querySelectorAll('.user-no-auth').forEach(el => el.classList.remove('d-none'));
        document.querySelectorAll('.user-ops').forEach(el => el.classList.add('d-none'));
        document.querySelectorAll('.user-client').forEach(el => el.classList.add('d-none'));
    }
}

// Setup logout functionality
function setupLogout() {
    const logoutLink = document.getElementById('logout-link');
    
    if (logoutLink) {
        logoutLink.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Clear authentication data
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            
            // Show success message (you can use a custom show alert function if available)
            if (typeof showAlert === 'function') {
                showAlert('success', 'You have been logged out successfully!');
            } else {
                alert('You have been logged out successfully!');
            }
            
            // Redirect to home page after logout
            setTimeout(() => {
                window.location.href = '/';
            }, 1000);
        });
    }
}

// Common alert function used across pages
function showAlert(type, message) {
    const alertsContainer = document.getElementById('alerts-container');
    
    if (!alertsContainer) return;
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    alertsContainer.appendChild(alert);
    
    // Auto dismiss after 5 seconds
    setTimeout(() => {
        alert.classList.remove('show');
        setTimeout(() => {
            alert.remove();
        }, 150);
    }, 5000);
}

// Helper function to format file sizes
function formatFileSize(sizeInBytes) {
    if (sizeInBytes < 1024) {
        return sizeInBytes + ' B';
    } else if (sizeInBytes < 1024 * 1024) {
        return (sizeInBytes / 1024).toFixed(2) + ' KB';
    } else if (sizeInBytes < 1024 * 1024 * 1024) {
        return (sizeInBytes / (1024 * 1024)).toFixed(2) + ' MB';
    } else {
        return (sizeInBytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
    }
}

// Helper function to validate file extension
function validateFileExtension(filename, allowedExtensions) {
    if (!filename) return false;
    
    const extension = filename.split('.').pop().toLowerCase();
    return allowedExtensions.includes(extension);
}

// Function to make authenticated API requests
async function apiRequest(endpoint, method = 'GET', data = null) {
    const token = localStorage.getItem('token');
    
    if (!token) {
        throw new Error('Not authenticated');
    }
    
    const options = {
        method: method,
        headers: {
            'Authorization': `Bearer ${token}`
        }
    };
    
    if (data) {
        if (data instanceof FormData) {
            options.body = data;
        } else {
            options.headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(data);
        }
    }
    
    const response = await fetch(endpoint, options);
    const result = await response.json();
    
    if (!response.ok) {
        throw new Error(result.message || 'API request failed');
    }
    
    return result;
}
