from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Group
from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone
from django.db.models import Q, Avg
import hashlib
import json
import io
from xhtml2pdf import pisa
from django.http import HttpResponse

from .models import User, Store, Product, Order, OrderItem, Review, Profile, Notification
from .forms import (
    UserRegistrationForm, StoreForm, ProductForm, 
    ReviewForm, CheckoutForm
)


def user_has_successful_order_for_product(user, product):
    return Order.objects.filter(
        buyer=user,
        items__product=product
    ).exclude(status='cancelled').exists()


# ============ AUTHENTICATION VIEWS ============

def register(request):
    """User registration view"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Assign to appropriate group and ensure permissions exist
            account_type = form.cleaned_data['account_type']
            group_name = 'Vendors' if account_type == 'vendor' else 'Buyers'
            group, created = Group.objects.get_or_create(name=group_name)
            
            if created or group.permissions.count() == 0:
                from django.contrib.auth.models import Permission
                if group_name == 'Vendors':
                    permissions = Permission.objects.filter(
                        content_type__app_label='ecommerce',
                        codename__in=['add_store', 'change_store', 'delete_store',
                                     'add_product', 'change_product', 'delete_product',
                                     'view_product', 'view_store']
                    )
                else: # Buyers
                    permissions = Permission.objects.filter(
                        content_type__app_label='ecommerce',
                        codename__in=['view_product']
                    )
                group.permissions.set(permissions)
            
            user.groups.add(group)
            
            # Log the user in
            login(request, user)
            # Set session to expire when browser closes (per brief)
            request.session.set_expiry(0)
            messages.success(request, f'Account created successfully! Welcome, {user.username}!')
            return redirect('ecommerce:home')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'ecommerce/register.html', {'form': form})

def login_view(request):
    """User login view"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            request.session.set_expiry(0)
            
            # Save cart from session to database if needed
            if 'cart' in request.session:
                # Could implement cart persistence here
                pass
                
            messages.success(request, f'Logged in as {username}.')
            return redirect('ecommerce:home')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'ecommerce/login.html')

def logout_view(request):
    """User logout view"""
    # Save cart data before logout if needed
    cart_data = request.session.get('cart', {})
    
    logout(request)
    
    # Restore cart data for next login? (optional)
    # request.session['cart'] = cart_data
    
    messages.info(request, 'You have been logged out.')
    return redirect('ecommerce:login')

# ============ PASSWORD RECOVERY (SECURITY QUESTIONS) ============

def forgot_password(request):
    """Handle recovery request using security questions"""
    questions = Profile.SECURITY_QUESTIONS
    return render(request, 'ecommerce/forgot_password.html', {'questions': questions})


def verify_security_answer(request):
    """API endpoint to verify security answer"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            question = data.get('security_question')
            answer = data.get('security_answer')
            
            user = User.objects.get(email=email)
            profile = user.profile
            
            if profile.security_question == question and profile.security_answer.lower() == answer.lower():
                return JsonResponse({'success': True, 'message': 'Answer verified. You can reset your password now.'})
            else:
                return JsonResponse({'success': False, 'message': 'Incorrect security answer.'}, status=400)
                
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'No user found with that email address.'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
            
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)


def reset_password_security(request):
    """API endpoint to reset password after verification"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            question = data.get('security_question')
            answer = data.get('security_answer')
            new_password = data.get('new_password')
            
            user = User.objects.get(email=email)
            profile = user.profile
            
            # Re-verify for safety
            if profile.security_question == question and profile.security_answer.lower() == answer.lower():
                user.set_password(new_password)
                user.save()
                return JsonResponse({'success': True, 'message': 'Password reset successfully.'})
            else:
                return JsonResponse({'success': False, 'message': 'Verification failed.'}, status=400)
                
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'User not found.'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
            
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

# ============ CORE ECOMMERCE VIEWS ============

def home(request):
    """Home page showing products"""
    products = Product.objects.filter(is_available=True, stock_quantity__gt=0)
    
    # Search functionality
    query = request.GET.get('q')
    if query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(store__name__icontains=query)
        )
    
    # Filter by store
    store_id = request.GET.get('store')
    if store_id:
        products = products.filter(store_id=store_id)
    
    # Annotate with average rating
    products = products.annotate(avg_rating=Avg('reviews__rating'))
    
    stores = Store.objects.filter(is_active=True)
    
    context = {
        'products': products,
        'stores': stores,
        'search_query': query,
    }
    return render(request, 'ecommerce/home.html', context)

