"""Tests for the cart, checkout, PayFast payments, order history, currency and vendor earnings."""

from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from . import payfast
from .currency import currency_from_accept_language, format_money
from .groups import ensure_group
from .models import CartItem, ExchangeRate, Order, Payout, Product, Profile, Store
from .orders import OutOfStock, cancel_unpaid, mark_paid, place_order, release_stale_orders

PASSWORD = 'Str0ng!Passw0rd'


def make_user(username, group=None):
    user = User.objects.create_user(username, f'{username}@example.com', PASSWORD)
    Profile.objects.create(user=user, security_question='first_pet', security_answer='x')
    if group:
        user.groups.add(ensure_group(group))
    return user


class ShopTestCase(TestCase):
    def setUp(self):
        self.vendor = make_user('vendor', 'Vendors')
        self.store = Store.objects.create(name='Shop', description='d', owner=self.vendor)
        self.lamp = Product.objects.create(store=self.store, name='Lamp', description='d', price=Decimal('100.00'),
                                           stock_quantity=5, image_url='https://example.com/lamp.jpg')
        self.chair = Product.objects.create(store=self.store, name='Chair', description='d', price=Decimal('250.00'),
                                            stock_quantity=1, image_url='https://example.com/chair.jpg')
        self.buyer = make_user('buyer', 'Buyers')
        # Rates are looked up on every page; keep tests offline.
        ExchangeRate.objects.create(currency='USD', rate=Decimal('0.05'))


class CartTests(ShopTestCase):
    def test_visitor_cart_survives_reload_and_updates(self):
        self.client.post(reverse('ecommerce:add_to_cart', args=[self.lamp.id]), {'quantity': 2})
        self.client.post(reverse('ecommerce:update_cart', args=[self.lamp.id]), {'quantity': 3})
        response = self.client.get(reverse('ecommerce:view_cart'))
        self.assertEqual(response.context['item_count'], 3)

    def test_cannot_add_more_than_stock(self):
        self.client.post(reverse('ecommerce:add_to_cart', args=[self.chair.id]), {'quantity': 1})
        self.client.post(reverse('ecommerce:add_to_cart', args=[self.chair.id]), {'quantity': 1})
        self.assertEqual(self.client.get(reverse('ecommerce:view_cart')).context['item_count'], 1)

    def test_add_to_cart_requires_post(self):
        response = self.client.get(reverse('ecommerce:add_to_cart', args=[self.lamp.id]))
        self.assertEqual(response.status_code, 405)

    def test_visitor_cart_moves_to_account_on_login_and_survives_logout(self):
        self.client.post(reverse('ecommerce:add_to_cart', args=[self.lamp.id]), {'quantity': 2})
        self.client.post(reverse('ecommerce:login'), {'username': 'buyer', 'password': PASSWORD})
        self.assertEqual(CartItem.objects.get(user=self.buyer, product=self.lamp).quantity, 2)
        self.client.get(reverse('ecommerce:logout'))
        self.client.post(reverse('ecommerce:login'), {'username': 'buyer', 'password': PASSWORD})
        self.assertEqual(self.client.get(reverse('ecommerce:view_cart')).context['item_count'], 2)

    def test_login_returns_to_next_page_but_not_offsite(self):
        response = self.client.post(reverse('ecommerce:login') + '?next=/checkout/',
                                    {'username': 'buyer', 'password': PASSWORD, 'next': '/checkout/'})
        self.assertEqual(response.url, '/checkout/')
        self.client.logout()
        response = self.client.post(reverse('ecommerce:login'),
                                    {'username': 'buyer', 'password': PASSWORD, 'next': '//evil.example'})
        self.assertEqual(response.url, reverse('ecommerce:home'))


