// Filtros y búsqueda AJAX para productos
document.addEventListener('DOMContentLoaded', function() {
    const filterForm = document.getElementById('filter-form');
    if (!filterForm) return;
    filterForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const url = filterForm.action + '?' + new URLSearchParams(new FormData(filterForm)).toString();
        fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(r => r.text())
            .then(html => {
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const newTable = doc.querySelector('#products-table');
                if (newTable) {
                    document.querySelector('#products-table').replaceWith(newTable);
                    showToast('Filtros aplicados', 'success');
                }
            })
            .catch(() => showToast('Error al filtrar', 'danger'));
    });
});
