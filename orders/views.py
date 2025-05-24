from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.http import JsonResponse
from django.db import transaction
from django.db.models import F
from django.contrib.auth import logout
from django.shortcuts import redirect

from .models import Category, MenuItem, Customer, Cart, CartItem, Order, OrderItem
from .forms import (
    UserRegistrationForm,
    CustomerForm,
    AddToCartForm,
    CartUpdateForm,
    CheckoutForm,
)


def get_or_create_customer_for_user(user):
    """
    Retrieves or creates a Customer profile for a given User.
    """
    customer, created = Customer.objects.get_or_create(
        user=user,
        defaults={
            "name": user.get_full_name() or user.username,
            "email": user.email,
        },
    )
    return customer


def get_or_create_cart(request):
    """Helper function to get or create a cart based on session or user."""
    cart = None
    if request.user.is_authenticated:
        customer = get_or_create_customer_for_user(request.user)
        cart, created = Cart.objects.get_or_create(customer=customer)

        # Check if there's a session cart to merge
        session_id = request.session.get("cart_session_id")
        if session_id:
            try:
                session_cart = Cart.objects.get(
                    session_id=session_id, customer__isnull=True
                )
                # Merge session_cart into user_cart
                for item in session_cart.items.all():
                    user_cart_item, item_created = CartItem.objects.get_or_create(
                        cart=cart,
                        menu_item=item.menu_item,
                        defaults={"quantity": item.quantity},
                    )
                    if not item_created:
                        user_cart_item.quantity = F("quantity") + item.quantity
                        user_cart_item.save()
                session_cart.delete()
                request.session.pop("cart_session_id", None)  # Clear session key
            except Cart.DoesNotExist:
                pass  # No session cart to merge or already merged

    else:
        session_id = request.session.get("cart_session_id")
        if not session_id:
            request.session.create()  # Ensure session exists
            session_id = request.session.session_key
            request.session["cart_session_id"] = (
                session_id  # Store specifically for cart
            )

        cart, created = Cart.objects.get_or_create(
            session_id=session_id, customer__isnull=True
        )
    return cart


def index(request):
    """Home page showing featured menu items and categories."""
    categories = Category.objects.all()
    featured_items = MenuItem.objects.filter(available=True).order_by("?")[
        :6
    ]  # TODO(JS): Define featured flag, now randomly pick some.

    return render(
        request,
        "orders/index.html",
        {"categories": categories, "featured_items": featured_items},
    )


def menu(request, category_id=None):
    """Display menu items, optionally filtered by category."""
    categories = Category.objects.all()
    menu_items = MenuItem.objects.filter(available=True)

    if category_id:
        category = get_object_or_404(Category, id=category_id)
        menu_items = menu_items.filter(category=category)
    else:
        category = None

    return render(
        request,
        "orders/menu.html",
        {
            "categories": categories,
            "category": category,
            "menu_items": menu_items,
        },
    )


@transaction.atomic  # JS: maybe an overkill
def add_to_cart(request):
    """Add an item to the cart."""
    if request.method == "POST":
        form = AddToCartForm(request.POST)
        if form.is_valid():
            menu_item_id = form.cleaned_data["menu_item_id"]
            quantity = form.cleaned_data["quantity"]

            menu_item = get_object_or_404(MenuItem, id=menu_item_id, available=True)
            cart = get_or_create_cart(request)

            cart_item, created = CartItem.objects.get_or_create(
                cart=cart, menu_item=menu_item, defaults={"quantity": quantity}
            )

            if not created:
                cart_item.quantity = F("quantity") + quantity
                cart_item.save()

            cart.refresh_from_db()

            messages.success(request, f"{menu_item.name} added to cart!")

            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({
                    "status": "success",
                    "message": f"{menu_item.name} added to cart!",
                    "cart_item_count": cart.items.count(),
                    "cart_total_quantity": sum(
                        item.quantity for item in cart.items.all()
                    ),
                    "cart_total_price": float(cart.total_price()),
                })

            return redirect(request.POST.get("next", "menu"))
        else:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse(
                    {"status": "error", "errors": form.errors}, status=400
                )
            messages.error(request, "Could not add item. Please check the quantity.")
            return redirect(request.POST.get("next", "menu"))

    messages.error(request, "Invalid request.")
    return redirect("menu")

