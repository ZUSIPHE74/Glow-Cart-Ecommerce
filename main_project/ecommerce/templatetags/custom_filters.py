from django import template

register = template.Library()

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
