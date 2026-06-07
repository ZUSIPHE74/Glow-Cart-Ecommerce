from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import api_views

app_name = 'ecommerce'

router = DefaultRouter()
router.register(r'stores', api_views.StoreViewSet, basename='store')
router.register(r'products', api_views.ProductViewSet, basename='product')
router.register(r'reviews', api_views.ReviewViewSet, basename='review')

urlpatterns = [
    # Authentication
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Password Recovery (Security Questions)
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('api/verify-security-answer', views.verify_security_answer, name='verify_security_answer'),
    path('api/reset-password-security', views.reset_password_security, name='reset_password_security'),
    
    # Core eCommerce
    path('', views.home, name='home'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    
    # Cart (session-based)
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:product_id>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    
    # Checkout (requires login)
    path('checkout/', views.checkout, name='checkout'),
    path('order-confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('invoice/<int:order_id>/pdf/', views.download_invoice_pdf, name='download_invoice_pdf'),
    
    # Notifications/Messages
    path('messages/', views.notifications_list, name='notifications_list'),
    
    # Reviews
    path('product/<int:product_id>/review/', views.add_review, name='add_review'),
    
    # Vendor routes (require permissions)
    path('vendor/dashboard/', views.vendor_dashboard, name='vendor_dashboard'),
    path('vendor/store/create/', views.create_store, name='create_store'),
    path('vendor/store/<int:store_id>/', views.manage_store, name='manage_store'),
    path('vendor/store/<int:store_id>/edit/', views.edit_store, name='edit_store'),
    path('vendor/store/<int:store_id>/delete/', views.delete_store, name='delete_store'),
    path('vendor/store/<int:store_id>/product/add/', views.add_product, name='add_product'),
    path('vendor/product/<int:product_id>/edit/', views.edit_product, name='edit_product'),
    path('vendor/product/<int:product_id>/delete/', views.delete_product, name='delete_product'),
    path('vendor/order/<int:order_id>/status/<str:status>/', views.update_order_status, name='update_order_status'),
    
    # REST API (Class-based ViewSets under DRF router & api/v1/)
    path('api/', include(router.urls)),
    path('api/v1/', include([
        path('stores/', api_views.StoreViewSet.as_view({'get': 'list', 'post': 'create'})),
        path('stores/<int:pk>/', api_views.StoreViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})),
        path('products/', api_views.ProductViewSet.as_view({'get': 'list', 'post': 'create'})),
        path('products/<int:pk>/', api_views.ProductViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})),
        path('reviews/', api_views.ReviewViewSet.as_view({'get': 'list'})),
        path('reviews/<int:pk>/', api_views.ReviewViewSet.as_view({'get': 'retrieve'})),
    ])),

    # REST API (Function-based views, exactly matching the task sheet and PDF)
    path('basic_response/', api_views.basic_api_response, name='basic_api_response'),
    path('get/stores/', api_views.view_stores, name='view_stores'),
    path('post/store/', api_views.add_store, name='add_store'),
    path('post/product/', api_views.add_product, name='add_product'),
    path('get/reviews/', api_views.get_reviews, name='get_reviews'),
    path('get/stores/vendor/<int:vendor_id>/', api_views.get_vendor_stores, name='get_vendor_stores'),
    path('get/products/store/<int:store_id>/', api_views.get_store_products, name='get_store_products'),

    # Function-based views also mapped under /api/ prefix for standard client conventions
    path('api/basic_response/', api_views.basic_api_response),
    path('api/get/stores/', api_views.view_stores),
    path('api/post/store/', api_views.add_store),
    path('api/post/product/', api_views.add_product),
    path('api/get/reviews/', api_views.get_reviews),
    path('api/get/stores/vendor/<int:vendor_id>/', api_views.get_vendor_stores),
    path('api/get/products/store/<int:store_id>/', api_views.get_store_products),
    path('api/docs/', views.api_docs, name='api_docs'),
]
