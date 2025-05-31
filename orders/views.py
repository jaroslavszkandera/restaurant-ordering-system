from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.http import JsonResponse
from django.db import transaction
from django.db.models import F
from django.contrib.auth import logout
from django.shortcuts import redirect
from .forms import ContactForm
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.conf import settings
from django.core.mail import send_mail
from .models import ContactMessage
from .models import Branch, Reservation
from datetime import timedelta, time, datetime
from django.utils import timezone
from django.db.models import Sum
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.http import require_POST
from .models import Branch, Reservation, BranchTimeSlotCapacity
from .models import Category, MenuItem, Customer, Cart, CartItem, Order, OrderItem
from .forms import (
    UserRegistrationForm,
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
                else:  
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
                pickup_branch=form.cleaned_data["pickup_branch"],
            )

            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    menu_item=cart_item.menu_item,
                    quantity=cart_item.quantity,
                    price=cart_item.menu_item.price,
                )

            # 寄送 Email
            order_items = order.items.all()
            branch = order.pickup_branch
            customer = final_customer
            total_price = sum(item.price * item.quantity for item in order_items)

            email_subject = f"Pomodoro House - Order Confirmation"
            email_body = render_to_string("orders/order_email.txt", {
                "customer": customer,
                "branch": branch,
                "order_items": order_items,
                "special_instructions": order.special_instructions,
                "total_price": total_price,
            })

            send_mail(
                email_subject,
                email_body,
                settings.DEFAULT_FROM_EMAIL,
                [customer.email],
                fail_silently=False,
            )

            # 清空購物車
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
        if current_customer_instance:  
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
        return redirect("index")  

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


def check_cart_empty(request):
    cart = get_or_create_cart(request)  
    return JsonResponse({'is_empty': cart.items.count() == 0})

