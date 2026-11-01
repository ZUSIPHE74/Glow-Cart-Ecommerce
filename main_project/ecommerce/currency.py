"""Display currencies. Prices are stored and charged in rand (PayFast is rand-only);
other currencies are shown converted with daily European Central Bank rates."""

import json
import logging
import re
import urllib.request
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.utils import timezone

from .models import ExchangeRate

logger = logging.getLogger(__name__)

RATES_URL = 'https://api.frankfurter.dev/v1/latest?base=ZAR'
RATES_MAX_AGE = timedelta(hours=12)
SESSION_KEY = 'currency'

# Currencies shoppers can pick, with how to write them.
CURRENCIES = {
    'ZAR': ('R', 'South African rand'),
    'USD': ('$', 'US dollar'),
    'EUR': ('€', 'Euro'),
    'GBP': ('£', 'British pound'),
    'AUD': ('A$', 'Australian dollar'),
    'CAD': ('C$', 'Canadian dollar'),
    'NZD': ('NZ$', 'New Zealand dollar'),
    'CHF': ('CHF ', 'Swiss franc'),
    'JPY': ('¥', 'Japanese yen'),
    'CNY': ('CN¥', 'Chinese yuan'),
    'INR': ('₹', 'Indian rupee'),
    'BRL': ('R$', 'Brazilian real'),
    'SEK': ('kr ', 'Swedish krona'),
    'NOK': ('kr ', 'Norwegian krone'),
    'SGD': ('S$', 'Singapore dollar'),
}
ZERO_DECIMAL = {'JPY'}

# Country (from the browser's language region) to its currency, where supported.
COUNTRY_CURRENCY = {
    'ZA': 'ZAR', 'NA': 'ZAR', 'LS': 'ZAR', 'SZ': 'ZAR', 'BW': 'ZAR',
    'US': 'USD', 'GB': 'GBP', 'AU': 'AUD', 'CA': 'CAD', 'NZ': 'NZD',
    'CH': 'CHF', 'JP': 'JPY', 'CN': 'CNY', 'IN': 'INR', 'BR': 'BRL',
    'SE': 'SEK', 'NO': 'NOK', 'SG': 'SGD',
    'DE': 'EUR', 'FR': 'EUR', 'IT': 'EUR', 'ES': 'EUR', 'NL': 'EUR', 'BE': 'EUR',
    'AT': 'EUR', 'IE': 'EUR', 'PT': 'EUR', 'FI': 'EUR', 'GR': 'EUR', 'LU': 'EUR',
}


def currency_from_accept_language(header):
    """First supported currency for the regions in an Accept-Language header,
    e.g. 'en-ZA,en;q=0.9' -> 'ZAR'. Rand when the region is unknown."""
    for region in re.findall(r'[a-zA-Z]{2,3}-([a-zA-Z]{2})\b', header or ''):
        currency = COUNTRY_CURRENCY.get(region.upper())
        if currency:
            return currency
    return settings.BASE_CURRENCY


def current_currency(request):
    """The shopper's chosen currency, else one guessed from their browser region."""
    chosen = request.session.get(SESSION_KEY)
    if chosen in CURRENCIES:
        return chosen
    return currency_from_accept_language(request.META.get('HTTP_ACCEPT_LANGUAGE'))


def remember_currency(request, code):
    if code not in CURRENCIES:
        return
    request.session[SESSION_KEY] = code
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        request.user.profile.currency = code
        request.user.profile.save(update_fields=['currency'])


def _fetch_rates():
    with urllib.request.urlopen(RATES_URL, timeout=4) as response:
        return json.load(response)['rates']


def get_rate(code):
    """Units of `code` per rand, refreshed from the internet at most every 12 hours.
    Returns None when no rate is known, so callers can fall back to rand."""
    if code == settings.BASE_CURRENCY:
        return Decimal(1)
    stored = ExchangeRate.objects.filter(currency=code).first()
    if stored and timezone.now() - stored.updated_at < RATES_MAX_AGE:
        return stored.rate
    try:
        rates = _fetch_rates()
        for currency, rate in rates.items():
            if currency in CURRENCIES:
                ExchangeRate.objects.update_or_create(currency=currency, defaults={'rate': Decimal(str(rate))})
        if code in rates:
            return Decimal(str(rates[code]))
    except Exception as err:  # A stale rate beats a broken page
        logger.warning('Could not refresh exchange rates: %s', err)
    return stored.rate if stored else None


def format_money(amount, code):
    symbol = CURRENCIES[code][0]
    places = Decimal('1') if code in ZERO_DECIMAL else Decimal('0.01')
    value = Decimal(amount).quantize(places, rounding=ROUND_HALF_UP)
    text = f'{value:,.0f}' if code in ZERO_DECIMAL else f'{value:,.2f}'
    return f'{symbol}{text}'


def display_price(amount_zar, code):
    """A rand amount shown in `code`, or in rand if no rate is available."""
    rate = get_rate(code)
    if rate is None:
        return format_money(amount_zar, settings.BASE_CURRENCY)
    return format_money(Decimal(amount_zar) * rate, code)
