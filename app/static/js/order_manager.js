document.addEventListener('DOMContentLoaded', function() {
    const csrfTokenEl = document.getElementById('csrf_token_js');
    const orderIdEl = document.getElementById('order_id_js');

    if (!csrfTokenEl || !orderIdEl) {
        return;
    }

    const csrfToken = csrfTokenEl.value;
    const orderId = orderIdEl.value;
    const orderItemsList = document.getElementById('order-items-list');
    const noItemsMessage = document.getElementById('no-items-message');
    const orderTotalElement = document.getElementById('order-total');
    const paymentButton = document.getElementById('open-payment-modal-btn');
    const searchInput = document.getElementById('product-search-input');

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

    function createItemElement(item) {
        const itemElement = document.createElement('div');
        itemElement.className = 'flex justify-between items-center p-2 border-b';
        itemElement.setAttribute('data-item-id', item.id);
        itemElement.setAttribute('data-product-id', item.product_id);

        itemElement.innerHTML = `
            <div class="flex-grow">
                <span class="font-medium">${item.name}</span>
                <div class="text-sm text-gray-600">
                    <span class="item-quantity">${item.quantity}</span>x ${item.unit_price.toLocaleString()} = <span class="font-bold">${item.subtotal.toLocaleString()}</span>
                </div>
            </div>
            <button onclick="removeItem(${item.id}, '${item.name}')" class="text-red-500 hover:text-red-700 ml-4 p-1">
                <i class="fas fa-times"></i>
            </button>
        `;
        return itemElement;
    }

    function renderOrUpdateItem(item) {
        if (!orderItemsList) return;
        let existingItemEl = orderItemsList.querySelector(`[data-item-id="${item.id}"]`);

        if (existingItemEl) {
            existingItemEl.querySelector('.item-quantity').textContent = item.quantity;
            existingItemEl.querySelector('.font-bold').textContent = `${item.subtotal.toLocaleString()}`;
        } else {
            const newItemEl = createItemElement(item);
            orderItemsList.appendChild(newItemEl);
        }
    }

    function updateOrderTotal(total) {
        if (orderTotalElement) {
            orderTotalElement.textContent = total.toLocaleString();
        }
        const hasItems = total > 0;
        if (noItemsMessage) {
            noItemsMessage.classList.toggle('hidden', hasItems);
        }
        if (paymentButton) {
            paymentButton.disabled = !hasItems;
            paymentButton.classList.toggle('opacity-50', !hasItems);
            paymentButton.classList.toggle('cursor-not-allowed', !hasItems);
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
                renderOrUpdateItem(data.item);
                updateOrderTotal(data.order_total);
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

    window.removeItem = function(itemId, itemName) {
        if (!confirm(`¿Seguro que quieres quitar "${itemName}" del pedido?`)) return;

        const formData = new FormData();
        formData.append('csrf_token', csrfToken);

        fetch(`/mozo/order_item/${itemId}/remove`, {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const itemToRemove = orderItemsList.querySelector(`[data-item-id="${data.removed_item_id}"]`);
                if (itemToRemove) {
                    itemToRemove.remove();
                }
                updateOrderTotal(data.order_total);
                showToast(data.message, 'success');
            } else {
                showToast(data.message, 'danger');
            }
        })
        .catch(error => {
            console.error('Error al eliminar ítem:', error);
            showToast('Error de red al eliminar el producto.', 'danger');
        });
    };

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
                    renderOrUpdateItem(data.item);
                    updateOrderTotal(data.order_total);
                    const halfPizzaModal = document.getElementById('half-pizza-modal');
                    if (halfPizzaModal) halfPizzaModal.classList.add('hidden');
                    this.reset();
                    showToast(data.message, 'success');
                } else {
                    showToast(data.message, 'danger');
                }
            });
        });
    }

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