def reorder_view(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    cart = get_or_create_cart(request)

    if request.method == "POST" and request.POST.get("force") == "true":
        cart.items.all().delete()
    elif cart.items.exists():
        messages.warning(request, "Your cart is not empty. Please clear it to reorder.")
        return redirect("order_detail", order_id=order_id)
    for item in order.items.all():
        try:
            latest_menu_item = MenuItem.objects.get(id=item.menu_item.id)

            CartItem.objects.create(
                cart=cart,
                menu_item=latest_menu_item,
                quantity=item.quantity
            )
        except MenuItem.DoesNotExist:
            continue

    messages.success(request, "Order items added to cart!")
    return redirect("view_cart")

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
                    pass  

            messages.success(
                request, f"Registration successful! Welcome, {user.username}."
            )
            return redirect("index") 
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        user_form = UserRegistrationForm()

    return render(
        request,
        "registration/register.html",
        {"user_form": user_form},
    )

def logout_view(request):
    logout(request)
    return redirect('index')

def contact_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            ContactMessage.objects.create(
                name=form.cleaned_data['name'],
                email=form.cleaned_data['email'],
                phone=form.cleaned_data['phone'],
                mobile=form.cleaned_data['mobile'],
                message=form.cleaned_data['message']
            )
            messages.success(request, "Thank you for contacting us!")
            return redirect('index')
    else:
        initial_data = {}
        if request.user.is_authenticated:
            full_name = f"{request.user.first_name} {request.user.last_name}".strip()
            if full_name:
                initial_data['name'] = full_name
            initial_data['email'] = request.user.email
        form = ContactForm(initial=initial_data)

    return render(request, 'orders/contact.html', {'form': form})

def get_time_slots(branch, date, requested_guests=1):
    slots = []
    weekday = date.weekday()

    if weekday < 5:
        opening_periods = [
            (time(11, 0), time(14, 30)),
            (time(17, 0), time(22, 30)),
        ]
    else:
        opening_periods = [
            (time(11, 0), time(22, 30)),
        ]

    now = datetime.now().astimezone()

    slot_settings = {
        s.time_slot: s for s in BranchTimeSlotCapacity.objects.filter(
            branch=branch,
            weekday=weekday
        )
    }

    for start, end in opening_periods:
        dt = datetime.combine(date, start)
        closing_dt = datetime.combine(date, end)

        while dt + timedelta(minutes=30) <= closing_dt:
            slot_time = dt.time()

            setting = slot_settings.get(slot_time)
            if not setting:
                dt += timedelta(minutes=30)
                continue  

            if not setting.available:
                available = False
                remaining_capacity = 0
            else:
                reserved = Reservation.objects.filter(
                    branch=branch,
                    date=date,
                    time_slot=slot_time
                ).aggregate(total=Sum('guests'))['total'] or 0

                remaining_capacity = setting.max_capacity - reserved
                available = remaining_capacity >= requested_guests

            slots.append({
                'time': slot_time,
                'time_display': dt.strftime('%I:%M %p'),
                'available': available,
                'remaining_capacity': remaining_capacity,
            })

            dt += timedelta(minutes=30)

    if date == timezone.localdate():
        current_time = timezone.localtime().time()
        slots = [slot for slot in slots if slot['time'] > current_time]

    return slots

def get_branch_availability(branches, date, guests):
    availability = {}

    weekday = date.weekday()

    for branch in branches:
        branch_slots = {}

        time_slots = BranchTimeSlotCapacity.objects.filter(
            branch=branch,
            weekday=weekday
        )

        for slot in time_slots:
            reserved = Reservation.objects.filter(
                branch=branch,
                date=date,
                time_slot=slot.time_slot
            ).aggregate(total=Sum('guests'))['total'] or 0

            max_capacity = slot.max_capacity if slot.max_capacity is not None else 20

            remaining = max_capacity - reserved
            branch_slots[str(slot.time_slot)] = {
                'remaining': remaining,
                'disabled': remaining < guests
            }

        availability[branch.id] = branch_slots

    return availability

def fetch_available_time_slots(request):
    branch_id = request.GET.get('branch')
    date_str = request.GET.get('date')
    guests = int(request.GET.get('guests', 1))

    if not branch_id or not date_str:
        return JsonResponse({'error': 'Missing parameters'}, status=400)

    try:
        branch = Branch.objects.get(id=branch_id)
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (Branch.DoesNotExist, ValueError):
        return JsonResponse({'error': 'Invalid data'}, status=400)

    slots = get_time_slots(branch, date, guests)

    data = [
        {
            'time': slot['time'].strftime('%H:%M'),
            'display': slot['time_display'],
            'available': slot['available'],
        }
        for slot in slots
    ]

    return JsonResponse({'slots': data})

def reservation(request):
    today = timezone.localdate()
    two_months_later = today + timedelta(days=60)
    branches = Branch.objects.filter(is_reservable=True)

    full_name = ""
    email = ""
    if request.user.is_authenticated:
        full_name = f"{request.user.first_name} {request.user.last_name}".strip()
        email = request.user.email or ""
    
    if request.method == 'POST':
        branch_id = request.POST.get('branch')
        date_str = request.POST.get('date')
        time_str = request.POST.get('time_slot')
        guests_str = request.POST.get('guests')
        name = request.POST.get('name') or full_name
        mobile = request.POST.get('mobile')
        email = request.POST.get('email') or email

        field_errors = {}
        is_valid = True

        # 驗證 guests
        try:
            guests = int(guests_str)
            if not (1 <= guests <= 8):
                field_errors['error_guests'] = "Invalid number of guests."
                is_valid = False
        except:
            field_errors['error_guests'] = "Please select the number of guests."
            is_valid = False

        # 驗證日期
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            if date < today or date > two_months_later:
                field_errors['error_date'] = "Date out of allowed range."
                is_valid = False
        except:
            field_errors['error_date'] = "Invalid date format."
            is_valid = False

        # 驗證分店
        try:
            branch = Branch.objects.get(pk=int(branch_id), is_reservable=True)
        except:
            field_errors['error_branch'] = "Please select a valid branch."
            is_valid = False

        # 驗證時間
        try:
            time_slot = datetime.strptime(time_str, '%H:%M').time()
        except:
            field_errors['error_time_slot'] = "Invalid time slot."
            is_valid = False

        # 驗證姓名
        if not name or len(name.strip()) < 2:
            field_errors['error_name'] = "Name must be at least 2 characters."
            is_valid = False

        # 驗證手機
        if not mobile or not mobile.isdigit() or len(mobile) != 10:
            field_errors['error_mobile'] = "Enter a valid 10-digit phone number."
            is_valid = False

        # 驗證email
        try:
            validate_email(email)
        except ValidationError:
            field_errors['error_email'] = "Enter a valid email address."
            is_valid = False

        # 再次確認時段是否仍可預約
        if is_valid:
            slots = get_time_slots(branch, date, guests)
            matched_slot = next((s for s in slots if s['time'] == time_slot), None)
            if not matched_slot or not matched_slot['available']:
                field_errors['error_time_slot'] = "This time slot is no longer available. Please select another."
                is_valid = False

        if is_valid:
            try:
                reservation_obj = Reservation.objects.create(
                    branch=branch,
                    date=date,
                    time_slot=time_slot,
                    guests=guests,
                    name=name.strip(),
                    mobile=mobile,
                    email=email.strip(),
                )

                # 寄送預約成功 email
                subject = 'Your Reservation at Pomodoro House'
                message = render_to_string('reservation/reservation_email.txt', {
                    'reservation': reservation_obj
                })
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [reservation_obj.email],
                    fail_silently=False,
                )    

                return redirect('reservation_confirmation', reservation_obj.id)
            except Exception as e:
                print("Reservation creation error:", e)
                error_message = "Unable to create reservation. Please try again."
        else:
            error_message = "Please correct the errors below."

        branch_availability = get_branch_availability(branches, date, guests) if 'date' in locals() else {}
        available_time_slots = get_time_slots(branch, date, guests) if 'date' in locals() and 'branch' in locals() else []

        return render(request, 'reservation/reservation.html', {
            'error_message': error_message,
            'today': today,
            'two_months_later': two_months_later,
            'branches': branches,
            'branch_availability': branch_availability,
            'available_time_slots': available_time_slots,
            'guest_range': range(1, 9),
            'selected_date': date if 'date' in locals() else None,
            'selected_branch_id': branch_id,
            'selected_guests': guests_str,
            'name': name,
            'mobile': mobile,
            'email': email,
            **field_errors,
        })

    else:
        selected_date_str = request.GET.get('date')
        selected_branch_id = request.GET.get('branch')
        selected_guests_str = request.GET.get('guests', '1')

        if not selected_date_str or not selected_branch_id:
            default_date = today.strftime('%Y-%m-%d')
            default_branch_id = str(branches.first().id) if branches.exists() else ''
            return redirect(f'/reservation/?date={default_date}&branch={default_branch_id}&guests={selected_guests_str}')

        try:
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
            if selected_date < today or selected_date > two_months_later:
                selected_date = today
        except (ValueError, TypeError):
            selected_date = today

        try:
            selected_guests = int(selected_guests_str)
        except ValueError:
            selected_guests = 1

        try:
            branch = get_object_or_404(Branch, pk=int(selected_branch_id), is_reservable=True)
            available_time_slots = get_time_slots(branch, selected_date, selected_guests)
            branch_availability = get_branch_availability(branches, selected_date, selected_guests)
        except Exception as e:
            print("GET request error:", e)
            available_time_slots = []
            branch_availability = {}

        return render(request, 'reservation/reservation.html', {
            'today': today,
            'two_months_later': two_months_later,
            'branches': branches,
            'branch_availability': branch_availability,
            'available_time_slots': available_time_slots,
            'guest_range': range(1, 9),
            'selected_date': selected_date,
            'selected_branch_id': selected_branch_id,
            'selected_guests': selected_guests,
            'name': full_name,
            'email': email,
        })

