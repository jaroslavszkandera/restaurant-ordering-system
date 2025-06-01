from django.core.validators import MinValueValidator
from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError

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
    is_featured = models.BooleanField(default=False)

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
        Customer, 
        on_delete=models.CASCADE, 
        related_name="orders",
        verbose_name="Customer"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At",
        help_text="Timestamp when the order was created"
    )
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.PENDING,
        verbose_name="Status"
    )
    special_instructions = models.TextField(
        blank=True,
        verbose_name="Special Instructions",
        help_text="Optional special instructions for the order"
    )
    pickup_branch = models.ForeignKey(
        "orders.Branch",
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name="Pickup Branch",
        help_text="Branch where the order will be picked up"
    )
    pickup_date = models.DateField(
        verbose_name="Pickup Date",
        help_text="The date for order pickup"
    )
    time_slot = models.TimeField(
        verbose_name="Pickup Time Slot",
        help_text="The time slot for order pickup"
    )

    def clean(self):
        """Validate pickup date and time slot."""
        if not self.pickup_date or not self.time_slot:
            return  
        
        pickup_datetime = timezone.make_aware(
            timezone.datetime.combine(self.pickup_date, self.time_slot),
            timezone.get_current_timezone()
        )
        now = timezone.now()

        if pickup_datetime < now:
            raise ValidationError("Pickup date and time must be in the future.")

        slot_exists = BranchTimeSlotCapacity.objects.filter(
            branch=self.pickup_branch,
            weekday=self.pickup_date.weekday(),
            time_slot=self.time_slot,
            is_orderable=True
        ).exists()
        if not slot_exists:
            raise ValidationError(
                "Selected time slot is not available or not orderable for this branch."
            )

        end_time = now + timedelta(hours=24)
        if pickup_datetime > end_time:
            raise ValidationError("Pickup time must be within 24 hours from now.")
        
        order_count = Order.objects.filter(
            pickup_branch=self.pickup_branch,
            pickup_date=self.pickup_date,
            time_slot=self.time_slot
        ).exclude(id=self.id).count()  
        slot = BranchTimeSlotCapacity.objects.filter(
            branch=self.pickup_branch,
            weekday=self.pickup_date.weekday(),
            time_slot=self.time_slot
        ).first()
        if slot and order_count >= slot.max_orderable:
            raise ValidationError("Selected time slot is full.")

    def __str__(self):
        return f"Order #{self.id} by {self.customer.name}"

    def total_price(self):
        return sum(item.subtotal() for item in self.items.all())

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ['-created_at']


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
    
    is_reservable = models.BooleanField(default=True, verbose_name="Reservable")
    is_orderable = models.BooleanField(default=False, verbose_name="Orderable")

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
    
    is_orderable = models.BooleanField(default=True, verbose_name="Orderable")
    max_orderable = models.PositiveIntegerField(default=10, verbose_name="Max Orderable")
    
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
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.guests > 8:
            raise ValidationError("A single reservation cannot exceed 8 guests.")

    def __str__(self):
        return f"{self.name} - {self.date} {self.time_slot}"