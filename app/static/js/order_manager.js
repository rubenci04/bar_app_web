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
        .then(handleApiResponse);
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

    // --- Funciones para actualizar la Interfaz de Usuario (DOM) ---

    // Función central para manejar las respuestas del servidor
    function handleApiResponse(data) {
        if (data.success) {
            showToast(data.message, 'success');
            if (data.item) {
                updateOrInsertItemRow(data.item);
            }
            if (data.removed_item_id) {
                removeItemRow(data.removed_item_id);
            }
            if (typeof data.order_total !== 'undefined') {
                updateOrderUI(data.order_total);
            }
        } else {
            showToast(data.message || 'Ocurrió un error.', 'danger');
        }
    }

    function updateOrderUI(newTotal) {
        // Actualiza el total
        if (orderTotalElement) {
            orderTotalElement.textContent = `$${parseFloat(newTotal).toFixed(2)}`;
        }

        // Habilita o deshabilita el botón de pago
        if (paymentButton) {
            const hasItems = newTotal > 0;
            paymentButton.disabled = !hasItems;
            paymentButton.classList.toggle('opacity-50', !hasItems);
            paymentButton.classList.toggle('cursor-not-allowed', !hasItems);
        }

        // Muestra u oculta el mensaje de "No hay ítems"
        if (noItemsMessage) {
            const hasItems = orderItemsList.children.length > 0;
            noItemsMessage.style.display = hasItems ? 'none' : 'block';
        }
    }

    function createItemRowHTML(item) {
        const escapedName = item.name.replace(/'/g, "\\'");
        return `
            <div id="item-row-${item.id}" class="py-3 flex justify-between items-center">
                <div>
                    <p class="font-medium text-gray-800 dark:text-gray-100">${item.name}</p>
                    <p class="text-sm text-gray-500 dark:text-gray-400">
                        <span class="quantity-display">${item.quantity} x</span> $${parseFloat(item.unit_price).toFixed(2)}
                    </p>
                </div>
                <div class="text-right">
                    <p class="font-semibold text-gray-800 dark:text-gray-100 subtotal-display">$${parseFloat(item.subtotal).toFixed(2)}</p>
                    <button onclick="window.removeItem(${item.id}, '${escapedName}')" class="text-xs text-red-600 hover:text-red-500 dark:text-red-500 dark:hover:text-red-400 transition-colors">Quitar</button>
                </div>
            </div>`;
    }

    function updateOrInsertItemRow(item) {
        if (noItemsMessage) noItemsMessage.style.display = 'none';

        let existingItemRow = document.getElementById(`item-row-${item.id}`);
        // Solo actualiza la fila si NO es una pizza mitad/mitad (esas son siempre ítems únicos)
        if (existingItemRow && !item.name.includes('Mitad:')) {
            existingItemRow.querySelector('.quantity-display').textContent = `${item.quantity} x`;
            existingItemRow.querySelector('.subtotal-display').textContent = `$${parseFloat(item.subtotal).toFixed(2)}`;
        } else if (!existingItemRow) {
            orderItemsList.insertAdjacentHTML('beforeend', createItemRowHTML(item));
        }
    }

    function removeItemRow(itemId) {
        const itemRow = document.getElementById(`item-row-${itemId}`);
        if (itemRow) {
            itemRow.remove();
        }
    }


    // --- Lógica de la interfaz de selección de productos (Categorías y Búsqueda) ---
    const categoryButtons = document.querySelectorAll('.category-btn');
    const productLists = document.querySelectorAll('.product-list');
    const searchInput = document.getElementById('product-search-input');

    if (categoryButtons.length > 0) {
        categoryButtons.forEach(button => {
            button.addEventListener('click', () => {
                const category = button.dataset.category;

                // Resetea el buscador
                if (searchInput) {
                    searchInput.value = '';
                    searchInput.dispatchEvent(new Event('input'));
                }

                // Actualiza el estilo de los botones
                categoryButtons.forEach(btn => btn.classList.remove('bg-blue-600', 'text-white'));
                button.classList.add('bg-blue-600', 'text-white');

                // Muestra la lista de productos correcta
                productLists.forEach(list => {
                    list.classList.toggle('hidden', list.id !== `products-${category}`);
                });
            });
        });
        // Activa la primera categoría por defecto
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