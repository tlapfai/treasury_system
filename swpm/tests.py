from django.test import TestCase
from swpm.models import *
import datetime
import QuantLib as ql


class FXOTestCase(TestCase):

    def setUp(self):

        d = datetime.date(2021, 10, 28)
        md = datetime.date(2021, 12, 28)

        hongkong, _ = Calendar.objects.get_or_create(name="HongKong")
        unitedstates, _ = Calendar.objects.get_or_create(name="UnitedStates")
        target, _ = Calendar.objects.get_or_create(name="TARGET")

        hkd, _ = Ccy.objects.get_or_create(
            code="EUR", defaults={'cdr': hongkong})
        eur, _ = Ccy.objects.get_or_create(
            code="EUR", defaults={'cdr': target})
        usd, _ = Ccy.objects.get_or_create(
            code="USD", defaults={'cdr': unitedstates})
        eurusd, _ = CcyPair.objects.get_or_create(
            name="EUR/USD", base_ccy=eur, quote_ccy=usd, defaults={'cdr': target})
        usdhkd, _ = CcyPair.objects.get_or_create(
            name="USD/HKD", base_ccy=usd, quote_ccy=hkd, defaults={'cdr': hongkong})

        spot = FxSpotRateQuote.objects.create(
            ref_date=d, rate=1.098, ccy_pair=eurusd)
        vol = FXVolatility.objects.create(
            ref_date=d, vol=0.08, ccy_pair=eurusd)
        r = RateQuote.objects.create(ref_date=d, name='USD LIBOR 6M', rate=0.0021,
                                     tenor='6M', instrument='DEPO', ccy=usd, day_counter='Actual360')
        rTS = IRTermStructure.objects.create(
            name='USD LIBOR', ref_date=d, as_fx_curve=usd)
        rTS.rates.add(r)
        q = RateQuote.objects.create(ref_date=d, name='EUR FX 3M', rate=-0.002,
                                     tenor='3M', instrument='DEPO', ccy=usd, day_counter='Actual365Fixed')
        qTS = IRTermStructure.objects.create(
            name='EUR FX', ref_date=d, as_fx_curve=eur)
        qTS.rates.add(r)
        opt = FXO.objects.create(trade_date=d, maturity_date=md, ccy_pair=eurusd,
                                 strike_price=1.12, notional_1=1000000, notional_2=1120000, type='EUR', cp='C')

    def test_npv(self):
        d = datetime.date(2021, 10, 28)
        a = FxSpotRateQuote.objects.get(id=1)
        opt = FXO.objects.get(id=1)
        opt_inst = opt.instrument()
        engine = opt.make_pricing_engine(d)
        print(engine)
        opt_inst.setPricingEngine(engine)
        print(f'NPV is {opt_inst.NPV()}')
        self.assertEqual(a.rate, 1.098)


class RateFixingTestCase(TestCase):
    def setUp(self):
        pass
