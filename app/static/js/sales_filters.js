// Filtros y búsqueda AJAX para ventas (puedes adaptar a otros módulos)
document.addEventListener('DOMContentLoaded', function() {
    const filterForm = document.querySelector("form[action*='sales_and_reports']");
    if (!filterForm) return;
    filterForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const url = filterForm.action + '?' + new URLSearchParams(new FormData(filterForm)).toString();
        fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(r => r.text())
            .then(html => {
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const newTable = doc.querySelector('#sales-table');
                if (newTable) {
                    document.querySelector('#sales-table').replaceWith(newTable);
                    showToast('Filtros aplicados', 'success');
                }
            })
            .catch(() => showToast('Error al filtrar', 'danger'));
    });
});