def product_detail(request, product_id):
    """Product detail page"""
    product = get_object_or_404(Product, id=product_id, is_available=True)
    reviews = product.reviews.all().order_by('-created_at')
    
    # Check if user has purchased this product (any successful order)
    user_purchased = False
    if request.user.is_authenticated:
        user_purchased = user_has_successful_order_for_product(request.user, product)
    
    # Check if user has already reviewed
    user_review = None
    if request.user.is_authenticated:
        user_review = Review.objects.filter(product=product, user=request.user).first()
    
    context = {
        'product': product,
        'reviews': reviews,
        'user_purchased': user_purchased,
        'user_review': user_review,
    }
    return render(request, 'ecommerce/product_detail.html', context)

# ============ CART VIEWS (USING SESSIONS) ============

def view_cart(request):
    """View shopping cart"""
    cart = request.session.get('cart', {})
    cart_items = []
    total = 0
    
    for product_id, item_data in cart.items():
        try:
            product = Product.objects.get(id=product_id, is_available=True)
            quantity = item_data.get('quantity', 1)
            subtotal = product.price * quantity
            total += subtotal
            
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'subtotal': subtotal
            })
        except Product.DoesNotExist:
            # Remove invalid products from cart
            continue
    
    context = {
        'cart_items': cart_items,
        'total': total,
        'item_count': sum(item.get('quantity', 0) for item in cart.values())
    }
    return render(request, 'ecommerce/cart.html', context)

def add_to_cart(request, product_id):
    """Add product to cart (session-based)"""
    product = get_object_or_404(Product, id=product_id, is_available=True)
    
    # Get quantity from request
    quantity = int(request.POST.get('quantity', 1))
    
    if quantity > product.stock_quantity:
        messages.error(request, f'Sorry, only {product.stock_quantity} available.')
        return redirect('ecommerce:product_detail', product_id=product_id)
    
    # Initialize cart if it doesn't exist
    if 'cart' not in request.session:
        request.session['cart'] = {}
    
    cart = request.session['cart']
    
    # Add or update item
    if str(product_id) in cart:
        cart[str(product_id)]['quantity'] += quantity
    else:
        cart[str(product_id)] = {
            'quantity': quantity,
            'added_at': str(timezone.now())
        }
    
    request.session.modified = True
    
    messages.success(request, f'{product.name} added to cart.')
    return redirect('ecommerce:view_cart')

def update_cart(request, product_id):
    """Update cart item quantity"""
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 0))
        
        if 'cart' in request.session:
            cart = request.session['cart']
            
            if quantity <= 0:
                # Remove item
                if str(product_id) in cart:
                    del cart[str(product_id)]
                    messages.info(request, 'Item removed from cart.')
            else:
                # Update quantity
                product = get_object_or_404(Product, id=product_id)
                if quantity <= product.stock_quantity:
                    cart[str(product_id)]['quantity'] = quantity
                    messages.success(request, 'Cart updated.')
                else:
                    messages.error(request, f'Only {product.stock_quantity} available.')
            
            request.session.modified = True
    
    return redirect('ecommerce:view_cart')

def remove_from_cart(request, product_id):
    """Remove item from cart"""
    if 'cart' in request.session:
        cart = request.session['cart']
        if str(product_id) in cart:
            del cart[str(product_id)]
            request.session.modified = True
            messages.success(request, 'Item removed from cart.')
    
    return redirect('ecommerce:view_cart')

# ============ CHECKOUT VIEWS ============

@login_required
def checkout(request):
    """Checkout process"""
    cart = request.session.get('cart', {})
    
    if not cart:
        messages.warning(request, 'Your cart is empty.')
        return redirect('ecommerce:home')
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            shipping_address = form.cleaned_data['shipping_address']
            
            # Create order
            order = Order.objects.create(
                buyer=request.user,
                shipping_address=shipping_address,
                status='pending'
            )
            
            total = 0
            order_items = []
            
            # Process each cart item
            for product_id, item_data in cart.items():
                try:
                    product = Product.objects.get(id=product_id)
                    quantity = item_data.get('quantity', 1)
                    
                    if quantity <= product.stock_quantity:
                        # Create order item
                        order_item = OrderItem.objects.create(
                            order=order,
                            product=product,
                            quantity=quantity,
                            price_at_time=product.price
                        )
                        order_items.append(order_item)
                        
                        # Update stock
                        product.stock_quantity -= quantity
                        if product.stock_quantity == 0:
                            product.is_available = False
                        product.save()
                        
                        total += product.price * quantity
                    else:
                        messages.error(request, f'{product.name} is out of stock.')
                        order.delete()  # Rollback order
                        return redirect('ecommerce:view_cart')
                        
                except Product.DoesNotExist:
                    continue
            
            # Update order total
            order.total_amount = total
            order.save()
            
            # Create Notification instead of sending email
            Notification.objects.create(
                user=request.user,
                title="Order Placed Successfully",
                message=f"Your order #{order.id} for ${total} has been placed. You can download your invoice below.",
                order=order
            )
            
            # Notify Vendors
            vendors = set(item.product.store.owner for item in order.items.all())
            for vendor in vendors:
                Notification.objects.create(
                    user=vendor,
                    title="New Order Received",
                    message=f"You have a new order: #{order.id}. Please check your dashboard to process it.",
                    order=order
                )
            
            # Clear cart
            del request.session['cart']
            request.session.modified = True
            
            messages.success(request, 'Order placed successfully! You and the vendor have been notified.')
            return redirect('ecommerce:order_confirmation', order_id=order.id)
    else:
        form = CheckoutForm()
    
    # Calculate total for display
    total = 0
    for product_id, item_data in cart.items():
        try:
            product = Product.objects.get(id=product_id)
            total += product.price * item_data.get('quantity', 1)
        except Product.DoesNotExist:
            continue
    
    context = {
        'form': form,
        'total': total,
    }
    return render(request, 'ecommerce/checkout.html', context)

