import datetime
from QuantLib.QuantLib import PiecewiseLogLinearDiscount, RealTimeSeries
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import query_utils
from django.db.models.base import Model
from django.db.models.deletion import CASCADE, DO_NOTHING, SET_NULL, SET_DEFAULT
from django.db.models.fields.related import ForeignKey
from django.utils import timezone
from django.utils.translation import gettext as _
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core import validators
from django.core.validators import RegexValidator, MinValueValidator, DecimalValidator
from django.core.cache import caches, cache

import QuantLib as ql
from numpy import isin
import pandas as pd
import math, time

PAYOFF_TYPE = [('VAN', 'Vanilla'), ('DIG', 'Digital'), ("BAR", "Barrier")]

EXERCISE_TYPE = [("EUR", "European"), ("AME", "American")]

FXO_CP = [("C", "Call"), ("P", "Put")]

SWAP_PAY_REC = [(ql.VanillaSwap.Receiver, "Receive"),
                (ql.VanillaSwap.Payer, "Pay")]

BUY_SELL = [("B", "Buy"), ("S", "Sell")]

CHOICE_DAY_COUNTER = models.TextChoices(
    'DAY_COUNTER',
    ['Actual360', 'Actual365Fixed', 'ActualActual', 'Thirty360'])
QL_DAY_COUNTER = {
    "Actual360": ql.Actual360(),
    'Actual365Fixed': ql.Actual365Fixed(),
    'ActualActual': ql.ActualActual(),
    'Thirty360': ql.Thirty360()
}

CHOICE_DAY_RULE = models.TextChoices('DAY_RULE', [
    'Following', 'ModifiedFollowing', 'Preceding', 'ModifiedPreceding',
    'Unadjusted'
])
QL_DAY_RULE = {
    'Following': ql.Following,
    'ModifiedFollowing': ql.ModifiedFollowing,
    'Preceding': ql.Preceding,
    'ModifiedPreceding': ql.ModifiedPreceding,
    'Unadjusted': ql.Unadjusted
}

CHOICE_DELTA_TYPE = models.TextChoices('DELTA_TYPE',
                                       ['Spot', 'PaSpot', 'Fwd', 'PaFwd'])
QL_DELTA_TYPE = {
    'Spot': ql.DeltaVolQuote.Spot,
    'PaSpot': ql.DeltaVolQuote.PaSpot,
    'PaFwd': ql.DeltaVolQuote.PaFwd,
    'Fwd': ql.DeltaVolQuote.Fwd
}

# https://docs.djangoproject.com/en/3.2/ref/models/fields/#enumeration-types

QL_CALENDAR = {
    'NullCalendar': ql.NullCalendar(),
    'WeekendsOnly': ql.WeekendsOnly(),
    'TARGET': ql.TARGET(),
    'UnitedStates': ql.UnitedStates(),
    'HongKong': ql.HongKong(),
    'UnitedKingdom': ql.UnitedKingdom()
}


def validate_positive(value):
    if value <= 0:
        raise ValidationError(_('Must be positive'), code='non_positive')


# class PositiveFloatField(models.Field):
#     default_validators = [validate_positive]
#     def validate(self, value):
#         super().validate(value)


def qlDate(d) -> ql.Date:
    if isinstance(d, str):
        return ql.DateParser.parseISO(d)
    elif isinstance(d, list):
        return [qlDate(dd) for dd in d]
    else:
        return ql.DateParser.parseISO(d.isoformat())


def str2date(s):
    if isinstance(s, datetime.date):
        return s
    elif len(s) == 10:
        return datetime.datetime.strptime(s, '%Y-%m-%d')
    elif len(str(s)) == 8:
        return datetime.datetime.strptime(str(s), '%Y%m%d')


class User(AbstractUser):
    pass


class Calendar(models.Model):
    name = models.CharField(max_length=24, primary_key=True)

    def __str__(self):
        return self.name

    #@property
    def calendar(self):
        return QL_CALENDAR.get(self.name)


class Ccy(models.Model):
    code = models.CharField(max_length=3, blank=False, primary_key=True)
    fixing_days = models.PositiveIntegerField(default=2)
    cal = models.ForeignKey(Calendar, DO_NOTHING, null=True)
    risk_free_curve = models.CharField(max_length=16, blank=True,
                                       null=True)  # free text
    foreign_exchange_curve = models.CharField(max_length=16,
                                              blank=True,
                                              null=True)  # free text
    rate_day_counter = models.CharField(max_length=24,
                                        blank=True,
                                        null=True,
                                        default=None)  # free text

    def __str__(self):
        return self.code

    def calendar(self):
        if self.cal:
            return self.cal.calendar()
        else:
            return ql.NullCalendar()


class CcyPair(models.Model):
    """ .quotes to get FxSpotRateQuote """
    name = models.CharField(max_length=7, primary_key=True)
    base_ccy = models.ForeignKey(Ccy, CASCADE, related_name="as_base_ccy")
    quote_ccy = models.ForeignKey(Ccy, CASCADE, related_name="as_quote_ccy")
    cal = models.ForeignKey(Calendar,
                            SET_NULL,
                            related_name="ccy_pairs",
                            null=True)
    fixing_days = models.PositiveIntegerField(default=2)

    def check_order():
        # check correct order
        return True

    def __str__(self):
        return f"{self.base_ccy}/{self.quote_ccy}"

    def get_quote(self, date):
        return self.quotes.get(ref_date=date)

    def calendar(self):
        if self.cal:
            return self.cal.calendar()
        else:
            return ql.JointCalendar(self.base_ccy.calendar(),
                                    self.quote_ccy.calendar())

    def fx_curves(self, ref_date):
        rts = self.quote_ccy.fx_curve.get(ref_date=ref_date).term_structure()
        qts = self.base_ccy.fx_curve.get(ref_date=ref_date).term_structure()
        return rts, qts


