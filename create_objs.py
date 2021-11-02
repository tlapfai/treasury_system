from QuantLib.QuantLib import Cdor, Instrument
from django.db.models import base
from swpm.models import *
import datetime
from forex_python.converter import CurrencyRates

#Ccy.objects.all().delete()
#Calendar.objects.all().delete()

d = datetime.date(2021, 10, 31)

hongkong, _ = Calendar.objects.get_or_create(name="HongKong")
unitedstates, _ = Calendar.objects.get_or_create(name="UnitedStates")
target, _ = Calendar.objects.get_or_create(name="TARGET")

hkd, _ = Ccy.objects.get_or_create(code="EUR", defaults={'cdr': hongkong})
eur, _ = Ccy.objects.get_or_create(code="EUR", defaults={'cdr': target})
usd, _ = Ccy.objects.get_or_create(code="USD", defaults={'cdr': unitedstates})

eurusd, _ = CcyPair.objects.get_or_create(name="EUR/USD", base_ccy=eur, quote_ccy=usd, defaults={'cdr': target})
usdhkd, _ = CcyPair.objects.get_or_create(name="USD/HKD", base_ccy=usd, quote_ccy=hkd, defaults={'cdr': hongkong})
print("CcyPair created")

c = CurrencyRates()
for i in range(20):
    if d.weekday() < 5:
        FxSpotRateQuote.objects.get_or_create( ref_date=d, ccy_pair=eurusd, defaults={'rate': float(c.get_rate('EUR', 'USD', d))} )
        FXVolatility.objects.get_or_create( ref_date=d, ccy_pair=eurusd, defaults={'vol': 0.08} )
        usdlibor6m = RateQuote.objects.create(name="USD LIBOR 6M", ref_date=d, rate=0.0024, tenor="6M", instrument="DEPO", ccy=usd, day_counter="A360")
        usdlibor12m = RateQuote.objects.create(name="USD LIBOR 12M", ref_date=d, rate=0.0024, tenor="12M", instrument="DEPO", ccy=usd, day_counter="A360")
        eurforex6m = RateQuote.objects.create(name="EUR FOREX 6M", ref_date=d, rate=-0.001, tenor="6M", instrument="DEPO", ccy=eur, day_counter="A365Fixed")
        eurforex12m = RateQuote.objects.create(name="EUR FOREX 12M", ref_date=d, rate=-0.001, tenor="12M", instrument="DEPO", ccy=eur, day_counter="A365Fixed")

        t = IRTermStructure.objects.create(name="USD LIBOR", ref_date=d, as_fx_curve=usd, as_rf_curve=usd)
        t.rates.add(usdlibor6m)
        t.rates.add(usdlibor12m)
        t = IRTermStructure.objects.create(name="EUR FOREX", ref_date=d, as_fx_curve=eur, as_rf_curve=eur)
        t.rates.add(eurforex6m)
        t.rates.add(eurforex12m)

    d -= datetime.timedelta(days=1)
