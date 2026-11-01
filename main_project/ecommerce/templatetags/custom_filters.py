from decimal import Decimal

from django import template

from ecommerce.currency import format_money

register = template.Library()


@register.simple_tag(takes_context=True)
def price(context, amount):
    """A rand amount in the shopper's display currency, e.g. {% price product.price %}."""
    code = context.get('currency_code', 'ZAR')
    rate = context.get('currency_rate', 1)
    return format_money(Decimal(amount or 0) * Decimal(rate), code)


@register.filter
def rand(amount):
    """A rand amount as charged and paid out, e.g. R1,250.00."""
    return format_money(Decimal(amount or 0), 'ZAR')


@register.filter
def multiply(value, arg):
    try:
        return value * arg
    except (ValueError, TypeError):
        return 0
@register.filter
def unread_count(user):
    if user.is_authenticated:
        return user.notifications.filter(is_read=False).count()
    return 0