def with_mktdataset(mktdata):

    def link_mktdataset(self, mktdataset):
        self.mktdataset = mktdataset

    mktdata.mktdataset = None
    mktdata.link_mktdataset = link_mktdataset
    return mktdata


@with_mktdataset
class FxSpotRateQuote(models.Model):
    ref_date = models.DateField()
    rate = models.FloatField()
    ccy_pair = models.ForeignKey(CcyPair, CASCADE, related_name="quotes")

    class Meta:
        unique_together = ('ref_date', 'ccy_pair')

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.rts = None
        self.qts = None
        self.quote = ql.SimpleQuote(self.rate)

    def set_yts(self, rts=None, qts=None):
        if rts:
            self.rts = rts
        if qts:
            self.qts = qts

    def setQuote(self, value):
        self.quote = ql.SimpleQuote(value)

    def resetQuote(self):
        self.quote = ql.SimpleQuote(self.rate)

    def handle(self):
        return ql.QuoteHandle(self.quote)

    def spot_date(self):
        return self.ccy_pair.calendar().advance(
            qlDate(self.ref_date), ql.Period(self.ccy_pair.fixing_days,
                                             ql.Days))

    def forward_rate(self, maturity) -> float:
        sd = self.spot_date()
        if self.rts == None or self.qts == None:
            self.rts, self.qts = self.ccy_pair.fx_curves(self.ref_date)
        return self.quote.value() / self.rts.discount(
            qlDate(maturity)) * self.rts.discount(sd) * self.qts.discount(
                qlDate(maturity)) / self.qts.discount(sd)

    def today_rate(self) -> float:
        return self.forward_rate(self.ref_date)

    def spot0_handle(self):
        return ql.QuoteHandle(ql.SimpleQuote(self.today_rate()))

    def __str__(self):
        return f"{self.ccy_pair} as of {self.ref_date}"


@with_mktdataset
class InterestRateQuote(models.Model):
    name = models.CharField(max_length=16)  # e.g. USD OIS 12M
    ref_date = models.DateField()
    yts = models.ForeignKey("IRTermStructure",
                            CASCADE,
                            null=True,
                            blank=True,
                            related_name="rates")
    rate = models.DecimalField(max_digits=12, decimal_places=8)
    tenor = models.CharField(max_length=5)
    instrument = models.CharField(max_length=5)
    ccy = models.ForeignKey(Ccy, CASCADE, related_name="rates")
    day_counter = models.CharField(max_length=16,
                                   choices=CHOICE_DAY_COUNTER.choices,
                                   null=True,
                                   blank=True)
    ccy_pair = models.ForeignKey(CcyPair, CASCADE, null=True, blank=True)

    # index = models.ForeignKey(RateIndex, DO_NOTHING, null=True, blank=True) # RateIndex is not defined yet above this model

    class Meta:
        unique_together = ('name', 'tenor', 'ref_date')

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.helper_obj = None

    def helper(self, **kwargs):
        if self.helper_obj:
            return self.helper_obj

        mkt = kwargs.get('mktdataset')
        if mkt:
            self.mktdataset = mkt
        elif self.mktdataset == None:
            self.mktdataset = MktDataSet(self.ref_date)

        q = ql.QuoteHandle(ql.SimpleQuote(float(self.rate)))
        if self.tenor in ['ON', 'TN']:
            tenor_ = ql.Period('1D')
            fixing_days = 0 if self.tenor == 'ON' else 1
        else:
            tenor_ = None if self.instrument == "FUT" else ql.Period(
                self.tenor)
            fixing_days = None

        if self.instrument == "DEPO":
            fixing_days = self.ccy.fixing_days
            convention = ql.ModifiedFollowing
            ccy = Ccy.objects.get(code=self.ccy)
            return ql.DepositRateHelper(self.rate, tenor_, fixing_days,
                                        ccy.calendar(), convention, False,
                                        QL_DAY_COUNTER[self.day_counter]), q
        elif self.instrument == "FUT":
            if self.tenor[:2] == 'ED':
                return ql.FuturesRateHelper(q, ql.IMM.date(self.tenor[2:4]),
                                            ql.USDLibor(ql.Period('3M'))), q
        elif self.instrument == "SWAP":
            if self.ccy.code == "USD":  # https://quant.stackexchange.com/questions/32345/quantlib-python-dual-curve-bootstrapping-example
                swapIndex = ql.UsdLiborSwapIsdaFixAm(tenor_)
                ref_curve = kwargs.get('ref_curve')  # is a handle
                if ref_curve:
                    return ql.SwapRateHelper(q, swapIndex, 0, ql.Period(),
                                             ref_curve), q
                else:
                    return ql.SwapRateHelper(q, swapIndex), q
        elif self.instrument == "OIS":
            if self.ccy.code == "USD":
                if self.tenor == '1D':
                    return ql.DepositRateHelper(q, tenor_, 0, ql.TARGET(),
                                                ql.Following, False,
                                                ql.Actual360()), q
                else:
                    overnight_index = ql.FedFunds()
                    settlementDays = 2
                    self.helper_obj = ql.OISRateHelper(
                        2,
                        tenor_,
                        q,
                        overnight_index,
                        paymentLag=0,
                        paymentCalendar=ql.UnitedStates()), q
                    return self.helper_obj
        elif self.instrument == "FXSW":  # ql.FxSwapRateHelper(fwdPoint, spotFx, tenor, fixingDays, calendar, convention, endOfMonth, isFxBaseCurrencyCollateralCurrency, collateralCurve)
            if self.ccy_pair:
                ref_curve = kwargs.get('ref_curve')  # is a handle, from kwargs
                fixing_days = self.ccy_pair.fixing_days if fixing_days == None else fixing_days
                s = self.mktdataset.get_fxspot(self.ccy_pair.name)
                return ql.FxSwapRateHelper(q, s.handle(), tenor_, fixing_days,
                                           self.ccy_pair.calendar(),
                                           ql.Following, True,
                                           self.ccy == self.ccy_pair.quote_ccy,
                                           ref_curve), q
            else:
                raise KeyError(
                    'CcyPair does not exist in FXSW type rate quote')

    def __str__(self):
        return f"{self.name} as of {self.ref_date.strftime('%Y-%m-%d')}: {self.rate}"


