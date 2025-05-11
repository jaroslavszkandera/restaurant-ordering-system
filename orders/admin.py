from django.contrib import admin
from .models import Category, MenuItem, Customer, Cart, CartItem, Order, OrderItem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "available")
    list_filter = ("category", "available")
    search_fields = ("name", "description")
    list_editable = ("price", "available")


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "email", "user")
    search_fields = ("name", "phone", "email")
    list_filter = ("user__is_active",)


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "session_id",
        "created_at",
        "items_count",
        "total",
    )
    inlines = [CartItemInline]
    search_fields = ("customer__name", "session_id")

    def items_count(self, obj):
        return obj.items.count()

    def total(self, obj):
        return f"${obj.total_price()}"


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("menu_item", "quantity", "price", "subtotal")

    def subtotal(self, obj):
        return f"${obj.subtotal()}"

    subtotal.short_description = "Subtotal"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "status", "created_at", "items_count", "total")
    list_filter = ("status", "created_at")
    search_fields = ("customer__name", "customer__phone")
    inlines = [OrderItemInline]
    readonly_fields = ("created_at",)
    list_editable = ("status",)

    def items_count(self, obj):
        return obj.items.count()

    def total(self, obj):
        return f"${obj.total_price()}"