class OrderTests(ShopTestCase):
    def test_place_order_reserves_stock_and_records_commission(self):
        order = place_order(self.buyer, {self.lamp.id: 2}, '1 Main Rd')
        self.lamp.refresh_from_db()
        self.assertEqual(self.lamp.stock_quantity, 3)
        self.assertEqual(order.total_amount, Decimal('200.00'))
        item = order.items.get()
        self.assertEqual((item.product_name, item.store, item.commission_amount),
                         ('Lamp', self.store, Decimal('20.00')))
        self.assertFalse(order.is_paid)

    def test_out_of_stock_changes_nothing(self):
        with self.assertRaises(OutOfStock):
            place_order(self.buyer, {self.lamp.id: 2, self.chair.id: 5}, '1 Main Rd')
        self.lamp.refresh_from_db()
        self.assertEqual(self.lamp.stock_quantity, 5)
        self.assertFalse(Order.objects.exists())

    def test_cancel_returns_stock_once(self):
        order = place_order(self.buyer, {self.chair.id: 1}, '1 Main Rd')
        self.assertTrue(cancel_unpaid(order.id))
        self.assertFalse(cancel_unpaid(order.id))
        self.chair.refresh_from_db()
        self.assertEqual(self.chair.stock_quantity, 1)
        self.assertTrue(self.chair.is_available)

    def test_paid_order_is_not_cancelled_and_payment_is_idempotent(self):
        order = place_order(self.buyer, {self.lamp.id: 1}, '1 Main Rd')
        self.assertTrue(mark_paid(order.id, 'pf-1'))
        self.assertTrue(mark_paid(order.id, 'pf-1'))
        self.assertFalse(cancel_unpaid(order.id))
        order.refresh_from_db()
        self.assertEqual(order.status, 'processing')
        self.assertEqual(self.buyer.notifications.count(), 1)
        self.assertEqual(self.vendor.notifications.count(), 1)

    def test_stale_unpaid_orders_release_stock(self):
        order = place_order(self.buyer, {self.lamp.id: 2}, '1 Main Rd')
        Order.objects.filter(id=order.id).update(order_date=timezone.now() - timedelta(hours=2))
        release_stale_orders()
        self.lamp.refresh_from_db()
        self.assertEqual(self.lamp.stock_quantity, 5)

    def test_checkout_creates_order_and_sends_to_payfast(self):
        self.client.force_login(self.buyer)
        self.client.post(reverse('ecommerce:add_to_cart', args=[self.lamp.id]), {'quantity': 1})
        response = self.client.post(reverse('ecommerce:checkout'),
                                    {'shipping_address': '1 Main Rd', 'confirm_purchase': 'on'})
        order = Order.objects.get()
        self.assertRedirects(response, reverse('ecommerce:pay_order', args=[order.id]))
        self.assertFalse(CartItem.objects.filter(user=self.buyer).exists())

        page = self.client.get(reverse('ecommerce:pay_order', args=[order.id]))
        fields = dict(page.context['fields'])
        self.assertEqual(page.context['process_url'], 'https://sandbox.payfast.co.za/eng/process')
        self.assertEqual(fields['amount'], '100.00')
        self.assertEqual(fields['m_payment_id'], str(order.id))
        self.assertTrue(fields['notify_url'].endswith(reverse('ecommerce:payfast_notify')))

    def test_cancelled_payment_puts_items_back_in_cart(self):
        self.client.force_login(self.buyer)
        order = place_order(self.buyer, {self.lamp.id: 2}, '1 Main Rd')
        self.client.get(reverse('ecommerce:payment_cancelled', args=[order.id]))
        order.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')
        self.assertEqual(CartItem.objects.get(user=self.buyer, product=self.lamp).quantity, 2)

    def test_other_users_cannot_pay_or_see_orders(self):
        order = place_order(self.buyer, {self.lamp.id: 1}, '1 Main Rd')
        self.client.force_login(make_user('stranger'))
        self.assertEqual(self.client.get(reverse('ecommerce:pay_order', args=[order.id])).status_code, 404)
        self.assertEqual(self.client.get(reverse('ecommerce:order_confirmation', args=[order.id])).status_code, 404)

    def test_my_orders_lists_only_own_orders(self):
        mine = place_order(self.buyer, {self.lamp.id: 1}, '1 Main Rd')
        place_order(make_user('other'), {self.lamp.id: 1}, '2 Main Rd')
        self.client.force_login(self.buyer)
        response = self.client.get(reverse('ecommerce:my_orders'))
        self.assertEqual(list(response.context['orders']), [mine])

    def test_invoice_only_for_paid_orders(self):
        order = place_order(self.buyer, {self.lamp.id: 1}, '1 Main Rd')
        self.client.force_login(self.buyer)
        url = reverse('ecommerce:download_invoice_pdf', args=[order.id])
        self.assertEqual(self.client.get(url).status_code, 404)
        mark_paid(order.id, 'pf-1')
        self.assertEqual(self.client.get(url)['Content-Type'], 'application/pdf')


