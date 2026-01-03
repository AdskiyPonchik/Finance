/* =========================================
 * UI MODULE
 * ========================================= */
let expenseChart = null;
let cashflowChart = null;

// Utility to format currency
export const formatCurrency = (valueInCents) => {
    // Check if value is a valid number
    if (isNaN(valueInCents)) {
        valueInCents = 0;
    }
    // Always display as positive number for UI consistency
    const absValue = Math.abs(valueInCents);
    return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(absValue / 100);
};

export function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3000);
}

export function updateBalanceCards(balance) {
    document.getElementById('liquid-balance').textContent = formatCurrency(balance.liquid);
    document.getElementById('staking-balance').textContent = formatCurrency(balance.vault);
    document.getElementById('net-worth-balance').textContent = formatCurrency(balance.net_worth);
}

export function renderTransactions(transactions) {
    const historyBody = document.getElementById('history-transactions-tbody');
    const dashboardBody = document.getElementById('dashboard-transactions-tbody');
    
    if (historyBody) historyBody.innerHTML = '';
    if (dashboardBody) dashboardBody.innerHTML = '';

    if (!transactions || transactions.length === 0) {
        const emptyRow = `<tr><td colspan="5" style="text-align:center; color: #888;">No recent activity</td></tr>`;
        if (historyBody) historyBody.innerHTML = emptyRow;
        if (dashboardBody) dashboardBody.innerHTML = emptyRow;
        return;
    }

    const sortedTx = transactions.sort((a, b) => new Date(b.date) - new Date(a.date));

    // Full history
    if (historyBody) {
        sortedTx.forEach(tx => {
            historyBody.appendChild(createTransactionRow(tx));
        });
    }

    // Recent 5 for dashboard
    if (dashboardBody) {
        sortedTx.slice(0, 5).forEach(tx => {
            dashboardBody.appendChild(createTransactionRow(tx));
        });
    }
}

