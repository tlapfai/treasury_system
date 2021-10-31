from QuantLib.QuantLib import Cdor, Instrument
from django.db.models import base
from swpm.models import *
import datetime

Ccy.objects.all().delete()
Calendar.objects.all().delete()

d = datetime.date(2021, 10, 31)

Calendar.objects.create(name="HongKong")
Calendar.objects.create(name="UnitedStates")
Calendar.objects.create(name="TARGET")

Ccy.objects.create(code="EUR", cdr=Calendar.objects.get(name="TARGET"))
Ccy.objects.create(code="USD", cdr=Calendar.objects.get(name="UnitedStates"))

CcyPair.objects.create(name="EUR/USD", 
    base_ccy=Ccy.objects.get(code="EUR"),
    quote_ccy=Ccy.objects.get(code="USD"),
    cdr=Calendar.objects.get(name="TARGET")
    )
print("CcyPair created")

FxSpotRateQuote.objects.create(ref_date=d,
    rate=1.1, 
    ccy_pair=CcyPair.objects.get(name="EUR/USD")
    )

RateQuote.objects.create(name="USD LIBOR 6M",
    ref_date=d,
    rate=0.0024, 
    tenor="6M",
    instrument="DEPO",
    ccy=Ccy.objects.get(code="USD"),
    day_counter="A360"
    )

RateQuote.objects.create(name="EUR FOREX 6M",
    ref_date=d,
    rate=-0.001, 
    tenor="6M",
    instrument="DEPO",
    ccy=Ccy.objects.get(code="EUR"),
    day_counter="A365Fixed"
    )

t = IRTermStructure.objects.create(name="USD LIBOR", 
    ref_date=d,
    as_fx_curve=Ccy.objects.get(code="USD"), 
    as_rf_curve=Ccy.objects.get(code="USD")
    )
t.rates.add(RateQuote.objects.get(name="USD LIBOR 6M"))

t2 = IRTermStructure.objects.create(name="EUR FOREX", 
    ref_date=d,
    as_fx_curve=Ccy.objects.get(code="EUR"), 
    as_rf_curve=Ccy.objects.get(code="EUR")
    )
t2.rates.add(RateQuote.objects.get(name="EUR FOREX 6M"))

FXVolatility.objects.create(
    ref_date=d,
    ccy_pair=CcyPair.objects.get(name="EUR/USD"), 
    vol=0.08
    )