@with_mktdataset
class IRTermStructure(models.Model):
    name = models.CharField(max_length=16)
    ref_date = models.DateField()
    ccy = models.ForeignKey(Ccy,
                            CASCADE,
                            related_name="all_curves",
                            null=True,
                            blank=True)
    #rates = models.ManyToManyField(InterestRateQuote, related_name="ts")
    as_fx_curve = models.ForeignKey(Ccy,
                                    CASCADE,
                                    related_name="fx_curve",
                                    null=True,
                                    blank=True)
    as_rf_curve = models.ForeignKey(Ccy,
                                    CASCADE,
                                    related_name="rf_curve",
                                    null=True,
                                    blank=True)
    ref_ccy = models.ForeignKey(Ccy, CASCADE, null=True, blank=True)
    ref_curve = models.CharField(max_length=16, null=True, blank=True)

    class Meta:
        unique_together = ('name', 'ref_date', 'ccy')

    def __init__(self, *args, **kwargs) -> None:
        self.yts = None
        super().__init__(*args, **kwargs)
        print(f'Called __init__() of {self.name} {self.ref_date} {self.ccy}')

    def term_structure(self):
        if self.yts:
            return self.yts

        if self.mktdataset == None:
            self.mktdataset = MktDataSet(self.ref_date)

        ref_curve_ = None
        if self.ref_curve and self.ref_ccy:
            ref_curve_ = self.mktdataset.get_yts(self.ref_ccy.code,
                                                 self.ref_curve)
        ref_yts_handle = ql.YieldTermStructureHandle(ref_curve_)
        helpers = [
            r.helper(ref_curve=ref_yts_handle, mktdataset=self.mktdataset)[0]
            for r in self.rates.all()
        ]
        self.yts = ql.PiecewiseLogLinearDiscount(qlDate(self.ref_date),
                                                 helpers, ql.Actual365Fixed())
        self.yts.enableExtrapolation()
        return self.yts

    def __str__(self):
        return f"{self.ccy} {self.name} as of {self.ref_date.strftime('%Y-%m-%d')}"


class RateIndex(models.Model):
    name = models.CharField(max_length=16, primary_key=True)
    ccy = models.ForeignKey(Ccy, CASCADE, related_name="rate_indexes")
    index = models.CharField(max_length=16)
    tenor = models.CharField(max_length=16)
    day_counter = models.CharField(max_length=16,
                                   choices=CHOICE_DAY_COUNTER.choices,
                                   null=True,
                                   blank=True)
    yts = models.CharField(max_length=16, null=True, blank=True)

    class Meta:
        unique_together = ('name', 'tenor')

    def __str__(self):
        return self.name

    def get_index(self, ref_date=None, eff_date=None):
        if 'USD LIBOR' in self.name:
            idx_cls = ql.USDLibor
        elif 'USD EFFR' in self.name:
            idx_cls = ql.OvernightIndex

        if ref_date:
            yts = IRTermStructure.objects.get(
                name=self.yts, ref_date=ref_date).term_structure()

        if 'USD LIBOR' in self.name:
            if yts:
                idx_obj = idx_cls(ql.Period(self.tenor),
                                  ql.YieldTermStructureHandle(yts))
            else:
                idx_obj = idx_cls(ql.Period(self.tenor))
        elif 'USD EFFR' in self.name:
            if yts:
                idx_obj = idx_cls('USD EFFR', 1, ql.USDCurrency(),
                                  ql.Actual360(),
                                  ql.YieldTermStructureHandle(yts))
            else:
                idx_obj = idx_cls('USD EFFR', 1, ql.USDCurrency(),
                                  ql.Actual360())

        if eff_date:
            first_fixing_date = idx_obj.fixingDate(qlDate(eff_date))
            for f in self.fixings.filter(
                    ref_date__gte=first_fixing_date.ISO()):
                idx_obj.addFixings([qlDate(f.ref_date)], [f.value])

        return idx_obj


class RateIndexFixing(models.Model):
    value = models.FloatField()
    index = models.ForeignKey(RateIndex, CASCADE, related_name="fixings")
    ref_date = models.DateField()

    class Meta:
        unique_together = ('ref_date', 'index')

    def __str__(self):
        return f'{self.index} on {self.ref_date}'


