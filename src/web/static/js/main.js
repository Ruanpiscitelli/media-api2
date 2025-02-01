// Token Management
function saveToken() {
    const token = document.getElementById('bearerToken').value;
    if (token) {
        localStorage.setItem('bearerToken', token);
        showToast('Token saved successfully!', 'success');
    }
}

function getToken() {
    return localStorage.getItem('bearerToken');
}

// Toast Notifications
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    document.body.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

// API Helpers
async function apiRequest(endpoint, options = {}) {
    const token = getToken();
    if (!token) {
        showToast('Please set your Bearer token first', 'warning');
        return null;
    }
    
    try {
        const response = await fetch(endpoint, {
            ...options,
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        
        if (!response.ok) {
            throw new Error(`API Error: ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        showToast(error.message, 'danger');
        return null;
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Load saved token
    const token = getToken();
    if (token) {
        document.getElementById('bearerToken').value = token;
    }
    
    // Initialize code highlighting
    document.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightBlock(block);
    });
}); 