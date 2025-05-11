from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.http import JsonResponse
from .models import Category, MenuItem, Customer, Cart, CartItem, Order, OrderItem
from .forms import (
    UserRegistrationForm,
    CustomerForm,
    AddToCartForm,
    CartUpdateForm,
    CheckoutForm,
)


def get_or_create_cart(request):
    """Helper function to get or create a cart based on session or user"""
    if request.user.is_authenticated:
        try:
            customer = request.user.customer
        except:  # TODO(JS): Do not use bare except
            # Create customer profile for user if it doesn't exist
            customer = Customer.objects.create(
                user=request.user,
                name=request.user.username,
            )

        cart, created = Cart.objects.get_or_create(customer=customer)
    else:
        # For non-authenticated users, use session
        session_id = request.session.session_key
        if not session_id:
            request.session.create()
            session_id = request.session.session_key

        cart, created = Cart.objects.get_or_create(session_id=session_id)
    return cart


def index(request):
    """Home page showing featured menu items and categories"""
    categories = Category.objects.all()
    featured_items = MenuItem.objects.filter(available=True)[:6]

    return render(
        request,
        "orders/index.html",
        {"categories": categories, "featured_items": featured_items},
    )


def menu(request, category_id=None):
    """Display menu items, optionally filtered by category"""
    categories = Category.objects.all()

    if category_id:
        category = get_object_or_404(Category, id=category_id)
        menu_items = MenuItem.objects.filter(category=category, available=True)
    else:
        category = None
        menu_items = MenuItem.objects.filter(available=True)

    add_to_cart_form = AddToCartForm()

    return render(
        request,
        "orders/menu.html",
        {
            "categories": categories,
            "category": category,
            "menu_items": menu_items,
            "add_to_cart_form": add_to_cart_form,
        },
    )


def add_to_cart(request):
    """Add an item to the cart"""
    if request.method == "POST":
        form = AddToCartForm(request.POST)
        if form.is_valid():
            menu_item_id = form.cleaned_data["menu_item_id"]
            quantity = form.cleaned_data["quantity"]

            menu_item = get_object_or_404(MenuItem, id=menu_item_id)
            cart = get_or_create_cart(request)

            # Check if item already in cart
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart, menu_item=menu_item, defaults={"quantity": quantity}
            )

            if not created:
                cart_item.quantity += quantity
                cart_item.save()

            messages.success(request, f"{menu_item.name} added to cart!")

            # If AJAX request
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({
                    "status": "success",
                    "message": f"{menu_item.name} added to cart!",
                    "cart_count": cart.items.count(),
                    "cart_total": float(cart.total_price()),
                })

            # Otherwise redirect
            return redirect("menu")

    # Form not valid or not POST
    return redirect("menu")


def view_cart(request):
    """View and update cart"""
    cart = get_or_create_cart(request)
    cart_items = cart.items.all()

    if request.method == "POST":
        form = CartUpdateForm(request.POST)
        if form.is_valid():
            cart_item_id = form.cleaned_data["cart_item_id"]
            quantity = form.cleaned_data["quantity"]

            try:
                cart_item = CartItem.objects.get(id=cart_item_id, cart=cart)

                if quantity > 0:
                    cart_item.quantity = quantity
                    cart_item.save()
                    messages.success(request, "Cart updated!")
                else:
                    cart_item.delete()
                    messages.success(request, "Item removed from cart!")

            except CartItem.DoesNotExist:
                messages.error(request, "Error updating cart!")

            return redirect("view_cart")

    # Create a form for each cart item
    update_forms = {}
    for item in cart_items:
        form = CartUpdateForm(
            initial={"cart_item_id": item.id, "quantity": item.quantity}
        )
        update_forms[item.id] = form

    return render(
        request,
        "orders/cart.html",
        {"cart": cart, "cart_items": cart_items, "update_forms": update_forms},
    )


def checkout(request):
    """Checkout process"""
    cart = get_or_create_cart(request)

    # Redirect if cart is empty
    if not cart.items.exists():
        messages.warning(request, "Your cart is empty!")
        return redirect("menu")

    if request.method == "POST":
        form = CheckoutForm(request.POST, user=request.user)
        if form.is_valid():
            # Get or create customer
            if request.user.is_authenticated:
                try:
                    customer = request.user.customer
                except:
                    customer = Customer.objects.create(
                        user=request.user, name=request.user.username
                    )
            else:
                # Handle guest checkout
                customer, created = Customer.objects.get_or_create(
                    name=form.cleaned_data["name"],
                    phone=form.cleaned_data["phone"],
                    email=form.cleaned_data["email"],
                )

            # Create the order
            order = Order.objects.create(
                customer=customer,
                special_instructions=form.cleaned_data["special_instructions"],
            )

            # Add items to the order
            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    menu_item=cart_item.menu_item,
                    quantity=cart_item.quantity,
                    price=cart_item.menu_item.price,
                )

            # Clear the cart
            cart.items.all().delete()

            # Redirect to order confirmation
            return redirect("order_confirmation", order_id=order.id)
    else:
        form = CheckoutForm(user=request.user)

    return render(
        request,
        "orders/checkout.html",
        {"form": form, "cart": cart, "cart_items": cart.items.all()},
    )


def order_confirmation(request, order_id):
    """Order confirmation page"""
    order = get_object_or_404(Order, id=order_id)

    # Security check - only allow customers to see their own orders
    if request.user.is_authenticated:
        try:
            if order.customer != request.user.customer:
                messages.error(request, "You don't have permission to view this order.")
                return redirect("index")
        except:
            pass

    return render(request, "orders/order_confirmation.html", {"order": order})


def order_detail(request, order_id):
    """Order detail page"""
    order = get_object_or_404(Order, id=order_id)

    # Security check - only allow customers to see their own orders
    if request.user.is_authenticated:
        try:
            if order.customer != request.user.customer:
                messages.error(request, "You don't have permission to view this order.")
                return redirect("index")
        except:
            pass

    return render(request, "orders/order_detail.html", {"order": order})


@login_required
def order_history(request):
    """View order history for authenticated users"""
    try:
        customer = request.user.customer
        orders = Order.objects.filter(customer=customer).order_by("-created_at")
    except:
        orders = []

    return render(request, "orders/order_history.html", {"orders": orders})


def register(request):
    """User registration view"""
    if request.method == "POST":
        user_form = UserRegistrationForm(request.POST)
        customer_form = CustomerForm(request.POST)

        if user_form.is_valid() and customer_form.is_valid():
            user = user_form.save()

            # Create customer profile
            customer = customer_form.save(commit=False)
            customer.user = user
            customer.save()

            # Log the user in
            login(request, user)

            # Move any existing cart items to the user's cart
            if "session_key" in request.session:
                try:
                    session_cart = Cart.objects.get(
                        session_id=request.session.session_key
                    )
                    user_cart, created = Cart.objects.get_or_create(customer=customer)

                    # Transfer cart items
                    for item in session_cart.items.all():
                        # Check if item already exists in user cart
                        existing_item = CartItem.objects.filter(
                            cart=user_cart, menu_item=item.menu_item
                        ).first()

                        if existing_item:
                            existing_item.quantity += item.quantity
                            existing_item.save()
                        else:
                            item.cart = user_cart
                            item.save()

                    # Delete the session cart
                    session_cart.delete()
                except Cart.DoesNotExist:
                    pass

            messages.success(request, "Registration successful!")
            return redirect("index")
    else:
        user_form = UserRegistrationForm()
        customer_form = CustomerForm()

    return render(
        request,
        "registration/register.html",
        {"user_form": user_form, "customer_form": customer_form},
    )
