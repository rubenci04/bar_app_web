// Reemplazo completo para app/static/js/order_manager.js

document.addEventListener('DOMContentLoaded', function() {
    // Primero, me aseguro de estar en una página de pedido obteniendo los datos necesarios.
    const csrfTokenEl = document.getElementById('csrf_token_js');
    const orderIdEl = document.getElementById('order_id_js');

    if (!csrfTokenEl || !orderIdEl) {
        // Si no estoy en una página de pedido, no hago nada.
        return;
    }

    const csrfToken = csrfTokenEl.value;
    const orderId = orderIdEl.value;

    // Almaceno las referencias a los elementos del DOM que voy a manipular.
    const orderItemsList = document.getElementById('order-items-list');
    const noItemsMessage = document.getElementById('no-items-message');
    const orderTotalElement = document.getElementById('order-total');
    const paymentButton = document.getElementById('open-payment-modal-btn');
    const searchInput = document.getElementById('product-search-input');
    const categoryButtons = document.querySelectorAll('.category-btn');
    const productLists = document.querySelectorAll('.product-list');

    // --- MANEJO DE MODALES ---
    // Esta función la uso para abrir y cerrar los modales de pago y de pizza mitad/mitad.
    function setupModal(modalId, openBtnId, closeBtnId) {
        const modal = document.getElementById(modalId);
        const openBtn = document.getElementById(openBtnId);
        const closeBtn = document.getElementById(closeBtnId);
        if (modal && openBtn && closeBtn) {
            openBtn.addEventListener('click', () => modal.classList.remove('hidden'));
            closeBtn.addEventListener('click', () => modal.classList.add('hidden'));
            // Cierro el modal si se hace clic fuera de él.
            modal.addEventListener('click', e => {
                if (e.target === modal) modal.classList.add('hidden');
            });
        }
    }
    setupModal('payment-modal', 'open-payment-modal-btn', 'close-payment-modal-btn');
    setupModal('half-pizza-modal', 'open-half-pizza-modal-btn', 'close-half-pizza-modal-btn');

    // --- FUNCIONES PARA ACTUALIZAR LA INTERFAZ ---

    function updateOrderUI(data) {
        // Esta función centraliza todas las actualizaciones visuales del pedido.
        if (!orderItemsList || !orderTotalElement) return;

        // Limpio la lista actual.
        orderItemsList.innerHTML = '';
        
        // Vuelvo a dibujar todos los ítems con los datos del servidor.
        if (data.items && data.items.length > 0) {
            data.items.forEach(item => {
                const itemHTML = `
                    <div id="item-row-${item.id}" class="py-3 flex justify-between items-center">
                        <div>
                            <p class="font-medium text-gray-800 dark:text-gray-100">${item.name}</p>
                            <p class="text-sm text-gray-500 dark:text-gray-400">
                                <span class="quantity-display">${item.quantity} x</span> $${item.unit_price.toFixed(2)}
                            </p>
                        </div>
                        <div class="text-right">
                            <p class="font-semibold text-gray-800 dark:text-gray-100 subtotal-display">$${item.subtotal.toFixed(2)}</p>
                            <button onclick="window.removeItem(${item.id}, '${item.name.replace(/'/g, "\\'")}')" class="text-xs text-red-600 hover:text-red-500 dark:text-red-500 dark:hover:text-red-400 transition-colors">Quitar</button>
                        </div>
                    </div>`;
                orderItemsList.insertAdjacentHTML('beforeend', itemHTML);
            });
        }

        // Actualizo el total.
        orderTotalElement.textContent = `$${parseFloat(data.order_total).toFixed(2)}`;

        // Muestro u oculto el mensaje "No hay ítems".
        const hasItems = data.items && data.items.length > 0;
        if (noItemsMessage) {
            noItemsMessage.style.display = hasItems ? 'none' : 'block';
        }

        // Habilito o deshabilito el botón de cobrar.
        if (paymentButton) {
            paymentButton.disabled = !hasItems;
            paymentButton.classList.toggle('opacity-50', !hasItems);
            paymentButton.classList.toggle('cursor-not-allowed', !hasItems);
        }
    }
    
    // --- LÓGICA DE PETICIONES AL SERVIDOR ---

    // Hago que las funciones addItem y removeItem estén disponibles globalmente en la ventana.
    window.addItem = function(productId) {
        const formData = new FormData();
        formData.append('product_id', productId);
        formData.append('quantity', 1);
        formData.append('csrf_token', csrfToken);

        fetch(`/mozo/order/${orderId}/add_item`, { method: 'POST', body: formData })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Si el servidor responde con éxito, actualizo la interfaz y muestro una notificación.
                    updateOrderUI(data);
                    showToast(data.message, 'success');
                } else {
                    showToast(data.message, 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('Error de red al añadir el producto.', 'danger');
            });
    };

    window.removeItem = function(itemId, itemName) {
        if (!confirm(`¿Seguro que quieres quitar "${itemName}" del pedido?`)) return;

        const formData = new FormData();
        formData.append('csrf_token', csrfToken);

        fetch(`/mozo/order_item/${itemId}/remove`, { method: 'POST', body: formData })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Si se elimina con éxito, actualizo la interfaz completa con los nuevos datos.
                    // Esto es más simple y robusto que solo quitar un elemento del DOM.
                     const itemRow = document.getElementById(`item-row-${itemId}`);
                    if (itemRow) {
                        itemRow.remove();
                    }
                    orderTotalElement.textContent = `$${parseFloat(data.order_total).toFixed(2)}`;
                    updateOrderUI(data);
                    showToast(data.message, 'success');
                } else {
                    showToast(data.message, 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('Error de red al eliminar el producto.', 'danger');
            });
    };

    // --- MANEJO DE PIZZA MITAD/MITAD ---
    const halfPizzaForm = document.getElementById('half-pizza-form');
    if (halfPizzaForm) {
        halfPizzaForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            formData.append('csrf_token', csrfToken);

            fetch(`/mozo/order/${orderId}/add_half_pizza`, { method: 'POST', body: formData })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        updateOrderUI(data); // Reutilizo mi función de actualización.
                        document.getElementById('half-pizza-modal').classList.add('hidden');
                        this.reset();
                        showToast(data.message, 'success');
                    } else {
                        showToast(data.message, 'danger');
                    }
                });
        });
    }

    // --- FILTRO Y BÚSQUEDA DE PRODUCTOS (EN TIEMPO REAL) ---
    
    // Lógica para los botones de categoría.
    categoryButtons.forEach(button => {
        button.addEventListener('click', () => {
            const category = button.dataset.category;
            
            productLists.forEach(list => list.classList.add('hidden'));
            
            categoryButtons.forEach(btn => {
                btn.classList.remove('bg-blue-600', 'text-white');
                btn.classList.add('bg-gray-200', 'dark:bg-gray-700', 'text-gray-800', 'dark:text-gray-200');
            });

            document.getElementById(`products-${category}`).classList.remove('hidden');
            button.classList.add('bg-blue-600', 'text-white');
            button.classList.remove('bg-gray-200', 'dark:bg-gray-700', 'text-gray-800', 'dark:text-gray-200');
        });
    });

    // Activo la primera categoría por defecto.
    if (categoryButtons.length > 0) {
        categoryButtons[0].click();
    }

    // ¡Aquí está la magia de la búsqueda en tiempo real!
    if (searchInput) {
        searchInput.addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase().trim();

            // Muestro todas las listas de productos para buscar en todas.
            productLists.forEach(list => list.classList.remove('hidden'));

            // Recorro cada producto y lo muestro u oculto según el término de búsqueda.
            document.querySelectorAll('.product-list button').forEach(productButton => {
                const productName = productButton.querySelector('span.font-semibold').textContent.toLowerCase();
                if (productName.includes(searchTerm)) {
                    productButton.style.display = 'block';
                } else {
                    productButton.style.display = 'none';
                }
            });
            
            // Si el campo de búsqueda está vacío, vuelvo a activar el filtro por categorías.
            if (searchTerm === '') {
                const activeButton = document.querySelector('.category-btn.bg-blue-600');
                if (activeButton) {
                    activeButton.click();
                } else {
                    categoryButtons[0].click();
                }
            }
        });
    }
});