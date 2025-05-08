from django.shortcuts import render, get_object_or_404, redirect
from .forms import OrderForm
from .models import Customer, Order


def index(request):
    orders = Order.objects.all().order_by("-created_at")
    return render(request, "orders/index.html", {"orders": orders})


def order_menu(request):
    if request.method == "POST":
        form = OrderForm(request.POST)
        if form.is_valid():
            # Create or retrieve the customer
            name = form.cleaned_data["name"]
            phone = form.cleaned_data["phone"]
            customer, created = Customer.objects.get_or_create(name=name, phone=phone)

            # Create the order
            order = Order.objects.create(customer=customer)
            order.items.set(form.cleaned_data["items"])
            order.save()

            return render(request, "orders/order_success.html", {"order": order})
        else:
            # Form was submitted but not valid
            return render(request, "orders/order_menu.html", {"form": form})
    else:
        # GET request: show blank form
        form = OrderForm()
        return render(request, "orders/order_menu.html", {"form": form})


def order_detail(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    return render(request, "orders/order_detail.html", {"order": order})
