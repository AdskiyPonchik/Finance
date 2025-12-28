/* =========================================
 * API MODULE
 * ========================================= */
const apiBase = '/api';

function getAuthHeaders() {
    const token = localStorage.getItem('token');
    return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
    };
}

async function handleResponse(res) {
    if (res.status === 401) {
        localStorage.removeItem('token');
        location.reload();
        return;
    }
    if (res.status === 204) {
        return;
    }
    if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'An API error occurred');
    }
    return res.json();
}

export async function loginApi(username, password) {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const res = await fetch(`${apiBase}/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData,
    });

    if (res.ok) {
        const data = await res.json();
        localStorage.setItem('token', data.access_token);
        return true;
    } else {
        throw new Error('Login failed');
    }
}

export async function fetchBalance() {
    const res = await fetch(`${apiBase}/balance/`, { headers: getAuthHeaders() });
    return handleResponse(res);
}

export async function fetchTransactions() {
    const res = await fetch(`${apiBase}/transactions/`, { headers: getAuthHeaders() });
    return handleResponse(res);
}

export async function fetchCategories() {
    const res = await fetch(`${apiBase}/categories/`, { headers: getAuthHeaders() });
    return handleResponse(res);
}

export async function fetchUser() {
    const res = await fetch(`${apiBase}/users/me`, { headers: getAuthHeaders() });
    return handleResponse(res);
}

export async function saveTransactionApi(data, id = null) {
    const method = id ? 'PUT' : 'POST';
    const endpoint = id ? `/transactions/${id}` : '/transactions/';
    
    const res = await fetch(`${apiBase}${endpoint}`, {
        method,
        headers: getAuthHeaders(),
        body: JSON.stringify(data),
    });
    return handleResponse(res);
}

export async function deleteTransactionApi(id) {
    const res = await fetch(`${apiBase}/transactions/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
    });
    return handleResponse(res);
}

export async function createCategoryApi(data) {
    const res = await fetch(`${apiBase}/categories/`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(data),
    });
    return handleResponse(res);
}

export async function deleteCategoryApi(id) {
    const res = await fetch(`${apiBase}/categories/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
    });
    return handleResponse(res);
}