def reservation_confirmation(request, id):
    reservation = get_object_or_404(Reservation, pk=id)
    return render(request, 'reservation/reservation_confirmation.html', {'reservation': reservation})

@user_passes_test(lambda u: u.is_superuser)
def branch_schedule(request):
    branches = Branch.objects.filter(is_reservable=True).order_by('name')
    today = timezone.localdate()

    branch_id = request.GET.get('branch')
    range_option = request.GET.get('range', 'future_all')
    time_slot_filter = request.GET.get('time_slot', 'all')

    selected_branch = None
    if branch_id:
        if branch_id == 'all':
            selected_branch = None
        else:
            try:
                selected_branch = Branch.objects.get(pk=branch_id, is_reservable=True)
            except Branch.DoesNotExist:
                selected_branch = None

    qs = Reservation.objects.all()
    if selected_branch:
        qs = qs.filter(branch=selected_branch)

    if range_option == "all":
        pass
    elif range_option == "past_year":
        start = today - timedelta(days=365)
        qs = qs.filter(date__gte=start, date__lt=today)
    elif range_option == "past_week":
        start = today - timedelta(days=7)
        qs = qs.filter(date__gte=start, date__lt=today)
    elif range_option == "today":
        qs = qs.filter(date=today)
    elif range_option == "next_week":
        end = today + timedelta(days=7)
        qs = qs.filter(date__gte=today, date__lte=end)
    else:  
        qs = qs.filter(date__gte=today)

    if time_slot_filter != 'all':
        try:
            filtered_time = datetime.strptime(time_slot_filter, "%H:%M").time()
            qs = qs.filter(time_slot=filtered_time)
        except ValueError:
            pass

    time_slots = generate_time_slots()

    context = {
        'branches': branches,
        'selected_branch': selected_branch,
        'range': range_option,
        'time_slot_filter': time_slot_filter,
        'time_slots': time_slots,
        'reservations': qs.order_by('date', 'time_slot'),
        'total_reservations': qs.count(),
    }
    return render(request, 'admin/branch_schedule.html', context)

def generate_time_slots(start_time=time(11,0), end_time=time(22,30), interval_minutes=30):
    slots = []
    current = datetime.combine(datetime.today(), start_time)
    end = datetime.combine(datetime.today(), end_time)
    while current <= end:
        slots.append(current.time())
        current += timedelta(minutes=interval_minutes)
    return slots

def reservation_history(request):
    reservations = Reservation.objects.order_by("-created_at")
    return render(request, "reservation/reservation_history.html", {"reservations": reservations})

def reservation_detail(request, reservation_id):
    reservation = get_object_or_404(Reservation, pk=reservation_id)
    return render(request, "reservation/reservation_detail.html", {"reservation": reservation})