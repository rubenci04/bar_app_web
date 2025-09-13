// Validación simple para formularios de caja y otros

document.addEventListener('DOMContentLoaded', function() {
    const cashForm = document.querySelector('form[action*="open_cash_session"]');
    if (cashForm) {
        cashForm.addEventListener('submit', function(e) {
            const input = document.getElementById('starting_cash');
            if (!input.value || isNaN(input.value.replace(',', '.')) || parseFloat(input.value.replace(',', '.')) < 0) {
                e.preventDefault();
                showToast('Ingrese un monto inicial válido para la caja.', 'danger');
                input.focus();
            }
        });
    }
});
