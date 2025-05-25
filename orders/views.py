from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.http import JsonResponse
from django.db import transaction
from django.db.models import F
from django.views.decorators.http import require_POST

from .models import Category, MenuItem, Customer, Cart, CartItem, Order, OrderItem
from .forms import (
    UserRegistrationForm,
    CustomerForm,
    AddToCartForm,
    CartUpdateForm,
    CheckoutForm,
)


def get_or_create_customer_for_user(user):
    customer, created = Customer.objects.get_or_create(
        user=user,
        defaults={
            "name": user.get_full_name() or user.username,
            "email": user.email,
            # "phone":
        },
    )
    return customer


def get_or_create_cart(request):
    customer = None
    if request.user.is_authenticated and hasattr(request.user, "customer"):
        customer = request.user.customer

    if customer:
        cart, created = Cart.objects.get_or_create(customer=customer)
        session_cart_id = request.session.get("cart_session_id")
        if session_cart_id:
            try:
                guest_cart = Cart.objects.get(
                    session_id=session_cart_id, customer__isnull=True
                )
                for item in guest_cart.items.all():
                    existing_item, item_created = CartItem.objects.get_or_create(
                        cart=cart,
                        menu_item=item.menu_item,
                        defaults={"quantity": item.quantity},
                    )
                    if not item_created:
                        existing_item.quantity += item.quantity
                        existing_item.save()
                guest_cart.delete()
                del request.session["cart_session_id"]
            except Cart.DoesNotExist:
                pass
        return cart
    else:
        session_id = request.session.get("cart_session_id")
        if not session_id:
            request.session.create()
            session_id = request.session.session_key
            request.session["cart_session_id"] = session_id

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


@transaction.atomic
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

    return render(
        request,
        "orders/cart.html",
        {"cart": cart, "cart_items": cart_items},
    )


@require_POST
@transaction.atomic
def update_cart_and_checkout(request):
    cart = get_or_create_cart(request)

    for item in cart.items.all():
        quantity = request.POST.get(f"quantity_{item.id}")
        if quantity is not None:
            try:
                qty = int(quantity)
                if qty > 0:
                    item.quantity = qty
                    item.save()
                else:
                    item.delete()
            except ValueError:
                continue

    return redirect("checkout")


@transaction.atomic
def checkout(request):
    cart = get_or_create_cart(request)

    if not cart or not cart.items.exists():
        messages.warning(request, "Your cart is empty!")
        return redirect("menu")

    current_customer_instance = None
    if request.user.is_authenticated:
        current_customer_instance = get_or_create_customer_for_user(request.user)

    if request.method == "POST":
        form = CheckoutForm(request.POST, user=request.user)
        if form.is_valid():
            customer_data_from_form = {
                "name": form.cleaned_data["name"],
                "email": form.cleaned_data["email"],
                "phone": form.cleaned_data["phone"],
            }
            final_customer = None

            if request.user.is_authenticated:
                final_customer = current_customer_instance
                needs_save = False
                for field, value in customer_data_from_form.items():
                    if value and getattr(final_customer, field) != value:
                        setattr(final_customer, field, value)
                        needs_save = True
                if needs_save:
                    if final_customer.user.email != customer_data_from_form["email"]:
                        final_customer.user.email = customer_data_from_form["email"]
                        final_customer.user.save(update_fields=["email"])
                    final_customer.save()
            else:  # Guest user
                try:
                    final_customer = Customer.objects.get(
                        email=customer_data_from_form["email"], user__isnull=True
                    )
                    final_customer.name = customer_data_from_form["name"]
                    final_customer.phone = customer_data_from_form["phone"]
                    final_customer.save()
                except Customer.DoesNotExist:
                    final_customer = Customer.objects.create(**customer_data_from_form)

            order = Order.objects.create(
                customer=final_customer,
                status=Order.Status.PENDING,
                special_instructions=form.cleaned_data.get("special_instructions", ""),
            )

            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    menu_item=cart_item.menu_item,
                    quantity=cart_item.quantity,
                    price=cart_item.menu_item.price,
                )

            cart.items.all().delete()
            if cart.session_id and not cart.customer:
                cart.delete()
                if "cart_session_id" in request.session:
                    del request.session["cart_session_id"]

            messages.success(request, "Order placed successfully!")
            request.session["last_order_id"] = order.id
            return redirect("order_confirmation", order_id=order.id)
        else:
            messages.error(
                request, "Please correct the errors below. Check all fields."
            )
    else:
        initial_form_data = {}
        if current_customer_instance:  # Pre-fill for authenticated user
            initial_form_data["name"] = current_customer_instance.name
            initial_form_data["email"] = current_customer_instance.email
            initial_form_data["phone"] = current_customer_instance.phone
        form = CheckoutForm(user=request.user, initial=initial_form_data)

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
    order = get_object_or_404(
        Order.objects.select_related("customer").prefetch_related("items__menu_item"),
        id=order_id,
    )
    can_view = False

    if request.user.is_authenticated and hasattr(request.user, "customer"):
        if order.customer == request.user.customer:
            can_view = True
    elif order.customer and not order.customer.user:
        last_order_id_in_session = request.session.get("last_order_id")
        if last_order_id_in_session == order.id:
            can_view = True

    if not can_view:
        messages.error(
            request,
            "You don't have permission to view this order confirmation, or your session has expired.",
        )
        return redirect("index")  # or menu

    return render(request, "orders/order_confirmation.html", {"order": order})


# TODO
@login_required
def order_detail(request, order_id):
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
    except Order.DoesNotExist:
        messages.error(
            request, "Order not found or you do not have permission to view it."
        )
        return redirect("order_history")

    return render(request, "orders/order_detail.html", {"order": order})


# TODO
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
        messages.warning(request, "No customer profile found to display order history.")
        orders_list = []

    return render(request, "orders/order_history.html", {"orders": orders_list})


@transaction.atomic
def register(request):
    if request.user.is_authenticated:
        return redirect("index")

    if request.method == "POST":
        user_form = UserRegistrationForm(request.POST)
        if user_form.is_valid():
            user = user_form.save()

            customer = get_or_create_customer_for_user(user)

            login(request, user, backend="django.contrib.auth.backends.ModelBackend")

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
                        if not created:
                            user_cart_item.quantity = F("quantity") + item.quantity
                            user_cart_item.save(update_fields=["quantity"])
                    session_cart.delete()
                    request.session.pop("cart_session_id", None)
                except Cart.DoesNotExist:
                    pass  # No guest cart to merge

            messages.success(
                request, f"Registration successful! Welcome, {user.username}."
            )
            return redirect("index")  # Or LOGIN_REDIRECT_URL
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        user_form = UserRegistrationForm()

    return render(
        request,
        "registration/register.html",
        {"user_form": user_form},
    )


# TODO
def contact(request):
    return render(request, "orders/contact.html")


# TODO
def about(request):
    return render(request, "orders/about.html")
