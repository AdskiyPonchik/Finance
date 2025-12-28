/* =========================================
 * 1. GLOBAL VARIABLES & UTILS
 * ========================================= */
let currentTransactionId = null; // null for create, ID for edit
let expenseChart = null; // To hold the chart instance
const apiBase = '/api';

// Utility to format currency
const formatCurrency = (valueInCents) => {
    return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(valueInCents / 100);
};

/* --- Toast Notifications --- */
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3000);
}

/* =========================================
 * 2. AUTHENTICATION & STATE
 * ========================================= */
document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('token');
    const loginOverlay = document.getElementById('login-overlay');
    const appSidebar = document.getElementById('app-sidebar');
    const mainContent = document.getElementById('app-main-content');

    if (token) {
        loginOverlay.style.display = 'none';
        appSidebar.style.display = 'flex';
        mainContent.style.display = 'block';
        initializeApp();
    } else {
        loginOverlay.style.display = 'flex';
        appSidebar.style.display = 'none';
        mainContent.style.display = 'none';
    }

    // Attach all event listeners once the DOM is loaded
    attachEventListeners();
});

async function login(username, password) {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    try {
        const res = await fetch(`${apiBase}/token`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData,
        });

        if (res.ok) {
            const data = await res.json();
            localStorage.setItem('token', data.access_token);
            location.reload();
        } else {
            document.getElementById('error-msg').textContent = 'Login failed. Please check your credentials.';
        }
    } catch (e) {
        console.error(e);
        document.getElementById('error-msg').textContent = 'A network error occurred.';
    }
}

function logout() {
    localStorage.removeItem('token');
    location.reload();
}

/* =========================================
 * 3. API & DATA LOADING
 * ========================================= */
async function fetchData(endpoint, options = {}) {
    const token = localStorage.getItem('token');
    const res = await fetch(`${apiBase}${endpoint}`, {
        ...options,
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
            ...options.headers,
        },
    });

    if (res.status === 401) {
        logout();
        return;
    }
    if (res.status === 204) { // Handle No Content response for DELETE
        return;
    }
    if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'An API error occurred');
    }
    return res.json();
}

async function loadDashboard() {
    try {
        const [balance, transactions, categories, user] = await Promise.all([
            fetchData('/balance/'),
            fetchData('/transactions/'),
            fetchData('/categories/'),
            fetchData('/users/me'),
        ]);

        renderBalance(balance);
        renderTransactions(transactions);
        renderCategoryTags(categories);
        renderChart(transactions, categories);
        renderUserInfo(user);
        
    } catch (error) {
        showToast(error.message, 'error');
        console.error("Dashboard Load Error:", error);
    }
}

async function initializeApp() {
    await loadDashboard();
}

/* =========================================
 * 4. UI RENDERING
 * ========================================= */
function renderBalance(balance) {
    document.getElementById('liquid-balance').textContent = formatCurrency(balance.liquid);
    document.getElementById('staking-balance').textContent = formatCurrency(balance.vault);
    document.getElementById('net-worth-balance').textContent = formatCurrency(balance.net_worth);
}

function renderTransactions(transactions) {
    const historyBody = document.getElementById('history-transactions-tbody');
    const dashboardBody = document.getElementById('dashboard-transactions-tbody');
    
    historyBody.innerHTML = '';
    dashboardBody.innerHTML = '';

    const sortedTx = transactions.sort((a, b) => new Date(b.date) - new Date(a.date));

    // Full history
    sortedTx.forEach(tx => {
        historyBody.appendChild(createTransactionRow(tx));
    });

    // Recent 5 for dashboard
    sortedTx.slice(0, 5).forEach(tx => {
        dashboardBody.appendChild(createTransactionRow(tx));
    });
}

function createTransactionRow(tx) {
    const tr = document.createElement('tr');
    const displayTitle = tx.title || tx.category_name || 'Untitled';
    const amountColor = tx.amount < 0 ? '#D32F2F' : '#2E7D32';

    tr.innerHTML = `
        <td>${displayTitle}</td>
        <td>${tx.category_name}</td>
        <td>${new Date(tx.date).toLocaleDateString()}</td>
        <td style="text-align: right; font-weight: 600; color: ${amountColor};">${formatCurrency(tx.amount)}</td>
        <td style="text-align: center;">
            <button class="edit-btn" data-tx-id="${tx.id}">Edit</button>
            <button class="delete-btn" data-tx-id="${tx.id}">Delete</button>
        </td>
    `;
    return tr;
}

function renderCategoryTags(categories) {
    const container = document.getElementById('category-tag-cloud');
    container.innerHTML = '';
    ['expense', 'income', 'vault'].forEach(type => {
        const filtered = categories.filter(c => c.type === type);
        filtered.forEach(cat => {
            const tag = document.createElement('div');
            tag.className = 'category-tag';
            tag.textContent = cat.name;
            tag.style.backgroundColor = cat.color;
            tag.dataset.id = cat.id;
            tag.dataset.name = cat.name;
            container.appendChild(tag);
        });
    });
}

