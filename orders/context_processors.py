from .models import Cart
from .views import get_or_create_cart


def cart_details(request):
    """Provides cart details to all templates."""
    cart = get_or_create_cart(request)

    cart_item_count = 0
    cart_total_price = 0.0
    distinct_item_count = 0

    if cart:
        cart_items = cart.items.all()
        distinct_item_count = cart_items.count()
        cart_item_count = sum(item.quantity for item in cart_items)
        cart_total_price = cart.total_price()

    return {
        "global_cart": cart,  # could be too heavy
        "global_cart_item_count": cart_item_count,
        "global_cart_distinct_item_count": distinct_item_count,
        "global_cart_total_price": cart_total_price,
    }
