from django.urls import path
from . import views

app_name = 'ecommerce'

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
]
