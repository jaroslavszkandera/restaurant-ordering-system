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
from .models import ContactMessage
from .models import Branch, Reservation
from datetime import timedelta, time, datetime
from django.utils import timezone
from django.db.models import Sum
from django.contrib.auth.decorators import user_passes_test
from collections import defaultdict
from .models import Branch, Reservation, BranchTimeSlotCapacity
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
        form = ContactForm()
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

    # 抓出該分店該星期幾所有 slot 設定
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
                continue  # 沒設定就略過

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

        # 抓出這個分店當天所有有定義的時段上限
        time_slots = BranchTimeSlotCapacity.objects.filter(
            branch=branch,
            weekday=weekday
        )

        for slot in time_slots:
            # 查詢這個分店在這個時段、這天的總訂位人數
            reserved = Reservation.objects.filter(
                branch=branch,
                date=date,
                time_slot=slot.time_slot
            ).aggregate(total=Sum('guests'))['total'] or 0

            # 如果沒設定 max_capacity 就預設為 20
            max_capacity = slot.max_capacity if slot.max_capacity is not None else 20

            # 計算是否足夠容納這次預約
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
    branches = Branch.objects.filter(is_active=True)

    if request.method == 'POST':
        # 取得表單資料
        branch_id = request.POST.get('branch')
        date_str = request.POST.get('date')
        time_str = request.POST.get('time_slot')
        guests_str = request.POST.get('guests')
        name = request.POST.get('name')
        mobile = request.POST.get('mobile')

        # 準備錯誤訊息
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
            branch = Branch.objects.get(pk=int(branch_id), is_active=True)
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

        # **後端再次驗證時段是否還有剩餘容量**
        if is_valid:
            # 取得該分店該天該時段的時段列表
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
                )
                return redirect('reservation_confirmation', reservation_obj.id)
            except Exception as e:
                print("Reservation creation error:", e)
                error_message = "Unable to create reservation. Please try again."
        else:
            error_message = "Please correct the errors below."

        # 預設錯誤後保留值
        branch_availability = get_branch_availability(branches, date, guests) if 'date' in locals() else {}
        available_time_slots = get_time_slots(branch, date, guests) if 'date' in locals() and 'branch' in locals() else []

        context = {
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
            **field_errors,
        }

        return render(request, 'reservation/reservation.html', context)

    else:  # GET 請求處理
        selected_date_str = request.GET.get('date')
        selected_branch_id = request.GET.get('branch')
        selected_guests_str = request.GET.get('guests', '1')

        # 若缺少必要參數則重導向附帶預設參數
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
            branch = get_object_or_404(Branch, pk=int(selected_branch_id), is_active=True)
            available_time_slots = get_time_slots(branch, selected_date, selected_guests)
            branch_availability = get_branch_availability(branches, selected_date, selected_guests)
        except Exception as e:
            print("GET request error:", e)
            available_time_slots = []
            branch_availability = {}

        context = {
            'today': today,
            'two_months_later': two_months_later,
            'branches': branches,
            'branch_availability': branch_availability,
            'available_time_slots': available_time_slots,
            'guest_range': range(1, 9),
            'selected_date': selected_date,
            'selected_branch_id': selected_branch_id,
            'selected_guests': selected_guests,
        }

        return render(request, 'reservation/reservation.html', context)


def reservation_confirmation(request, id):
    reservation = get_object_or_404(Reservation, pk=id)
    return render(request, 'reservation/reservation_confirmation.html', {'reservation': reservation})

@user_passes_test(lambda u: u.is_active and u.is_superuser)
def branch_schedule(request):
    branches = Branch.objects.filter(is_active=True).order_by('name')
    today = timezone.localdate()

    # 取得 GET 參數
    branch_id = request.GET.get('branch')
    range_option = request.GET.get('range', 'future_all')
    time_slot_filter = request.GET.get('time_slot', 'all')

    # 取得選擇的分店物件或 None 表示全部
    selected_branch = None
    if branch_id:
        if branch_id == 'all':
            selected_branch = None
        else:
            try:
                selected_branch = Branch.objects.get(pk=branch_id, is_active=True)
            except Branch.DoesNotExist:
                selected_branch = None

    # 取得預約 queryset 並過濾分店
    qs = Reservation.objects.all()
    if selected_branch:
        qs = qs.filter(branch=selected_branch)

    # 時間範圍篩選
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
    else:  # future_all or default
        qs = qs.filter(date__gte=today)

    # 時段過濾（time_slot 是 TimeField 或 CharField，視你的模型而定）
    if time_slot_filter != 'all':
        try:
            # 如果 time_slot 是 TimeField，要轉成 time 物件過濾
            filtered_time = datetime.strptime(time_slot_filter, "%H:%M").time()
            qs = qs.filter(time_slot=filtered_time)
        except ValueError:
            # 如果格式錯誤，忽略時段過濾
            pass

    # 產生固定半小時時段列表，給前端下拉選單用
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