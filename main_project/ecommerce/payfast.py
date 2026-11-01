"""PayFast payments: the signed form that sends the shopper to PayFast, and the
checks on PayFast's Instant Transaction Notification (ITN) that confirm payment.

Follows PayFast's official SDK (github.com/Payfast/payfast-php-sdk): values are
URL-encoded like PHP's urlencode, signed with MD5 plus the account passphrase, and
an ITN is trusted only once PayFast's own server answers VALID for it."""

import hashlib
import logging
import socket
import urllib.parse
import urllib.request
from decimal import Decimal

from django.conf import settings

logger = logging.getLogger(__name__)

SANDBOX_HOST = 'sandbox.payfast.co.za'
LIVE_HOST = 'www.payfast.co.za'
# Hosts PayFast sends ITNs from (from the official SDK).
ITN_HOSTS = ['www.payfast.co.za', 'sandbox.payfast.co.za', 'w1w.payfast.co.za', 'w2w.payfast.co.za']
SANDBOX_MERCHANT_ID = '10000100'

# Fields covered by the payment signature, in PayFast's documented order.
SIGNED_FIELDS = [
    'merchant_id', 'merchant_key', 'return_url', 'cancel_url', 'notify_url',
    'name_first', 'name_last', 'email_address', 'cell_number',
    'm_payment_id', 'amount', 'item_name', 'item_description',
    'custom_int1', 'custom_str1',
]


class PayFastConfigError(Exception):
    pass


def host():
    return SANDBOX_HOST if settings.PAYFAST_SANDBOX else LIVE_HOST


def process_url():
    return f'https://{host()}/eng/process'


def check_config():
    """Refuses live mode with the public sandbox merchant, which would take no money."""
    if not settings.PAYFAST_SANDBOX and settings.PAYFAST_MERCHANT_ID == SANDBOX_MERCHANT_ID:
        raise PayFastConfigError('PAYFAST_SANDBOX is off but the sandbox merchant ID is still set.')


def uses_shared_test_merchant():
    """PayFast's shared sandbox merchant checks signatures against a passphrase it
    doesn't publish, but accepts unsigned payments. With it, payments go unsigned
    and ITNs are trusted on PayFast's own confirmation; your own merchant account
    (sandbox or live) gets full signature checks."""
    return settings.PAYFAST_SANDBOX and settings.PAYFAST_MERCHANT_ID == SANDBOX_MERCHANT_ID


def encode(value, strip=True):
    """PHP urlencode: spaces as '+', everything but letters, digits and -_. escaped.
    Outgoing values are trimmed; ITN values are signed exactly as received."""
    value = str(value).strip() if strip else str(value)
    return urllib.parse.quote_plus(value, safe='').replace('~', '%7E')


def _sign(pairs, strip=True):
    query = '&'.join(f'{key}={encode(value, strip)}' for key, value in pairs)
    if settings.PAYFAST_PASSPHRASE:
        query += f'&passphrase={encode(settings.PAYFAST_PASSPHRASE)}'
    return hashlib.md5(query.encode()).hexdigest()


def payment_fields(order, return_url, cancel_url, notify_url):
    """The hidden form fields (signature included) that start payment for an order."""
    check_config()
    data = {
        'merchant_id': settings.PAYFAST_MERCHANT_ID,
        'merchant_key': settings.PAYFAST_MERCHANT_KEY,
        'return_url': return_url,
        'cancel_url': cancel_url,
        'notify_url': notify_url,
        'email_address': order.buyer.email,
        'm_payment_id': str(order.id),
        'amount': f'{order.total_amount:.2f}',
        'item_name': f'GlowCart order {order.id}',
    }
    pairs = [(key, data[key]) for key in SIGNED_FIELDS if data.get(key)]
    if uses_shared_test_merchant():
        return pairs
    return pairs + [('signature', _sign(pairs))]


def itn_signature_valid(posted_pairs):
    """posted_pairs: the ITN's fields in the order received. PayFast signs every
    field before 'signature', in that order."""
    pairs = []
    received = None
    for key, value in posted_pairs:
        if key == 'signature':
            received = value
            break
        pairs.append((key, value))
    return received is not None and _sign(pairs, strip=False) == received


def itn_param_string(posted_pairs):
    """The ITN fields before 'signature', encoded, for PayFast's validate endpoint."""
    pairs = []
    for key, value in posted_pairs:
        if key == 'signature':
            break
        pairs.append(f'{key}={encode(value, strip=False)}')
    return '&'.join(pairs)


def itn_amount_matches(posted, order):
    try:
        return abs(Decimal(posted.get('amount_gross', '')) - order.total_amount) <= Decimal('0.01')
    except Exception:
        return False


def itn_confirmed_by_payfast(param_string):
    """Asks PayFast's server whether it really sent this ITN."""
    request = urllib.request.Request(
        f'https://{host()}/eng/query/validate',
        data=param_string.encode(),
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.read().decode().strip() == 'VALID'
    except Exception as err:
        logger.warning('PayFast validate request failed: %s', err)
        return False


def is_payfast_ip(ip):
    valid = set()
    for name in ITN_HOSTS:
        try:
            valid.update(socket.gethostbyname_ex(name)[2])
        except OSError:
            continue
    return ip in valid
