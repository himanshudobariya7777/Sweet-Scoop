/* ==========================================================================
   Sweet Scoop - Admin Management Panel JavaScript
   ========================================================================== */

// Update Order Status via AJAX
async function updateOrderStatus(orderId, newStatus) {
    try {
        const resp = await fetch('/admin/order/update-status', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ order_id: orderId, status: newStatus })
        });
        const data = await resp.json();

        if (data.success) {
            showToast(data.message, 'success');
            // Update status badge UI if present
            const badge = document.getElementById(`status-badge-${orderId}`);
            if (badge) {
                badge.textContent = newStatus;
                badge.className = 'badge ' + (
                    newStatus === 'Delivered' ? 'bg-success' :
                    newStatus === 'Out for Delivery' ? 'bg-info text-dark' :
                    newStatus === 'Preparing' ? 'bg-warning text-dark' :
                    newStatus === 'Cancelled' ? 'bg-danger' : 'bg-secondary'
                );
            }
        } else {
            showToast(data.message || 'Failed to update order status', 'danger');
        }
    } catch (e) {
        console.error(e);
        showToast('Network error while updating status', 'danger');
    }
}

// Toggle Contact Message Read/Unread Status
async function toggleMessageReadStatus(msgId, btnElem) {
    try {
        const resp = await fetch(`/admin/messages/toggle-read/${msgId}`, { method: 'POST' });
        const data = await resp.json();

        if (data.success) {
            const btn = btnElem || document.getElementById(`msg-btn-${msgId}`);
            if (btn) {
                btn.textContent = data.new_status === 'Read' ? 'Mark Unread' : 'Mark Read';
                btn.className = `btn btn-sm ${data.new_status === 'Read' ? 'btn-outline-secondary' : 'btn-outline-primary'}`;
            }
            const badge = document.getElementById(`msg-status-${msgId}`);
            if (badge) {
                badge.textContent = data.new_status;
                badge.className = `badge ${data.new_status === 'Read' ? 'bg-secondary' : 'bg-primary'}`;
            }
            if (typeof showToast === 'function') {
                showToast(`Message status changed to ${data.new_status}`, 'info');
            }
        }
    } catch (e) {
        console.error('Error toggling message status:', e);
    }
}

// Delegated Click Handler for Message Status Toggle
document.addEventListener('click', function (e) {
    const btn = e.target.closest('.btn-toggle-msg-status');
    if (btn) {
        const msgId = btn.dataset.msgId;
        if (msgId) {
            toggleMessageReadStatus(msgId, btn);
        }
    }

    const editBtn = e.target.closest('[data-edit-product]');
    if (editBtn) {
        const modal = document.getElementById('addProductModal');
        const form = document.getElementById('productForm');
        const modalTitle = document.getElementById('productModalTitle');
        const submitBtn = document.getElementById('productSubmitBtn');

        if (!modal || !form || !modalTitle || !submitBtn) return;

        const id = editBtn.dataset.id;
        form.action = `/admin/products/update/${id}`;
        modalTitle.textContent = 'Edit Ice Cream Flavour';
        submitBtn.textContent = 'Update Flavour';

        document.getElementById('product_name').value = editBtn.dataset.name || '';
        document.getElementById('product_description').value = editBtn.dataset.description || '';
        document.getElementById('product_category').value = editBtn.dataset.category || 'chocolate';
        document.getElementById('product_small').value = editBtn.dataset.small || '319.00';
        document.getElementById('product_medium').value = editBtn.dataset.medium || '479.00';
        document.getElementById('product_large').value = editBtn.dataset.large || '639.00';
        document.getElementById('product_image').value = editBtn.dataset.image || '/static/images/chocolate.jpg';
        document.getElementById('product_ingredients').value = editBtn.dataset.ingredients || 'Cream, Whole Milk, Cane Sugar, Natural Extracts';
        document.getElementById('product_popular').checked = editBtn.dataset.popular === 'true';
        document.getElementById('product_special').checked = editBtn.dataset.special === 'true';
        document.getElementById('product_discount').value = editBtn.dataset.discount || '0';

        const bootstrapModal = bootstrap.Modal.getOrCreateInstance(modal);
        bootstrapModal.show();
    }

    const addBtn = e.target.closest('[data-bs-target="#addProductModal"]');
    if (addBtn) {
        const form = document.getElementById('productForm');
        const modalTitle = document.getElementById('productModalTitle');
        const submitBtn = document.getElementById('productSubmitBtn');
        if (form && modalTitle && submitBtn) {
            form.action = '/admin/products';
            modalTitle.textContent = 'Add New Ice Cream Flavour';
            submitBtn.textContent = 'Save Flavour';
            form.reset();
            document.getElementById('product_small').value = '319.00';
            document.getElementById('product_medium').value = '479.00';
            document.getElementById('product_large').value = '639.00';
            document.getElementById('product_image').value = '/static/images/chocolate.jpg';
            document.getElementById('product_ingredients').value = 'Cream, Whole Milk, Cane Sugar, Natural Extracts';
            document.getElementById('product_discount').value = '10';
        }
    }
});