def download_invoice_pdf(request, order_id):
    """Generate and download order invoice as PDF"""
    order = get_object_or_404(Order, id=order_id, buyer=request.user)
    order_items = order.items.all()
    
    context = {
        'order': order,
        'items': order_items,
        'user': request.user,
        'order_date': order.order_date,
    }
    
    html = render_to_string('ecommerce/pdf/invoice_pdf.html', context)
    result = io.BytesIO()
    
    # Create PDF
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), result)
    
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{order.id}.pdf"'
        return response
    
    return HttpResponse("Error generating PDF", status=500)

@login_required
def notifications_list(request):
    """View user notifications/messages"""
    notifications = request.user.notifications.all().order_by('-created_at')
    
    # Mark all as read
    notifications.update(is_read=True)
    
    context = {
        'notifications': notifications,
    }
    return render(request, 'ecommerce/notifications.html', context)

# Remove the send_invoice_email function as it's no longer needed

@login_required
def order_confirmation(request, order_id):
    """Order confirmation page"""
    order = get_object_or_404(Order, id=order_id, buyer=request.user)
    order_items = order.items.select_related('product')
    seen_products = set()
    reviewable_products = []
    for item in order_items:
        product = item.product
        if product.id in seen_products:
            continue
        seen_products.add(product.id)
        if not Review.objects.filter(product=product, user=request.user).exists():
            reviewable_products.append(product)

    return render(request, 'ecommerce/order_confirmation.html', {
        'order': order,
        'reviewable_products': reviewable_products,
    })

# ============ REVIEW VIEWS ============

@login_required
def add_review(request, product_id):
    """Add a review for a product"""
    product = get_object_or_404(Product, id=product_id)

    if not user_has_successful_order_for_product(request.user, product):
        messages.error(request, 'You can leave a review only after purchasing this product.')
        return redirect('ecommerce:product_detail', product_id=product_id)
    
    # Check if user already reviewed
    existing_review = Review.objects.filter(product=product, user=request.user).first()
    if existing_review:
        messages.warning(request, 'You have already reviewed this product.')
        return redirect('ecommerce:product_detail', product_id=product_id)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            
            # Check if purchase is verified (any successful order)
            review.is_verified = user_has_successful_order_for_product(request.user, product)
            review.save()
            
            messages.success(request, 'Review added successfully!')
            return redirect('ecommerce:product_detail', product_id=product_id)
    else:
        form = ReviewForm()
    
    return render(request, 'ecommerce/add_review.html', {
        'form': form,
        'product': product
    })

# ============ VENDOR VIEWS (WITH PERMISSIONS) ============

@login_required
@permission_required('ecommerce.add_store', raise_exception=True)
def vendor_dashboard(request):
    """Vendor dashboard showing their stores and products"""
    stores = Store.objects.filter(owner=request.user)
    
    context = {
        'stores': stores,
        'total_stores': stores.count(),
        'total_products': Product.objects.filter(store__owner=request.user).count(),
    }
    return render(request, 'ecommerce/vendor/dashboard.html', context)

@login_required
@permission_required('ecommerce.add_store', raise_exception=True)
def create_store(request):
    """Create a new store"""
    if request.method == 'POST':
        form = StoreForm(request.POST)
        if form.is_valid():
            store = form.save(commit=False)
            store.owner = request.user
            store.save()
            messages.success(request, 'Store created successfully!')
            return redirect('ecommerce:vendor_dashboard')
    else:
        form = StoreForm()
    
    return render(request, 'ecommerce/vendor/store_form.html', {'form': form, 'action': 'Create'})

@login_required
def manage_store(request, store_id):
    """Manage a specific store's products and orders"""
    store = get_object_or_404(Store, id=store_id)
    
    # Check ownership
    if store.owner != request.user and not request.user.is_superuser:
        messages.error(request, 'You do not have permission to manage this store.')
        return redirect('ecommerce:home')
    
    products = Product.objects.filter(store=store)
    
    # Get orders that contain items from this store
    all_orders = Order.objects.filter(items__product__store=store).distinct().order_by('-order_date')
    
    pending_orders = all_orders.filter(status='pending')
    shipped_orders = all_orders.filter(status='shipped')
    
    context = {
        'store': store,
        'products': products,
        'pending_orders': pending_orders,
        'shipped_orders': shipped_orders,
        'all_orders': all_orders,
    }
    return render(request, 'ecommerce/vendor/manage_store.html', context)