@with_mktdataset
class FXVolatility(models.Model):
    """ use .quotes to get quotes """
    ref_date = models.DateField()
    ccy_pair = models.ForeignKey(CcyPair, CASCADE, related_name='vol')

    class Meta:
        verbose_name_plural = "FX volatilities"
        unique_together = ('ref_date', 'ccy_pair')

    class TargetFun:

        def __init__(self, ref_date, spot, rdf, qdf, strike, maturity, deltas,
                     delta_types, smile_section):
            self.ref_date = ref_date
            self.strike = strike
            self.maturity = qlDate(maturity)
            self.s0 = spot
            self.rDcf = rdf
            self.qDcf = qdf
            self.t = ql.Actual365Fixed().yearFraction(qlDate(self.ref_date),
                                                      self.maturity)

            for i, delta_type in enumerate(delta_types):
                if not delta_type == ql.DeltaVolQuote.Spot:
                    stdDev = math.sqrt(self.t) * smile_section[i]
                    calc = ql.BlackDeltaCalculator(ql.Option.Call, delta_type,
                                                   self.s0, self.rDcf,
                                                   self.qDcf, stdDev)
                    k = calc.strikeFromDelta(deltas[i])
                    calc = ql.BlackDeltaCalculator(ql.Option.Call,
                                                   ql.DeltaVolQuote.Spot,
                                                   self.s0, self.rDcf,
                                                   self.qDcf, stdDev)
                    deltas[i] = calc.deltaFromStrike(k)

            self.delta_types = ql.DeltaVolQuote.Spot
            self.interp = ql.LinearInterpolation(deltas, smile_section)

        def __call__(self, v0):
            optionType = ql.Option.Call
            stdDev = math.sqrt(self.t) * v0
            calc = ql.BlackDeltaCalculator(optionType, self.delta_types,
                                           self.s0, self.rDcf, self.qDcf,
                                           stdDev)
            d = calc.deltaFromStrike(self.strike)
            v = self.interp(d, allowExtrapolation=True)
            return (v - v0)

    def __init__(self, *args, **kwargs) -> None:
        self.rts = None
        self.qts = None
        self.spot = None
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"{self.ccy_pair} as of {self.ref_date}"

    def surface_matrix(self):
        obj = cache.get(f'{self.ref_date}-{self.ccy_pair}', None)
        if not obj:
            maturities = []
            surf_vol = []
            surf_delta = []
            surf_delta_type = []
            prev_t = None  # datetime.date
            row = -1
            for q in self.quotes.all().order_by('maturity', 'delta'):
                if q.maturity == prev_t:
                    surf_vol[row].append(q.value)
                    surf_delta[row].append(q.delta)
                    surf_delta_type[row].append(QL_DELTA_TYPE[q.delta_type])
                else:
                    surf_vol.append([q.value])
                    surf_delta.append([q.delta])
                    surf_delta_type.append([QL_DELTA_TYPE[q.delta_type]])
                    maturities.append(q.maturity)
                    row += 1
                prev_t = q.maturity
            obj = surf_vol, surf_delta, surf_delta_type, maturities
            cache.set(f'{self.ref_date}-{self.ccy_pair}', obj)
        return obj

    def set_yts(self, rts, qts):
        if rts:
            self.rts = rts
        if qts:
            self.qts = qts

    def set_spot(self, spot: FxSpotRateQuote):
        self.spot = spot  # FxSpotRateQuote

    def handle(self, strike, **kwargs):

        surf_vol, surf_delta, surf_delta_type, maturities = self.surface_matrix(
        )

        if self.mktdataset == None:
            self.mktdataset = MktDataSet(self.ref_date)

        solver = ql.Brent()
        accuracy = 1e-12
        step = 1e-6
        volatilities = []
        """if kwargs.get('maturity'):
            mat = kwargs.get('maturity')
            ii = []
            ii.append(max([j for j, m in maturities if m <= qlDate(mat)]))
            ii.append(min([j for j, m in maturities if m >= qlDate(mat)]))
            surf_vol = [surf_vol[i_] for i_ in ii if i_]
            surf_delta = [surf_delta[i_] for i_ in ii if i_]
            surf_delta_type = [surf_delta_type[i_] for i_ in ii if i_]
            maturities = [maturities[i_] for i_ in ii if i_]"""

        if self.spot == None:
            self.spot = self.mktdataset.get_fxspot(self.ccy_pair.name)
        s0 = self.spot.today_rate()

        if self.rts == None:  # yts is the slowest part
            ccy = self.ccy_pair.quote_ccy.code
            cvname = self.mktdataset.get_fxyts_name(ccy)
            self.rts = self.mktdataset.get_yts(ccy, cvname)
        if self.qts == None:
            ccy = self.ccy_pair.base_ccy.code
            cvname = self.mktdataset.get_fxyts_name(ccy)
            self.qts = self.mktdataset.get_yts(ccy, cvname)

        spread = 0.
        if kwargs.get('spread'):
            spread = kwargs.get('spread')

        for i, smile in enumerate(surf_vol):
            mat = qlDate(maturities[i])
            target = self.TargetFun(self.ref_date, s0, self.rts.discount(mat),
                                    self.qts.discount(mat), strike,
                                    maturities[i], surf_delta[i],
                                    surf_delta_type[i], smile)
            guess = smile[2]
            volatilities.append(
                solver.solve(target, accuracy, guess, step) + spread)
        vts = ql.BlackVarianceCurve(qlDate(self.ref_date), qlDate(maturities),
                                    volatilities, ql.Actual365Fixed(), False)
        vts.enableExtrapolation()

        return ql.BlackVolTermStructureHandle(vts)
        # spread = ql.QuoteHandle(ql.SimpleQuote(0.0000))
        # return ql.BlackVolTermStructureHandle(
        #     ql.ZeroSpreadedTermStructure(v, spread))

    def surface_dataframe(self):
        surf_vol, surf_delta, surf_delta_type, maturities = self.surface_matrix(
        )
        smiles_temp = [
            pd.DataFrame([smile], columns=surf_delta[i], index=[maturities[i]])
            for i, smile in enumerate(surf_vol)
        ]
        return pd.concat(smiles_temp)


""" class FXVolatilitySmile(models.Model):
    CHOICE_ATM_TYPE = models.TextChoices(
        'ATM_TYPE', ['Spot', 'Fwd', 'PaSpot', 'PaFwd'])
    tenor = models.CharField(max_length=6)
    fx_volatility = models.ForeignKey(
        FXVolatility, CASCADE, related_name='smiles')
    delta_type = models.CharField(max_length=6, choices=CHOICE_ATM_TYPE)
    atm_type = models.CharField(max_length=20, choices=[
                                'AtmNull', 'AtmSpot', 'AtmFwd', 'AtmDeltaNeutral'])

    def __str__(self):
        return f"{self.fx_volatility.ccy_pair} {self.tenor} smile"

    def ql_period(self):
        return ql.Period(self.tenor)

    def ql_delta_vol_quote(self):
        return ql.DeltaVolQuote() """


