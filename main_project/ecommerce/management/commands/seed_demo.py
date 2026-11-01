"""Sets up the groups, demo accounts and a starter catalogue. Safe to run on every
deploy: products are only created if missing, so vendors' edits are kept."""

from decimal import Decimal

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from ecommerce.groups import ensure_group
from ecommerce.models import Product, Profile, Store

DEMO_PASSWORD = 'GlowDemo2026!'
DEMO_LOGINS = {'demo_buyer', 'demo_vendor'}
IMG = 'https://images.unsplash.com/photo-{}?q=80&w=1200&auto=format&fit=crop'

STORES = [
    {
        'owner': 'demo_vendor',
        'name': 'Glow Tech Elite',
        'description': 'Modern technology and lifestyle gadgets, curated for everyday use.',
        'products': [
            ('Sonic Pro Noise-Cancelling Headphones', 'electronics', 'Sonic', '6499.00', 45,
             'Wireless over-ear headphones with active noise cancellation and 40-hour battery life.',
             'Bluetooth 5.3, 40-hour battery, 40mm dynamic drivers', '1505740420928-5e560c06d30e'),
            ('Graphite Ultra Slim Laptop', 'electronics', 'Graphite', '32999.00', 15,
             'A light, fast laptop with a bright 14-inch display for work and study.',
             '32GB RAM, 1TB SSD, 14.2-inch display', '1496181133206-80ce9b88a853'),
            ('Nebula Mirrorless Camera X1', 'electronics', 'Nebula', '41999.00', 8,
             'Full-frame mirrorless camera in a compact body with 8K video.',
             '45MP full-frame sensor, 8K/60fps video', '1516035069371-29a1b244cc32'),
            ('Pulse Minimal Smartwatch (2-pack)', 'electronics', 'Pulse', '2899.00', 30,
             'Two clean, lightweight smartwatches that track steps, sleep and heart rate.',
             'Heart-rate sensor, 7-day battery, water resistant to 50m', '1523275335684-37898b6baf30'),
        ],
    },
    {
        'owner': 'urban_thread',
        'name': 'Urban Thread',
        'description': 'Wardrobe staples and accessories made to last.',
        'products': [
            ('Midnight Essence Watch', 'fashion', 'LuxeTime', '21999.00', 10,
             'Automatic watch with a sapphire crystal face and a hand-stitched leather strap.',
             '42mm titanium case, automatic movement, 100m water resistance', '1524592094714-0f0654e20314'),
            ('Classic Leather Biker Jacket', 'fashion', 'Urban Thread', '3499.00', 25,
             'Soft genuine leather jacket with an asymmetric zip and quilted lining.',
             '100% genuine leather, sizes S to XXL', '1551028719-00167b16eac5'),
            ('Elysian Silk Scarf', 'fashion', 'Elysian', '1299.00', 80,
             'Pure mulberry silk scarf with a hand-printed botanical design.',
             '100% mulberry silk, 90 x 90 cm', '1606760227091-3dd870d97f1d'),
            ('Titanium Ridge Wallet', 'fashion', 'Ridge', '1199.00', 150,
             'Slim titanium card holder with RFID blocking.',
             'Grade 5 titanium, holds 1 to 12 cards', '1627123424574-724758594e93'),
        ],
    },
    {
        'owner': 'nest_and_bloom',
        'name': 'Nest & Bloom',
        'description': 'Home, wellness and fitness essentials.',
        'products': [
            ('Vertex Ergonomic Chair', 'home', 'Vertex', '8999.00', 20,
             'Office chair with adjustable lumbar support, 4D armrests and breathable mesh.',
             'Supports 135 kg, reclines to 135 degrees', '1505797149-43b0069ec26b'),
            ('Mustard Accent Armchair', 'home', 'Nest & Bloom', '4599.00', 12,
             'A cheerful mid-century armchair that brightens any living room.',
             'Solid wood legs, velvet upholstery, 72 x 78 x 80 cm', '1586023492125-27b2c045efd7'),
            ('Nordic Pendant Lamp', 'home', 'Nest & Bloom', '899.00', 40,
             'Matte white pendant light with a soft, glare-free glow.',
             'E27 fitting, 1.5 m adjustable cable, bulb not included', '1513506003901-1e6a229e2d15'),
            ('Botanical Skincare Set', 'beauty', 'Bloom Botanics', '749.00', 60,
             'Cleanser, serum and moisturiser made with plant extracts.',
             'Vegan, cruelty-free, suitable for all skin types', '1612817288484-6f916006741a'),
            ('Hex Dumbbell Set (2 x 10 kg)', 'sports', 'Nest Fit', '1299.00', 18,
             'Rubber-coated hex dumbbells that won\'t roll or mark floors.',
             '2 x 10 kg, knurled chrome handles', '1576678927484-cc907957088c'),
            ('Insulated Steel Water Bottle', 'sports', 'Nest Fit', '349.00', 120,
             'Keeps drinks cold for 24 hours or hot for 12.',
             '750 ml, double-wall stainless steel, BPA-free', '1602143407151-7111542de6e8'),
        ],
    },
]


class Command(BaseCommand):
    help = 'Create groups, demo accounts (when DEMO_ACCOUNTS is on) and the starter catalogue.'

    def handle(self, *args, **options):
        vendors = ensure_group('Vendors')
        buyers = ensure_group('Buyers')

        self._user('demo_buyer', 'Demo', 'Buyer', buyers, public=True)
        self._user('demo_vendor', 'Demo', 'Vendor', vendors, public=True)
        created = 0
        for store_data in STORES:
            owner = self._user(store_data['owner'], store_data['name'], '', vendors,
                               public=store_data['owner'] in DEMO_LOGINS)
            store, _ = Store.objects.get_or_create(
                owner=owner, name=store_data['name'],
                defaults={'description': store_data['description']},
            )
            for name, category, brand, price, stock, description, specs, photo in store_data['products']:
                _, was_created = Product.objects.get_or_create(
                    store=store, name=name,
                    defaults={
                        'category': category, 'brand': brand, 'price': Decimal(price),
                        'stock_quantity': stock, 'description': description,
                        'specifications': specs, 'condition': 'new', 'image_url': IMG.format(photo),
                    },
                )
                created += was_created
        state = 'enabled' if settings.DEMO_ACCOUNTS else 'disabled'
        self.stdout.write(f'Catalogue ready ({created} new products). Demo accounts {state}.')

    def _user(self, username, first_name, last_name, group, public):
        """public: a published demo login, active only while DEMO_ACCOUNTS is on.
        Otherwise a catalogue owner nobody can sign in as."""
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={'first_name': first_name, 'last_name': last_name,
                      'email': f'{username}@glowcart.example'},
        )
        if public:
            user.set_password(DEMO_PASSWORD)
            user.is_active = settings.DEMO_ACCOUNTS
        else:
            user.set_unusable_password()
        user.save()
        user.groups.add(group)
        Profile.objects.get_or_create(
            user=user, defaults={'security_question': 'first_pet', 'security_answer': make_password(None)}
        )
        return user
