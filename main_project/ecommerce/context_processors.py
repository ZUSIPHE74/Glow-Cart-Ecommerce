from django.conf import settings

from . import cart
from .currency import CURRENCIES, current_currency, get_rate


def shop(request):
    """Cart count, display currency and seller details for every page."""
    code = current_currency(request)
    rate = get_rate(code)
    if rate is None:  # No rate yet: show rand rather than a wrong number
        code, rate = settings.BASE_CURRENCY, 1
    return {
        'cart_count': cart.item_count(request),
        'currency_code': code,
        'currency_rate': rate,
        'currencies': [(c, name) for c, (_, name) in CURRENCIES.items()],
        'payfast_sandbox': settings.PAYFAST_SANDBOX,
        'demo_accounts': settings.DEMO_ACCOUNTS,
        'seller': {
            'name': settings.SELLER_NAME,
            'email': settings.SELLER_EMAIL,
            'phone': settings.SELLER_PHONE,
            'address': settings.SELLER_ADDRESS,
        },
    }
