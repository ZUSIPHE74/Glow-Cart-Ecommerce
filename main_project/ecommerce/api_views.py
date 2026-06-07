from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import Store, Product, Review
from .serializers import StoreSerializer, ProductSerializer, ReviewSerializer

from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from django.http import JsonResponse
from django.core import serializers as django_serializers
from django.contrib.auth.models import User


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # obj is either Store or Product
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        if hasattr(obj, 'store'):
            return obj.store.owner == request.user
        return False

class IsVendorOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow vendors to create objects.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        # Only vendors should be able to create stores or products.
        # Check if user has add_store permission (assigned to Vendors group)
        return request.user and request.user.is_authenticated and request.user.has_perm('ecommerce.add_store')

class StoreViewSet(viewsets.ModelViewSet):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer
    permission_classes = [IsVendorOrReadOnly, IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def get_queryset(self):
        queryset = Store.objects.all()
        vendor_id = self.request.query_params.get('vendor_id')
        if vendor_id is not None:
            queryset = queryset.filter(owner_id=vendor_id)
        return queryset

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsVendorOrReadOnly, IsOwnerOrReadOnly]

    def create(self, request, *args, **kwargs):
        # Ensure the user owns the store they are adding a product to
        store_id = request.data.get('store')
        try:
            store = Store.objects.get(id=store_id)
            if store.owner != request.user:
                return Response(
                    {"detail": "You do not have permission to add products to this store."},
                    status=status.HTTP_403_FORBIDDEN
                )
        except Store.DoesNotExist:
            return Response(
                {"detail": "Store not found."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Product.objects.all()
        store_id = self.request.query_params.get('store_id')
        if store_id is not None:
            queryset = queryset.filter(store_id=store_id)
        return queryset

class ReviewViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    
    def get_queryset(self):
        queryset = Review.objects.all()
        product_id = self.request.query_params.get('product_id')
        if product_id is not None:
            queryset = queryset.filter(product_id=product_id)
        return queryset


# ============ FUNCTION-BASED API VIEWS ============

def basic_api_response(request):
    """Raw Django serializer JSON response of all stores"""
    if request.method == "GET":
        data = django_serializers.serialize('json', Store.objects.all())
        return JsonResponse(data=data, safe=False)
    return JsonResponse({"detail": "Method not allowed"}, status=405)


@api_view(['GET'])
def view_stores(request):
    """View all stores, optionally filtered by vendor_id query param"""
    if request.method == "GET":
        queryset = Store.objects.all()
        vendor_id = request.query_params.get('vendor_id') or request.GET.get('vendor_id')
        if vendor_id is not None:
            queryset = queryset.filter(owner_id=vendor_id)
        serializer = StoreSerializer(queryset, many=True)
        return JsonResponse(data=serializer.data, safe=False)


@api_view(['POST'])
@authentication_classes([BasicAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def add_store(request):
    """Add a new store, ensuring owner matches authenticated user"""
    if request.method == "POST":
        vendor_id = request.data.get('vendor') or request.data.get('owner')
        if not vendor_id:
            return JsonResponse({'error': 'Vendor ID is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if str(request.user.id) != str(vendor_id):
            return JsonResponse({'ID mismatch': 'User ID and store ID not matching'}, status=status.HTTP_400_BAD_REQUEST)
            
        serializer = StoreSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(owner=request.user)
            return JsonResponse(data=serializer.data, status=status.HTTP_201_CREATED)
        return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@authentication_classes([BasicAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def add_product(request):
    """Add a product, checking the user owns the store they are adding to"""
    if request.method == "POST":
        store_id = request.data.get('store')
        if not store_id:
            return JsonResponse({'error': 'Store ID is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            store = Store.objects.get(id=store_id)
            if store.owner != request.user:
                return JsonResponse({'detail': 'You do not have permission to add products to this store.'}, status=status.HTTP_403_FORBIDDEN)
        except Store.DoesNotExist:
            return JsonResponse({'detail': 'Store not found.'}, status=status.HTTP_400_BAD_REQUEST)
            
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(data=serializer.data, status=status.HTTP_201_CREATED)
        return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@authentication_classes([BasicAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_reviews(request):
    """Retrieve reviews, optionally filtered by store_id or product_id"""
    if request.method == "GET":
        store_id = request.query_params.get('store_id') or request.GET.get('store_id')
        product_id = request.query_params.get('product_id') or request.GET.get('product_id')
        
        queryset = Review.objects.all()
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        elif store_id:
            queryset = queryset.filter(product__store_id=store_id)
            
        serializer = ReviewSerializer(queryset, many=True)
        return JsonResponse(data=serializer.data, safe=False)


@api_view(['GET'])
def get_vendor_stores(request, vendor_id):
    """Retrieve stores belonging to a specific vendor ID"""
    if request.method == "GET":
        queryset = Store.objects.filter(owner_id=vendor_id)
        serializer = StoreSerializer(queryset, many=True)
        return JsonResponse(data=serializer.data, safe=False)


@api_view(['GET'])
def get_store_products(request, store_id):
    """Retrieve products belonging to a specific store ID"""
    if request.method == "GET":
        queryset = Product.objects.filter(store_id=store_id)
        serializer = ProductSerializer(queryset, many=True)
        return JsonResponse(data=serializer.data, safe=False)

