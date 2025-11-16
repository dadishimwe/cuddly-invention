// Starlink Manager - Main JavaScript

// Auto-hide flash messages after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });
});

// Form validation for date ranges
const startDateInput = document.getElementById('start_date');
const endDateInput = document.getElementById('end_date');

if (startDateInput && endDateInput) {
    startDateInput.addEventListener('change', function() {
        endDateInput.min = this.value;
    });

    endDateInput.addEventListener('change', function() {
        startDateInput.max = this.value;
    });
}

// Confirm before sending reports
const reportForm = document.querySelector('.report-form');
if (reportForm) {
    reportForm.addEventListener('submit', function(e) {
        const dryRun = document.querySelector('input[name="dry_run"]');
        if (!dryRun || !dryRun.checked) {
            if (!confirm('Are you sure you want to send this report?')) {
                e.preventDefault();
            }
        }
    });
}

// Table sorting (simple implementation)
function sortTable(table, column, asc = true) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    rows.sort((a, b) => {
        const aValue = a.cells[column].textContent.trim();
        const bValue = b.cells[column].textContent.trim();
        
        return asc ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue);
    });
    
    rows.forEach(row => tbody.appendChild(row));
}

// Add click handlers to table headers for sorting
document.querySelectorAll('.table th').forEach((th, index) => {
    th.style.cursor = 'pointer';
    th.addEventListener('click', function() {
        const table = this.closest('table');
        const currentOrder = this.dataset.order || 'asc';
        const newOrder = currentOrder === 'asc' ? 'desc' : 'asc';
        
        // Reset all headers
        table.querySelectorAll('th').forEach(header => {
            delete header.dataset.order;
        });
        
        this.dataset.order = newOrder;
        sortTable(table, index, newOrder === 'asc');
    });
});
