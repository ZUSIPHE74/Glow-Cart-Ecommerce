import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from django.contrib.auth.models import User, Group, Permission
from ecommerce.models import Store, Product, Review

def seed():
    # Create or get vendor group
    vendor_group, _ = Group.objects.get_or_create(name='Vendors')
    buyer_group, _ = Group.objects.get_or_create(name='Buyers')

    # Create a vendor user
    vendor_user, _ = User.objects.get_or_create(username='premium_vendor')
    vendor_user.set_password('premium123')
    vendor_user.is_active = True
    vendor_user.save()
    vendor_user.groups.add(vendor_group)

    # Create a store
    store, _ = Store.objects.get_or_create(
        name='Glow Tech Elite',
        owner=vendor_user,
        defaults={'description': 'The pinnacle of modern technology and luxury lifestyle gadgets.'}
    )

    # PREMIUM Products Data
    products_data = [
        {
            'name': 'Midnight Essence Watch',
            'description': 'A masterclass in horology. Features a sapphire crystal face, Swiss automatic movement, and a hand-stitched alligator leather strap.',
            'price': 1250.00,
            'stock_quantity': 10,
            'category': 'fashion',
            'brand': 'LuxeTime',
            'condition': 'new',
            'specifications': 'Case: 42mm Titanium, Movement: ETA 2824-2, Water Resistance: 100m',
            'image_url': 'https://images.unsplash.com/photo-1524592094714-0f0654e20314?q=80&w=1200&auto=format&fit=crop'
        },
        {
            'name': 'Sonic Pro Noise-Cancelling Headphones',
            'description': 'Industry-leading noise cancellation with spatial audio support. Experience studio-quality sound anywhere.',
            'price': 349.99,
            'stock_quantity': 45,
            'category': 'electronics',
            'brand': 'Sonic',
            'condition': 'new',
            'specifications': 'Bluetooth 5.3, 40-hour battery life, 40mm Dynamic Drivers',
            'image_url': 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?q=80&w=1200&auto=format&fit=crop'
        },
        {
            'name': 'Graphite Ultra Slim Laptop',
            'description': 'The ultimate productivity machine. Powered by the latest M-series chip with a stunning liquid retina display.',
            'price': 1899.00,
            'stock_quantity': 15,
            'category': 'electronics',
            'brand': 'Graphite',
            'condition': 'new',
            'specifications': 'RAM: 32GB, Storage: 1TB SSD, Screen: 14.2-inch Mini-LED',
            'image_url': 'https://images.unsplash.com/photo-1496181133206-80ce9b88a853?q=80&w=1200&auto=format&fit=crop'
        },
        {
            'name': 'Elysian Silk Scarf',
            'description': '100% pure Mulberry silk, hand-printed with exclusive botanical designs. A timeless accessory for every season.',
            'price': 120.00,
            'stock_quantity': 80,
            'category': 'fashion',
            'brand': 'Elysian',
            'condition': 'new',
            'specifications': 'Material: 100% Mulberry Silk, Dimensions: 90x90cm',
            'image_url': 'https://images.unsplash.com/photo-1606760227091-3dd870d97f1d?q=80&w=1200&auto=format&fit=crop'
        },
        {
            'name': 'Nebula Smart Camera X1',
            'description': 'Professional mirrorless camera in a compact body. 8K video recording and AI-powered autofocus.',
            'price': 2400.00,
            'stock_quantity': 8,
            'category': 'electronics',
            'brand': 'Nebula',
            'condition': 'new',
            'specifications': 'Sensor: 45MP Full Frame, Video: 8K/60fps, ISO: 100-51200',
            'image_url': 'https://images.unsplash.com/photo-1516035069371-29a1b244cc32?q=80&w=1200&auto=format&fit=crop'
        },
        {
            'name': 'Titanium Ridge Wallet',
            'description': 'Military-grade titanium cardholder with RFID blocking technology. Slim profile for the modern minimalist.',
            'price': 95.00,
            'stock_quantity': 150,
            'category': 'fashion',
            'brand': 'Ridge',
            'condition': 'new',
            'specifications': 'Material: Grade 5 Titanium, Capacity: 1-12 cards',
            'image_url': 'https://images.unsplash.com/photo-1627123424574-724758594e93?q=80&w=1200&auto=format&fit=crop'
        },
        {
            'name': 'Vertex Ergonomic Chair',
            'description': 'Designed for long hours of comfort. Features adjustable lumbar support, 4D armrests, and breathable mesh.',
            'price': 599.00,
            'stock_quantity': 20,
            'category': 'home',
            'brand': 'Vertex',
            'condition': 'new',
            'specifications': 'Weight Capacity: 300lbs, Reclining: 135 degrees',
            'image_url': 'https://images.unsplash.com/photo-1505797149-43b0069ec26b?q=80&w=1200&auto=format&fit=crop'
        },
        {
            'name': 'Vertex Ergonomic Office Chair',
            'description': 'Premium office chair with lumbar support and adjustable height. Perfect for long work sessions.',
            'price': 599.00,
            'stock_quantity': 20,
            'category': 'home',
            'brand': 'Vertex',
            'condition': 'new',
            'specifications': 'Weight Capacity: 300lbs, Reclining: 135 degrees',
            'image_url': 'https://images.unsplash.com/photo-1505797149-43b0069ec26b?q=80&w=1200&auto=format&fit=crop'
        }
    ]

    # Clear existing dummy products without store/images
    Product.objects.filter(store__isnull=True).delete()
    
    for p_data in products_data:
        Product.objects.update_or_create(
            name=p_data['name'],
            store=store,
            defaults={
                'description': p_data['description'],
                'price': p_data['price'],
                'stock_quantity': p_data['stock_quantity'],
                'category': p_data.get('category', 'other'),
                'brand': p_data.get('brand', ''),
                'condition': p_data.get('condition', 'new'),
                'specifications': p_data.get('specifications', ''),
                'image_url': p_data['image_url'],
                'is_available': True
            }
        )

    print(f"Database seeded with {len(products_data)} premium products.")

if __name__ == '__main__':
    seed()
