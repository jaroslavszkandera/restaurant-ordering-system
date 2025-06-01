from django.contrib import admin
from .models import Category, MenuItem, Customer, Cart, CartItem, OrderItem
from .models import ContactMessage
from .models import  Reservation
from . import models
from django.urls import reverse
from django.utils.html import format_html
from .models import BranchTimeSlotCapacity
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "user_link_display")
    search_fields = ("name", "email", "phone", "user__username")
    list_filter = (("user", admin.RelatedOnlyFieldListFilter),)
    readonly_fields = ("user_link_display",)

    def user_link_display(self, obj):
        if obj.user:
            link = reverse("admin:auth_user_change", args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', link, obj.user.username)
        return "N/A (Guest Customer)"

    user_link_display.short_description = "Associated User"


class CustomerInline(admin.StackedInline):
    model = Customer
    can_delete = False
    verbose_name_plural = "Customer Profile"
    fk_name = "user"
    fields = ("name", "phone", "email")
    extra = 0


class UserAdmin(BaseUserAdmin):
    inlines = (CustomerInline,)
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "customer_name_display",
    )
    list_select_related = ("customer",)

    def customer_name_display(self, instance):
        if hasattr(instance, "customer") and instance.customer:
            return instance.customer.name
        return "No Customer Profile"

    customer_name_display.short_description = "Customer Name (Profile)"


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "available", "image_thumbnail","is_featured")
    list_filter = ("category", "available")
    search_fields = ("name", "description", "category__name")
    list_editable = ("price", "available", "is_featured")

    def image_thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px;" />',
                obj.image.url,
            )
        return "No Image"

    image_thumbnail.short_description = "Image"


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ("menu_item",)
    fields = ("menu_item_link", "quantity", "price", "subtotal_display")
    readonly_fields = (
        "menu_item_link",
        "price",
        "subtotal_display",
    )
    extra = 0

    def menu_item_link(self, obj):
        if obj.menu_item:
            link = reverse("admin:orders_menuitem_change", args=[obj.menu_item.id])
            return format_html('<a href="{}">{}</a>', link, obj.menu_item.name)
        return "N/A"

    menu_item_link.short_description = "Menu Item"

    def subtotal_display(self, obj):
        return f"${obj.subtotal()}"

    subtotal_display.short_description = "Subtotal"


@admin.register(models.Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer_link_display",
        "pickup_branch", 
        "status",
        "created_at",
        "total_price_display",
    )
    list_editable = ("status",)
    list_filter = (
        "status",
        "created_at",
        ("customer", admin.RelatedOnlyFieldListFilter),
    )
    search_fields = (
        "id",
        "customer__name",
        "customer__email",
        "items__menu_item__name",
    )
    date_hierarchy = "created_at"
    inlines = [OrderItemInline]
    readonly_fields = (
        "id",
        "created_at",
        "customer_link_display",
        "total_price_display",
        "customer_contact_info",
    )
    fieldsets = (
        (
            "Order Information",
            {
                "fields": (
                    "id",
                    "customer_link_display",
                    "pickup_branch",
                    "status",
                    "created_at",
                    "customer_contact_info",
                )
            },
        ),
        ("Order Details", {"fields": ("special_instructions", "total_price_display")}),
    )

    def customer_link_display(self, obj):
        if obj.customer:
            link = reverse("admin:orders_customer_change", args=[obj.customer.id])
            return format_html('<a href="{}">{}</a>', link, obj.customer.name)
        return "N/A"

    customer_link_display.short_description = "Customer"
    customer_link_display.admin_order_field = "customer__name"

    def customer_contact_info(self, obj):
        if obj.customer:
            return format_html(
                "<b>Email:</b> {}<br><b>Phone:</b> {}",
                obj.customer.email or "N/A",
                obj.customer.phone or "N/A",
            )
        return "N/A"

    customer_contact_info.short_description = "Customer Contact"

    def total_price_display(self, obj):
        return f"${obj.total_price()}"

    total_price_display.short_description = "Total Price"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("customer", "customer__user")
            .prefetch_related("items__menu_item")
        )

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "customer_display", "session_id", "created_at", "total_price")
    readonly_fields = ("created_at", "total_price")
    search_fields = ("customer__name", "session_id")

    def customer_display(self, obj):
        return obj.customer.name if obj.customer else "Guest Cart"

    customer_display.short_description = "Cart Owner"


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = (
        "cart_id_display",
        "menu_item_name_display",
        "quantity",
        "subtotal_display",
    )
    readonly_fields = ("subtotal_display",)
    list_select_related = ("cart", "menu_item")

    def cart_id_display(self, obj):
        return obj.cart.id

    cart_id_display.short_description = "Cart ID"

    def menu_item_name_display(self, obj):
        return obj.menu_item.name

    menu_item_name_display.short_description = "Menu Item"

    def subtotal_display(self, obj):
        return obj.subtotal()

    subtotal_display.short_description = "Subtotal"

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'mobile', 'submitted_at')
    search_fields = ('name', 'email', 'message')

class BranchTimeSlotCapacityInline(admin.TabularInline):
    model = models.BranchTimeSlotCapacity
    extra = 0  
    fields = ('weekday', 'time_slot', 'max_capacity', 'available', 'is_orderable', 'max_orderable')
    ordering = ('weekday', 'time_slot')
    verbose_name = "Time Slot Capacity"
    verbose_name_plural = "Per-Time Slot Capacity"

@admin.register(models.Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_reservable', 'is_orderable', 'schedule')
    list_editable = ('is_reservable', 'is_orderable')
    inlines = [BranchTimeSlotCapacityInline]

    def schedule(self, obj):
        url = reverse('branch_schedule')
        return format_html('<a href="{}" target="_blank" rel="noopener noreferrer">View</a>', url)

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("id","name", "mobile", 'email', "branch", "date", "time_slot", "guests")
    list_filter = ("branch", "date")