def view_cart(request):
    """View and update cart."""
    cart = get_or_create_cart(request)
    cart_items = cart.items.all().select_related("menu_item")

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
                    messages.success(
                        request, f"{cart_item.menu_item.name} quantity updated!"
                    )
                else:  # Quantity is 0 or less, remove the item
                    item_name = cart_item.menu_item.name
                    cart_item.delete()
                    messages.success(request, f"{item_name} removed from cart!")

            except CartItem.DoesNotExist:
                messages.error(request, "Item not found in your cart.")

            return redirect("view_cart")
        else:
            messages.error(request, "Invalid data submitted. Please check your input.")
            # No need to repopulate update_forms for error display if template renders manually

    # For GET request, no individual forms are needed if template renders inputs manually
    return render(
        request,
        "orders/cart.html",
        {"cart": cart, "cart_items": cart_items},
    )


@transaction.atomic
def checkout(request):
    """Checkout process."""
    cart = get_or_create_cart(request)

    if not cart.items.exists():
        messages.warning(request, "Your cart is empty!")
        return redirect("menu")

    customer = None
    if request.user.is_authenticated:
        customer = get_or_create_customer_for_user(request.user)

    if request.method == "POST":
        form = CheckoutForm(
            request.POST, user=request.user, instance=customer if customer else None
        )
        if form.is_valid():
            if request.user.is_authenticated:
                # Customer should already be set or
                #   created via get_or_create_cart/get_or_create_customer_for_user
                # Update customer details if the form allows it (e.g. address, phone)
                if (
                    customer and form.has_changed()
                ):  # Check if form is bound to customer instance and has changes
                    form.save()
            else:
                customer_data = {
                    key: form.cleaned_data[key]
                    for key in ["name", "email", "phone"]
                    if key in form.cleaned_data
                }
                # This logic might need refinement based on CheckoutForm structure
                # email is unique for customers, get_or_create by email.
                if "email" in customer_data:
                    customer, _ = Customer.objects.get_or_create(
                        email=customer_data["email"], defaults=customer_data
                    )
                    if not _:  # if customer was fetched, update details
                        for attr, value in customer_data.items():
                            setattr(customer, attr, value)
                        customer.save()
                else:  # Fallback if no email for guest, less ideal
                    customer = Customer.objects.create(**customer_data)

            order = Order.objects.create(
                customer=customer,
                status=Order.Status.PENDING,
                special_instructions=form.cleaned_data.get("special_instructions", ""),
            )

            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    menu_item=cart_item.menu_item,
                    quantity=cart_item.quantity,
                    price=cart_item.menu_item.price,  # Crucial: price at time of order
                )

            cart.items.all().delete()

            # Allow guest access to order confirmation page
            guest_order_ids = request.session.get("guest_order_ids", [])
            guest_order_ids.append(order.id)
            request.session["guest_order_ids"] = guest_order_ids          
            
            if (
                cart.session_id and not cart.customer
            ):  # If it was a session-only cart, can delete it.
                cart.delete()
                request.session.pop("cart_session_id", None)

            messages.success(request, "Order placed successfully!")
            return redirect("order_confirmation", order_id=order.id)
    else:
        initial_data = {}
        if customer:  # Pre-fill for logged-in user
            initial_data = {
                "name": customer.name,
                "email": customer.email,
                "phone": customer.phone,
            }
        form = CheckoutForm(user=request.user, initial=initial_data)

    return render(
        request,
        "orders/checkout.html",
        {
            "form": form,
            "cart": cart,
            "cart_items": cart.items.all().select_related("menu_item"),
        },
    )


