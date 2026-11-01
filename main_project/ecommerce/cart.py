"""The shopping cart: kept in the session for visitors and in the database for
signed-in shoppers, so it survives logout, closed browsers and other devices."""

from .models import CartItem, Product

SESSION_KEY = 'cart'


def _session_cart(request):
    return request.session.get(SESSION_KEY, {})


def get_quantities(request):
    """{product_id: quantity} for the current shopper."""
    if request.user.is_authenticated:
        return dict(request.user.cart_items.values_list('product_id', 'quantity'))
    return {int(pid): data.get('quantity', 1) for pid, data in _session_cart(request).items()}


def item_count(request):
    return sum(get_quantities(request).values())


def get_lines(request):
    """Cart lines with their products. Products no longer for sale are dropped."""
    quantities = get_quantities(request)
    products = Product.objects.filter(id__in=quantities, is_available=True).select_related('store')
    lines = []
    for product in products:
        quantity = quantities[product.id]
        lines.append({'product': product, 'quantity': quantity, 'subtotal': product.price * quantity})
    return lines


def set_quantity(request, product, quantity):
    """Sets a line's quantity; zero or less removes it."""
    if request.user.is_authenticated:
        if quantity <= 0:
            CartItem.objects.filter(user=request.user, product=product).delete()
        else:
            CartItem.objects.update_or_create(
                user=request.user, product=product, defaults={'quantity': quantity}
            )
        return
    cart = request.session.setdefault(SESSION_KEY, {})
    if quantity <= 0:
        cart.pop(str(product.id), None)
    else:
        cart[str(product.id)] = {'quantity': quantity}
    request.session.modified = True


def clear(request):
    if request.user.is_authenticated:
        request.user.cart_items.all().delete()
    request.session.pop(SESSION_KEY, None)


def merge_session_into_user(request, user):
    """Called at login/registration: moves the visitor's cart onto the account,
    adding quantities (capped at stock) to anything already saved there."""
    session_cart = _session_cart(request)
    if not session_cart:
        return
    products = Product.objects.in_bulk([int(pid) for pid in session_cart])
    for pid, data in session_cart.items():
        product = products.get(int(pid))
        if not product:
            continue
        item, _ = CartItem.objects.get_or_create(user=user, product=product, defaults={'quantity': 0})
        item.quantity = min(item.quantity + data.get('quantity', 1), max(product.stock_quantity, 1))
        item.save()
    request.session.pop(SESSION_KEY, None)
