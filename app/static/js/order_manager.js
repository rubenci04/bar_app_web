document.addEventListener('DOMContentLoaded', function() {
    const csrfTokenEl = document.getElementById('csrf_token_js');
    const orderIdEl = document.getElementById('order_id_js');

    // Si no hay elementos de orden en la página, no ejecuta nada.
    if (!csrfTokenEl || !orderIdEl) {
        return;
    }

    const csrfToken = csrfTokenEl.value;
    const orderId = orderIdEl.value;
    const orderItemsList = document.getElementById('order-items-list');
    const noItemsMessage = document.getElementById('no-items-message');
    const orderTotalElement = document.getElementById('order-total');
    const paymentButton = document.getElementById('open-payment-modal-btn');

    // --- Gestión de Modales (Pago y Pizza Mitad/Mitad) ---
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

    // --- Funciones para interactuar con la API del Backend ---

    // Función para añadir un producto normal
    window.addItem = function(productId) {
        const formData = new FormData();
        formData.append('product_id', productId);
        formData.append('quantity', 1);
        formData.append('csrf_token', csrfToken);

        fetch(`/mozo/order/${orderId}/add_item`, {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateOrderView(data.order_data);
                showToast(data.message, 'success');
            } else {
                showToast(data.message, 'danger');
            }
        })
        .catch(error => {
            console.error('Error al añadir ítem:', error);
            showToast('Error de red al añadir el producto.', 'danger');
        });
    };

    // Función para quitar un ítem del pedido
    window.removeItem = function(itemId, itemName) {
        if (!confirm(`¿Seguro que quieres quitar "${itemName}" del pedido?`)) return;

        const formData = new FormData();
        formData.append('csrf_token', csrfToken);

        fetch(`/mozo/order_item/${itemId}/remove`, {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(handleApiResponse);
    };

    // Listener para el formulario de Pizza Mitad/Mitad
    const halfPizzaForm = document.getElementById('half-pizza-form');
    if (halfPizzaForm) {
        halfPizzaForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            formData.append('csrf_token', csrfToken);

            fetch(`/mozo/order/${orderId}/add_half_pizza`, {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const halfPizzaModal = document.getElementById('half-pizza-modal');
                    if (halfPizzaModal) halfPizzaModal.classList.add('hidden');
                    this.reset();
                }
                handleApiResponse(data);
            });
        });
    }
    
    window.addItem = function(productId) {
        const formData = new FormData();
        formData.append('csrf_token', csrfToken);
        formData.append('product_id', productId);
        formData.append('quantity', 1);

        fetch(`/mozo/order/${orderId}/add_item`, { method: 'POST', body: formData })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                addItemToDOM(data.item);
                updateOrderTotal(data.order_total);
                showJsMessage(data.message, 'success');
            } else {
                showJsMessage(data.message, 'danger');
            }
        });
    };

    window.removeItem = function(itemId, itemName, productId) {
        if (!confirm(`¿Seguro que quieres quitar "${itemName}" del pedido?`)) return;
        const formData = new FormData();
        formData.append('csrf_token', csrfToken);
        
        fetch(`/mozo/order_item/${itemId}/remove`, { method: 'POST', body: formData })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                const itemRow = document.getElementById(`item-row-${itemId}`);
                if (itemRow) itemRow.remove();
                updateOrderTotal(data.order_total);
                if (orderItemsList && orderItemsList.children.length === 0) {
                     orderItemsList.innerHTML = '<p id="no-items-message" class="text-gray-400 dark:text-gray-500 py-4 text-center">No hay ítems en este pedido.</p>';
                }
            } else {
                showJsMessage(data.message, 'danger');
            }
        });
    };

    const categoryButtons = document.querySelectorAll('.category-btn');
    const productLists = document.querySelectorAll('.product-list');

    categoryButtons.forEach(button => {
        button.addEventListener('click', () => {
            const category = button.dataset.category;
            
            productLists.forEach(list => list.classList.add('hidden'));
            
            categoryButtons.forEach(btn => {
                btn.classList.remove('bg-blue-600', 'text-white', 'font-semibold');
                btn.classList.add('bg-gray-200', 'dark:bg-gray-700', 'text-gray-800', 'dark:text-gray-200');
            });

            document.getElementById(`products-${category}`).classList.remove('hidden');
            button.classList.add('bg-blue-600', 'text-white', 'font-semibold');
            button.classList.remove('bg-gray-200', 'dark:bg-gray-700', 'text-gray-800', 'dark:text-gray-200');
        });
    });

    if (categoryButtons.length > 0) {
        categoryButtons[0].click();
    }

    if (searchInput) {
        searchInput.addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase().trim();

            productLists.forEach(list => {
                const products = list.querySelectorAll('button');
                products.forEach(product => {
                    const productName = product.querySelector('span.font-semibold').textContent.toLowerCase();
                    product.style.display = productName.includes(searchTerm) ? 'block' : 'none';
                });
            });
        });
    }
});