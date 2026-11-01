"""The Buyers and Vendors groups and what each may do."""

from django.contrib.auth.models import Group, Permission

GROUP_PERMISSIONS = {
    'Vendors': ['add_store', 'change_store', 'delete_store', 'view_store',
                'add_product', 'change_product', 'delete_product', 'view_product'],
    'Buyers': ['view_product'],
}


def ensure_group(name):
    """The named group with its permissions, created if missing."""
    group, _ = Group.objects.get_or_create(name=name)
    if group.permissions.count() == 0:
        group.permissions.set(Permission.objects.filter(
            content_type__app_label='ecommerce', codename__in=GROUP_PERMISSIONS[name]
        ))
    return group
