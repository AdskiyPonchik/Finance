import { getAuthHeaders, formatCurrency, logout } from './app.js';
import { showToast } from './ui.js';

let cashflowChart = null;
let heatmapData = {};
let selectionStart = null;
let selectionEnd = null;

document.addEventListener('DOMContentLoaded', () => {
    // Initialize dates to current month
    const today = new Date();
    const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
    const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);

    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');

    // Format dates as YYYY-MM-DD
    startDateInput.value = firstDay.toISOString().split('T')[0];
    endDateInput.value = lastDay.toISOString().split('T')[0];

    updateDateDisplay(startDateInput.value, endDateInput.value);

    // Bind events
    document.getElementById('calculate-btn').addEventListener('click', loadAnalytics);
    document.getElementById('logout-btn').addEventListener('click', logout);
    
    // Mobile menu toggle
    const menuToggle = document.getElementById('menu-toggle');
    const sidebar = document.getElementById('app-sidebar');
    const overlay = document.getElementById('sidebar-overlay');

    if (menuToggle) {
        menuToggle.addEventListener('click', () => {
            sidebar.style.display = 'block';
            overlay.style.display = 'block';
        });
    }

    if (overlay) {
        overlay.addEventListener('click', () => {
            sidebar.style.display = 'none';
            overlay.style.display = 'none';
        });
    }

    // Initial load
    loadHeatmap();
    loadAnalytics();
});

async function loadHeatmap() {
    try {
        const response = await fetch('/api/analytics/heatmap', {
            headers: getAuthHeaders()
        });

        if (response.status === 401) return; // Handled elsewhere usually

        if (response.ok) {
            heatmapData = await response.json();
            renderHeatmap();
        }
    } catch (error) {
        console.error("Failed to load heatmap data", error);
    }
}

function renderHeatmap() {
    const grid = document.getElementById('heatmap-grid');
    grid.innerHTML = '';

    const today = new Date();
    // Generate last 365 days
    const days = [];
    for (let i = 364; i >= 0; i--) {
        const d = new Date(today);
        d.setDate(d.getDate() - i);
        days.push(d);
    }

    days.forEach(date => {
        const dateStr = date.toISOString().split('T')[0];
        const count = heatmapData[dateStr] || 0;

        const cell = document.createElement('div');
        cell.className = `heatmap-cell heatmap-level-${getLevel(count)}`;
        cell.title = `${dateStr}: ${count} transactions`;
        cell.dataset.date = dateStr;

        cell.addEventListener('click', () => handleDateSelection(dateStr));

        grid.appendChild(cell);
    });

    // Highlight initial range if set
    highlightRange();
}

function getLevel(count) {
    if (count === 0) return 0;
    if (count <= 2) return 1;
    if (count <= 5) return 2;
    if (count <= 10) return 3;
    return 4;
}

function handleDateSelection(dateStr) {
    if (!selectionStart || (selectionStart && selectionEnd)) {
        // Start new selection
        selectionStart = dateStr;
        selectionEnd = null;
    } else {
        // Complete selection
        if (dateStr < selectionStart) {
            selectionEnd = selectionStart;
            selectionStart = dateStr;
        } else {
            selectionEnd = dateStr;
        }

        // Update inputs and trigger load
        document.getElementById('start-date').value = selectionStart;
        document.getElementById('end-date').value = selectionEnd;
        updateDateDisplay(selectionStart, selectionEnd);
        loadAnalytics();
    }

    highlightRange();
}

function highlightRange() {
    const cells = document.querySelectorAll('.heatmap-cell');
    const start = selectionStart || document.getElementById('start-date').value;
    const end = selectionEnd || document.getElementById('end-date').value;

    cells.forEach(cell => {
        const d = cell.dataset.date;
        cell.classList.remove('selected-start', 'selected-end', 'selected-range');

        if (d === start) cell.classList.add('selected-start');
        if (d === end) cell.classList.add('selected-end');
        if (start && end && d > start && d < end) cell.classList.add('selected-range');
    });
}

function updateDateDisplay(start, end) {
    const startEl = document.getElementById('display-start');
    const endEl = document.getElementById('display-end');
    if (startEl) startEl.textContent = start || 'Select start';
    if (endEl) endEl.textContent = end || 'Select end';
}

async function loadAnalytics() {
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;

    if (!startDate || !endDate) {
        showToast("Please select both start and end dates.", "error");
        return;
    }

    // Sync selection state if manually triggered
    selectionStart = startDate;
    selectionEnd = endDate;
    highlightRange();
    updateDateDisplay(startDate, endDate);

    try {
        const response = await fetch(`/api/analytics/cashflow?start_date=${startDate}&end_date=${endDate}`, {
            headers: getAuthHeaders()
        });

        if (response.status === 401) {
            window.location.href = '/'; // Redirect to login
            return;
        }

        if (!response.ok) {
            throw new Error('Failed to fetch analytics data');
        }

        const data = await response.json();
        updateUI(data);
        renderCashflowChart(data);

    } catch (error) {
        console.error('Error loading analytics:', error);
        showToast('Failed to load analytics data.', 'error');
    }
}

function updateUI(data) {
    // Liquid
    updateElement('liquid-opening', data.liquid.opening);
    updateElement('liquid-income', data.liquid.income);
    updateElement('liquid-expense', data.liquid.expense);
    updateElement('liquid-net-flow', data.liquid.net_flow);
    updateElement('liquid-closing', data.liquid.closing);

    // Vault
    updateElement('vault-opening', data.vault.opening);
    updateElement('vault-deposit', data.vault.deposit);
    updateElement('vault-withdraw', data.vault.withdraw);
    updateElement('vault-closing', data.vault.closing);
}

function updateElement(id, value) {
    const el = document.getElementById(id);
    if (el) {
        // Convert cents to float
        const floatVal = value / 100;
        el.textContent = formatCurrency(floatVal);
        
        // Add color classes for flows
        if (id.includes('income') || id.includes('deposit')) {
            el.classList.remove('negative');
            el.classList.add('positive');
        } else if (id.includes('expense') || id.includes('withdraw')) {
            el.classList.remove('positive');
            el.classList.add('negative');
        } else if (id.includes('net-flow')) {
            el.classList.remove('positive', 'negative');
            if (floatVal > 0) el.classList.add('positive');
            if (floatVal < 0) el.classList.add('negative');
        }
    }
}

function renderCashflowChart(data) {
    const ctx = document.getElementById('cashflowChart').getContext('2d');
    
    if (cashflowChart) {
        cashflowChart.destroy();
    }

    const income = data.liquid.income / 100;
    const expense = Math.abs(data.liquid.expense / 100); // Show as positive bar
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
                    'rgba(46, 125, 50, 0.7)',  // Green (Income)
                    'rgba(211, 47, 47, 0.7)',  // Red (Expense)
                    'rgba(109, 76, 65, 0.7)',  // Brown (Vault In)
                    'rgba(25, 118, 210, 0.7)'  // Blue (Vault Out)
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
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '€' + value;
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(context.raw);
                        }
                    }
                }
            }
        }
    });
}