@login_required
def update_order_status(request, order_id, status):
    """Update order status (e.g. to 'shipped')"""
    order = get_object_or_404(Order, id=order_id)
    
    # Simple check: if any product in order is from a store owned by user
    if not OrderItem.objects.filter(order=order, product__store__owner=request.user).exists() and not request.user.is_superuser:
        messages.error(request, 'Permission denied.')
        return redirect('ecommerce:vendor_dashboard')
        
    if status in dict(Order.STATUS_CHOICES):
        order.status = status
        order.save()
        messages.success(request, f'Order status updated to {status}.')

        # Sync review verification for this buyer and order products
        order_products = order.items.values_list('product', flat=True)
        if status == 'cancelled':
            Review.objects.filter(
                product_id__in=order_products,
                user=order.buyer,
                is_verified=True
            ).update(is_verified=False)
        else:
            Review.objects.filter(
                product_id__in=order_products,
                user=order.buyer,
                is_verified=False
            ).update(is_verified=True)
        
        # Notify buyer
        Notification.objects.create(
            user=order.buyer,
            title=f"Order Update: {status.capitalize()}",
            message=f"Your order #{order.id} has been marked as {status}.",
            order=order
        )
        
    return redirect(request.META.get('HTTP_REFERER', 'ecommerce:vendor_dashboard'))

@login_required
def edit_store(request, store_id):
    """Edit store details"""
    store = get_object_or_404(Store, id=store_id)
    
    # Check ownership
    if store.owner != request.user and not request.user.is_superuser:
        messages.error(request, 'You do not have permission to edit this store.')
        return redirect('ecommerce:home')
    
    if request.method == 'POST':
        form = StoreForm(request.POST, instance=store)
        if form.is_valid():
            form.save()
            messages.success(request, 'Store updated successfully!')
            return redirect('ecommerce:manage_store', store_id=store.id)
    else:
        form = StoreForm(instance=store)
    
    return render(request, 'ecommerce/vendor/store_form.html', {
        'form': form, 
        'action': 'Edit',
        'store': store
    })

@login_required
def delete_store(request, store_id):
    """Delete a store"""
    store = get_object_or_404(Store, id=store_id)
    
    # Check ownership
    if store.owner != request.user and not request.user.is_superuser:
        messages.error(request, 'You do not have permission to delete this store.')
        return redirect('ecommerce:home')
    
    if request.method == 'POST':
        store.delete()
        messages.success(request, 'Store deleted successfully!')
        return redirect('ecommerce:vendor_dashboard')
    
    return render(request, 'ecommerce/vendor/confirm_delete.html', {
        'object': store,
        'type': 'store'
    })

@login_required
def add_product(request, store_id):
    """Add product to store"""
    store = get_object_or_404(Store, id=store_id)
    
    # Check ownership
    if store.owner != request.user and not request.user.is_superuser:
        messages.error(request, 'You do not have permission to add products to this store.')
        return redirect('ecommerce:home')
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.store = store
            product.save()
            messages.success(request, 'Product added successfully!')
            return redirect('ecommerce:manage_store', store_id=store.id)
    else:
        form = ProductForm()
    
    return render(request, 'ecommerce/vendor/product_form.html', {
        'form': form,
        'store': store,
        'action': 'Add'
    })

@login_required
def edit_product(request, product_id):
    """Edit product"""
    product = get_object_or_404(Product, id=product_id)
    
    # Check ownership
    if product.store.owner != request.user and not request.user.is_superuser:
        messages.error(request, 'You do not have permission to edit this product.')
        return redirect('ecommerce:home')
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully!')
            return redirect('ecommerce:manage_store', store_id=product.store.id)
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'ecommerce/vendor/product_form.html', {
        'form': form,
        'product': product,
        'store': product.store,
        'action': 'Edit'
    })

@login_required
def delete_product(request, product_id):
    """Delete product"""
    product = get_object_or_404(Product, id=product_id)
    
    # Check ownership
    if product.store.owner != request.user and not request.user.is_superuser:
        messages.error(request, 'You do not have permission to delete this product.')
        return redirect('ecommerce:home')
    
    if request.method == 'POST':
        store_id = product.store.id
        product.delete()
        messages.success(request, 'Product deleted successfully!')
        return redirect('ecommerce:manage_store', store_id=store_id)
    
    return render(request, 'ecommerce/vendor/confirm_delete.html', {
        'object': product,
        'type': 'product'
    })