function renderUserInfo(user) {
    document.getElementById('profile-username').textContent = user.username;
    document.getElementById('settings-username').textContent = user.username;
}

function renderChart(transactions, categories) {
    const expenseData = transactions
        .filter(tx => tx.amount < 0)
        .reduce((acc, tx) => {
            const name = tx.category_name || 'Uncategorized';
            acc[name] = (acc[name] || 0) + Math.abs(tx.amount);
            return acc;
        }, {});

    const labels = Object.keys(expenseData);
    const data = Object.values(expenseData);
    
    const categoryColors = labels.map(label => {
        const cat = categories.find(c => c.name === label);
        return cat ? cat.color : '#CCCCCC';
    });

    const ctx = document.getElementById('expenseChart').getContext('2d');
    if (expenseChart) {
        expenseChart.destroy();
    }
    expenseChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data.map(v => v / 100), // convert cents to euros
                backgroundColor: categoryColors,
                borderColor: '#FFFFFF',
                borderWidth: 2,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.label}: ${formatCurrency(context.raw * 100)}`;
                        }
                    }
                }
            }
        }
    });
}

/* =========================================
 * 5. EVENT LISTENERS & UI INTERACTIONS
 * ========================================= */
function attachEventListeners() {
    // --- Login Form ---
    document.getElementById('login-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        await login(username, password);
    });

    // --- Sidebar Navigation ---
    document.querySelectorAll('.sidebar-nav .nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = link.getAttribute('data-target');
            
            document.querySelectorAll('.page').forEach(page => page.style.display = 'none');
            document.getElementById(targetId).style.display = 'block';
            
            document.querySelectorAll('.sidebar-nav .nav-link').forEach(l => l.classList.remove('active'));
            link.classList.add('active');

            // Close mobile sidebar on navigation
            if (window.innerWidth <= 768) {
                document.getElementById('app-sidebar').classList.remove('active');
                document.getElementById('sidebar-overlay').classList.remove('show');
            }
        });
    });

    // --- Mobile Sidebar Toggle ---
    document.getElementById('menu-toggle').addEventListener('click', () => {
        document.getElementById('app-sidebar').classList.add('active');
        document.getElementById('sidebar-overlay').classList.add('show');
    });

    document.getElementById('sidebar-overlay').addEventListener('click', () => {
        document.getElementById('app-sidebar').classList.remove('active');
        document.getElementById('sidebar-overlay').classList.remove('show');
    });

    // --- Logout ---
    document.getElementById('logout-btn').addEventListener('click', logout);

    // --- Modal ---
    document.getElementById('quick-add-btn').addEventListener('click', openAddModal);
    document.querySelector('.modal-close').addEventListener('click', () => closeModal('add-tx-modal'));
    
    // --- Transaction Actions (Edit/Delete) using Event Delegation ---
    document.querySelector('main').addEventListener('click', async (e) => {
        if (e.target.classList.contains('delete-btn')) {
            const txId = e.target.dataset.txId;
            if (confirm('Are you sure you want to delete this transaction?')) {
                await deleteTransaction(txId);
            }
        }
        if (e.target.classList.contains('edit-btn')) {
            const txId = e.target.dataset.txId;
            const allTx = await fetchData('/transactions/');
            const tx = allTx.find(t => t.id == txId);
            openEditModal(tx);
        }
    });

    // --- Form & Category Logic ---
    document.getElementById('add-tx-form').addEventListener('submit', (e) => {
        e.preventDefault();
        saveTransaction();
    });

    document.getElementById('category-tag-cloud').addEventListener('click', (e) => {
        if (e.target.classList.contains('category-tag')) {
            selectCategory(e.target);
        }
    });

    document.getElementById('save-category-btn').addEventListener('click', saveNewCategory);

    // --- Form Type Switch ---
    document.querySelectorAll('input[name="category_type"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            const type = e.target.value;
            document.getElementById('vault-action-toggle').style.display = type === 'vault' ? 'block' : 'none';
        });
    });
}

/* =========================================
 * 6. MODAL & FORM LOGIC
 * ========================================= */
function openModal(modalId) {
    document.getElementById(modalId).style.display = 'flex';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

function openAddModal() {
    currentTransactionId = null;
    document.getElementById('modal-title').textContent = 'Add Transaction';
    document.getElementById('add-tx-form').reset();
    document.getElementById('tx-date').valueAsDate = new Date();
    document.getElementById('edit-tx-id').value = '';
    document.getElementById('vault-action-toggle').style.display = 'none';
    document.querySelector('input[name="category_type"][value="expense"]').checked = true;
    
    // Reset category selection
    const selectedTag = document.querySelector('.category-tag.selected');
    if (selectedTag) selectedTag.classList.remove('selected');
    document.getElementById('tx-category-name-selected').value = '';

    openModal('add-tx-modal');
}

function openEditModal(tx) {
    currentTransactionId = tx.id;
    document.getElementById('modal-title').textContent = 'Edit Transaction';
    document.getElementById('add-tx-form').reset();
    
    document.getElementById('edit-tx-id').value = tx.id;
    document.getElementById('tx-title').value = tx.title || '';
    document.getElementById('tx-amount').value = Math.abs(tx.amount / 100).toFixed(2);
    document.getElementById('tx-date').value = tx.date.split('T')[0];

    // Set transaction type radio
    const typeRadio = document.querySelector(`input[name="category_type"][value="${tx.category_type}"]`);
    if (typeRadio) typeRadio.checked = true;
    
    document.getElementById('vault-action-toggle').style.display = tx.category_type === 'vault' ? 'block' : 'none';
    if (tx.category_type === 'vault') {
        const vaultAction = tx.amount > 0 ? 'withdraw' : 'deposit';
        document.querySelector(`input[name="vault_action"][value="${vaultAction}"]`).checked = true;
    }

    // Select category tag
    const selectedTag = document.querySelector('.category-tag.selected');
    if (selectedTag) selectedTag.classList.remove('selected');
    const tagToSelect = document.querySelector(`.category-tag[data-id="${tx.category_id}"]`);
    if (tagToSelect) tagToSelect.classList.add('selected');
    document.getElementById('tx-category-name-selected').value = tx.category_id;

    openModal('add-tx-modal');
}

function selectCategory(tagElement) {
    document.querySelectorAll('.category-tag').forEach(t => t.classList.remove('selected'));
    tagElement.classList.add('selected');
    document.getElementById('tx-category-name-selected').value = tagElement.dataset.id;
}

/* =========================================
 * 7. DATA MANIPULATION (SAVE, DELETE)
 * ========================================= */
async function saveTransaction() {
    const saveBtn = document.querySelector('#add-tx-form button[type="submit"]');
    const categoryId = document.getElementById('tx-category-name-selected').value;
    if (!categoryId) {
        showToast('Please select a category.', 'error');
        return;
    }

    const amountRaw = parseFloat(document.getElementById('tx-amount').value);
    if (isNaN(amountRaw) || amountRaw <= 0) {
        showToast('Please enter a valid, positive amount.', 'error');
        return;
    }
    let amountCents = Math.round(amountRaw * 100);

    const txType = document.querySelector('input[name="category_type"]:checked').value;
    if (txType === 'expense') {
        amountCents = -amountCents;
    } else if (txType === 'vault') {
        const vaultAction = document.querySelector('input[name="vault_action"]:checked').value;
        if (vaultAction === 'deposit') {
            amountCents = -amountCents;
        }
    }

    const payload = {
        title: document.getElementById('tx-title').value.trim() || null,
        amount: amountCents,
        date: document.getElementById('tx-date').value,
        category_id: parseInt(categoryId),
    };

    const method = currentTransactionId ? 'PUT' : 'POST';
    const endpoint = currentTransactionId ? `/transactions/${currentTransactionId}` : '/transactions/';

    saveBtn.disabled = true; // Disable button
    try {
        await fetchData(endpoint, { method, body: JSON.stringify(payload) });
        showToast('Transaction saved successfully!', 'success');
        closeModal('add-tx-modal');
        await loadDashboard(); // Refresh all data
    } catch (error) {
        showToast(`Save failed: ${error.message}`, 'error');
    } finally {
        saveBtn.disabled = false; // Re-enable button
    }
}

async function deleteTransaction(id) {
    try {
        await fetchData(`/transactions/${id}`, { method: 'DELETE' });
        showToast('Transaction deleted.', 'success');
        await loadDashboard(); // Refresh all data
    } catch (error) {
        showToast(`Delete failed: ${error.message}`, 'error');
    }
}

async function saveNewCategory() {
    const name = document.getElementById('new-category-name').value.trim();
    const color = document.getElementById('new-category-color').value;
    const type = document.querySelector('input[name="category_type"]:checked').value;

    if (!name) {
        showToast('Please enter a category name.', 'error');
        return;
    }

    try {
        const newCategory = await fetchData('/categories/', {
            method: 'POST',
            body: JSON.stringify({ name, color, type }),
        });
        showToast('Category created!', 'success');
        
        // Reset form and refresh categories
        document.getElementById('new-category-name').value = '';
        document.querySelector('details').open = false;
        
        const categories = await fetchData('/categories/');
        renderCategoryTags(categories);

        // Automatically select the newly created tag
        const newTag = document.querySelector(`.category-tag[data-id="${newCategory.id}"]`);
        if(newTag) selectCategory(newTag);

    } catch (error) {
        showToast(`Failed to create category: ${error.message}`, 'error');
    }
}
