from bdb import effective
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
        pass


class FXOTestCase(TestCase):

    def setUp(self):

        d = datetime.date(2021, 10, 28)
        md = datetime.date(2021, 12, 28)

        hongkong, _ = Calendar.objects.get_or_create(name="HongKong")
        unitedstates, _ = Calendar.objects.get_or_create(name="UnitedStates")
        target, _ = Calendar.objects.get_or_create(name="TARGET")

        hkd = Ccy.objects.create(code="HKD", cal=hongkong)
        eur = Ccy.objects.create(code="EUR", cal=target)
        usd = Ccy.objects.create(code="USD", cal=unitedstates)
        eurusd = CcyPair.objects.create(name="EUR/USD",
                                        base_ccy=eur,
                                        quote_ccy=usd)
        usdhkd = CcyPair.objects.create(name="USD/HKD",
                                        base_ccy=usd,
                                        quote_ccy=hkd)

        spot = FxSpotRateQuote.objects.create(ref_date=d,
                                              rate=1.098,
                                              ccy_pair=eurusd)

        usdyts = IRTermStructure.objects.create(name='OIS',
                                                ccy=usd,
                                                ref_date=d,
                                                as_fx_curve=usd,
                                                as_rf_curve=usd)
        usdir = InterestRateQuote.objects.create(ref_date=d,
                                                 yts=usdyts,
                                                 name='USD OIS 6M',
                                                 rate=0.0021,
                                                 tenor='6M',
                                                 instrument='OIS',
                                                 ccy=usd,
                                                 day_counter='Actual360')
        euryts = IRTermStructure.objects.create(name='FOREX',
                                                ccy=eur,
                                                ref_date=d,
                                                as_fx_curve=eur,
                                                ref_ccy=usd,
                                                ref_curve='OIS')
        eurir = InterestRateQuote.objects.create(ref_date=d,
                                                 yts=euryts,
                                                 name='EUR FOREX 6M',
                                                 rate=-0.002,
                                                 tenor='6M',
                                                 instrument='FXSW',
                                                 ccy=eur,
                                                 ccy_pair=eurusd)

        volSurf = FXVolatility.objects.create(ref_date=d, ccy_pair=eurusd)

        vol1 = FXVolatilityQuote.objects.create(ref_date=d,
                                                tenor='6M',
                                                delta=0.5,
                                                value=0.02,
                                                surface=volSurf,
                                                delta_type='Spot')
        vol2 = FXVolatilityQuote.objects.create(ref_date=d,
                                                tenor='6M',
                                                delta=0.75,
                                                value=0.02,
                                                surface=volSurf,
                                                delta_type='Spot')
        vol3 = FXVolatilityQuote.objects.create(ref_date=d,
                                                tenor='6M',
                                                delta=0.25,
                                                value=0.02,
                                                surface=volSurf,
                                                delta_type='Spot')
        opt = FXO.objects.create(trade_date=d,
                                 maturity_date=md,
                                 ccy_pair=eurusd,
                                 strike_price=1.098,
                                 notional_1=1000000,
                                 notional_2=1098000,
                                 payoff_type='VAN',
                                 exercise_type='EUR',
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
        print(f'NPV is {opt.NPV():.2f}')
        print(f'Delta is {opt.delta():.2f}')
        self.assertEqual(fxspot.rate, 1.098)


class SwapTestCase(TestCase):

    def setUp(self):

        d = datetime.date(2021, 11, 18)
        md = datetime.date(2022, 11, 18)

        unitedstates = Calendar.objects.create(name="UnitedStates")
        usd = Ccy.objects.create(code="USD", cal=unitedstates)
        usdyts = IRTermStructure.objects.create(name='OIS',
                                                ccy=usd,
                                                ref_date=d,
                                                as_fx_curve=usd,
                                                as_rf_curve=usd)
        usdir = InterestRateQuote.objects.create(ref_date=d,
                                                 yts=usdyts,
                                                 name='USD OIS 6M',
                                                 rate=0.0021,
                                                 tenor='6M',
                                                 instrument='OIS',
                                                 ccy=usd,
                                                 day_counter='Actual360')
        swap = Swap.objects.create()
        sch6m = Schedule.objects.create(start_date=d,
                                        end_date=md,
                                        freq="6M",
                                        calendar=unitedstates)
        print(sch6m.schedule().calendar())
        leg_fix = SwapLeg.objects.create(trade=swap,
                                         pay_rec=1,
                                         ccy=usd,
                                         fixed_rate=0.01,
                                         schedule=sch6m,
                                         day_counter='Actual360',
                                         notional=1000000)
        leg_fix2 = SwapLeg.objects.create(trade=swap,
                                          pay_rec=-1,
                                          ccy=usd,
                                          fixed_rate=0.02,
                                          day_counter='Actual360',
                                          schedule=sch6m,
                                          notional=1000000)

    def test_npv(self):
        d = datetime.date(2021, 11, 18)
        mkt = MktDataSet(d)
        tr = Swap.objects.get(id=1)
        tr.link_mktdataset(mkt)
        leg_inst = leg.leg()
        eng = leg.make_pricing_engine()
        leg_inst.setPricingEngine(eng)
        npv = leg.npv()