class PayFastSignatureTests(TestCase):
    @override_settings(PAYFAST_PASSPHRASE='')
    def test_matches_payfast_sdk_test_vector(self):
        # From PayFast's official PHP SDK tests (NotificationTest.php), no passphrase.
        pairs = [
            ('m_payment_id', '000000020'), ('pf_payment_id', '1579137'), ('payment_status', 'COMPLETE'),
            ('item_name', 'Order #000000020'), ('item_description', ''), ('amount_gross', '15.00'),
            ('amount_fee', '-2.30'), ('amount_net', '12.70'),
            ('custom_str1', ''), ('custom_str2', ''), ('custom_str3', ''), ('custom_str4', ''), ('custom_str5', ''),
            ('custom_int1', ''), ('custom_int2', ''), ('custom_int3', ''), ('custom_int4', ''), ('custom_int5', ''),
            ('name_first', 'Tom'), ('name_last', 'Tom'), ('email_address', 'lindley+user1@appinlet.com'),
            ('merchant_id', '10027938'), ('signature', '4078bca2c8987e0e0c4e7230f2f46323'),
        ]
        self.assertTrue(payfast.itn_signature_valid(pairs))
        tampered = [(k, '16.00' if k == 'amount_gross' else v) for k, v in pairs]
        self.assertFalse(payfast.itn_signature_valid(tampered))

    def test_php_style_encoding(self):
        self.assertEqual(payfast.encode('a b+c@d~e*'), 'a+b%2Bc%40d%7Ee%2A')

    @override_settings(PAYFAST_SANDBOX=False, PAYFAST_MERCHANT_ID='10000100')
    def test_live_mode_refuses_sandbox_merchant(self):
        with self.assertRaises(payfast.PayFastConfigError):
            payfast.check_config()


