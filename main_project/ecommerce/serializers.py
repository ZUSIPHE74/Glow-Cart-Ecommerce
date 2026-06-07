from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Store, Product, Review

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class ReviewSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Review
        fields = ['id', 'product', 'user', 'rating', 'comment', 'created_at', 'is_verified']
        read_only_fields = ['user', 'is_verified', 'created_at']

class ProductSerializer(serializers.ModelSerializer):
    reviews = ReviewSerializer(many=True, read_only=True)
    store_name = serializers.ReadOnlyField(source='store.name')
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'stock_quantity', 
            'category', 'brand', 'condition', 'specifications', 
            'store', 'store_name', 'created_at', 'updated_at', 
            'is_available', 'image', 'image_url', 'reviews'
        ]
        read_only_fields = ['created_at', 'updated_at', 'is_available']

class StoreSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    vendor = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='owner',
        required=False
    )
    products = ProductSerializer(many=True, read_only=True)
    
    class Meta:
        model = Store
        fields = ['id', 'name', 'description', 'owner', 'vendor', 'created_at', 'updated_at', 'is_active', 'products']
        read_only_fields = ['owner', 'created_at', 'updated_at']