class FXVolatilityQuote(models.Model):
    ref_date = models.DateField()
    tenor = models.CharField(max_length=6)
    delta = models.FloatField(
        error_messages={'required': 'Delta value is required.'})
    value = models.FloatField(validators=[validate_positive])
    surface = models.ForeignKey(FXVolatility, CASCADE, related_name='quotes')
    delta_type = models.CharField(choices=CHOICE_DELTA_TYPE.choices,
                                  max_length=8,
                                  null=True)
    maturity = models.DateField(null=True, blank=True)

    def save(self, *args, **kwargs):
        self.maturity = (qlDate(self.ref_date) + ql.Period(self.tenor)).ISO()
        if self.delta < 0:
            self.delta = round(1.0 + self.delta, 8)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.ref_date}, {self.tenor}, {self.delta}'


class FXOManager(models.Manager):

    def create_fxo(self, trade_date, maturity_date, ccy_pair, strike_price,
                   type, cp, notional_1):
        fxo = self.create(trade_date=trade_date,
                          maturity_date=maturity_date,
                          ccy_pair=ccy_pair,
                          strike_price=strike_price,
                          type=type,
                          cp=cp,
                          notional_1=notional_1,
                          notional_2=notional_1 * strike_price)
        return fxo


class Portfolio(models.Model):
    name = models.CharField(max_length=16, primary_key=True)

    def __str__(self) -> str:
        return self.name


class Book(models.Model):
    name = models.CharField(max_length=16, primary_key=True)
    portfolio = models.ForeignKey(Portfolio, DO_NOTHING, related_name="books")
    owner = models.ForeignKey(User,
                              DO_NOTHING,
                              null=True,
                              related_name="books")

    def __str__(self) -> str:
        return self.name


class Counterparty(models.Model):
    code = models.CharField(max_length=16, primary_key=True)
    name = models.CharField(max_length=64)
    is_internal = models.OneToOneField(Book,
                                       DO_NOTHING,
                                       null=True,
                                       blank=True,
                                       related_name="internal_cpty")

    class Meta:
        verbose_name_plural = "Counterparties"

    def __str__(self) -> str:
        return self.name


class TradeDetail(models.Model):
    # trade = models.ForeignKey(FXO, CASCADE, related_name="detail")
    # def __str__(self) -> str:
    #     return f"ID: {self.trade.id}"
    pass


class TradeMarkToMarket(models.Model):
    as_of = models.DateField()
    trade_d = models.ForeignKey(TradeDetail,
                                CASCADE,
                                null=True,
                                related_name="mtms")
    npv = models.FloatField(null=True)
    delta = models.FloatField(null=True)
    gamma = models.FloatField(null=True)
    vega = models.FloatField(null=True)

    class Meta:
        unique_together = ('as_of', 'trade_d')

    def __str__(self):
        return f"Trade {self.trade_d.trade.first().id} NPV={self.npv:.2f} as of {self.as_of}"


class Trade(models.Model):
    id = models.BigAutoField(primary_key=True)
    active = models.BooleanField(default=True)
    create_time = models.DateTimeField(auto_now_add=True)
    trade_date = models.DateField(null=False, default=datetime.date.today)
    value_date = models.DateField(null=False, default=datetime.date.today)
    pl_ccy = models.ForeignKey(Ccy, CASCADE, null=True, blank=True)
    detail = models.OneToOneField(TradeDetail, CASCADE, null=True)
    book = models.ForeignKey(Book,
                             SET_NULL,
                             null=True,
                             blank=True,
                             related_name="trades")
    input_user = models.ForeignKey(User,
                                   SET_NULL,
                                   null=True,
                                   related_name='input_trades')
    counterparty = models.ForeignKey(Counterparty,
                                     SET_NULL,
                                     related_name="trade_set",
                                     null=True,
                                     blank=True)

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        if Swap.objects.filter(trade_ptr=self):
            Swap.objects.filter(trade_ptr=self).delete()
        elif FXO.objects.filter(trade_ptr=self):
            FXO.objects.filter(trade_ptr=self).delete()
        if self.detail:
            self.detail.delete()

    # class Meta:
    # abstract = True
    # ordering = ['id']
    # def save(self, *args, **kwargs):
    #     if self.detail == None:
    #         d = TradeDetail.objects.create()
    #         d.save()
    #         self.detail = d
    #     super().save(*args, **kwargs)


class CashFlow(models.Model):
    ccy = models.ForeignKey(Ccy, CASCADE)
    amount = models.FloatField(default=0)
    trade = models.ForeignKey(Trade, CASCADE, null=True, blank=True)


class FXOPricingSets:
    pass


def has_make_pricing_engine(trade):

    def make_pricing_engine(self, as_of, **kwargs):
        if self.active:
            try:
                spot_rate = ql.QuoteHandle(
                    ql.SimpleQuote(
                        self.ccy_pair.rates.get(ref_date=as_of).today_rate()))
                v = self.ccy_pair.vol.get(ref_date=as_of).handle(
                    kwargs.get('strike'))
                q = self.ccy_pair.base_ccy.fx_curve.get(
                    ref_date=as_of).term_structure()
                r = self.ccy_pair.quote_ccy.fx_curve.get(
                    ref_date=as_of).term_structure()
                process = ql.BlackScholesMertonProcess(
                    spot_rate, ql.YieldTermStructureHandle(q),
                    ql.YieldTermStructureHandle(r), v)
                return ql.AnalyticEuropeanEngine(process), process
            except ObjectDoesNotExist as error:
                raise error

    trade.make_pricing_engine = make_pricing_engine
    return trade


class FXOBarrierDetail(models.Model):
    trade = models.ForeignKey("FXO", CASCADE)
    barrier_start = models.DateField(null=True, blank=True)
    barrier_end = models.DateField(null=True, blank=True)
    upper_barrier_level = models.FloatField(validators=[validate_positive])
    lower_barrier_level = models.FloatField(validators=[validate_positive])
    rebate = models.FloatField(default=0)
    rebate_at_hit = models.BooleanField()
    payoff_at_hit = models.BooleanField()


