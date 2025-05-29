from django.core.validators import MinValueValidator
from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
import uuid



class Category(models.Model):

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"


class MenuItem(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=6, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="items"
    )
    image = models.ImageField(upload_to="menu_items/", blank=True, null=True)
    available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} (${self.price})"


class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)

    def __str__(self):
        return self.name


class Cart(models.Model):
    customer = models.OneToOneField(
        Customer, on_delete=models.CASCADE, null=True, blank=True
    )
    session_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart {self.id}"

    def total_price(self):
        return sum(item.subtotal() for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.menu_item.name}"

    def subtotal(self):
        return self.menu_item.price * self.quantity


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PREPARING = "preparing", "Preparing"
        READY = "ready", "Ready for Pickup"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="orders"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    special_instructions = models.TextField(blank=True)

    def __str__(self):
        return f"Order #{self.id} by {self.customer.name}"

    def total_price(self):
        return sum(item.subtotal() for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.menu_item.name}"

    def subtotal(self):
        return self.price * self.quantity

class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    mobile = models.CharField(max_length=20)
    message = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.email}"

class Branch(models.Model):
    REGION_CHOICES = [
        ("North", "Northern Region"),
        ("Central", "Central Region"),
        ("South", "Southern Region"),
    ]
    name = models.CharField(max_length=100)
    region = models.CharField(
        max_length=10,
        choices=REGION_CHOICES,
        default="North"
    )
    address = models.TextField()
    phone = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)

    map_embed_html = models.TextField(blank=True)

    def __str__(self):
        return self.name


class BranchTimeSlotCapacity(models.Model):
    WEEKDAYS = (
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    )

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    weekday = models.IntegerField(choices=WEEKDAYS)  
    time_slot = models.TimeField()
    max_capacity = models.PositiveIntegerField()
    available = models.BooleanField(default=True) # 是否可供預約
    
    class Meta:
        unique_together = ('branch', 'weekday', 'time_slot')

    def __str__(self):
        return f"{self.branch.name} - {self.get_weekday_display()} {self.time_slot.strftime('%H:%M')}"


class Reservation(models.Model):

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    date = models.DateField()
    time_slot = models.TimeField()
    guests = models.PositiveIntegerField()
    name = models.CharField(max_length=100)
    mobile = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.guests > 8:
            raise ValidationError("A single reservation cannot exceed 8 guests.")

    def __str__(self):
        return f"{self.name} - {self.date} {self.time_slot}"