def order_confirmation(request, order_id):
    """Order confirmation page."""
    order = get_object_or_404(Order.objects.select_related("customer"), id=order_id)

    can_view = False

    # 1. 登入使用者可看自己下的訂單
    if request.user.is_authenticated and hasattr(request.user, "customer"):
        if order.customer == request.user.customer:
            can_view = True

    # 2. 未登入使用者，可從 session 確認剛剛建立的 order_id
    if not can_view:
        guest_order_ids = request.session.get("guest_order_ids", [])
        if order.id in guest_order_ids:
            can_view = True

    # 3. 拒絕非授權存取
    if not can_view:
        messages.error(request, "You don't have permission to view this order confirmation.")
        return redirect("index")

    return render(request, "orders/order_confirmation.html", {"order": order})



@login_required
def order_detail(request, order_id):
    """Displays details of a specific order."""
    try:
        customer = request.user.customer
        order = get_object_or_404(
            Order.objects.select_related("customer").prefetch_related(
                "items__menu_item"
            ),
            id=order_id,
            customer=customer,
        )
    except Customer.DoesNotExist:
        messages.error(request, "Customer profile not found.")
        return redirect("index")
    except (
        Order.DoesNotExist
    ):  # Should be caught by get_object_or_404 if customer filter is not applied first
        messages.error(
            request, "Order not found or you do not have permission to view it."
        )
        return redirect("order_history")

    return render(request, "orders/order_detail.html", {"order": order})


@login_required
def order_history(request):
    """View order history for authenticated users."""
    try:
        customer = request.user.customer
        orders_list = (
            Order.objects.filter(customer=customer)
            .order_by("-created_at")
            .prefetch_related("items")
        )
    except Customer.DoesNotExist:
        # This case should ideally be handled by ensuring customer profile exists upon login/registration.
        messages.warning(request, "No customer profile found to display order history.")
        orders_list = []

    return render(request, "orders/order_history.html", {"orders": orders_list})


@transaction.atomic
def register(request):
    """User registration view."""
    if request.user.is_authenticated:
        return redirect("index")

    if request.method == "POST":
        user_form = UserRegistrationForm(request.POST)
        customer_form = CustomerForm(
            request.POST
        )  # Assuming CustomerForm collects name, phone, email

        if user_form.is_valid() and customer_form.is_valid():
            user = user_form.save()

            customer = customer_form.save(commit=False)
            customer.user = user
            # Ensure customer name/email are consistent if User model has them
            # customer.name = user.get_full_name() or user.username (if CustomerForm doesn't have name)
            # customer.email = user.email (if CustomerForm doesn't have email)
            customer.save()

            login(request, user)  # Log the user in

            # Merge session cart to user's cart
            session_id = request.session.get("cart_session_id")
            if session_id:
                try:
                    session_cart = Cart.objects.get(
                        session_id=session_id, customer__isnull=True
                    )
                    user_cart, _ = Cart.objects.get_or_create(customer=customer)

                    for item in session_cart.items.all():
                        user_cart_item, created = CartItem.objects.get_or_create(
                            cart=user_cart,
                            menu_item=item.menu_item,
                            defaults={"quantity": item.quantity},
                        )
                        if not created:  # Item already in user's cart, sum quantities
                            user_cart_item.quantity = F("quantity") + item.quantity
                            user_cart_item.save()

                    session_cart.delete()
                    request.session.pop("cart_session_id", None)
                except Cart.DoesNotExist:
                    pass  # No session cart to merge

            messages.success(request, "Registration successful! Welcome.")
            return redirect("index")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        user_form = UserRegistrationForm()
        customer_form = CustomerForm()

    return render(
        request,
        "registration/register.html",
        {"user_form": user_form, "customer_form": customer_form},
    )

def logout_view(request):
    logout(request)
    return redirect('index')