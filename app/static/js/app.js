/* =========================================
 * APP MODULE (Main Entry Point)
 * ========================================= */
import { 
    loginApi, 
    fetchBalance, 
    fetchExpenseBreakdown,
    fetchTransactions, 
    fetchCategories, 
    fetchUser, 
    fetchUserProfile,
    updateUserProfile,
    saveTransactionApi, 
    deleteTransactionApi, 
    createCategoryApi,
    deleteCategoryApi,
    fetchRecurring,
    processRecurring,
    createRecurring,
    deleteRecurring,
    fetchCashflow,
    fetchActivityMap
} from './api.js';

import { 
    showToast, 
    updateBalanceCards, 
    renderTransactions, 
    renderCategoryTags, 
    renderSubscriptions,
    renderAnalytics,
    renderUserInfo, 
    renderChart, 
    selectCategory, 
    openModal, 
    closeModal,
    openProfileModal,
    updateToggleState,
    animateDashboard,
    renderActivityMap
} from './ui.js';

import { formatLocalDate } from './date.js';

let currentTransactionId = null;
let currentHistoryPage = 0;
const HISTORY_PAGE_SIZE = 50;
let allTransactions = []; // Store for optimistic updates

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
        animateDashboard(); // Animate on initial load
    } else {
        loginOverlay.style.display = 'flex';
        appSidebar.style.display = 'none';
        mainContent.style.display = 'none';
    }

    attachEventListeners();
});

async function loadDashboard() {
    try {
        await processRecurring();
        const [balance, transactionsResponse, categories, user, expenses] = await Promise.all([
            fetchBalance(),
            fetchTransactions(), // Fetches first page by default
            fetchCategories(),
            fetchUser(),
            fetchExpenseBreakdown(),
        ]);

        allTransactions = transactionsResponse.items; // Store locally
        const totalTransactions = transactionsResponse.total;

        updateBalanceCards(balance);
        renderTransactions(allTransactions);
        renderCategoryTags(categories);
        renderChart(expenses);
        renderUserInfo(user);
        
        // Update Pagination Controls
        updatePaginationControls(totalTransactions);
        
        animateDashboard(); // Animate after data refresh
        
    } catch (error) {
        showToast(error.message, 'error');
        console.error("Dashboard Load Error:", error);
    }
}

