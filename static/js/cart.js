/* ==========================================================================
   Sweet Scoop - Shopping Cart & Coupon Engine
   ========================================================================== */

const CART_STORAGE_KEY = 'sweet_scoop_cart_v1';
const COUPON_STORAGE_KEY = 'sweet_scoop_applied_coupon';

// Helper: Get Cart items
function getCart() {
    try {
        const data = localStorage.getItem(CART_STORAGE_KEY);
        return data ? JSON.parse(data) : [];
    } catch (e) {
        console.error('Error reading cart:', e);
        return [];
    }
}

// Helper: Save Cart items
function saveCart(cart) {
    localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(cart));
    renderCartUI();
}

// Helper: Get Applied Coupon
function getAppliedCoupon() {
    try {
        const data = localStorage.getItem(COUPON_STORAGE_KEY);
        return data ? JSON.parse(data) : null;
    } catch (e) {
        return null;
    }
}

// Helper: Save Coupon
function setAppliedCoupon(couponObj) {
    if (couponObj) {
        localStorage.setItem(COUPON_STORAGE_KEY, JSON.stringify(couponObj));
    } else {
        localStorage.removeItem(COUPON_STORAGE_KEY);
    }
    renderCartUI();
}

// Add Item to Cart
function addToCart(productId, name, unitPrice, image, size = 'Regular', quantity = 1) {
    let cart = getCart();
    quantity = parseInt(quantity) || 1;
    unitPrice = parseFloat(unitPrice);

    // Check if same product ID and same size already exists
    const existingIndex = cart.findIndex(item => item.id == productId && item.size === size);

    if (existingIndex > -1) {
        cart[existingIndex].quantity += quantity;
    } else {
        cart.push({
            id: productId,
            name: name,
            price: unitPrice,
            image: image,
            size: size,
            quantity: quantity
        });
    }

    saveCart(cart);
    showToast(`Added <b>${name} (${size})</b> to cart! 🍦`, 'success');
}

// Update Quantity by Index
function updateCartQuantity(index, delta) {
    let cart = getCart();
    if (index >= 0 && index < cart.length) {
        cart[index].quantity += delta;
        if (cart[index].quantity <= 0) {
            cart.splice(index, 1);
        }
        saveCart(cart);
    }
}

// Remove Item from Cart
function removeCartItem(index) {
    let cart = getCart();
    if (index >= 0 && index < cart.length) {
        const removedName = cart[index].name;
        cart.splice(index, 1);
        saveCart(cart);
        showToast(`Removed ${removedName} from cart.`, 'info');
    }
}

// Clear Entire Cart
function clearCart() {
    localStorage.removeItem(CART_STORAGE_KEY);
    localStorage.removeItem(COUPON_STORAGE_KEY);
    renderCartUI();
}

// Calculate Subtotal & Totals
function calculateCartTotals() {
    const cart = getCart();
    let subtotal = 0;
    cart.forEach(item => {
        subtotal += (item.price * item.quantity);
    });
    subtotal = Math.round(subtotal * 100) / 100;

    let discountAmount = 0;
    let appliedCoupon = getAppliedCoupon();
    if (appliedCoupon && appliedCoupon.discount_percent) {
        if (appliedCoupon.min_amount && subtotal < appliedCoupon.min_amount) {
            // Remove coupon if subtotal fell below minimum
            localStorage.removeItem(COUPON_STORAGE_KEY);
            appliedCoupon = null;
        } else {
            discountAmount = Math.round(subtotal * (appliedCoupon.discount_percent / 100) * 100) / 100;
        }
    }

    const total = Math.max(0, Math.round((subtotal - discountAmount) * 100) / 100);

    return {
        count: cart.reduce((sum, item) => sum + item.quantity, 0),
        subtotal: subtotal,
        discount: discountAmount,
        total: total,
        coupon: appliedCoupon
    };
}

