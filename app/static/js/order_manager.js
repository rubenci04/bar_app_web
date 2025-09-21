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
    // Función para actualizar la vista del pedido
    function updateOrderView(items, total) {
        if (!orderItemsList) return;

        // Limpiar la lista actual
        orderItemsList.innerHTML = '';
        
        if (items && items.length > 0) {
            // Ocultar el mensaje de "no hay items"
            if (noItemsMessage) noItemsMessage.classList.add('hidden');
            
            // Agregar cada item a la lista
            items.forEach(item => {
                const itemElement = document.createElement('div');
                itemElement.className = 'flex justify-between items-center p-2 border-b';
                itemElement.innerHTML = `
                    <div class="flex-grow">
                        <span class="font-medium">${item.name}</span>
                        <div class="text-sm">
                            ${item.quantity}x $${item.unit_price.toLocaleString()} = $${item.subtotal.toLocaleString()}
                        </div>
                    </div>
                    <button onclick="removeItem(${item.id})" class="text-red-600 hover:text-red-800">
                        <i class="fas fa-times"></i>
                    </button>
                `;
                orderItemsList.appendChild(itemElement);
            });
        } else {
            // Mostrar el mensaje de "no hay items"
            if (noItemsMessage) noItemsMessage.classList.remove('hidden');
        }

        // Actualizar el total
        if (orderTotalElement) {
            orderTotalElement.textContent = total.toLocaleString();
        }

        // Habilitar/deshabilitar el botón de pago según si hay items o no
        if (paymentButton) {
            if (items && items.length > 0) {
                paymentButton.disabled = false;
                paymentButton.classList.remove('opacity-50', 'cursor-not-allowed');
            } else {
                paymentButton.disabled = true;
                paymentButton.classList.add('opacity-50', 'cursor-not-allowed');
            }
        }
    }

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
                updateOrderView(data.items, data.order_total);
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

        fetch(`/mozo/order/${orderId}/add_item`, { 
            method: 'POST', 
            body: formData 
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                // Usar la función updateOrderView que maneja toda la actualización
                updateOrderView(data.items, data.order_total);
                showToast(data.message, 'success');
            } else {
                showToast(data.message, 'danger');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('Error al agregar el producto. Por favor, intente de nuevo.', 'danger');
        });
    };

    window.removeItem = function(itemId) {
        const formData = new FormData();
        formData.append('csrf_token', csrfToken);
        
        fetch(`/mozo/order_item/${itemId}/remove`, { 
            method: 'POST', 
            body: formData 
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                // Usar la misma función updateOrderView para mantener la consistencia
                const items = data.items || [];
                updateOrderView(items, data.order_total);
                showToast(data.message, 'success');
            } else {
                showToast(data.message, 'danger');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('Error al eliminar el producto. Por favor, intente de nuevo.', 'danger');
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