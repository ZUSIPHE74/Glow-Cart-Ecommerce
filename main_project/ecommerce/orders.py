"""Order lifecycle: place (reserving stock), mark paid, cancel (returning stock).
Each step runs in one database transaction, so a failure never leaves stock or
orders half-changed."""

from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Notification, Order, OrderItem, Product


class OutOfStock(Exception):
    def __init__(self, product):
        super().__init__(product.name)
        self.product = product


def commission_for(line_total):
    rate = Decimal(str(settings.MARKETPLACE_COMMISSION_PERCENT)) / 100
    return (line_total * rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


@transaction.atomic
def place_order(buyer, quantities, shipping_address):
    """Creates an unpaid order for {product_id: quantity}, reserving the stock.
    Raises OutOfStock (changing nothing) if any product can't be supplied."""
    products = Product.objects.select_for_update().in_bulk(list(quantities))
    order = Order.objects.create(buyer=buyer, shipping_address=shipping_address, status='pending')
    total = Decimal('0')
    for product_id, quantity in quantities.items():
        product = products.get(product_id)
        if product is None:
            continue
        if not product.is_available or quantity > product.stock_quantity:
            raise OutOfStock(product)
        line_total = product.price * quantity
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            store=product.store,
            quantity=quantity,
            price_at_time=product.price,
            commission_amount=commission_for(line_total),
        )
        product.stock_quantity -= quantity
        product.save()
        total += line_total
    if total == 0:
        raise ValueError('The order has no purchasable items.')
    order.total_amount = total
    order.save(update_fields=['total_amount'])
    return order


@transaction.atomic
def mark_paid(order_id, payment_reference):
    """Records a confirmed payment and tells the buyer and vendors. Safe to call
    twice (PayFast may resend an ITN). Returns False if the order was cancelled."""
    order = Order.objects.select_for_update().get(id=order_id)
    if order.is_paid:
        return True
    if order.status == 'cancelled':
        return False
    order.paid_at = timezone.now()
    order.payment_reference = payment_reference
    order.status = 'processing'
    order.save(update_fields=['paid_at', 'payment_reference', 'status'])

    Notification.objects.create(
        user=order.buyer,
        title='Payment received',
        message=f'Thank you! Payment for order #{order.id} (R{order.total_amount}) was received. '
                'You can download your invoice below.',
        order=order,
    )
    owners = {item.store.owner for item in order.items.select_related('store__owner') if item.store}
    for owner in owners:
        Notification.objects.create(
            user=owner,
            title='New paid order',
            message=f'Order #{order.id} has been paid. Please prepare it for shipping.',
            order=order,
        )
    return True


@transaction.atomic
def cancel_unpaid(order_id):
    """Cancels an unpaid order and returns its stock. Paid orders are left alone."""
    order = Order.objects.select_for_update().get(id=order_id)
    if order.is_paid or order.status == 'cancelled':
        return False
    for item in order.items.select_related('product'):
        if item.product_id:
            product = Product.objects.select_for_update().get(id=item.product_id)
            product.stock_quantity += item.quantity
            product.save()
    order.status = 'cancelled'
    order.save(update_fields=['status'])
    return True


def release_stale_orders():
    """Cancels unpaid orders older than the timeout, freeing their stock."""
    cutoff = timezone.now() - timedelta(minutes=settings.UNPAID_ORDER_TIMEOUT_MINUTES)
    stale = Order.objects.filter(status='pending', paid_at__isnull=True, order_date__lt=cutoff)
    for order_id in stale.values_list('id', flat=True):
        cancel_unpaid(order_id)