async function loadHistoryPage(offset) {
    try {
        // Manually fetch with offset
        const res = await fetch(`/api/transactions/?offset=${offset}&limit=${HISTORY_PAGE_SIZE}`, {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`,
                'Content-Type': 'application/json',
            }
        });
        
        if (!res.ok) throw new Error('Failed to fetch history');
        const data = await res.json();
        
        allTransactions = data.items;
        renderTransactions(allTransactions);
        updatePaginationControls(data.total);
        
    } catch (error) {
        showToast("Failed to load history page.", "error");
    }
}

function updatePaginationControls(total) {
    const prevBtn = document.getElementById('prev-page-btn');
    const nextBtn = document.getElementById('next-page-btn');
    const pageInfo = document.getElementById('page-info');
    
    if (!prevBtn || !nextBtn || !pageInfo) return;

    const totalPages = Math.ceil(total / HISTORY_PAGE_SIZE) || 1;
    const currentPage = Math.floor(currentHistoryPage / HISTORY_PAGE_SIZE) + 1;

    pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
    
    prevBtn.disabled = currentHistoryPage === 0;
    nextBtn.disabled = currentPage >= totalPages;
}

async function loadSubscriptions() {
    try {
        const [subs, categories] = await Promise.all([
            fetchRecurring(),
            fetchCategories()
        ]);
        renderSubscriptions(subs, categories);
    } catch (error) {
        showToast("Failed to load subscriptions.", "error");
    }
}

async function loadAnalytics() {
    const startDate = document.getElementById('analytics-start').value;
    const endDate = document.getElementById('analytics-end').value;
    if (!startDate || !endDate) {
        showToast("Please select a start and end date.", "error");
        return;
    }
    try {
        const data = await fetchCashflow(startDate, endDate);
        renderAnalytics(data);
    } catch (error) {
        showToast("Failed to load analytics data.", "error");
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
        link.addEventListener('click', async (e) => {
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
            
            if (targetId === 'subscriptions-page') {
                loadSubscriptions();
            } else if (targetId === 'analytics-page') {
                const today = new Date();
                const firstDay = formatLocalDate(new Date(today.getFullYear(), today.getMonth(), 1));
                const lastDay = formatLocalDate(new Date(today.getFullYear(), today.getMonth() + 1, 0));
                document.getElementById('analytics-start').value = firstDay;
                document.getElementById('analytics-end').value = lastDay;

                try {
                    const activityData = await fetchActivityMap();
                    renderActivityMap(activityData, (date) => {
                        // Callback when a date is clicked on heatmap
                        // We can auto-set range or just start date
                        // For now, let's just set both to the clicked date for single day view, 
                        // or handle range logic inside analytics.js (which we did).
                        // The callback in ui.js actually just passes the date string.
                        // The logic in analytics.js handles the range selection state.
                        // So we just need to trigger the load if a range is complete.
                        
                        // Actually, analytics.js handles the click logic internally now.
                        // We just need to ensure the initial render happens.
                    });
                } catch (error) {
                    console.error("Failed to load activity map", error);
                }

                loadAnalytics();
            }
            
            // Re-trigger animation when switching tabs
            animateDashboard();
        });
    });

    // --- Pagination Controls ---
    const prevBtn = document.getElementById('prev-page-btn');
    const nextBtn = document.getElementById('next-page-btn');
    
    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            if (currentHistoryPage > 0) {
                currentHistoryPage -= HISTORY_PAGE_SIZE;
                loadHistoryPage(currentHistoryPage);
            }
        });
    }
    
    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            currentHistoryPage += HISTORY_PAGE_SIZE;
            loadHistoryPage(currentHistoryPage);
        });
    }

    // --- Mobile Sidebar Toggle ---
    const menuToggle = document.getElementById('menu-toggle');
    if (menuToggle) {
        menuToggle.addEventListener('click', () => {
            document.getElementById('app-sidebar').classList.add('active');
            document.getElementById('sidebar-overlay').classList.add('show');
        });
    }

    const sidebarOverlay = document.getElementById('sidebar-overlay');
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', () => {
            document.getElementById('app-sidebar').classList.remove('active');
            document.getElementById('sidebar-overlay').classList.remove('show');
        });
    }

    // --- Logout ---
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            localStorage.removeItem('token');
            location.reload();
        });
    }

    // --- Modal ---
    const quickAddBtn = document.getElementById('quick-add-btn');
    if (quickAddBtn) {
        quickAddBtn.addEventListener('click', openAddModal);
    }
    
    const modalCloseBtn = document.querySelector('.modal-close');
    if (modalCloseBtn) {
        modalCloseBtn.addEventListener('click', () => closeModal('add-tx-modal'));
    }
    
    // --- Transaction Actions (Edit/Delete) ---
    const mainElement = document.querySelector('main');
    if (mainElement) {
        mainElement.addEventListener('click', async (e) => {
            if (e.target.classList.contains('delete-btn')) {
                const txId = e.target.dataset.txId;
                if (confirm('Are you sure you want to delete this transaction?')) {
                    try {
                        await deleteTransactionApi(txId);
                        showToast('Transaction deleted.', 'success');
                        // Optimistic delete
                        allTransactions = allTransactions.filter(t => t.id != txId);
                        renderTransactions(allTransactions);
                        // Also refresh balance in background
                        fetchBalance().then(updateBalanceCards);
                    } catch (error) {
                        showToast(`Delete failed: ${error.message}`, 'error');
                    }
                }
            }
            if (e.target.classList.contains('edit-btn')) {
                const txId = e.target.dataset.txId;
                // Use local data instead of fetching again
                const tx = allTransactions.find(t => t.id == txId);
                if (tx) openEditModal(tx);
            }
        });
    }

    // --- Form & Category Logic ---
    const addTxForm = document.getElementById('add-tx-form');
    if (addTxForm) {
        addTxForm.addEventListener('submit', (e) => {
            e.preventDefault();
            saveTransaction();
        });
    }

    const categoryTagCloud = document.getElementById('category-tag-cloud');
    if (categoryTagCloud) {
        categoryTagCloud.addEventListener('click', async (e) => {
            // Handle Delete
            if (e.target.classList.contains('delete-cat-btn')) {
                e.stopPropagation();
                const catId = e.target.dataset.id;
                if (confirm('Delete this category?')) {
                    try {
                        await deleteCategoryApi(catId);
                        showToast('Category deleted.', 'success');
                        const categories = await fetchCategories();
                        renderCategoryTags(categories);
                    } catch (error) {
                        showToast(`Delete failed: ${error.message}`, 'error');
                    }
                }
                return;
            }

            // Handle Select
            const tag = e.target.closest('.category-tag');
            if (tag) {
                selectCategory(tag);
                const type = tag.dataset.type;
                if (type) {
                    updateToggleState('tx-type-toggle-group', type);
                }
            }
        });
    }

    const saveCategoryBtn = document.getElementById('save-category-btn');
    if (saveCategoryBtn) {
        saveCategoryBtn.addEventListener('click', saveNewCategory);
    }

    // --- Toggle Group Logic ---
    document.querySelectorAll('.toggle-group').forEach(group => {
        group.addEventListener('click', (e) => {
            if (e.target.tagName === 'BUTTON') {
                e.preventDefault(); // Prevent form submission
                const selectedValue = e.target.dataset.value;
                updateToggleState(group.id, selectedValue);
            }
        });
    });

    // --- Profile Settings Logic ---
    const settingsLink = document.getElementById('settings-link');
    if (settingsLink) {
        settingsLink.addEventListener('click', async (e) => {
            // The default behavior is already handled by the sidebar navigation logic (switching tabs)
            // But we might want to refresh user data when entering settings
            try {
                const user = await fetchUserProfile();
                renderUserInfo(user);
            } catch (error) {
                console.error("Failed to fetch user profile:", error);
            }
        });
    }

    const editProfileBtn = document.getElementById('edit-profile-btn');
    if (editProfileBtn) {
        editProfileBtn.addEventListener('click', async () => {
            try {
                const user = await fetchUserProfile();
                openProfileModal(user);
            } catch (error) {
                showToast("Failed to load profile data", "error");
            }
        });
    }

    const profileForm = document.getElementById('profile-form');
    if (profileForm) {
        profileForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            showToast("Profile update not yet implemented on backend.", "info");
            closeModal('profile-modal');
        });
    }

    // --- Subscriptions Logic ---
    const addSubBtn = document.getElementById('add-sub-btn');
    if (addSubBtn) {
        addSubBtn.addEventListener('click', async () => {
            const categories = await fetchCategories();
            renderCategoryTags(categories.filter(c => c.type !== 'vault'), 'sub-category-tag-cloud');
            openModal('add-sub-modal');
        });
    }

    const addSubForm = document.getElementById('add-sub-form');
    if (addSubForm) {
        addSubForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const title = document.getElementById('sub-title').value;
            const amount = parseFloat(document.getElementById('sub-amount').value);
            const categoryId = document.getElementById('sub-category-id').value;
            const dayOfMonth = parseInt(document.getElementById('sub-day').value);
            const type = document.getElementById('sub_type').value;

            if (!title || !amount || !categoryId || !dayOfMonth) {
                showToast("All fields are required.", "error");
                return;
            }
            if (dayOfMonth < 1 || dayOfMonth > 31) {
                showToast("Day must be between 1 and 31.", "error");
                return;
            }

            let finalAmount = Math.round(amount * 100);
            if (type === 'expense') {
                finalAmount = -finalAmount;
            }

            const data = { title, amount: finalAmount, category_id: parseInt(categoryId), day_of_month: dayOfMonth, type };
            
            try {
                await createRecurring(data);
                showToast("Subscription added!", "success");
                closeModal('add-sub-modal');
                await loadDashboard();
                await loadSubscriptions();
            } catch (error) {
                showToast(`Error: ${error.message}`, "error");
            }
        });
    }

    const subCategoryCloud = document.getElementById('sub-category-tag-cloud');
    if (subCategoryCloud) {
        subCategoryCloud.addEventListener('click', (e) => {
            const tag = e.target.closest('.category-tag');
            if (tag) {
                selectCategory(tag, 'sub-category-id');
                updateToggleState('sub-type-toggle-group', tag.dataset.type);
            }
        });
    }

    const subList = document.getElementById('subscriptions-list');
    if (subList) {
        subList.addEventListener('click', async (e) => {
            const deleteBtn = e.target.closest('.delete-sub-btn');
            if (deleteBtn) {
                const subId = deleteBtn.dataset.id;
                if (confirm('Are you sure you want to delete this subscription?')) {
                    try {
                        await deleteRecurring(subId);
                        showToast('Subscription deleted.', 'success');
                        loadSubscriptions();
                    } catch (error) {
                        showToast(`Delete failed: ${error.message}`, 'error');
                    }
                }
            }
        });
    }

    // --- Analytics Logic ---
    const calcAnalyticsBtn = document.getElementById('calc-analytics-btn');
    if (calcAnalyticsBtn) {
        calcAnalyticsBtn.addEventListener('click', loadAnalytics);
    }
}

function openAddModal() {
    currentTransactionId = null;
    document.getElementById('modal-title').textContent = 'Add Transaction';
    document.getElementById('add-tx-form').reset();
    document.getElementById('tx-date').value = formatLocalDate(new Date());
    document.getElementById('edit-tx-id').value = '';
    
    // Reset toggles
    updateToggleState('tx-type-toggle-group', 'expense');
    updateToggleState('vault-action-toggle-group', 'deposit');
    
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

    // Set transaction type toggle
    updateToggleState('tx-type-toggle-group', tx.category_type);
    
    if (tx.category_type === 'vault') {
        const vaultAction = tx.amount > 0 ? 'withdraw' : 'deposit';
        updateToggleState('vault-action-toggle-group', vaultAction);
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

    const txType = document.getElementById('category_type').value;
    if (txType === 'expense') {
        amountCents = -amountCents;
    } else if (txType === 'vault') {
        const vaultAction = document.getElementById('vault_action').value;
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
        const updatedTx = await saveTransactionApi(payload, currentTransactionId);
        showToast('Transaction saved successfully!', 'success');
        closeModal('add-tx-modal');
        
        // Optimistic Update
        if (currentTransactionId) {
            // Edit mode: Update existing item in array
            const index = allTransactions.findIndex(t => t.id === currentTransactionId);
            if (index !== -1) {
                allTransactions[index] = updatedTx;
                renderTransactions(allTransactions);
            }
        } else {
            // Add mode: Add to top of list
            allTransactions.unshift(updatedTx);
            renderTransactions(allTransactions);
        }
        
        // Refresh balance in background
        fetchBalance().then(updateBalanceCards);
        
    } catch (error) {
        showToast(`Save failed: ${error.message}`, 'error');
    } finally {
        saveBtn.disabled = false;
    }
}

async function saveNewCategory() {
    const name = document.getElementById('new-category-name').value.trim();
    const color = document.getElementById('new-category-color').value;
    const type = document.getElementById('category_type').value;

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
