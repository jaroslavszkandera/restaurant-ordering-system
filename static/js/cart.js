function updatePrices() {
let total = 0;
document.querySelectorAll('tr').forEach(function (row) {
    const priceEl = row.querySelector('.item-price');
    const qtyEl = row.querySelector('.quantity-input');
    const subtotalEl = row.querySelector('.item-subtotal');

    if (priceEl && qtyEl && subtotalEl) {
    const price = parseFloat(priceEl.textContent.replace('$', '')) || 0;
    const qty = parseInt(qtyEl.value) || 0;
    const subtotal = price * qty;
    subtotalEl.textContent = `$${subtotal.toFixed(2)}`;
    total += subtotal;

    const hiddenInput = document.getElementById(`checkout-qty-${qtyEl.dataset.itemId}`);
    if (hiddenInput) {
        hiddenInput.value = qty;
    }
    }
});
document.getElementById('cart-total-price').textContent = `$${total.toFixed(2)}`;
document.getElementById('cart-total-price-total').textContent = `$${total.toFixed(2)}`;
}

document.querySelectorAll('.quantity-input').forEach(input => {
input.addEventListener('change', updatePrices);
});

updatePrices();