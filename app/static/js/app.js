/* =========================================
 * APP MODULE (Main Entry Point)
 * ========================================= */
import { 
    loginApi, 
    fetchBalance, 
    fetchTransactions, 
    fetchCategories, 
    fetchUser, 
    saveTransactionApi, 
    deleteTransactionApi, 
    createCategoryApi 
} from './api.js';

import { 
    showToast, 
    updateBalanceCards, 
    renderTransactions, 
    renderCategoryTags, 
    renderUserInfo, 
    renderChart, 
    selectCategory, 
    openModal, 
    closeModal 
} from './ui.js';

let currentTransactionId = null;

document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('token');
    const loginOverlay = document.getElementById('login-overlay');
    const appSidebar = document.getElementById('app-sidebar');
    const mainContent = document.getElementById('app-main-content');

    if (token) {
        loginOverlay.style.display = 'none';
        appSidebar.style.display = 'flex';
        mainContent.style.display = 'block';
        loadDashboard();
    } else {
        loginOverlay.style.display = 'flex';
        appSidebar.style.display = 'none';
        mainContent.style.display = 'none';
    }

    attachEventListeners();
});

async function loadDashboard() {
    try {
        const [balance, transactions, categories, user] = await Promise.all([
            fetchBalance(),
            fetchTransactions(),
            fetchCategories(),
            fetchUser(),
        ]);

        updateBalanceCards(balance);
        renderTransactions(transactions);
        renderCategoryTags(categories);
        renderChart(transactions, categories);
        renderUserInfo(user);
        
    } catch (error) {
        showToast(error.message, 'error');
        console.error("Dashboard Load Error:", error);
    }
}

function attachEventListeners() {
    // --- Login Form ---
    document.getElementById('login-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        try {
            await loginApi(username, password);
            location.reload();
        } catch (e) {
            document.getElementById('error-msg').textContent = 'Login failed. Please check your credentials.';
        }
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
    document.getElementById('logout-btn').addEventListener('click', () => {
        localStorage.removeItem('token');
        location.reload();
    });

    // --- Modal ---
    document.getElementById('quick-add-btn').addEventListener('click', openAddModal);
    document.querySelector('.modal-close').addEventListener('click', () => closeModal('add-tx-modal'));
    
    // --- Transaction Actions (Edit/Delete) ---
    document.querySelector('main').addEventListener('click', async (e) => {
        if (e.target.classList.contains('delete-btn')) {
            const txId = e.target.dataset.txId;
            if (confirm('Are you sure you want to delete this transaction?')) {
                try {
                    await deleteTransactionApi(txId);
                    showToast('Transaction deleted.', 'success');
                    await loadDashboard();
                } catch (error) {
                    showToast(`Delete failed: ${error.message}`, 'error');
                }
            }
        }
        if (e.target.classList.contains('edit-btn')) {
            const txId = e.target.dataset.txId;
            const allTx = await fetchTransactions();
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

function openAddModal() {
    currentTransactionId = null;
    document.getElementById('modal-title').textContent = 'Add Transaction';
    document.getElementById('add-tx-form').reset();
    document.getElementById('tx-date').valueAsDate = new Date();
    document.getElementById('edit-tx-id').value = '';
    document.getElementById('vault-action-toggle').style.display = 'none';
    document.querySelector('input[name="category_type"][value="expense"]').checked = true;
    
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

    const typeRadio = document.querySelector(`input[name="category_type"][value="${tx.category_type}"]`);
    if (typeRadio) typeRadio.checked = true;
    
    document.getElementById('vault-action-toggle').style.display = tx.category_type === 'vault' ? 'block' : 'none';
    if (tx.category_type === 'vault') {
        const vaultAction = tx.amount > 0 ? 'withdraw' : 'deposit';
        document.querySelector(`input[name="vault_action"][value="${vaultAction}"]`).checked = true;
    }

    const selectedTag = document.querySelector('.category-tag.selected');
    if (selectedTag) selectedTag.classList.remove('selected');
    const tagToSelect = document.querySelector(`.category-tag[data-id="${tx.category_id}"]`);
    if (tagToSelect) tagToSelect.classList.add('selected');
    document.getElementById('tx-category-name-selected').value = tx.category_id;

    openModal('add-tx-modal');
}

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

    saveBtn.disabled = true;
    try {
        await saveTransactionApi(payload, currentTransactionId);
        showToast('Transaction saved successfully!', 'success');
        closeModal('add-tx-modal');
        await loadDashboard();
    } catch (error) {
        showToast(`Save failed: ${error.message}`, 'error');
    } finally {
        saveBtn.disabled = false;
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
        const newCategory = await createCategoryApi({ name, color, type });
        showToast('Category created!', 'success');
        
        document.getElementById('new-category-name').value = '';
        document.querySelector('details').open = false;
        
        const categories = await fetchCategories();
        renderCategoryTags(categories);

        const newTag = document.querySelector(`.category-tag[data-id="${newCategory.id}"]`);
        if(newTag) selectCategory(newTag);

    } catch (error) {
        showToast(`Failed to create category: ${error.message}`, 'error');
    }
}

// Expose closeModal to global scope for the HTML onclick attribute
window.closeModal = closeModal;
