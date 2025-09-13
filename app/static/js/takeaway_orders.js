// JS para eliminar fila de pedido para llevar sin recargar

document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.delete-takeaway-order-form').forEach(function(form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            if (!confirm('¿Estás seguro de que quieres eliminar este pedido de la lista?')) return;
            const row = form.closest('tr');
            const formData = new FormData(form);
            fetch(form.action, {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (response.redirected || response.status === 204 || response.ok) {
                    row.remove();
                } else {
                    return response.text().then(text => { throw new Error(text); });
                }
            })
            .catch(err => {
                alert('Error al eliminar el pedido.');
            });
        });
    });
});
