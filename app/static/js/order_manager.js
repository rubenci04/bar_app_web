// Reemplazo completo para app/static/js/order_manager.js
// [Yo]: He añadido lógica para manejar cantidades +/- y mejorar la respuesta visual.

document.addEventListener('DOMContentLoaded', function() {
    const csrfTokenEl = document.getElementById('csrf_token_js');
    const orderIdEl = document.getElementById('order_id_js');

    if (!csrfTokenEl || !orderIdEl) return;

    const csrfToken = csrfTokenEl.value;
    const orderId = orderIdEl.value;

    const orderItemsList = document.getElementById('order-items-list');
    const noItemsMessage = document.getElementById('no-items-message');
    const orderTotalElement = document.getElementById('order-total');
    const paymentButton = document.getElementById('open-payment-modal-btn');
    const searchInput = document.getElementById('product-search-input');
    const categoryButtons = document.querySelectorAll('.category-btn');
    const productLists = document.querySelectorAll('.product-list');

    // --- UTILIDADES VISUALES ---
    function formatCurrency(amount) {
        return '$' + parseFloat(amount).toFixed(2);
    }

    // --- ACTUALIZAR INTERFAZ (UI) ---
    function updateOrderUI(data) {
        if (!orderItemsList || !orderTotalElement) return;

        orderItemsList.innerHTML = '';
        
        // [Yo]: Aquí cambio el HTML generado para incluir botones de + y -
        if (data.items && data.items.length > 0) {
            data.items.forEach(item => {
                const itemHTML = `
                    <div id="item-row-${item.id}" class="py-3 flex justify-between items-center border-b border-gray-100 dark:border-gray-700 last:border-0 animate-fade-in">
                        <div class="flex-1 min-w-0 mr-2">
                            <p class="font-medium text-gray-800 dark:text-gray-100 truncate text-sm sm:text-base" title="${item.name}">${item.name}</p>
                            <p class="text-xs text-gray-500 dark:text-gray-400">
                                Unitario: ${formatCurrency(item.unit_price)}
                            </p>
                        </div>
                        
                        <div class="flex items-center gap-3">
                            <div class="flex items-center bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
                                <button onclick="window.updateQuantity(${item.id}, -1)" class="w-7 h-7 flex items-center justify-center text-gray-600 dark:text-gray-300 hover:bg-white dark:hover:bg-gray-600 rounded shadow-sm transition-colors active:scale-95">
                                    <i class="fa-solid fa-minus text-xs"></i>
                                </button>
                                <span class="w-8 text-center font-semibold text-gray-800 dark:text-gray-100 text-sm">${item.quantity}</span>
                                <button onclick="window.updateQuantity(${item.id}, 1)" class="w-7 h-7 flex items-center justify-center text-blue-600 dark:text-blue-400 hover:bg-white dark:hover:bg-gray-600 rounded shadow-sm transition-colors active:scale-95">
                                    <i class="fa-solid fa-plus text-xs"></i>
                                </button>
                            </div>
                            
                            <div class="text-right min-w-[70px]">
                                <p class="font-bold text-gray-800 dark:text-gray-100 text-sm sm:text-base">${formatCurrency(item.subtotal)}</p>
                            </div>
                        </div>
                    </div>`;
                orderItemsList.insertAdjacentHTML('beforeend', itemHTML);
            });
        }

        orderTotalElement.textContent = formatCurrency(data.order_total);

        const hasItems = data.items && data.items.length > 0;
        if (noItemsMessage) noItemsMessage.style.display = hasItems ? 'none' : 'block';

        if (paymentButton) {
            paymentButton.disabled = !hasItems;
            paymentButton.classList.toggle('opacity-50', !hasItems);
            paymentButton.classList.toggle('cursor-not-allowed', !hasItems);
        }
    }
    
    // --- COMUNICACIÓN CON EL SERVIDOR ---

    // Añadir ítem (Crear)
    window.addItem = function(productId, buttonElement) {
        if (buttonElement) {
            buttonElement.disabled = true;
            buttonElement.classList.add('opacity-75');
        }
        
        const formData = new FormData();
        formData.append('product_id', productId);
        formData.append('quantity', 1);
        formData.append('csrf_token', csrfToken);

        fetch(`/mozo/order/${orderId}/add_item`, { method: 'POST', body: formData })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    updateOrderUI(data);
                    showToast(data.message, 'success');
                    // Feedback visual rápido
                    if (navigator.vibrate) navigator.vibrate(50); 
                } else {
                    showToast(data.message, 'danger');
                }
            })
            .catch(err => {
                console.error(err);
                showToast('Error de conexión.', 'danger');
            })
            .finally(() => {
                if (buttonElement) {
                    buttonElement.disabled = false;
                    buttonElement.classList.remove('opacity-75');
                }
            });
    };

    // Actualizar Cantidad (Editar/Eliminar)
    // [Yo]: Esta función llama al nuevo endpoint que creé en mozo.py
    window.updateQuantity = function(itemId, change) {
        const formData = new FormData();
        formData.append('change', change);
        formData.append('csrf_token', csrfToken);

        // Optimistic UI update (opcional, pero lo haremos simple primero)
        fetch(`/mozo/order_item/${itemId}/update_quantity`, { method: 'POST', body: formData })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    updateOrderUI(data);
                } else {
                    showToast(data.message, 'warning');
                }
            })
            .catch(err => {
                console.error(err);
                showToast('Error al actualizar.', 'danger');
            });
    };

    // Eliminar totalmente (ahora es opcional, ya que el "-" lo hace si llega a 0)
    window.removeItem = function(itemId, itemName) {
        if (!confirm(`¿Quitar "${itemName}"?`)) return;
        const formData = new FormData();
        formData.append('csrf_token', csrfToken);

        fetch(`/mozo/order_item/${itemId}/remove`, { method: 'POST', body: formData })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    updateOrderUI(data);
                    showToast('Eliminado.', 'success');
                }
            });
    };

    // --- BÚSQUEDA Y FILTROS ---
    // [Yo]: Mantengo la lógica de búsqueda que ya funcionaba bien
    categoryButtons.forEach(button => {
        button.addEventListener('click', () => {
            const category = button.dataset.category;
            productLists.forEach(list => list.classList.add('hidden'));
            categoryButtons.forEach(btn => {
                btn.classList.remove('bg-blue-600', 'text-white', 'shadow-md');
                btn.classList.add('bg-gray-200', 'dark:bg-gray-700', 'text-gray-800', 'dark:text-gray-200');
            });
            const targetList = document.getElementById(`products-${category}`);
            if(targetList) targetList.classList.remove('hidden');
            
            button.classList.add('bg-blue-600', 'text-white', 'shadow-md');
            button.classList.remove('bg-gray-200', 'dark:bg-gray-700', 'text-gray-800', 'dark:text-gray-200');
        });
    });

    if (categoryButtons.length > 0) categoryButtons[0].click();

    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', function(e) {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                const searchTerm = e.target.value.toLowerCase().trim();
                if (searchTerm === '') {
                    const activeButton = document.querySelector('.category-btn.bg-blue-600');
                    if (activeButton) activeButton.click();
                    return;
                }
                productLists.forEach(list => list.classList.remove('hidden'));
                document.querySelectorAll('.product-list button').forEach(btn => {
                    const name = btn.querySelector('span.font-semibold').textContent.toLowerCase();
                    btn.style.display = name.includes(searchTerm) ? 'block' : 'none';
                });
            }, 300);
        });
        // Limpiar con ESC
        searchInput.addEventListener('keydown', e => {
            if (e.key === 'Escape') {
                e.target.value = '';
                e.target.dispatchEvent(new Event('input'));
                e.target.blur();
            }
        });
    }

    // --- MODALES ---
    function setupModal(modalId, openBtnId, closeBtnId) {
        const modal = document.getElementById(modalId);
        const openBtn = document.getElementById(openBtnId);
        const closeBtn = document.getElementById(closeBtnId);
        if (modal && openBtn && closeBtn) {
            openBtn.addEventListener('click', () => modal.classList.remove('hidden'));
            closeBtn.addEventListener('click', () => modal.classList.add('hidden'));
            modal.addEventListener('click', e => {
                if (e.target === modal) modal.classList.add('hidden');
            });
        }
    }
    setupModal('payment-modal', 'open-payment-modal-btn', 'close-payment-modal-btn');
    setupModal('half-pizza-modal', 'open-half-pizza-modal-btn', 'close-half-pizza-modal-btn');

    // Pizza Mitad/Mitad
    const halfPizzaForm = document.getElementById('half-pizza-form');
    if (halfPizzaForm) {
        halfPizzaForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const pizza1 = this.querySelector('[name="pizza1_id"]').value;
            const pizza2 = this.querySelector('[name="pizza2_id"]').value;
            
            if (!pizza1 || !pizza2) {
                showToast('Elige dos mitades.', 'warning');
                return;
            }
            
            const formData = new FormData(this);
            formData.append('csrf_token', csrfToken);

            fetch(`/mozo/order/${orderId}/add_half_pizza`, { method: 'POST', body: formData })
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        updateOrderUI(data);
                        document.getElementById('half-pizza-modal').classList.add('hidden');
                        this.reset();
                        showToast('Pizza añadida.', 'success');
                    } else {
                        showToast(data.message, 'danger');
                    }
                });
        });
    }
});