// Apply Discount Coupon via Backend Validation API
async function applyCouponCode(code) {
    const totals = calculateCartTotals();
    if (totals.subtotal <= 0) {
        showToast('Your cart is empty! Add products first.', 'warning');
        return;
    }

    try {
        const resp = await fetch('/api/coupon/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: code, subtotal: totals.subtotal })
        });
        const data = await resp.json();

        if (data.valid) {
            setAppliedCoupon({
                code: data.code,
                discount_percent: data.discount_percent,
                discount_amount: data.discount_amount
            });
            showToast(data.message, 'success');
        } else {
            showToast(data.message, 'danger');
        }
    } catch (err) {
        console.error(err);
        showToast('Failed to validate coupon code.', 'danger');
    }
}

// Remove Coupon
function removeCouponCode() {
    setAppliedCoupon(null);
    showToast('Discount coupon removed.', 'info');
}

// Global UI Sync & Render Function
function renderCartUI() {
    const cart = getCart();
    const totals = calculateCartTotals();

    // 1. Update Navbar Badges
    const badgeElems = document.querySelectorAll('.cart-badge');
    badgeElems.forEach(el => {
        el.textContent = totals.count;
    });

    // 2. Render Offcanvas Cart Drawer (if exists in DOM)
    const offcanvasList = document.getElementById('offcanvas-cart-items');
    const offcanvasSubtotal = document.getElementById('offcanvas-subtotal');
    const offcanvasTotal = document.getElementById('offcanvas-total');

    if (offcanvasList) {
        if (cart.length === 0) {
            offcanvasList.innerHTML = `
                <div class="text-center py-5">
                    <div style="font-size: 3.5rem;">🍦</div>
                    <h6 class="mt-3 text-muted">Your scoop cart is empty</h6>
                    <a href="/menu" class="btn btn-sm btn-primary-custom mt-2">Explore Menu</a>
                </div>`;
        } else {
            offcanvasList.innerHTML = cart.map((item, idx) => `
                <div class="d-flex align-items-center justify-content-between p-2 mb-2 bg-light rounded-3">
                    <img src="${item.image}" alt="${item.name}" style="width: 50px; height: 50px; object-fit: cover;" class="rounded-3 me-2">
                    <div class="flex-grow-1 ms-2">
                        <h6 class="mb-0 text-truncate" style="max-width: 140px; font-size: 0.9rem;">${item.name}</h6>
                        <span class="badge bg-secondary" style="font-size: 0.65rem;">${item.size}</span>
                        <div class="fw-bold text-primary-pink mt-1">₹${(item.price * item.quantity).toFixed(2)}</div>
                    </div>
                    <div class="d-flex align-items-center gap-1">
                        <button onclick="updateCartQuantity(${idx}, -1)" class="btn btn-sm btn-outline-secondary py-0 px-2">-</button>
                        <span class="fw-bold px-1">${item.quantity}</span>
                        <button onclick="updateCartQuantity(${idx}, 1)" class="btn btn-sm btn-outline-secondary py-0 px-2">+</button>
                        <button onclick="removeCartItem(${idx})" class="btn btn-sm text-danger ms-1"><i class="bi bi-trash"></i></button>
                    </div>
                </div>
            `).join('');
        }
    }

    if (offcanvasSubtotal) offcanvasSubtotal.textContent = `₹${totals.subtotal.toFixed(2)}`;
    if (offcanvasTotal) offcanvasTotal.textContent = `₹${totals.total.toFixed(2)}`;

    // 3. Render Cart Page Table (if on /cart)
    const cartTableBody = document.getElementById('cart-table-body');
    const cartSummarySubtotal = document.getElementById('summary-subtotal');
    const cartSummaryDiscount = document.getElementById('summary-discount');
    const cartSummaryTotal = document.getElementById('summary-total');
    const couponDisplayRow = document.getElementById('applied-coupon-row');

    if (cartTableBody) {
        if (cart.length === 0) {
            cartTableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-5">
                        <div style="font-size: 4rem;">🍧</div>
                        <h5 class="mt-3">Your shopping cart is empty</h5>
                        <p class="text-muted">Choose your favorite flavors from our delicious menu.</p>
                        <a href="/menu" class="btn btn-primary-custom">Browse Menu</a>
                    </td>
                </tr>`;
        } else {
            cartTableBody.innerHTML = cart.map((item, idx) => `
                <tr>
                    <td>
                        <div class="d-flex align-items-center">
                            <img src="${item.image}" alt="${item.name}" class="rounded-3 me-3" style="width: 60px; height: 60px; object-fit: cover;">
                            <div>
                                <h6 class="mb-1 fw-bold">${item.name}</h6>
                                <span class="badge bg-light text-dark border">${item.size} Scoop</span>
                            </div>
                        </div>
                    </td>
                    <td class="align-middle fw-semibold">₹${item.price.toFixed(2)}</td>
                    <td class="align-middle">
                        <div class="qty-control-group">
                            <button onclick="updateCartQuantity(${idx}, -1)" class="qty-btn">-</button>
                            <span class="qty-val">${item.quantity}</span>
                            <button onclick="updateCartQuantity(${idx}, 1)" class="qty-btn">+</button>
                        </div>
                    </td>
                    <td class="align-middle fw-bold text-danger">₹${(item.price * item.quantity).toFixed(2)}</td>
                    <td class="align-middle text-end">
                        <button onclick="removeCartItem(${idx})" class="btn btn-link text-danger p-0" title="Remove">
                            <i class="bi bi-trash3 fs-5"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        }
    }

    if (cartSummarySubtotal) cartSummarySubtotal.textContent = `₹${totals.subtotal.toFixed(2)}`;
    if (cartSummaryDiscount) cartSummaryDiscount.textContent = `-₹${totals.discount.toFixed(2)}`;
    if (cartSummaryTotal) cartSummaryTotal.textContent = `₹${totals.total.toFixed(2)}`;

    if (couponDisplayRow) {
        if (totals.coupon) {
            couponDisplayRow.innerHTML = `
                <div class="alert alert-success d-flex align-items-center justify-content-between py-2 px-3 mb-0">
                    <div>
                        <i class="bi bi-tag-fill me-1"></i> <b>${totals.coupon.code}</b> (${totals.coupon.discount_percent}% off applied)
                    </div>
                    <button onclick="removeCouponCode()" class="btn btn-sm btn-link text-success p-0 fw-bold">Remove</button>
                </div>`;
        } else {
            couponDisplayRow.innerHTML = '';
        }
    }

    // 4. Render Checkout Page Breakdown (if on /checkout)
    const checkoutItemList = document.getElementById('checkout-items-list');
    const checkoutSubtotal = document.getElementById('checkout-subtotal');
    const checkoutDiscount = document.getElementById('checkout-discount');
    const checkoutTotal = document.getElementById('checkout-total');

    if (checkoutItemList) {
        checkoutItemList.innerHTML = cart.map(item => `
            <div class="d-flex justify-content-between align-items-center mb-2 pb-2 border-bottom">
                <div>
                    <span class="fw-semibold">${item.name}</span>
                    <span class="text-muted ms-1">(${item.size} x${item.quantity})</span>
                </div>
                <div class="fw-bold">₹${(item.price * item.quantity).toFixed(2)}</div>
            </div>
        `).join('');
    }

    if (checkoutSubtotal) checkoutSubtotal.textContent = `₹${totals.subtotal.toFixed(2)}`;
    if (checkoutDiscount) checkoutDiscount.textContent = `-₹${totals.discount.toFixed(2)}`;
    if (checkoutTotal) checkoutTotal.textContent = `₹${totals.total.toFixed(2)}`;
}

// Toast Notification Helper
function showToast(message, type = 'info') {
    let container = document.querySelector('.toast-container-custom');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container-custom';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    const bgClass = type === 'success' ? 'bg-success text-white' : 
                     type === 'danger' ? 'bg-danger text-white' : 
                     type === 'warning' ? 'bg-warning text-dark' : 'bg-dark text-white';

    toast.className = `toast align-items-center ${bgClass} border-0 show mb-2 shadow-lg`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body py-2 px-3">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" onclick="this.parentElement.parentElement.remove()"></button>
        </div>
    `;

    container.appendChild(toast);
    setTimeout(() => {
        toast.remove();
    }, 4000);
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    renderCartUI();
});
