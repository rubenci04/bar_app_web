// Archivo: app/static/js/order_manager.js
document.addEventListener('DOMContentLoaded', function () {
    const csrfTokenEl = document.getElementById('csrf_token_js');
    if (!csrfTokenEl) return;

    const csrfToken = csrfTokenEl.value;
    const orderId = document.getElementById('order_id_js').value;
    const orderItemsList = document.getElementById('order-items-list');
    const orderTotalEl = document.getElementById('order-total');

    function setupModal(modalId, openBtnId, closeBtnId) {
        const modal = document.getElementById(modalId);
        const openBtn = document.getElementById(openBtnId);
        const closeBtn = document.getElementById(closeBtnId);
        if (modal && openBtn && closeBtn) {
            openBtn.addEventListener('click', () => modal.classList.remove('hidden'));
            closeBtn.addEventListener('click', () => modal.classList.add('hidden'));
            modal.addEventListener('click', e => { if (e.target === modal) modal.classList.add('hidden'); });
        }
    }
    setupModal('payment-modal', 'open-payment-modal-btn', 'close-payment-modal-btn');
    setupModal('half-pizza-modal', 'open-half-pizza-modal-btn', 'close-half-pizza-modal-btn');

    function showJsMessage(message, type = 'danger') {
        const messageDiv = document.getElementById('add-item-message');
        if (!messageDiv) return;
        const colors = type === 'success' 
            ? 'bg-green-100 text-green-800 dark:bg-green-900/50 dark:text-green-300' 
            : 'bg-red-100 text-red-800 dark:bg-red-900/50 dark:text-red-300';
        messageDiv.className = `p-3 my-2 text-sm rounded-md ${colors}`;
        messageDiv.textContent = message;
        setTimeout(() => { messageDiv.textContent = ''; messageDiv.className = 'text-sm'; }, 4000);
    }

    function addItemToDOM(item) {
        const noItemsMsg = document.getElementById('no-items-message');
        if (noItemsMsg) noItemsMsg.remove();
        
        let existingRow = document.getElementById(`item-row-${item.id}`);
        if(existingRow && !item.name.includes('Mitad:')) {
             existingRow.querySelector('.quantity-display').textContent = `${item.quantity} x`;
             existingRow.querySelector('.subtotal-display').textContent = `$${item.subtotal.toFixed(2)}`;
        } else {
            const escapedItemName = item.name.replace(/'/g, "\\'").replace(/"/g, '&quot;');
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
                        <button onclick="window.removeItem(${item.id}, '${escapedItemName}', ${item.product_id})" class="text-xs text-red-600 hover:text-red-500 dark:text-red-500 dark:hover:text-red-400 transition-colors">Quitar</button>
                    </div>
                </div>`;
            orderItemsList.insertAdjacentHTML('beforeend', itemHTML);
        }
    }

    function updateOrderTotal(newTotal) {
        if (orderTotalEl) orderTotalEl.textContent = `$${newTotal.toFixed(2)}`;
        const payBtn = document.getElementById('open-payment-modal-btn');
        if(payBtn) {
            const hasItems = newTotal > 0;
            payBtn.disabled = !hasItems;
            payBtn.classList.toggle('opacity-50', !hasItems);
            payBtn.classList.toggle('cursor-not-allowed', !hasItems);
        }
    }
    
    const halfPizzaForm = document.getElementById('half-pizza-form');
    if (halfPizzaForm) {
        halfPizzaForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            formData.append('csrf_token', csrfToken);
            
            fetch(`/mozo/order/${orderId}/add_half_pizza`, { method: 'POST', body: formData })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    addItemToDOM(data.item);
                    updateOrderTotal(data.order_total);
                    document.getElementById('half-pizza-modal').classList.add('hidden');
                    this.reset();
                } else {
                    alert(data.message);
                }
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
});