@with_mktdataset
class FXO(Trade):
    product_type = models.CharField(max_length=12, default="FXO")
    maturity_date = models.DateField(null=False)
    buy_sell = models.CharField(max_length=1, choices=BUY_SELL, default='B')
    ccy_pair = models.ForeignKey(CcyPair, models.DO_NOTHING, null=False)
    strike_price = models.FloatField(validators=[validate_positive])
    notional_1 = models.FloatField(default=1e6, validators=[validate_positive])
    notional_2 = models.FloatField(validators=[validate_positive])
    payoff_type = models.CharField(max_length=5, choices=PAYOFF_TYPE)
    exercise_type = models.CharField(max_length=5, choices=EXERCISE_TYPE)
    exercise_start = models.DateField(null=True, blank=True)
    exercise_end = models.DateField(null=True, blank=True)
    cp = models.CharField(max_length=1, choices=FXO_CP)
    barrier = models.BooleanField(default=False)
    barrier_detail = models.OneToOneField(FXOBarrierDetail, CASCADE, null=True)
    objects = FXOManager()

    def __str__(self):
        return f"FXO ID: {self.id}, {self.ccy_pair}, Notional={self.notional_1:.0f}, K={self.strike_price}, {self.cp}"

    def save(self, *args, **kwargs):
        if self.notional_2 == None:
            self.notional_2 = self.notional_1 * self.strike_price
        if self.exercise_type == "EUR":
            self.exercise_start = None
            self.exercise_end = None
        elif self.exercise_type == "AME":
            if self.exercise_start == None:
                self.exercise_start = self.trade_date
            if self.exercise_end == None:
                self.exercise_end = self.maturity_date
        super().save(*args, **kwargs)

    def instrument(self):
        cp = ql.Option.Call if self.cp == "C" else ql.Option.Put
        if self.payoff_type == 'VAN':
            payoff = ql.PlainVanillaPayoff(cp, self.strike_price)
        elif self.payoff_type == 'DIG':
            payoff = ql.CashOrNothingPayoff(cp, self.strike_price, 1.0)
        else:
            payoff = ql.PlainVanillaPayoff(cp, self.strike_price)

        if self.exercise_type == 'EUR':
            exercise = ql.EuropeanExercise(qlDate(self.maturity_date))
        elif self.exercise_type == 'AME':
            exercise = ql.AmericanExercise(qlDate(self.exercise_start),
                                           qlDate(self.exercise_end))

        self.inst = ql.VanillaOption(payoff, exercise)
        return self.inst

    def make_pricing_engine(self):
        if self.mktdataset:
            mkt = self.mktdataset.fxo_mkt_data(self.ccy_pair.name)
            process = ql.BlackScholesMertonProcess(
                mkt.get('spot').spot0_handle(),
                ql.YieldTermStructureHandle(mkt.get('qts')),
                ql.YieldTermStructureHandle(mkt.get('rts')),
                mkt.get('vol').handle(self.strike_price))
            if self.exercise_type == "EUR":
                return ql.AnalyticEuropeanEngine(process)
            elif self.exercise_type == "AME":
                return ql.BinomialVanillaEngine(process, 'crr', steps=200)

    def self_inst(self):
        self.inst = self.instrument()
        self.inst.setPricingEngine(self.make_pricing_engine())

    def NPV(self):
        side = 1. if self.buy_sell == "B" else -1.
        return self.inst.NPV() * self.notional_1 * side

    def delta(self):
        side = 1. if self.buy_sell == "B" else -1.
        return self.inst.delta() * self.notional_1 * side

    def gamma(self):
        """ Delta sensitivity respect to 1% change of spot rate """
        side = 1. if self.buy_sell == "B" else -1.
        spot0 = self.mktdataset.get_fxspot(self.ccy_pair_id).today_rate()
        return self.inst.gamma() * self.notional_1 * side * 0.01 / spot0

    def vega(self):
        side = 1. if self.buy_sell == "B" else -1.
        if self.exercise_type == "EUR":
            return self.inst.vega() * self.notional_1 * side * 0.01
        else:
            npv = self.inst.NPV()
            mkt = self.mktdataset.fxo_mkt_data(self.ccy_pair.name)
            process = ql.BlackScholesMertonProcess(
                mkt.get('spot').spot0_handle(),
                ql.YieldTermStructureHandle(mkt.get('qts')),
                ql.YieldTermStructureHandle(mkt.get('rts')),
                mkt.get('vol').handle(self.strike_price, spread=0.0001))
            inst1 = self.instrument()
            inst1.setPricingEngine(
                ql.BinomialVanillaEngine(process, 'crr', steps=200))
            return side * self.notional_1 * (inst1.NPV() - npv) / 0.01

    def thetaPerDay(self):
        side = 1. if self.buy_sell == "B" else -1.
        if self.exercise_type == "EUR":
            return side * self.notional_1 * self.inst.thetaPerDay()
        else:
            return side * self.notional_1 * self.inst.theta() / 365

    def rho(self):
        side = 1. if self.buy_sell == "B" else -1.
        if self.exercise_type == "EUR":
            return self.inst.rho() * self.notional_1 * side * 0.01
        else:
            npv = self.inst.NPV()
            mkt = self.mktdataset.fxo_mkt_data(self.ccy_pair.name)
            spread = ql.QuoteHandle(ql.SimpleQuote(0.0001))
            spreaded_rts = ql.ZeroSpreadedTermStructure(
                ql.YieldTermStructureHandle(mkt.get('rts')), spread)
            process = ql.BlackScholesMertonProcess(
                mkt.get('spot').spot0_handle(),
                ql.YieldTermStructureHandle(mkt.get('qts')),
                ql.YieldTermStructureHandle(spreaded_rts),
                mkt.get('vol').handle(self.strike_price))
            inst1 = self.instrument()
            inst1.setPricingEngine(
                ql.BinomialVanillaEngine(process, 'crr', steps=200))
            return side * self.notional_1 * (inst1.NPV() - npv) * 100.

    def dividendRho(self):
        side = 1. if self.buy_sell == "B" else -1.
        if self.exercise_type == "EUR":
            return self.inst.dividendRho() * self.notional_1 * side * 0.01
        else:
            npv = self.inst.NPV()
            mkt = self.mktdataset.fxo_mkt_data(self.ccy_pair.name)
            spread = ql.QuoteHandle(ql.SimpleQuote(0.0001))
            spreaded_qts = ql.ZeroSpreadedTermStructure(
                ql.YieldTermStructureHandle(mkt.get('qts')), spread)
            process = ql.BlackScholesMertonProcess(
                mkt.get('spot').spot0_handle(),
                ql.YieldTermStructureHandle(spreaded_qts),
                ql.YieldTermStructureHandle(mkt.get('rts')),
                mkt.get('vol').handle(self.strike_price))
            inst1 = self.instrument()
            inst1.setPricingEngine(
                ql.BinomialVanillaEngine(process, 'crr', steps=200))
            return side * self.notional_1 * (inst1.NPV() - npv) * 100.


