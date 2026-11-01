from django.contrib import admin

from .models import Notification, Order, OrderItem, Payout, Product, Review, Store


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'product_name', 'store', 'quantity', 'price_at_time', 'commission_amount']
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'buyer', 'order_date', 'status', 'total_amount', 'paid_at', 'payment_reference']
    list_filter = ['status', 'paid_at']
    search_fields = ['id', 'buyer__username', 'buyer__email', 'payment_reference']
    readonly_fields = ['buyer', 'order_date', 'total_amount', 'paid_at', 'payment_reference']
    inlines = [OrderItemInline]


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    """Record each bank transfer to a vendor; it comes off their balance."""
    list_display = ['store', 'amount', 'paid_on', 'reference']
    list_filter = ['store']
    search_fields = ['store__name', 'reference']


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'is_active', 'created_at']
    search_fields = ['name', 'owner__username']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'store', 'category', 'price', 'stock_quantity', 'is_available']
    list_filter = ['category', 'is_available', 'store']
    search_fields = ['name', 'brand']


admin.site.register(Review)
admin.site.register(Notification)
