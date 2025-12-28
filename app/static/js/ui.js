/* =========================================
 * UI MODULE
 * ========================================= */
let expenseChart = null;

// Utility to format currency
const formatCurrency = (valueInCents) => {
    return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(valueInCents / 100);
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

export function renderCategoryTags(categories) {
    const container = document.getElementById('category-tag-cloud');
    container.innerHTML = '';
    ['expense', 'income', 'vault'].forEach(type => {
        const filtered = categories.filter(c => c.type === type);
        filtered.forEach(cat => {
            const tag = document.createElement('div');
            tag.className = 'category-tag';
            tag.textContent = cat.name; // This sets the text content, potentially overwriting children if appended later? No, textContent replaces all children.
            // Better to create a text node for the name
            tag.textContent = ''; // Clear
            tag.appendChild(document.createTextNode(cat.name));
            
            tag.style.backgroundColor = cat.color;
            tag.dataset.id = cat.id;
            tag.dataset.name = cat.name;
            tag.dataset.type = cat.type; // Add type for smart select

            const deleteBtn = document.createElement('span');
            deleteBtn.className = 'delete-cat-btn';
            deleteBtn.dataset.id = cat.id;
            deleteBtn.textContent = '×';
            tag.appendChild(deleteBtn);

            container.appendChild(tag);
        });
    });
}

export function renderUserInfo(user) {
    document.getElementById('profile-username').textContent = user.username;
    document.getElementById('settings-username').textContent = user.username;
}

export function renderChart(transactions, categories) {
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

export function selectCategory(tagElement) {
    document.querySelectorAll('.category-tag').forEach(t => t.classList.remove('selected'));
    tagElement.classList.add('selected');
    document.getElementById('tx-category-name-selected').value = tagElement.dataset.id;
}

export function openModal(modalId) {
    document.getElementById(modalId).style.display = 'flex';
}

export function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
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
