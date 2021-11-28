#from QuantLib.QuantLib import Cdor, Instrument
#from django.db.models import base
from swpm.models import *
import datetime
from forex_python.converter import CurrencyRates
from random import random
from math import exp, sqrt
import pandas as pd

d = datetime.date.today()

hongkong, _ = Calendar.objects.get_or_create(name="HongKong")
unitedstates, _ = Calendar.objects.get_or_create(name="UnitedStates")
target, _ = Calendar.objects.get_or_create(name="TARGET")

hkd, _ = Ccy.objects.get_or_create(code="HKD", defaults={'cdr': hongkong})
eur, _ = Ccy.objects.get_or_create(code="EUR", defaults={
                                   'cdr': target, 'risk_free_curve': 'EUR FOREX', 'foreign_exchange_curve': 'EUR FOREX', 'rate_day_counter': 'Actual360'})
usd, _ = Ccy.objects.get_or_create(code="USD", defaults={
                                   'cdr': unitedstates, 'risk_free_curve': 'USD OIS', 'foreign_exchange_curve': 'USD OIS', 'rate_day_counter': 'Actual360'})
print("Ccy created")

eurusd, _ = CcyPair.objects.get_or_create(
    name="EUR/USD", base_ccy=eur, quote_ccy=usd, defaults={'cdr': target})
usdhkd, _ = CcyPair.objects.get_or_create(
    name="USD/HKD", base_ccy=usd, quote_ccy=hkd, defaults={'cdr': hongkong})
print("CcyPair created")

admin = User.objects.get(pk=1)
hkfx, _ = Portfolio.objects.get_or_create(name="HKFX")
fxo1, _ = Book.objects.get_or_create(name="FXO1", portfolio=hkfx, owner=admin)
fxo2, _ = Book.objects.get_or_create(name="FXO2", portfolio=hkfx, owner=admin)
hsbc, _ = Counterparty.objects.get_or_create(name="HSBC", code="HSBC")
print("Book created")

usdlibor3midx, _ = RateIndex.objects.get_or_create(name="USD LIBOR 3M", ccy=usd, defaults={
                                                   'index': 'LIBOR', 'tenor': '3M', 'day_counter': 'Actual360', 'yts': 'USD LIBOR'})
usdlibor6midx, _ = RateIndex.objects.get_or_create(name="USD LIBOR 6M", ccy=usd, defaults={
                                                   'index': 'LIBOR', 'tenor': '6M', 'day_counter': 'Actual360', 'yts': 'USD LIBOR'})
print('Rate index created')

# -------------------------------------------------------------------------------------
# cv_df = pd.read_csv('curve.csv' ,index_col = 'Term')
# cv = cv_df.drop(columns=['Shift','Shifted Rate','Zero Rate','Discount'])
# cv['Market Rate'] = cv['Market Rate'] * 0.01

# helpers = ql.RateHelperVector()
# simple_quote = []

# for term, textRate in cv.iterrows():
# term = term.replace(' ','')
# if term == '3MO':
# simple_quote.append( ql.SimpleQuote(float(textRate)) )
# helpers.append( ql.DepositRateHelper(ql.QuoteHandle(simple_quote[-1]), index) )
# elif term[:2] == 'ED':
# simple_quote.append( ql.SimpleQuote((1.0-float(textRate))*100) )
# helpers.append( ql.FuturesRateHelper(ql.QuoteHandle(simple_quote[-1]), ql.IMM.date(term[-2:]), index) )
# elif term[-2:] == 'YR':
# simple_quote.append( ql.SimpleQuote(float(textRate)) )
# swapIndex = ql.UsdLiborSwapIsdaFixAm(ql.Period(term.replace('YR','y')))
# helpers.append( ql.SwapRateHelper(ql.QuoteHandle(simple_quote[-1]), swapIndex))
# -------------------------------------------------------------------------------------

c = CurrencyRates()
for i in range(50):
    if d.weekday() < 500:
        xr = 1.12 * exp((random()-0.5)*0.5/sqrt(365))
        #FxSpotRateQuote.objects.get_or_create( ref_date=d, ccy_pair=eurusd, defaults={'rate': float(c.get_rate('EUR', 'USD', d))} )
        FxSpotRateQuote.objects.get_or_create(
            ref_date=d, ccy_pair=eurusd, defaults={'rate': float(xr)})
        FXVolatility.objects.get_or_create(
            ref_date=d, ccy_pair=eurusd, defaults={'vol': 0.08*xr})
        l3m = round(0.0024*xr, 4)
        usdlibor3m, _ = RateQuote.objects.update_or_create(
            name="USD LIBOR 3M", ref_date=d, tenor="3M", instrument="DEPO", ccy=usd, day_counter="Actual360", defaults={'rate': l3m})
        usdlibor6m, _ = RateQuote.objects.update_or_create(
            name="USD LIBOR 6M", ref_date=d, tenor="6M", instrument="DEPO", ccy=usd, day_counter="Actual360", defaults={'rate': round(0.0024*xr, 4)})
        usdlibor12m, _ = RateQuote.objects.update_or_create(
            name="USD LIBOR 12M", ref_date=d, tenor="12M", instrument="DEPO", ccy=usd, day_counter="Actual360", defaults={'rate': round(0.00241*xr, 4)})
        eurforex6m, _ = RateQuote.objects.update_or_create(
            name="EUR FOREX 6M", ref_date=d, tenor="6M", instrument="DEPO", ccy=eur, day_counter="Actual365Fixed", defaults={'rate': round(-0.001*xr, 4)})
        eurforex12m, _ = RateQuote.objects.update_or_create(
            name="EUR FOREX 12M", ref_date=d, tenor="12M", instrument="DEPO", ccy=eur, day_counter="Actual365Fixed", defaults={'rate': round(-0.0024*xr, 4)})

        usdlibor3mfixing, _ = RateIndexFixing.objects.update_or_create(
            index=usdlibor3midx, ref_date=d, defaults={'value': l3m})

        t, _ = IRTermStructure.objects.get_or_create(
            name="USD LIBOR", ref_date=d, ccy=usd, as_fx_curve=usd, as_rf_curve=usd)
        t.rates.add(usdlibor3m)
        t.rates.add(usdlibor6m)
        t.rates.add(usdlibor12m)
        t, _ = IRTermStructure.objects.get_or_create(
            name="EUR FOREX", ref_date=d, ccy=eur, as_fx_curve=eur, as_rf_curve=eur)
        t.rates.add(eurforex6m)
        t.rates.add(eurforex12m)

    d -= datetime.timedelta(days=1)