@override_settings(PAYFAST_PASSPHRASE='secret phrase', PAYFAST_MERCHANT_ID='12345678', PAYFAST_MERCHANT_KEY='k')
class PayFastNotifyTests(ShopTestCase):
    def setUp(self):
        super().setUp()
        self.order = place_order(self.buyer, {self.lamp.id: 2}, '1 Main Rd')

    def itn(self, amount='200.00', status='COMPLETE', sign_with=None):
        pairs = [
            ('m_payment_id', str(self.order.id)), ('pf_payment_id', '987654'), ('payment_status', status),
            ('item_name', f'GlowCart order {self.order.id}'), ('item_description', ''),
            ('amount_gross', amount), ('amount_fee', '-4.60'), ('amount_net', '195.40'),
            ('email_address', 'buyer@example.com'), ('merchant_id', '10000100'),
        ]
        signature = payfast._sign(pairs, strip=False)
        if sign_with is not None:
            with override_settings(PAYFAST_PASSPHRASE=sign_with):
                signature = payfast._sign(pairs, strip=False)
        return dict(pairs + [('signature', signature)])

    def post(self, data, confirmed=True):
        with mock.patch.object(payfast, 'itn_confirmed_by_payfast', return_value=confirmed) as confirm, \
                mock.patch.object(payfast, 'is_payfast_ip', return_value=True):
            response = self.client.post(reverse('ecommerce:payfast_notify'), data)
        self.order.refresh_from_db()
        return response, confirm

    def test_valid_itn_marks_order_paid(self):
        response, confirm = self.post(self.itn())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.order.is_paid)
        self.assertEqual(self.order.payment_reference, '987654')
        # PayFast is asked to confirm the exact fields it signed.
        self.assertIn(f'm_payment_id={self.order.id}', confirm.call_args.args[0])
        self.assertNotIn('signature', confirm.call_args.args[0])

    def test_wrong_passphrase_is_rejected(self):
        response, _ = self.post(self.itn(sign_with='guessed'))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.order.is_paid)

    def test_wrong_amount_is_rejected(self):
        response, _ = self.post(self.itn(amount='2.00'))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.order.is_paid)

    def test_unconfirmed_by_payfast_is_rejected(self):
        response, _ = self.post(self.itn(), confirmed=False)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.order.is_paid)

    def test_cancelled_itn_cancels_and_restocks(self):
        self.post(self.itn(status='CANCELLED'))
        self.lamp.refresh_from_db()
        self.assertEqual(self.order.status, 'cancelled')
        self.assertEqual(self.lamp.stock_quantity, 5)


class SharedTestMerchantTests(ShopTestCase):
    """PayFast's shared sandbox merchant: unsigned payments, ITNs trusted on PayFast's confirmation."""

    def test_payment_form_is_unsigned(self):
        order = place_order(self.buyer, {self.lamp.id: 1}, '1 Main Rd')
        fields = dict(payfast.payment_fields(order, 'https://x/r', 'https://x/c', 'https://x/n'))
        self.assertNotIn('signature', fields)

    @override_settings(PAYFAST_MERCHANT_ID='12345678')
    def test_own_merchant_form_is_signed(self):
        order = place_order(self.buyer, {self.lamp.id: 1}, '1 Main Rd')
        fields = dict(payfast.payment_fields(order, 'https://x/r', 'https://x/c', 'https://x/n'))
        self.assertEqual(len(fields['signature']), 32)

    def test_itn_needs_payfast_confirmation(self):
        order = place_order(self.buyer, {self.lamp.id: 1}, '1 Main Rd')
        itn = {'m_payment_id': str(order.id), 'pf_payment_id': '55', 'payment_status': 'COMPLETE',
               'amount_gross': '100.00', 'signature': 'not-checkable'}
        for confirmed, paid in [(False, False), (True, True)]:
            with mock.patch.object(payfast, 'itn_confirmed_by_payfast', return_value=confirmed):
                self.client.post(reverse('ecommerce:payfast_notify'), itn)
            order.refresh_from_db()
            self.assertEqual(order.is_paid, paid)


class CurrencyTests(ShopTestCase):
    def test_region_picks_currency(self):
        self.assertEqual(currency_from_accept_language('en-ZA,en;q=0.9'), 'ZAR')
        self.assertEqual(currency_from_accept_language('en-US,en;q=0.9'), 'USD')
        self.assertEqual(currency_from_accept_language('de-DE'), 'EUR')
        self.assertEqual(currency_from_accept_language('en'), 'ZAR')

    def test_formatting(self):
        self.assertEqual(format_money(Decimal('1250'), 'ZAR'), 'R1,250.00')
        self.assertEqual(format_money(Decimal('1250.4'), 'JPY'), '¥1,250')

    def test_browser_region_sets_display_currency(self):
        response = self.client.get(reverse('ecommerce:view_cart'), HTTP_ACCEPT_LANGUAGE='en-US')
        self.assertEqual(response.context['currency_code'], 'USD')

    def test_choice_is_remembered_and_saved_on_account(self):
        self.client.force_login(self.buyer)
        self.client.post(reverse('ecommerce:set_currency'), {'currency': 'USD', 'next': '/cart/'})
        response = self.client.get(reverse('ecommerce:view_cart'), HTTP_ACCEPT_LANGUAGE='en-ZA')
        self.assertEqual(response.context['currency_code'], 'USD')
        self.buyer.profile.refresh_from_db()
        self.assertEqual(self.buyer.profile.currency, 'USD')

    def test_product_price_shown_converted(self):
        self.client.post(reverse('ecommerce:set_currency'), {'currency': 'USD'})
        response = self.client.get(reverse('ecommerce:product_detail', args=[self.lamp.id]))
        self.assertContains(response, '$5.00')