function createTransactionRow(tx) {
    const tr = document.createElement('tr');
    const displayTitle = tx.title || tx.category_name || 'Untitled';
    const amountColor = tx.amount < 0 ? '#D32F2F' : '#2E7D32';

    // Ensure opacity is 1 by default if animation fails or isn't applied immediately
    tr.style.opacity = '1'; 

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

export function renderCategoryTags(categories, containerId = 'category-tag-cloud') {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    container.innerHTML = '';
    ['expense', 'income', 'vault'].forEach(type => {
        const filtered = categories.filter(c => c.type === type);
        filtered.forEach(cat => {
            const tag = document.createElement('div');
            tag.className = 'category-tag';
            tag.textContent = ''; // Clear
            tag.appendChild(document.createTextNode(cat.name));
            
            tag.style.backgroundColor = cat.color;
            tag.dataset.id = cat.id;
            tag.dataset.name = cat.name;
            tag.dataset.type = cat.type; // Add type for smart select

            // Only add delete button for the main tag cloud, not for selection clouds
            if (containerId === 'category-tag-cloud') {
                const deleteBtn = document.createElement('span');
                deleteBtn.className = 'delete-cat-btn';
                deleteBtn.dataset.id = cat.id;
                deleteBtn.textContent = '×';
                tag.appendChild(deleteBtn);
            }

            container.appendChild(tag);
        });
    });
}

export function renderSubscriptions(subs, categories) {
    const container = document.getElementById('subscriptions-list');
    if (!container) return;
    container.innerHTML = '';

    if (subs.length === 0) {
        container.innerHTML = '<p style="grid-column: span 3; text-align: center; color: #757575;">No active subscriptions found.</p>';
        return;
    }

    subs.forEach(sub => {
        const card = document.createElement('div');
        card.className = 'card animate-entry';
        
        const category = categories.find(c => c.id === sub.category_id);
        const categoryName = category ? category.name : 'Unknown';
        const categoryColor = category ? category.color : '#ccc';
        const amountColor = sub.amount < 0 ? '#D32F2F' : '#2E7D32';

        card.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
                <div style="font-weight: bold; font-size: 1.1rem;">${sub.title}</div>
                <span style="background-color: ${categoryColor}; color: #fff; padding: 2px 8px; border-radius: 12px; font-size: 0.8rem;">${categoryName}</span>
            </div>
            <div style="font-size: 1.5rem; font-weight: bold; color: ${amountColor}; margin-bottom: 10px;">
                ${formatCurrency(sub.amount)}
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; color: #757575; font-size: 0.9rem;">
                <span>Repeats on day: <strong>${sub.day_of_month}</strong></span>
                <button class="delete-sub-btn" data-id="${sub.id}" style="background: none; border: none; cursor: pointer; color: #D32F2F; font-size: 1.2rem;">
                    <i class='bx bx-trash'></i> &times;
                </button>
            </div>
        `;
        container.appendChild(card);
    });
}

export function renderUserInfo(user) {
    const profileUsername = document.getElementById('profile-username');
    const settingsUsername = document.getElementById('settings-username');
    if (profileUsername) profileUsername.textContent = user.username;
    if (settingsUsername) settingsUsername.textContent = user.username;
}

export function renderChart(transactions, categories) {
    const canvas = document.getElementById('expenseChart');
    if (!canvas) return;

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

    const ctx = canvas.getContext('2d');
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

export function renderAnalytics(data) {
    // Helper to update text and class
    const updateRow = (id, amount, invertColor=false) => {
        const el = document.getElementById(id);
        if (!el) return;
        
        // Convert cents to units (backend sends cents)
        const val = amount / 100;
        el.textContent = formatCurrency(amount); 
        
        el.className = 'row-amount'; // Reset
        
        // Color logic
        if (val > 0) el.classList.add(invertColor ? 'negative' : 'positive');
        if (val < 0) el.classList.add(invertColor ? 'positive' : 'negative');
        // Specific fix for "Expense" rows which are usually negative:
        if (id.includes('expense') || id.includes('withdraw')) el.classList.add('negative');
        if (id.includes('income') || id.includes('deposit')) el.classList.add('positive');
    };

    // Liquid
    updateRow('liquid-opening', data.liquid.opening);
    updateRow('liquid-income', data.liquid.income);
    updateRow('liquid-expense', data.liquid.expense);
    updateRow('liquid-net-flow', data.liquid.net_flow);
    updateRow('liquid-closing', data.liquid.closing);

    // Vault
    updateRow('vault-opening', data.vault.opening);
    updateRow('vault-deposit', data.vault.deposit);
    updateRow('vault-withdraw', data.vault.withdraw);
    updateRow('vault-closing', data.vault.closing);

    // Chart logic (Keep existing Chart.js logic)
    const ctx = document.getElementById('cashflowChart').getContext('2d');
    if (cashflowChart) cashflowChart.destroy();

    const income = data.liquid.income / 100;
    const expense = Math.abs(data.liquid.expense / 100);
    const vaultIn = data.vault.deposit / 100;
    const vaultOut = Math.abs(data.vault.withdraw / 100);

    cashflowChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Income', 'Expense', 'Vault In', 'Vault Out'],
            datasets: [{
                label: 'Amount (€)',
                data: [income, expense, vaultIn, vaultOut],
                backgroundColor: [
                    'rgba(46, 125, 50, 0.7)',
                    'rgba(211, 47, 47, 0.7)',
                    'rgba(109, 76, 65, 0.7)',
                    'rgba(25, 118, 210, 0.7)'
                ],
                borderColor: [
                    'rgba(46, 125, 50, 1)',
                    'rgba(211, 47, 47, 1)',
                    'rgba(109, 76, 65, 1)',
                    'rgba(25, 118, 210, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: { y: { beginAtZero: true } },
            plugins: { legend: { display: false } }
        }
    });
}

export function renderActivityMap(data, onDateClickCallback) {
    const grid = document.getElementById('heatmap-grid');
    if (!grid) return;
    grid.innerHTML = '';
    
    const today = new Date();
    // Generate last 365 days
    const days = [];
    for (let i = 364; i >= 0; i--) {
        const d = new Date(today);
        d.setDate(d.getDate() - i);
        days.push(d);
    }
    
    // Group by month
    const months = {};
    days.forEach(d => {
        const key = `${d.getFullYear()}-${d.getMonth()}`;
        if (!months[key]) months[key] = [];
        months[key].push(d);
    });

    // Render months
    Object.keys(months).sort().reverse().forEach(key => {
        const monthContainer = document.createElement('div');
        monthContainer.className = 'heatmap-month';
        
        const monthLabel = document.createElement('div');
        monthLabel.className = 'heatmap-month-label';
        const firstDate = months[key][0];
        monthLabel.textContent = firstDate.toLocaleString('default', { month: 'short' });
        monthContainer.appendChild(monthLabel);

        const daysContainer = document.createElement('div');
        daysContainer.className = 'heatmap-days';

        months[key].forEach(date => {
            const dateStr = date.toISOString().split('T')[0];
            const count = data[dateStr] || 0;
            
            const cell = document.createElement('div');
            
            // Determine level (0-4)
            let level = 0;
            if (count > 0) {
                // Simple scale for now
                if (count <= 2) level = 1;
                else if (count <= 5) level = 2;
                else if (count <= 10) level = 3;
                else level = 4;
            }

            cell.className = `heatmap-cell heatmap-level-${level}`;
            cell.title = `${dateStr}: ${count} transactions`; // Tooltip
            cell.dataset.date = dateStr;
            
            cell.addEventListener('click', () => {
                if (onDateClickCallback) {
                    onDateClickCallback(dateStr);
                }
            });
            
            daysContainer.appendChild(cell);
        });
        
        monthContainer.appendChild(daysContainer);
        grid.appendChild(monthContainer);
    });
}

export function selectCategory(tagElement, inputId = 'tx-category-name-selected') {
    // Only remove 'selected' from siblings within the same container
    const container = tagElement.parentElement;
    container.querySelectorAll('.category-tag').forEach(t => t.classList.remove('selected'));
    
    tagElement.classList.add('selected');
    const input = document.getElementById(inputId);
    if (input) input.value = tagElement.dataset.id;
}

export function openModal(modalId) {
    document.getElementById(modalId).style.display = 'flex';
}

export function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

export function openProfileModal(user) {
    document.getElementById('profile-username-input').value = user.username;
    openModal('profile-modal');
}

export function updateToggleState(groupId, selectedValue) {
    const group = document.getElementById(groupId);
    if (!group) return;

    // Update active class on buttons
    const buttons = group.querySelectorAll('button');
    buttons.forEach(btn => {
        if (btn.dataset.value === selectedValue) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // Update hidden input value
    const hiddenInput = group.nextElementSibling;
    if (hiddenInput && hiddenInput.type === 'hidden') {
        hiddenInput.value = selectedValue;
    }

    // Handle visibility of Vault Action toggle
    if (groupId === 'tx-type-toggle-group') {
        const vaultActionToggle = document.getElementById('vault-action-toggle');
        if (vaultActionToggle) {
            vaultActionToggle.style.display = selectedValue === 'vault' ? 'block' : 'none';
        }
    }
}

export function animateDashboard() {
    // Select elements to animate
    const elements = [
        ...document.querySelectorAll('.card-title'),
        ...document.querySelectorAll('.card'),
        ...document.querySelectorAll('.chart-wrapper'),
        ...document.querySelectorAll('tbody tr')
    ];

    // Reset animations first (optional, but good for re-runs)
    elements.forEach(el => {
        el.classList.remove('animate-entry');
        el.style.opacity = '0'; // Ensure hidden before animation starts
        void el.offsetWidth; // Trigger reflow
    });

    // Apply animation with stagger
    let delay = 0;
    elements.forEach((el, index) => {
        el.classList.add('animate-entry');
        
        // Custom stagger logic
        if (el.classList.contains('card-title')) {
            el.style.animationDelay = '0ms';
        } else if (el.classList.contains('card')) {
            delay += 50;
            el.style.animationDelay = `${100 + delay}ms`;
        } else if (el.tagName === 'TR') {
            // Only stagger first 10 rows to avoid massive delay on long lists
            const rowDelay = index < 15 ? index * 30 : 15 * 30; 
            el.style.animationDelay = `${400 + rowDelay}ms`;
        } else {
            el.style.animationDelay = '200ms';
        }
    });
}