# class SwapManager():
#    pass


class Swap(Trade):
    # objects = SwapManager()
    product_type = models.CharField(max_length=12, default="SWAP")
    maturity_date = models.DateField(null=True, blank=True)

    def instrument(self, as_of):
        # maybe need to use x.leg(as_of=xxxxx)
        legs = [x.leg(as_of=as_of) for x in self.legs.all()]
        is_pay = [leg.pay_rec > 0 for leg in self.legs.all()]
        return ql.Swap(legs, is_pay)

    def make_pricing_engine(self, as_of):
        leg = self.legs.get(pay_rec=-1)
        yts1 = leg.ccy.rf_curve.filter(ref_date=as_of).first().term_structure()
        return ql.DiscountingSwapEngine(ql.YieldTermStructureHandle(yts1))

    def __str__(self):
        return f"Swap ID: {self.id}, Notional={self.legs.first().notional:.0f} {self.legs.first().ccy} vs {self.legs.last().notional:.0f} {self.legs.last().ccy}"

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        if self.detail:
            self.detail.delete()


class SwapLeg(models.Model):
    trade = ForeignKey(Swap,
                       CASCADE,
                       null=True,
                       blank=True,
                       related_name="legs")
    ccy = ForeignKey(Ccy, CASCADE)
    effective_date = models.DateField(default=datetime.date.today)
    tenor = models.CharField(max_length=8, null=True, blank=True)
    maturity_date = models.DateField()
    notional = models.FloatField(default=1e6, validators=[validate_positive])
    pay_rec = models.IntegerField(choices=SWAP_PAY_REC)
    fixed_rate = models.FloatField(null=True, blank=True)
    index = models.ForeignKey(RateIndex, SET_NULL, null=True, blank=True)
    spread = models.FloatField(null=True, blank=True)
    reset_freq = models.CharField(max_length=16,
                                  validators=[RegexValidator],
                                  null=True,
                                  blank=True)
    payment_freq = models.CharField(max_length=16, validators=[RegexValidator])
    calendar = models.ForeignKey(Calendar,
                                 SET_NULL,
                                 null=True,
                                 blank=True,
                                 default=None)
    day_counter = models.CharField(max_length=16,
                                   choices=CHOICE_DAY_COUNTER.choices)
    day_rule = models.CharField(max_length=24,
                                choices=CHOICE_DAY_RULE.choices,
                                default='ModifiedFollowing')

    def save(self, *args, **kwargs):
        if self.day_counter is None:
            self.day_counter = self.ccy.rate_day_counter
        if self.calendar is None:
            self.calendar = self.ccy.cal
        super(SwapLeg, self).save(*args, **kwargs)

    def get_schedule(self):
        cdr = self.calendar.calendar()
        return ql.MakeSchedule(qlDate(self.effective_date),
                               qlDate(self.maturity_date),
                               ql.Period(self.payment_freq),
                               rule=QL_DAY_RULE[self.day_rule],
                               calendar=cdr)

    def leg(self, as_of):
        sch = self.get_schedule()
        dc = QL_DAY_COUNTER[self.day_counter]
        # day_rule = QL_DAY_RULE[self.day_rule]
        if self.index:
            leg_idx = self.index.get_index(
                ref_date=as_of, eff_date=self.effective_date)  # need to fix
            if 'IBOR' in self.index.name:
                leg = ql.IborLeg([self.notional],
                                 sch,
                                 leg_idx,
                                 dc,
                                 fixingDays=[leg_idx.fixingDays()],
                                 spreads=[float(self.spread or 0.0)])
            elif 'OIS' in self.index.name:
                leg = ql.OvernightLeg([self.notional],
                                      sch,
                                      leg_idx,
                                      dc,
                                      BusinessDayConvention=self.day_rule,
                                      gearing=[1],
                                      spread=self.spread,
                                      TelescopicValueDates=True)
            else:
                pass  # other floating leg
        else:  # self.index==None
            leg = ql.FixedRateLeg(sch, QL_DAY_COUNTER[self.day_counter],
                                  [self.notional], [self.fixed_rate * 0.01])

        return leg

    def make_pricing_engine(self, as_of):
        yts = self.ccy.rf_curve.get(ref_date=as_of).term_structure()
        return ql.DiscountingSwapEngine(ql.YieldTermStructureHandle(yts))

    def discounting_curve(self, as_of):
        # return self.ccy.rf_curve.filter(ref_date=as_of).term_structure()
        return IRTermStructure.objects.filter(
            ref_date=as_of,
            name=self.ccy.risk_free_curve).first().term_structure()

    def npv(self, as_of, discounting_curve=None):
        yts = discounting_curve if discounting_curve else self.discounting_curve(
            as_of)
        return ql.CashFlows.npv(self.leg(as_of),
                                ql.YieldTermStructureHandle(yts))


