from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from ecommerce.models import Store, Product, Review

class Command(BaseCommand):
    help = 'Sets up user groups and permissions'

    def handle(self, *args, **options):
        # Create Vendors group
        vendors_group, created = Group.objects.get_or_create(name='Vendors')
        
        # Get permissions for vendors
        store_content_type = ContentType.objects.get_for_model(Store)
        product_content_type = ContentType.objects.get_for_model(Product)
        
        vendor_permissions = Permission.objects.filter(
            content_type__in=[store_content_type, product_content_type],
            codename__in=['add_store', 'change_store', 'delete_store',
                         'add_product', 'change_product', 'delete_product', 'view_product']
        )
        
        vendors_group.permissions.set(vendor_permissions)
        
        # Create Buyers group
        buyers_group, created = Group.objects.get_or_create(name='Buyers')
        
        # Get permissions for buyers
        review_content_type = ContentType.objects.get_for_model(Review)
        
        buyer_permissions = Permission.objects.filter(
            content_type__in=[product_content_type, review_content_type],
            codename__in=['view_product', 'add_review']
        )
        
        buyers_group.permissions.set(buyer_permissions)
        
        self.stdout.write(self.style.SUCCESS('Successfully set up groups and permissions'))