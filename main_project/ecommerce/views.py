from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Group
from django.contrib import messages
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone
from django.db.models import Q, Avg
import hashlib
import json
import io
import logging
from xhtml2pdf import pisa
from django.http import HttpResponse

from . import cart, payfast
from .groups import ensure_group
from .currency import remember_currency
from .orders import OutOfStock, cancel_unpaid, mark_paid, place_order, release_stale_orders

from django.conf import settings

from .models import User, Store, Product, Order, OrderItem, Review, Profile, Notification, Payout
from .forms import (
    UserRegistrationForm, StoreForm, ProductForm,
    ReviewForm, CheckoutForm, security_answer_matches
)

logger = logging.getLogger(__name__)


def user_has_successful_order_for_product(user, product):
    return Order.objects.filter(
        buyer=user,
        items__product=product,
        paid_at__isnull=False,
    ).exclude(status='cancelled').exists()


# ============ AUTHENTICATION VIEWS ============

def register(request):
    """User registration view"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()

            account_type = form.cleaned_data['account_type']
            group = ensure_group('Vendors' if account_type == 'vendor' else 'Buyers')
            user.groups.add(group)

            login(request, user)
            cart.merge_session_into_user(request, user)
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
            cart.merge_session_into_user(request, user)
            saved_currency = getattr(getattr(user, 'profile', None), 'currency', '')
            if saved_currency:
                request.session['currency'] = saved_currency

            messages.success(request, f'Logged in as {username}.')
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url and next_url.startswith('/') and not next_url.startswith('//'):
                return redirect(next_url)
            return redirect('ecommerce:home')
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'ecommerce/login.html')

def logout_view(request):
    """User logout view. A signed-in cart is saved on the account."""
    logout(request)
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

            if profile.security_question == question and security_answer_matches(profile, answer):
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
            if profile.security_question == question and security_answer_matches(profile, answer):
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
    products = Product.objects.filter(is_available=True, stock_quantity__gt=0).exclude(
        (Q(image='') | Q(image__isnull=True)) &
        (Q(image_url='') | Q(image_url__isnull=True))
    )

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

# ============ CART VIEWS ============

def view_cart(request):
    """View shopping cart"""
    lines = cart.get_lines(request)
    context = {
        'cart_items': lines,
        'total': sum((line['subtotal'] for line in lines), 0),
        'item_count': sum(line['quantity'] for line in lines),
    }
    return render(request, 'ecommerce/cart.html', context)


def _posted_quantity(request, default):
    try:
        return int(request.POST.get('quantity', default))
    except (TypeError, ValueError):
        return default


@require_POST
def add_to_cart(request, product_id):
    """Add product to cart"""
    product = get_object_or_404(Product, id=product_id, is_available=True)
    quantity = max(_posted_quantity(request, 1), 1)
    in_cart = cart.get_quantities(request).get(product.id, 0)

    if in_cart + quantity > product.stock_quantity:
        messages.error(request, f'Sorry, only {product.stock_quantity} available.')
        return redirect('ecommerce:product_detail', product_id=product_id)

    cart.set_quantity(request, product, in_cart + quantity)
    messages.success(request, f'{product.name} added to cart.')
    return redirect('ecommerce:view_cart')


@require_POST
def update_cart(request, product_id):
    """Update cart item quantity (0 removes it)"""
    product = get_object_or_404(Product, id=product_id)
    quantity = _posted_quantity(request, 0)
    if quantity > product.stock_quantity:
        messages.error(request, f'Only {product.stock_quantity} available.')
    else:
        cart.set_quantity(request, product, quantity)
        messages.success(request, 'Cart updated.' if quantity > 0 else 'Item removed from cart.')
    return redirect('ecommerce:view_cart')


def remove_from_cart(request, product_id):
    """Remove item from cart"""
    product = get_object_or_404(Product, id=product_id)
    cart.set_quantity(request, product, 0)
    messages.success(request, 'Item removed from cart.')
    return redirect('ecommerce:view_cart')

# ============ CHECKOUT & PAYMENT ============

@login_required
def checkout(request):
    """Shipping details, then on to PayFast to pay."""
    release_stale_orders()
    lines = cart.get_lines(request)
    if not lines:
        messages.warning(request, 'Your cart is empty.')
        return redirect('ecommerce:home')
    total = sum((line['subtotal'] for line in lines), 0)

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            quantities = {line['product'].id: line['quantity'] for line in lines}
            try:
                order = place_order(request.user, quantities, form.cleaned_data['shipping_address'])
            except OutOfStock as err:
                messages.error(request, f'Sorry, {err.product.name} no longer has enough stock. Please update your cart.')
                return redirect('ecommerce:view_cart')
            cart.clear(request)
            return redirect('ecommerce:pay_order', order_id=order.id)
    else:
        form = CheckoutForm()

    return render(request, 'ecommerce/checkout.html', {'form': form, 'total': total, 'cart_items': lines})


def _buyer_order_or_404(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if order.buyer != request.user:
        raise Http404('Order not found')
    return order


@login_required
def pay_order(request, order_id):
    """Sends the shopper to PayFast with a signed payment form."""
    order = _buyer_order_or_404(request, order_id)
    if order.is_paid:
        return redirect('ecommerce:order_confirmation', order_id=order.id)
    if order.status != 'pending':
        messages.error(request, 'This order was cancelled. Please place a new order.')
        return redirect('ecommerce:my_orders')
    fields = payfast.payment_fields(
        order,
        return_url=request.build_absolute_uri(reverse('ecommerce:order_confirmation', args=[order.id])),
        cancel_url=request.build_absolute_uri(reverse('ecommerce:payment_cancelled', args=[order.id])),
        notify_url=request.build_absolute_uri(reverse('ecommerce:payfast_notify')),
    )
    return render(request, 'ecommerce/pay_redirect.html', {
        'order': order,
        'fields': fields,
        'process_url': payfast.process_url(),
    })


@login_required
def payment_cancelled(request, order_id):
    """The shopper backed out on PayFast: cancel the order, return items to the cart."""
    order = _buyer_order_or_404(request, order_id)
    if cancel_unpaid(order.id):
        for item in order.items.select_related('product'):
            if item.product and item.product.is_available:
                in_cart = cart.get_quantities(request).get(item.product.id, 0)
                cart.set_quantity(request, item.product, min(in_cart + item.quantity, item.product.stock_quantity))
        messages.info(request, 'Payment was cancelled. Your items are back in your cart.')
    return redirect('ecommerce:view_cart')


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    return forwarded.split(',')[-1].strip() if forwarded else request.META.get('REMOTE_ADDR', '')


@csrf_exempt
@require_POST
def payfast_notify(request):
    """PayFast's server-to-server payment notification (ITN). Only this marks an
    order paid: the shopper returning to the site proves nothing on its own."""
    # PayFast signs the fields in the order it sent them, so keep that order.
    posted_pairs = [(key, values[0]) for key, values in request.POST.lists()]
    posted = dict(posted_pairs)
    order = Order.objects.filter(id=posted.get('m_payment_id') or 0).first()

    if not payfast.is_payfast_ip(_client_ip(request)):
        # Logged only: behind Render's proxy the IP is unreliable. The signature,
        # amount and PayFast's own confirmation below are the real proof.
        logger.warning('ITN from unrecognised IP %s', _client_ip(request))
    if order is None:
        logger.warning('ITN for unknown order %s', posted.get('m_payment_id'))
        return HttpResponse(status=200)
    if not payfast.uses_shared_test_merchant() and not payfast.itn_signature_valid(posted_pairs):
        logger.warning('ITN for order %s has a bad signature', order.id)
        return HttpResponse(status=400)
    if not payfast.itn_amount_matches(posted, order):
        logger.warning('ITN for order %s has amount %s, expected %s',
                       order.id, posted.get('amount_gross'), order.total_amount)
        return HttpResponse(status=400)
    if not payfast.itn_confirmed_by_payfast(payfast.itn_param_string(posted_pairs)):
        logger.warning('PayFast did not confirm the ITN for order %s', order.id)
        return HttpResponse(status=400)

    status = posted.get('payment_status')
    if status == 'COMPLETE':
        if not mark_paid(order.id, posted.get('pf_payment_id', '')):
            logger.error('Order %s was paid after being cancelled; refund needed (pf_payment_id %s)',
                         order.id, posted.get('pf_payment_id'))
    elif status == 'CANCELLED':
        cancel_unpaid(order.id)
    return HttpResponse(status=200)


@login_required
def my_orders(request):
    """The shopper's order history."""
    orders = request.user.orders.prefetch_related('items').order_by('-order_date')
    return render(request, 'ecommerce/my_orders.html', {'orders': orders})


