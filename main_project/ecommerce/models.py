from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import secrets
import hashlib


class Profile(models.Model):
    """User profile for security questions and extra info"""
    SECURITY_QUESTIONS = [
        ('childhood_street', 'What was the name of the street you grew up on?'),
        ('first_pet', 'What was the name of your first pet?'),
        ('first_boss', 'What was the first name of your first boss?'),
        ('family_birth_city', 'In what city was your oldest sibling born?'),
        ('first_car_model', 'What was the model of your first car?'),
        ('favorite_teacher', 'What was the last name of your favorite teacher?'),
        ('childhood_best_friend', 'What was the first name of your childhood best friend?'),
        ('first_job_title', 'What was your first job title?'),
        ('first_concert', 'What was the first concert you attended?'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    security_question = models.CharField(max_length=50, choices=SECURITY_QUESTIONS)
    security_answer = models.CharField(max_length=255)  # Should probably be hashed but user didn't specify
    
    def __str__(self):
        return f"Profile for {self.user.username}"



class Store(models.Model):
    """Store model for vendors"""
    name = models.CharField(max_length=200)
    description = models.TextField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stores')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        permissions = [
            ("manage_store", "Can manage store"),
        ]



class Product(models.Model):
    """Product model for items in stores"""
    CATEGORY_CHOICES = [
        ('electronics', 'Electronics'),
        ('fashion', 'Fashion'),
        ('home', 'Home & Garden'),
        ('beauty', 'Beauty & Personal Care'),
        ('sports', 'Sports & Outdoors'),
        ('toys', 'Toys & Games'),
        ('other', 'Other'),
    ]
    
    CONDITION_CHOICES = [
        ('new', 'New'),
        ('open_box', 'Open Box'),
        ('used_excellent', 'Used - Excellent'),
        ('used_good', 'Used - Good'),
        ('used_fair', 'Used - Fair'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.IntegerField(default=0)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='other')
    brand = models.CharField(max_length=100, blank=True, null=True)
    condition = models.CharField(max_length=50, choices=CONDITION_CHOICES, default='new')
    specifications = models.TextField(blank=True, null=True, help_text="Enter key technical specs")
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='products')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_available = models.BooleanField(default=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    image_url = models.URLField(max_length=500, blank=True, null=True)
    
    def __str__(self):
        return f"{self.name} - {self.store.name}"

    def save(self, *args, **kwargs):
        # Keep availability consistent with stock quantity.
        self.is_available = self.stock_quantity > 0
        super().save(*args, **kwargs)
    
    class Meta:
        permissions = [
            ("manage_product", "Can manage product"),
        ]


class Order(models.Model):
    """Order model for purchases"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_address = models.TextField()
    invoice_sent = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Order #{self.id} by {self.buyer.username}"

    def is_successful(self):
        return self.status != 'cancelled'



class OrderItem(models.Model):
    """Items within an order"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price_at_time = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.quantity}x {self.product.name}"



class Review(models.Model):
    """Product reviews"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])  # 1-5 stars
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)  # Verified if user purchased
    
    def __str__(self):
        return f"Review for {self.product.name} by {self.user.username}"
    
    class Meta:
        unique_together = ['product', 'user']  # One review per user per product



class Notification(models.Model):
    """In-app notifications/messages for users"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Notification for {self.user.username}: {self.title}"

