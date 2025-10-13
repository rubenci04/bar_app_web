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

    // --- FUNCIONES PARA ACTUALIZAR LA INTERFAZ ---

    function updateOrderUI(data) {
        if (!orderItemsList || !orderTotalElement) return;

        orderItemsList.innerHTML = '';
        
        if (data.items && data.items.length > 0) {
            data.items.forEach(item => {
                // Se añade la clase 'fade-in' para una aparición suave
                const itemHTML = `
                    <div id="item-row-${item.id}" class="py-3 flex justify-between items-center fade-in">
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

        orderTotalElement.textContent = `$${parseFloat(data.order_total).toFixed(2)}`;

        const hasItems = data.items && data.items.length > 0;
        if (noItemsMessage) {
            noItemsMessage.style.display = hasItems ? 'none' : 'block';
        }

        if (paymentButton) {
            paymentButton.disabled = !hasItems;
            paymentButton.classList.toggle('opacity-50', !hasItems);
            paymentButton.classList.toggle('cursor-not-allowed', !hasItems);
        }
    }
    
    // --- LÓGICA DE PETICIONES AL SERVIDOR ---

    window.addItem = function(productId, buttonElement) {
        // ✅ MEJORA: Mostramos un feedback visual de carga en el botón del producto
        const originalText = buttonElement.innerHTML;
        buttonElement.innerHTML = '<span class="spinner"></span>';
        buttonElement.disabled = true;
        
        const formData = new FormData();
        formData.append('product_id', productId);
        formData.append('quantity', 1);
        formData.append('csrf_token', csrfToken);

        fetch(`/mozo/order/${orderId}/add_item`, { method: 'POST', body: formData })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateOrderUI(data);
                    showToast(data.message, 'success');
                    
                    // ✅ MEJORA: Efecto visual de éxito en el botón
                    buttonElement.innerHTML = '<i class="fas fa-check text-green-500"></i>';
                } else {
                    showToast(data.message, 'danger');
                    buttonElement.innerHTML = '<i class="fas fa-times text-red-500"></i>';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('Error de red al añadir el producto.', 'danger');
                buttonElement.innerHTML = '<i class="fas fa-exclamation-triangle text-red-500"></i>';
            })
            .finally(() => {
                // ✅ MEJORA: Restauramos el botón a su estado original después de un momento
                setTimeout(() => {
                    buttonElement.innerHTML = originalText;
                    buttonElement.disabled = false;
                }, 700);
            });
    };

    window.removeItem = function(itemId, itemName) {
        if (!confirm(`¿Seguro que quieres quitar "${itemName}" del pedido?`)) return;

        const itemRow = document.getElementById(`item-row-${itemId}`);
        if (itemRow) {
            itemRow.style.transition = 'opacity 0.3s, transform 0.3s';
            itemRow.style.opacity = '0.5';
            itemRow.style.transform = 'translateX(20px)';
        }
        
        const formData = new FormData();
        formData.append('csrf_token', csrfToken);

        fetch(`/mozo/order_item/${itemId}/remove`, { method: 'POST', body: formData })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // La actualización de la UI eliminará la fila, no necesitamos hacerlo manualmente
                    updateOrderUI(data);
                    showToast(data.message, 'success');
                } else {
                    showToast(data.message, 'danger');
                    if (itemRow) { // Si falla, restauramos la fila a su estado original
                        itemRow.style.opacity = '1';
                        itemRow.style.transform = 'translateX(0)';
                    }
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('Error de red al eliminar el producto.', 'danger');
                if (itemRow) {
                    itemRow.style.opacity = '1';
                    itemRow.style.transform = 'translateX(0)';
                }
            });
    };

    // --- MANEJO DE PIZZA MITAD/MITAD ---
    const halfPizzaForm = document.getElementById('half-pizza-form');
    if (halfPizzaForm) {
        halfPizzaForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const submitBtn = this.querySelector('button[type="submit"]');
            
            const pizza1 = this.querySelector('[name="pizza1_id"]').value;
            const pizza2 = this.querySelector('[name="pizza2_id"]').value;
            
            if (!pizza1 || !pizza2) {
                showToast('Debes seleccionar dos sabores de pizza.', 'warning');
                return;
            }
            
            if (pizza1 === pizza2) {
                showToast('Debes seleccionar dos sabores diferentes.', 'warning');
                return;
            }
            
            // ✅ MEJORA: Usamos la función global setButtonLoading que ya existe en tu app
            if (window.setButtonLoading) {
                setButtonLoading(submitBtn, true);
            }
            
            const formData = new FormData(this);
            formData.append('csrf_token', csrfToken);

            fetch(`/mozo/order/${orderId}/add_half_pizza`, { method: 'POST', body: formData })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        updateOrderUI(data);
                        document.getElementById('half-pizza-modal').classList.add('hidden');
                        this.reset();
                        showToast(data.message, 'success');
                    } else {
                        showToast(data.message, 'danger');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showToast('Error de red al añadir la pizza.', 'danger');
                })
                .finally(() => {
                    if (window.setButtonLoading) {
                        setButtonLoading(submitBtn, false);
                    }
                });
        });
    }

    // --- FILTRO Y BÚSQUEDA DE PRODUCTOS (EN TIEMPO REAL) ---
    categoryButtons.forEach(button => {
        button.addEventListener('click', () => {
            const category = button.dataset.category;
            
            productLists.forEach(list => list.classList.add('hidden'));
            
            categoryButtons.forEach(btn => {
                btn.classList.remove('bg-blue-600', 'text-white', 'dark:bg-blue-500');
                btn.classList.add('bg-gray-200', 'dark:bg-gray-700', 'text-gray-800', 'dark:text-gray-200');
            });

            document.getElementById(`products-${category}`).classList.remove('hidden');
            button.classList.add('bg-blue-600', 'text-white', 'dark:bg-blue-500');
            button.classList.remove('bg-gray-200', 'dark:bg-gray-700', 'text-gray-800', 'dark:text-gray-200');
        });
    });

    if (categoryButtons.length > 0) {
        categoryButtons[0].click();
    }

    if (searchInput) {
        let searchTimeout;
        
        searchInput.addEventListener('input', function(e) {
            clearTimeout(searchTimeout);
            
            searchTimeout = setTimeout(() => {
                const searchTerm = e.target.value.toLowerCase().trim();

                if (searchTerm === '') {
                    const activeButton = document.querySelector('.category-btn.bg-blue-600');
                    if (activeButton) {
                        activeButton.click();
                    } else if (categoryButtons.length > 0) {
                        categoryButtons[0].click();
                    }
                    document.querySelectorAll('.product-list button').forEach(productButton => {
                        productButton.style.display = 'block';
                    });
                    return;
                }

                productLists.forEach(list => list.classList.remove('hidden'));

                let foundCount = 0;
                document.querySelectorAll('.product-list button').forEach(productButton => {
                    const productName = productButton.querySelector('span.font-semibold').textContent.toLowerCase();
                    if (productName.includes(searchTerm)) {
                        productButton.style.display = 'block';
                        productButton.closest('.product-list').classList.remove('hidden');
                        foundCount++;
                    } else {
                        productButton.style.display = 'none';
                    }
                });
                
                if (foundCount === 0) {
                    showToast(`No se encontraron productos con "${searchTerm}"`, 'info');
                }
            }, 250);
        });
        
        searchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                this.value = '';
                this.dispatchEvent(new Event('input'));
                this.blur();
            }
        });
    }
});