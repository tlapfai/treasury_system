from django.test import TestCase
from swpm.models import *
import datetime
import QuantLib as ql

class FXOTestCase(TestCase):

    def setUp(self):
    
        d = datetime.date(2021,10,28)
        md = datetime.date(2021,12,28)

        cdr_us = Calendar.objects.create(name='UnitedStates')
        cdr_eu = Calendar.objects.create(name='TARGET')
        cdr_uk = Calendar.objects.create(name='UnitedKingdom')
        cdr_hk = Calendar.objects.create(name='HongKong')

        hkd = Ccy.objects.create(code="HKD", cdr=cdr_hk)
        cnh = Ccy.objects.create(code="CNH", cdr=cdr_hk)
        usd = Ccy.objects.create(code="USD", cdr=cdr_us)
        eur = Ccy.objects.create(code="EUR", cdr=cdr_eu)
        eurusd = CcyPair.objects.create(base_ccy=eur, quote_ccy=usd, cdr=cdr_us)
        usdhkd = CcyPair.objects.create(base_ccy=usd, quote_ccy=hkd, cdr=cdr_hk)

        spot = FxSpotRateQuote.objects.create(ref_date=d, rate=1.098, ccy_pair=eurusd)
        vol = FXVolatility.objects.create(ref_date=d, vol=0.08, ccy_pair=eurusd)
        r = RateQuote.objects.create(name='USD LIBOR 3M', rate=0.0021, tenor='3M', instrument='DEPO', ccy=usd, day_counter='A360')
        rTS = IRTermStructure.objects.create(name='USD LIBOR', ref_date=d, as_fx_curve=usd)
        rTS.rates.add(r)
        q = RateQuote.objects.create(name='EUR FX 3M', rate=-0.002, tenor='3M', instrument='DEPO', ccy=usd, day_counter='A365')
        qTS = IRTermStructure.objects.create(name='EUR FX', ref_date=d, as_fx_curve=eur)
        qTS.rates.add(r)
        opt = FXO.objects.create(trade_date=d, maturity_date=md, ccy_pair=eurusd, 
            strike_price=1.12, notional_1=100, notional_2=112, type='EUR', cp='C')

    def test_npv(self):
        d = datetime.date(2021,10,28)
        a = FxSpotRateQuote.objects.get(id=1)
        opt = FXO.objects.get(id=1)
        opt_inst = opt.instrument()
        engine = opt.make_pricing_engine(d)
        print(engine)
        opt_inst.setPricingEngine(engine)
        print(f'NPV is {opt_inst.NPV()}')
        self.assertEqual(a.rate, 1.098)