class MktDataSet:

    def add_ccy_pair_with_args(self, **kwargs):
        """ input kwargs for manually initialize MktDataSet """
        if kwargs:
            cp = kwargs.get('ccy_pair')
            ref_date = kwargs.get('ref_date')
            ccy1, ccy2 = cp.split('/')
            self.ccy_pairs[cp] = CcyPair.objects.get(name=cp)
            fxspot = FxSpotRateQuote(ref_date=ref_date,
                                     rate=float(kwargs.get('s')),
                                     ccy_pair=self.ccy_pairs[cp])
            self.spots[cp] = fxspot.save(False)
            self.ytss[ccy2] = ql.FlatForward(
                qlDate(ref_date),
                ql.QuoteHandle(ql.SimpleQuote(float(kwargs.get('r')))),
                ql.Actual365Fixed(), ql.Compounded, ql.Continuous)
            self.ytss[ccy1] = ql.FlatForward(
                qlDate(ref_date),
                ql.QuoteHandle(ql.SimpleQuote(float(kwargs.get('q')))),
                ql.Actual365Fixed(), ql.Compounded, ql.Continuous)
            # self.vols[ccy_pair] = FXVolatility(...)

    def __init__(self, date, **kwargs) -> None:
        """ input kwargs for manually initialize MktDataSet """
        self.date = str2date(date)
        self.ccy_pairs = dict()  # Ccypair
        self.fxytss = dict()
        self.ytss = dict()
        self.spots = dict()  # FxSpotRateQuote
        self.fxvols = dict()
        if kwargs:
            self.add_ccy_pair_with_args(**kwargs)

    def get_yts(self, ccy: str, name: str):
        ccy_cvname = ccy + " " + name
        yts = self.ytss.get(ccy_cvname)
        if yts == None:
            yts_obj = IRTermStructure.objects.get(name=name,
                                                  ccy=ccy,
                                                  ref_date=self.date)
            yts_obj.link_mktdataset(self)
            yts = yts_obj.term_structure()
            self.ytss[ccy_cvname] = yts
        return yts

    def get_fxyts_name(self, ccy: str) -> str:
        name = self.fxytss.get(ccy)
        if name == None:
            yts = Ccy.objects.get(code=ccy).fx_curve.get(ref_date=self.date)
            yts.link_mktdataset(self)
            name = yts.name
            self.fxytss[ccy] = name
            self.ytss[ccy + " " + name] = yts.term_structure()
        return name

    def get_fxspot(self, ccy_pair: str) -> FxSpotRateQuote:
        try:
            cp = self.ccy_pairs.get(ccy_pair)

            if cp == None:
                cp = CcyPair.objects.get(name=ccy_pair)
                self.ccy_pairs[ccy_pair] = cp

            fxs = self.spots.get(ccy_pair)

            if fxs == None:
                fxs = FxSpotRateQuote.objects.get(ccy_pair=ccy_pair,
                                                  ref_date=self.date)
                self.spots[ccy_pair] = fxs
                fxs.link_mktdataset(self)
                ccy1, ccy2 = ccy_pair.split('/')
                fxs.set_yts(self.get_yts(ccy2, self.get_fxyts_name(ccy2)),
                            self.get_yts(ccy1, self.get_fxyts_name(ccy1)))
            return fxs  # FxSpotRateQuote
        except RuntimeError as error:
            raise error

    def get_fxvol(self, ccy_pair: str) -> FXVolatility:
        cp = self.ccy_pairs.get(ccy_pair)

        if cp == None:
            cp = CcyPair.objects.get(name=ccy_pair)
            self.ccy_pairs[ccy_pair] = cp

        fxvol = self.fxvols.get(ccy_pair)

        if fxvol == None:
            fxvol = FXVolatility.objects.get(ccy_pair=ccy_pair,
                                             ref_date=self.date)
            fxvol.link_mktdataset(self)
            ccy1, ccy2 = ccy_pair.split('/')
            fxvol.set_yts(self.get_yts(ccy2, self.get_fxyts_name(ccy2)),
                          self.get_yts(ccy1, self.get_fxyts_name(ccy1)))
            fxvol.set_spot(self.get_fxspot(ccy_pair))
            self.fxvols[ccy_pair] = fxvol
        return fxvol

    def get_fxyts(self, ccy_pair: str) -> tuple:
        """ return ccy1 yts and ccy2 yts """
        ccy1, ccy2 = ccy_pair.split('/')
        cp = self.ccy_pairs.get(ccy_pair)

        if cp == None:
            cp = CcyPair.objects.get(name=ccy_pair)
            self.ccy_pairs[ccy_pair] = cp

        return {
            'qts': self.get_yts(ccy1, self.get_fxyts_name(ccy1)),
            'rts': self.get_yts(ccy2, self.get_fxyts_name(ccy2))
        }

    def add_yts(self, ccy, name, yts):
        self.ytss[ccy + " " + name] = yts

    def add_ccy_pair_with_trades(self, trades):
        if isinstance(trades, list):
            tradelist = trades
        else:
            tradelist = [trades]
        for t in tradelist:
            self.add_ccy_pair(t.ccy_pair, self.date)
            t.link_mktdataset(self)

    def fxo_mkt_data(self, ccy_pair: str) -> dict:
        spot = self.get_fxspot(ccy_pair)
        yts = self.get_fxyts(ccy_pair)
        vol = self.get_fxvol(ccy_pair)
        # fxv is a Django object, invoke vol.hendle(strike)
        return {
            'ccy_pair': ccy_pair,
            'spot': spot,
            'qts': yts.get('qts'),
            'rts': yts.get('rts'),
            'vol': vol
        }