class VendorTests(ShopTestCase):
    def test_vendor_cannot_ship_unpaid_order(self):
        order = place_order(self.buyer, {self.lamp.id: 1}, '1 Main Rd')
        self.client.force_login(self.vendor)
        self.client.get(reverse('ecommerce:update_order_status', args=[order.id, 'shipped']))
        order.refresh_from_db()
        self.assertEqual(order.status, 'pending')

    def test_earnings_count_paid_orders_less_commission_and_payouts(self):
        paid = place_order(self.buyer, {self.lamp.id: 2}, '1 Main Rd')
        mark_paid(paid.id, 'pf-1')
        place_order(self.buyer, {self.lamp.id: 1}, '1 Main Rd')  # unpaid: not counted
        Payout.objects.create(store=self.store, amount=Decimal('50.00'), reference='EFT1',
                              paid_on=timezone.now().date())
        self.client.force_login(self.vendor)
        context = self.client.get(reverse('ecommerce:vendor_dashboard')).context
        self.assertEqual(context['total_sales'], Decimal('200.00'))
        self.assertEqual(context['earnings'], Decimal('180.00'))
        self.assertEqual(context['balance'], Decimal('130.00'))


class SecurityAnswerTests(TestCase):
    def test_answers_are_hashed_and_checked_loosely(self):
        from .forms import hash_security_answer, security_answer_matches
        profile = Profile(security_answer=hash_security_answer('  Rex  The Dog'))
        self.assertNotIn('rex', profile.security_answer)
        self.assertTrue(security_answer_matches(profile, 'rex the dog'))
        self.assertFalse(security_answer_matches(profile, 'fido'))


class AppShellTests(TestCase):
    def test_manifest_and_service_worker(self):
        manifest = self.client.get(reverse('ecommerce:web_manifest')).json()
        self.assertEqual(manifest['display'], 'standalone')
        worker = self.client.get('/sw.js')
        self.assertEqual(worker['Content-Type'], 'application/javascript')
        self.assertContains(worker, 'glowcart-v1')

    def test_info_pages(self):
        for page in ['contact', 'terms', 'returns', 'privacy']:
            self.assertEqual(self.client.get(reverse('ecommerce:info_page', args=[page])).status_code, 200)
        self.assertEqual(self.client.get(reverse('ecommerce:info_page', args=['nope'])).status_code, 404)


class SeedTests(TestCase):
    def test_seed_is_repeatable_and_demo_logins_work(self):
        from django.core.management import call_command
        call_command('seed_demo', stdout=open(__import__('os').devnull, 'w'))
        call_command('seed_demo', stdout=open(__import__('os').devnull, 'w'))
        self.assertEqual(Product.objects.count(), 14)
        for username in ['demo_buyer', 'demo_vendor']:
            self.assertTrue(self.client.login(username=username, password='GlowDemo2026!'), username)
        self.assertFalse(User.objects.get(username='urban_thread').has_usable_password())

    @override_settings(DEMO_ACCOUNTS=False)
    def test_demo_logins_disabled_when_turned_off(self):
        from django.core.management import call_command
        call_command('seed_demo', stdout=open(__import__('os').devnull, 'w'))
        self.assertFalse(self.client.login(username='demo_buyer', password='GlowDemo2026!'))
