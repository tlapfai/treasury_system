from django.test import TestCase
from swpm.models import *
import datetime
import QuantLib as ql


class MktDataSetTestCase(TestCase):

    def setUp(self):
        unitedstates, _ = Calendar.objects.get_or_create(name="UnitedStates")
        usd, _ = Ccy.objects.get_or_create(code="USD",
                                           defaults={'cal': unitedstates})

    def test_cv(self):
        mkt = MktDataSet('2021-11-18')
        ois = mkt.get_yts('USD', 'OIS')
        print(ois)


class FXOTestCase(TestCase):

    def setUp(self):

        d = datetime.date(2021, 10, 28)
        md = datetime.date(2021, 12, 28)

        hongkong, _ = Calendar.objects.get_or_create(name="HongKong")
        unitedstates, _ = Calendar.objects.get_or_create(name="UnitedStates")
        target, _ = Calendar.objects.get_or_create(name="TARGET")

        hkd, _ = Ccy.objects.get_or_create(code="EUR",
                                           defaults={'cal': hongkong})
        eur, _ = Ccy.objects.get_or_create(code="EUR",
                                           defaults={'cal': target})
        usd, _ = Ccy.objects.get_or_create(code="USD",
                                           defaults={'cal': unitedstates})
        eurusd, _ = CcyPair.objects.get_or_create(name="EUR/USD",
                                                  base_ccy=eur,
                                                  quote_ccy=usd)
        usdhkd, _ = CcyPair.objects.get_or_create(name="USD/HKD",
                                                  base_ccy=usd,
                                                  quote_ccy=hkd)

        spot = FxSpotRateQuote.objects.create(ref_date=d,
                                              rate=1.098,
                                              ccy_pair=eurusd)

        volSurf = FXVolatility.objects.create(ref_date=d, ccy_pair=eurusd)

        vol1 = FXVolatilityQuote.objects.create(ref_date=d,
                                                tenor='6M',
                                                delta=0.5,
                                                vol=0.02,
                                                surface=volSurf,
                                                delta_type='Spot')
        vol2 = FXVolatilityQuote.objects.create(ref_date=d,
                                                tenor='6M',
                                                delta=0.75,
                                                vol=0.02,
                                                surface=volSurf,
                                                delta_type='Spot')
        vol3 = FXVolatilityQuote.objects.create(ref_date=d,
                                                tenor='6M',
                                                delta=0.25,
                                                vol=0.02,
                                                surface=volSurf,
                                                delta_type='Spot')

        r = InterestRateQuote.objects.create(ref_date=d,
                                             name='USD OIS 6M',
                                             rate=0.0021,
                                             tenor='6M',
                                             instrument='OIS',
                                             ccy=usd,
                                             day_counter='Actual360')
        rTS = IRTermStructure.objects.create(name='OIS',
                                             ccy=usd,
                                             ref_date=d,
                                             as_fx_curve=usd,
                                             as_rf_curve=usd)
        rTS.rates.add(r)
        q = InterestRateQuote.objects.create(ref_date=d,
                                             name='EUR FOREX 6M',
                                             rate=-0.002,
                                             tenor='6M',
                                             instrument='FXSW',
                                             ccy=eur,
                                             ccy_pair=eurusd)
        qTS = IRTermStructure.objects.create(name='FOREX',
                                             ccy=eur,
                                             ref_date=d,
                                             as_fx_curve=eur)
        qTS.rates.add(r)
        opt = FXO.objects.create(trade_date=d,
                                 maturity_date=md,
                                 ccy_pair=eurusd,
                                 strike_price=1.098,
                                 notional_1=1000000,
                                 notional_2=1098000,
                                 type='EUR',
                                 cp='C',
                                 buy_sell='B')

    def test_npv(self):
        d = datetime.date(2021, 10, 28)
        ql.Settings.instance().evaluationDate = qlDate(d)
        mkt = MktDataSet(d.isoformat())
        fxspot = mkt.get_fxspot('EUR/USD')
        opt = FXO.objects.get(id=1)
        opt.link_mktdataset(mkt)
        opt_inst = opt.instrument()
        engine = opt.make_pricing_engine()
        opt_inst.setPricingEngine(engine)
        print(f'NPV is {opt_inst.NPV()}')
        print(f'Delta is {opt_inst.delta()}')
        self.assertEqual(fxspot.rate, 1.098)


class RateFixingTestCase(TestCase):

    def setUp(self):
        pass
