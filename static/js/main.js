/* ==========================================================================
   Sweet Scoop - Main Application JavaScript
   ========================================================================== */

const WISHLIST_KEY = 'sweet_scoop_wishlist';

// Get Saved Wishlist IDs
function getWishlist() {
    try {
        const data = localStorage.getItem(WISHLIST_KEY);
        return data ? JSON.parse(data) : [];
    } catch (e) {
        return [];
    }
}

// Toggle Favorite Item
function toggleWishlist(productId, btnElement) {
    let wishlist = getWishlist();
    const index = wishlist.indexOf(productId);
    
    if (index > -1) {
        wishlist.splice(index, 1);
        if (btnElement) btnElement.classList.remove('active');
        showToast('Removed from favorites', 'info');
    } else {
        wishlist.push(productId);
        if (btnElement) btnElement.classList.add('active');
        showToast('Saved to your favorites ❤️', 'success');
    }
    
    localStorage.setItem(WISHLIST_KEY, JSON.stringify(wishlist));
    renderWishlistUI();
}

// Sync Wishlist Buttons UI
function renderWishlistUI() {
    const wishlist = getWishlist();
    document.querySelectorAll('.fav-badge-btn').forEach(btn => {
        const pId = parseInt(btn.dataset.id);
        if (wishlist.includes(pId)) {
            btn.classList.add('active');
            btn.innerHTML = '<i class="bi bi-heart-fill"></i>';
        } else {
            btn.classList.remove('active');
            btn.innerHTML = '<i class="bi bi-heart"></i>';
        }
    });
}

// Client-side Instant Filter for Menu Page
function initMenuFilter() {
    const searchInput = document.getElementById('menu-search-input');
    const categoryChips = document.querySelectorAll('.category-chip');
    const productCards = document.querySelectorAll('.product-card-col');
    const emptyState = document.getElementById('no-products-msg');

    if (!searchInput && categoryChips.length === 0) return;

    function applyFilter() {
        const query = searchInput ? searchInput.value.toLowerCase().trim() : '';
        const activeChip = document.querySelector('.category-chip.active');
        const selectedCategory = activeChip ? activeChip.dataset.slug : 'all';
        let visibleCount = 0;

        productCards.forEach(card => {
            const name = card.dataset.name.toLowerCase();
            const desc = card.dataset.desc.toLowerCase();
            const category = card.dataset.category;

            const matchesSearch = !query || name.includes(query) || desc.includes(query);
            const matchesCategory = selectedCategory === 'all' || category === selectedCategory;

            if (matchesSearch && matchesCategory) {
                card.style.display = 'block';
                visibleCount++;
            } else {
                card.style.display = 'none';
            }
        });

        if (emptyState) {
            emptyState.style.display = (visibleCount === 0) ? 'block' : 'none';
        }
    }

    if (searchInput) {
        searchInput.addEventListener('input', applyFilter);
    }

    categoryChips.forEach(chip => {
        chip.addEventListener('click', (e) => {
            e.preventDefault();
            categoryChips.forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            applyFilter();
        });
    });

    // Run filter on initial page load
    applyFilter();
}

function resetMenuFilters(e) {
    if (e) e.preventDefault();
    const searchInput = document.getElementById('menu-search-input');
    if (searchInput) searchInput.value = '';
    
    const categoryChips = document.querySelectorAll('.category-chip');
    categoryChips.forEach(chip => {
        if (chip.dataset.slug === 'all') {
            chip.classList.add('active');
        } else {
            chip.classList.remove('active');
        }
    });

    const productCards = document.querySelectorAll('.product-card-col');
    productCards.forEach(card => card.style.display = 'block');
    
    const emptyState = document.getElementById('no-products-msg');
    if (emptyState) emptyState.style.display = 'none';
}

// Product Details Size Switcher & Add to Cart Handler
function initProductDetailsPage() {
    const sizeBtns = document.querySelectorAll('.size-selector-btn');
    const priceDisplay = document.getElementById('detail-product-price');
    const addToCartBtn = document.getElementById('detail-add-cart-btn');
    const qtyInput = document.getElementById('detail-qty-input');

    if (!addToCartBtn) return;

    let selectedSize = 'Regular';

    sizeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            sizeBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedSize = btn.dataset.size;
            const newPrice = parseFloat(btn.dataset.price);
            if (priceDisplay) {
                priceDisplay.textContent = `₹${newPrice.toFixed(2)}`;
            }
        });
    });

    addToCartBtn.addEventListener('click', () => {
        const pId = addToCartBtn.dataset.id;
        const name = addToCartBtn.dataset.name;
        const img = addToCartBtn.dataset.image;
        const qty = parseInt(qtyInput ? qtyInput.value : 1);

        const activeSizeBtn = document.querySelector('.size-selector-btn.active');
        const currentPrice = activeSizeBtn ? parseFloat(activeSizeBtn.dataset.price) : parseFloat(addToCartBtn.dataset.price);

        addToCart(pId, name, currentPrice, img, selectedSize, qty);
    });
}

// Checkout Form Submission
function initCheckoutPage() {
    const checkoutForm = document.getElementById('checkout-form');
    if (!checkoutForm) return;

    checkoutForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const cart = getCart();
        if (cart.length === 0) {
            showToast('Your cart is empty! Please add products before checking out.', 'danger');
            return;
        }

        const customerName = document.getElementById('customer_name').value.trim();
        const mobileNumber = document.getElementById('mobile_number').value.trim();
        const address = document.getElementById('address').value.trim();
        const paymentOption = document.querySelector('input[name="payment_option"]:checked')?.value || 'COD';

        const coupon = getAppliedCoupon();
        const couponCode = coupon ? coupon.code : '';

        const submitBtn = document.getElementById('place-order-btn');
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Placing Order...`;

        try {
            const resp = await fetch('/place-order', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    customer_name: customerName,
                    mobile_number: mobileNumber,
                    address: address,
                    payment_option: paymentOption,
                    coupon_code: couponCode,
                    cart_items: cart
                })
            });

            const data = await resp.json();
            if (data.success) {
                clearCart();
                window.location.href = `/order-success/${data.order_code}`;
            } else {
                showToast(data.message || 'Failed to place order.', 'danger');
                submitBtn.disabled = false;
                submitBtn.innerHTML = `Place Order Now 🍦`;
            }
        } catch (err) {
            console.error(err);
            showToast('An error occurred while placing your order.', 'danger');
            submitBtn.disabled = false;
            submitBtn.innerHTML = `Place Order Now 🍦`;
        }
    });
}

// Review Submission Handler
function submitReview(productId) {
    const nameInput = document.getElementById('review-author-name');
    const ratingInput = document.getElementById('review-rating-val');
    const commentInput = document.getElementById('review-comment-text');

    const name = nameInput ? nameInput.value.trim() : 'Ice Cream Lover';
    const rating = ratingInput ? ratingInput.value : 5;
    const comment = commentInput ? commentInput.value.trim() : '';

    if (!comment) {
        showToast('Please enter your review text!', 'warning');
        return;
    }

    fetch(`/api/product/${productId}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_name: name, rating: rating, comment: comment })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showToast(data.message, 'success');
            setTimeout(() => location.reload(), 1200);
        } else {
            showToast(data.message, 'danger');
        }
    })
    .catch(err => {
        console.error(err);
        showToast('Failed to submit review.', 'danger');
    });
}

// Initialization on DOM Loaded
document.addEventListener('DOMContentLoaded', () => {
    renderWishlistUI();
    initMenuFilter();
    initProductDetailsPage();
    initCheckoutPage();
});