@require_POST
def set_currency(request):
    remember_currency(request, request.POST.get('currency', ''))
    next_url = request.POST.get('next') or '/'
    if not next_url.startswith('/') or next_url.startswith('//'):
        next_url = '/'
    return redirect(next_url)


@login_required
def download_invoice_pdf(request, order_id):
    """Generate and download order invoice as PDF"""
    order = get_object_or_404(Order, id=order_id)
    is_vendor = order.items.filter(product__store__owner=request.user).exists()
    if order.buyer != request.user and not is_vendor and not request.user.is_superuser:
        raise Http404("Order not found or permission denied")
    if not order.is_paid:
        raise Http404("Invoices are available once the order is paid")

    order_items = order.items.all()

    context = {
        'order': order,
        'items': order_items,
        'user': order.buyer,  # Invoice usually prints buyer details
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

@login_required
def order_confirmation(request, order_id):
    """Order page: shown when PayFast returns the shopper, and from order history."""
    order = get_object_or_404(Order, id=order_id)
    is_vendor = order.items.filter(product__store__owner=request.user).exists()
    if order.buyer != request.user and not is_vendor and not request.user.is_superuser:
        raise Http404("Order not found or permission denied")

    order_items = order.items.select_related('product')
    seen_products = set()
    reviewable_products = []

    if order.buyer == request.user and order.is_paid:
        for item in order_items:
            product = item.product
            if product is None or product.id in seen_products:
                continue
            seen_products.add(product.id)
            if not Review.objects.filter(product=product, user=request.user).exists():
                reviewable_products.append(product)

    show_review_popup = False
    if reviewable_products and order.buyer == request.user:
        popup_count = request.session.get('review_popup_count', 0)
        if popup_count < 3:
            show_review_popup = True
            request.session['review_popup_count'] = popup_count + 1

    return render(request, 'ecommerce/order_confirmation.html', {
        'order': order,
        'awaiting_payment': order.status == 'pending' and not order.is_paid,
        'reviewable_products': reviewable_products,
        'is_vendor': is_vendor,
        'show_review_popup': show_review_popup,
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

            # No notification for reviews, only for orders and order updates

            messages.success(request, 'Review added successfully!')

            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
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
    """Vendor dashboard: stores, products and earnings from paid orders."""
    from django.db.models.functions import TruncDate
    from django.db.models import Sum, F, DecimalField, ExpressionWrapper
    stores = Store.objects.filter(owner=request.user)

    sold = OrderItem.objects.filter(
        store__owner=request.user, order__paid_at__isnull=False
    ).exclude(order__status='cancelled')
    line_total = ExpressionWrapper(F('quantity') * F('price_at_time'), output_field=DecimalField())
    totals = sold.aggregate(gross=Sum(line_total), commission=Sum('commission_amount'))
    gross = totals['gross'] or 0
    commission = totals['commission'] or 0
    paid_out = Payout.objects.filter(store__owner=request.user).aggregate(total=Sum('amount'))['total'] or 0

    sales_data = sold.annotate(date=TruncDate('order__paid_at')).values('date').annotate(
        revenue=Sum(line_total)
    ).order_by('date')

    context = {
        'stores': stores,
        'total_stores': stores.count(),
        'total_products': Product.objects.filter(store__owner=request.user).count(),
        'total_sales': gross,
        'commission': commission,
        'earnings': gross - commission,
        'paid_out': paid_out,
        'balance': gross - commission - paid_out,
        'commission_percent': settings.MARKETPLACE_COMMISSION_PERCENT,
        'payouts': Payout.objects.filter(store__owner=request.user).select_related('store').order_by('-paid_on')[:10],
        'total_buyers': sold.values('order__buyer').distinct().count(),
        'chart_labels': [d['date'].strftime("%Y-%m-%d") for d in sales_data if d['date']],
        'chart_data': [float(d['revenue']) for d in sales_data if d['date']],
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

    # Paid orders waiting to be shipped (unpaid ones are the buyer's to finish).
    pending_orders = all_orders.filter(status='processing', paid_at__isnull=False)
    shipped_orders = all_orders.filter(status='shipped')

    # Get reviews for this store's products
    reviews = Review.objects.filter(product__store=store).order_by('-created_at')

    context = {
        'store': store,
        'products': products,
        'pending_orders': pending_orders,
        'shipped_orders': shipped_orders,
        'all_orders': all_orders,
        'reviews': reviews,
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

    if status in {'shipped', 'delivered'} and not order.is_paid:
        messages.error(request, 'This order has not been paid yet, so it cannot be shipped.')
        return redirect(request.META.get('HTTP_REFERER', 'ecommerce:vendor_dashboard'))
    if status == 'pending':
        messages.error(request, 'Orders cannot be moved back to awaiting payment.')
        return redirect(request.META.get('HTTP_REFERER', 'ecommerce:vendor_dashboard'))

    if status in dict(Order.STATUS_CHOICES):
        if status == 'cancelled' and not order.is_paid:
            cancel_unpaid(order.id)  # returns the reserved stock
        order.refresh_from_db()
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

def api_docs(request):
    """API documentation view"""
    return render(request, 'ecommerce/api_docs.html')


# ============ INFO PAGES & INSTALLABLE APP ============

INFO_PAGES = {
    'contact': 'Contact us',
    'terms': 'Terms of sale',
    'returns': 'Returns & refunds',
    'privacy': 'Privacy policy',
}


def info_page(request, page):
    if page not in INFO_PAGES:
        raise Http404()
    return render(request, f'ecommerce/info/{page}.html', {
        'page_title': INFO_PAGES[page],
        'unpaid_timeout': settings.UNPAID_ORDER_TIMEOUT_MINUTES,
    })


def web_manifest(request):
    """Lets browsers install GlowCart as an app."""
    from django.templatetags.static import static
    manifest = {
        'name': 'GlowCart Marketplace',
        'short_name': 'GlowCart',
        'description': 'Shop fashion, tech and home goods from independent vendors.',
        'start_url': '/',
        'scope': '/',
        'display': 'standalone',
        'background_color': '#ffffff',
        'theme_color': '#ff6b00',
        'icons': [
            {'src': static('ecommerce/icons/icon-192.png'), 'sizes': '192x192', 'type': 'image/png'},
            {'src': static('ecommerce/icons/icon-512.png'), 'sizes': '512x512', 'type': 'image/png'},
            {'src': static('ecommerce/icons/icon-maskable-512.png'), 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'},
        ],
    }
    return JsonResponse(manifest, content_type='application/manifest+json')


def service_worker(request):
    """Served from the site root so it can control every page."""
    response = render(request, 'ecommerce/sw.js', content_type='application/javascript')
    response['Cache-Control'] = 'no-cache'
    return response


def offline(request):
    return render(request, 'ecommerce/offline.html')
