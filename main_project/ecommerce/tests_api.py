import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import Store, Product, Review

class APITestCase(TestCase):
    def setUp(self):
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        
        self.client = Client()
        self.vendor = User.objects.create_user(username='vendor1', password='password123')
        
        # Give vendor add_store permission
        content_type = ContentType.objects.get_for_model(Store)
        permission, _ = Permission.objects.get_or_create(
            codename='add_store',
            content_type=content_type,
        )
        self.vendor.user_permissions.add(permission)
        
        self.buyer = User.objects.create_user(username='buyer1', password='password123')
        
    def test_create_store(self):
        self.client.login(username='vendor1', password='password123')
        response = self.client.post('/api/v1/stores/', {
            'name': 'Test Store',
            'description': 'A test store'
        }, content_type='application/json')
        
        if response.status_code != 201:
            print("CREATE STORE FAILED:", response.status_code, response.content)
        self.assertEqual(response.status_code, 201)
        
    def test_create_product(self):
        self.client.login(username='vendor1', password='password123')
        store = Store.objects.create(name='Test Store 2', description='Test', owner=self.vendor)
        
        response = self.client.post('/api/v1/products/', {
            'name': 'Test Product',
            'description': 'Test desc',
            'price': '10.00',
            'stock_quantity': 5,
            'store': store.id
        }, content_type='application/json')
        
        if response.status_code != 201:
            print("CREATE PRODUCT FAILED:", response.status_code, response.content)
        self.assertEqual(response.status_code, 201)
        
    def test_get_stores(self):
        Store.objects.create(name='Test Store 3', description='Test', owner=self.vendor)
        response = self.client.get(f'/api/v1/stores/?vendor_id={self.vendor.id}')
        if response.status_code != 200:
            print("GET STORES FAILED:", response.status_code, response.content)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data), 1)

    def test_get_products(self):
        store = Store.objects.create(name='Test Store 4', description='Test', owner=self.vendor)
        Product.objects.create(name='Prod', description='Desc', price=10, stock_quantity=1, store=store)
        response = self.client.get(f'/api/v1/products/?store_id={store.id}')
        if response.status_code != 200:
            print("GET PRODUCTS FAILED:", response.status_code, response.content)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data), 1)
        
    def test_get_reviews(self):
        store = Store.objects.create(name='Test Store 5', description='Test', owner=self.vendor)
        product = Product.objects.create(name='Prod', description='Desc', price=10, stock_quantity=1, store=store)
        Review.objects.create(product=product, user=self.buyer, rating=5, comment='Great')
        response = self.client.get(f'/api/v1/reviews/?product_id={product.id}')
        if response.status_code != 200:
            print("GET REVIEWS FAILED:", response.status_code, response.content)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data), 1)

    # ============ FUNCTION-BASED API TESTS ============

    def test_basic_api_response(self):
        Store.objects.create(name='Test Store 6', description='Test', owner=self.vendor)
        response = self.client.get('/api/basic_response/')
        self.assertEqual(response.status_code, 200)
        # basic_api_response returns Django-serialized json string
        data = json.loads(response.content)
        # Verify it can be loaded and contains store data
        if isinstance(data, str):
            data = json.loads(data)
        self.assertGreaterEqual(len(data), 1)

    def test_function_view_stores(self):
        Store.objects.create(name='Test Store 7', description='Test', owner=self.vendor)
        response = self.client.get('/api/get/stores/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertGreaterEqual(len(data), 1)

    def test_function_add_store(self):
        self.client.login(username='vendor1', password='password123')
        response = self.client.post('/api/post/store/', {
            'vendor': self.vendor.id,
            'name': 'Function Store',
            'description': 'A store created via function-based API'
        }, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.content)
        self.assertEqual(data['name'], 'Function Store')

    def test_function_add_store_mismatch(self):
        self.client.login(username='vendor1', password='password123')
        # Try to create store for a different vendor ID
        response = self.client.post('/api/post/store/', {
            'vendor': self.buyer.id,
            'name': 'Invalid Store',
            'description': 'Mismatch vendor'
        }, content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_function_add_product(self):
        self.client.login(username='vendor1', password='password123')
        store = Store.objects.create(name='Store for Product', description='Test', owner=self.vendor)
        response = self.client.post('/api/post/product/', {
            'store': store.id,
            'name': 'Function Product',
            'description': 'A product created via function API',
            'price': '15.99',
            'stock_quantity': 20,
            'category': 'electronics',
            'condition': 'new'
        }, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.content)
        self.assertEqual(data['name'], 'Function Product')

    def test_function_get_reviews(self):
        self.client.login(username='vendor1', password='password123')
        store = Store.objects.create(name='Store for Reviews', description='Test', owner=self.vendor)
        product = Product.objects.create(name='Reviewable Prod', description='Desc', price=10, stock_quantity=1, store=store)
        Review.objects.create(product=product, user=self.buyer, rating=4, comment='Nice')
        
        response = self.client.get('/api/get/reviews/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertGreaterEqual(len(data), 1)

    def test_function_get_vendor_stores(self):
        Store.objects.create(name='Vendor Store A', description='Test', owner=self.vendor)
        response = self.client.get(f'/api/get/stores/vendor/{self.vendor.id}/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data), 1)

    def test_function_get_store_products(self):
        store = Store.objects.create(name='Store B', description='Test', owner=self.vendor)
        Product.objects.create(name='Prod B', description='Desc', price=10, stock_quantity=1, store=store)
        response = self.client.get(f'/api/get/products/store/{store.id}/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data), 1)
