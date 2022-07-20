from concurrent.futures import process
import datetime
from operator import truediv
#from tkinter import N
from QuantLib.QuantLib import PiecewiseLogLinearDiscount, RealTimeSeries
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import query_utils
from django.db.models.base import Model
from django.db.models.deletion import CASCADE, DO_NOTHING, SET_NULL, SET_DEFAULT
from django.db.models.fields.related import ForeignKey
from django.db.models.fields import DecimalField, CharField
from django.forms import DateField, IntegerField
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
import re

FXO_SUBTYPE = [('VAN', 'VAN'), ('AME', 'AME'), ('DOUB_KO', 'DOUB_KO'),
               ('DOUB_KI', 'DOUB_KI'), ('KIKO', 'KIKO'), ('KOKI', 'KOKI')]

PAYOFF_TYPE = [('PLA', 'Plain'), ('DIG', 'Digital')]

EXERCISE_TYPE = [("EUR", "European"), ("AME", "American")]

FXO_CP = [("C", "Call"), ("P", "Put")]

SWAP_PAY_REC = [(ql.VanillaSwap.Receiver, "Receive"),
                (ql.VanillaSwap.Payer, "Pay")]

BUY_SELL = [("B", "Buy"), ("S", "Sell")]

KIKO = [('IN', 'IN'), ('OUT', 'OUT')]

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

CHOICE_ATM_TYPE = models.TextChoices('ATM_TYPE',
                                     ['Spot', 'Fwd', 'DeltaNeutral'])

QL_ATM_TYPE = {
    'Spot': ql.DeltaVolQuote.AtmSpot,
    'Fwd': ql.DeltaVolQuote.AtmFwd,
    'DeltaNeutral': ql.DeltaVolQuote.AtmDeltaNeutral,
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

period_regex1 = re.compile(r"^(\d+[DMYdmy])+$")
period_regex2 = re.compile(r"^(\d+[Ww])+$")


def validate_positive(value):
    if float(value) <= 0:
        raise ValidationError(_('Must be positive'), code='non_positive')


def validate_period(s):
    if not period_regex1.match(s) and not period_regex2.match(s):
        raise ValidationError(_('Period is not correct'),
                              code='incorrect_period')


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
        return ql.DateParser.parseISO(d.strftime('%Y-%m-%d'))


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
    name = CharField(max_length=24, primary_key=True)

    def __str__(self):
        return self.name

    #@property
    def calendar(self):
        return QL_CALENDAR.get(self.name)


class Ccy(models.Model):
    code = CharField(max_length=3, blank=False, primary_key=True)
    fixing_days = models.PositiveIntegerField(default=2)
    cal = ForeignKey(Calendar, DO_NOTHING, null=True)
    risk_free_curve = CharField(max_length=16, blank=True,
                                null=True)  # free text
    foreign_exchange_curve = CharField(max_length=16, blank=True,
                                       null=True)  # free text
    rate_day_counter = CharField(max_length=24, 
                                 choices=CHOICE_DAY_COUNTER.choices, 
                                 blank=True,
                                 null=True,
                                 default=None)

    def __str__(self):
        return self.code

    def calendar(self):
        if self.cal:
            return self.cal.calendar()
        else:
            return ql.NullCalendar()


class CcyPair(models.Model):
    """ .quotes to get FxSpotRateQuote """
    name = CharField(max_length=7, primary_key=True)
    base_ccy = ForeignKey(Ccy, CASCADE, related_name="as_base_ccy")
    quote_ccy = ForeignKey(Ccy, CASCADE, related_name="as_quote_ccy")
    cal = ForeignKey(Calendar, SET_NULL, related_name="ccy_pairs", null=True)
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
    ccy_pair = ForeignKey(CcyPair, CASCADE, related_name="quotes")

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
    """ name is the full name e.g. USD OIS 12M """

    def limit_choices_yts():
        return None

    name = CharField(max_length=16)
    ref_date = models.DateField()
    yts = ForeignKey('IRTermStructure',
                     CASCADE,
                     null=True,
                     blank=True,
                     related_name="rates")
    rate = models.DecimalField(max_digits=12, decimal_places=8)
    tenor = CharField(max_length=5, validators=[validate_period])
    instrument = CharField(max_length=12)
    ccy = ForeignKey(Ccy, CASCADE, related_name="ir_quotes")
    day_counter = CharField(max_length=16,
                            choices=CHOICE_DAY_COUNTER.choices,
                            null=True,
                            blank=True)
    ccy_pair = ForeignKey(CcyPair, CASCADE, null=True, blank=True)
    index = ForeignKey('RateIndex',
                       DO_NOTHING,
                       null=True,
                       blank=True,
                       related_name='quotes')
    days_key = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ('name', 'ref_date')

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.helper_obj = None

    def save(self, *args, **kwargs) -> None:
        self.days_key = ql.NullCalendar().advance(qlDate(self.ref_date),
                                                  ql.Period(
                                                      self.tenor)).to_date()
        super().save(*args, **kwargs)

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
            if self.instrument == "FUT":
                tenor_ = None
            else:
                tenor_ = ql.Period(self.tenor)
            fixing_days = None

        if self.instrument == "DEPO":
            fixing_days = self.ccy.fixing_days
            convention = ql.ModifiedFollowing
            ccy = Ccy.objects.get(code=self.ccy)  # may build ccy in mktdataset
            self.helper_obj = ql.DepositRateHelper(
                q, tenor_, fixing_days, ccy.calendar(), convention, False,
                QL_DAY_COUNTER[self.day_counter])
            return self.helper_obj, q

        elif self.instrument == "FUT":
            if self.tenor[:2] == 'ED':
                return ql.FuturesRateHelper(q, ql.IMM.date(self.tenor[2:4]),
                                            ql.USDLibor(ql.Period('3M'))), q
        elif self.instrument == "SOFRFUT":
            return ql.SofrFutureRateHelper(), q
        elif self.instrument == "SWAP":
            if self.ccy_id == "USD":
                # https://quant.stackexchange.com/questions/32345/quantlib-python-dual-curve-bootstrapping-example
                swapIndex = ql.UsdLiborSwapIsdaFixAm(tenor_)
                ref_curve = kwargs.get('ref_curve')  # is a handle
                if ref_curve:
                    return ql.SwapRateHelper(q, swapIndex, 0, ql.Period(),
                                             ref_curve), q
                else:
                    return ql.SwapRateHelper(q, swapIndex), q
        elif self.instrument in ["OIS", "SOFROIS"]:
            if self.instrument == "OIS":
                idx = ql.FedFunds()
                paymentLag_ = 2
                settlementDays_ = 2
            else:
                idx = ql.Sofr()
                paymentLag_ = 0
                settlementDays_ = 0

            if self.ccy_id == "USD":
                cal_ = ql.UnitedStates()
                if self.tenor == '1D':
                    #return ql.DepositRateHelper(q, tenor_, 0, cal_, ql.Following, False, ql.Actual360()), q
                    return ql.DepositRateHelper(q, ql.Sofr()), q
                else:
                    # https://github.com/lballabio/QuantLib-SWIG/blob/a88a28b95e7abdacd1112f23864a63523433711b/SWIG/ratehelpers.i#L315
                    self.helper_obj = ql.OISRateHelper(
                        settlementDays_,
                        tenor_,
                        q,
                        idx,
                        paymentLag=paymentLag_,
                        paymentFrequency=ql.Annual,
                        paymentCalendar=cal_), q
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
    """ name: e.g. LIBOR, OIS, FOREX """
    name = CharField(max_length=16)
    ref_date = models.DateField()
    ccy = ForeignKey(Ccy,
                     CASCADE,
                     related_name="all_curves",
                     null=True,
                     blank=True)
    as_fx_curve = ForeignKey(Ccy,
                             CASCADE,
                             related_name="fx_curve",
                             null=True,
                             blank=True)
    as_rf_curve = ForeignKey(Ccy,
                             CASCADE,
                             related_name="rf_curve",
                             null=True,
                             blank=True)
    ref_ccy = ForeignKey(Ccy, CASCADE, null=True, blank=True)
    ref_curve = CharField(max_length=16, null=True, blank=True)

    # ref_curve: only curve name, e.g. OIS

    class Meta:
        unique_together = ('name', 'ref_date', 'ccy')

    def __init__(self, *args, **kwargs) -> None:
        self.yts = None
        super().__init__(*args, **kwargs)

    def term_structure(self):
        if self.yts:
            return self.yts

        if self.mktdataset == None:
            self.mktdataset = MktDataSet(self.ref_date)

        ql.Settings.instance().evaluationDate = qlDate(self.ref_date)

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

    def quotes_dict(self):
        quotes = []
        for r in self.rates.all():
            quotes.append({
                'tenor': r.tenor,
                'rate': r.rate * 100,
                'instrument': r.instrument,
                'day_counter': r.day_counter
            })
        return quotes

    def __str__(self):
        return f"{self.ccy} {self.name} as of {self.ref_date.strftime('%Y-%m-%d')}"


@with_mktdataset
class RateIndex(models.Model):
    name = CharField(max_length=16, primary_key=True)
    ccy = ForeignKey(Ccy, CASCADE, related_name="rate_indexes")
    tenor = CharField(max_length=16, validators=[validate_period])
    day_counter = CharField(max_length=16,
                            choices=CHOICE_DAY_COUNTER.choices,
                            null=True,
                            blank=True)
    yts = CharField(max_length=16, null=True, blank=True)

    # yts: only name, e.g. LIBOR

    class Meta:
        unique_together = ('name', 'tenor')

    def __str__(self):
        return self.name

    def index(self, ref_date=None, eff_date=None):
        if self.mktdataset == None:
            self.mktdataset = MktDataSet(ref_date)

        yts = self.mktdataset.get_yts(self.ccy_id, self.yts)
        ytsHandle = ql.YieldTermStructureHandle(yts)

        if self.name == 'SOFR':
            idxObj = ql.Sofr(ytsHandle)
        elif self.name == 'LIBOR' and self.ccy.code == 'USD':
            idxObj = ql.USDLibor(ql.Period(self.tenor), ytsHandle)
        elif self.name == 'OIS' and self.ccy.code == 'USD':
            idxObj = ql.OvernightIndex('USD EFFR', 1, ql.USDCurrency(),
                                       ql.Actual360(), ytsHandle)

        if eff_date:
            firstFixingDate = idxObj.fixingDate(qlDate(eff_date))
            for f in self.fixings.filter(ref_date__gte=firstFixingDate.ISO()):
                idxObj.addFixing(qlDate(f.ref_date), float(f.value))

        return idxObj


class RateIndexFixing(models.Model):
    value = models.DecimalField(max_digits=12, decimal_places=8)
    index = ForeignKey(RateIndex, CASCADE, related_name="fixings")
    ref_date = models.DateField()

    class Meta:
        unique_together = ('ref_date', 'index')

    def __str__(self):
        return f'{self.index} on {self.ref_date}'


@with_mktdataset
class FXVolatility(models.Model):
    """ use .quotes to get quotes """
    ref_date = models.DateField()
    ccy_pair = ForeignKey(CcyPair, CASCADE, related_name='vol')

    class Meta:
        verbose_name_plural = "FX volatilities"
        unique_together = ('ref_date', 'ccy_pair')

    class TargetFun:

        def toSpotDelta(self, vol, delta, delta_type):
            if delta_type == ql.DeltaVolQuote.Spot:
                return delta
            else:
                sd = math.sqrt(self.t) * vol
                put = ql.Option.Put
                calc = ql.BlackDeltaCalculator(put, self.delta_type, self.s0,
                                               self.rDcf, self.qDcf, sd)
                k = calc.strikeFromDelta(delta)
                calc = ql.BlackDeltaCalculator(put, ql.DeltaVolQuote.Spot,
                                               self.s0, self.rDcf, self.qDcf,
                                               sd)
                return calc.deltaFromStrike(k)

        def __init__(self, ref_date, spot, rdf, qdf, strike, maturity, deltas,
                     delta_type, atm_vol, atm_type, smile_section):
            """ 
            delta_type is same along the smile
            """
            self.ref_date = ref_date
            self.strike = strike
            self.maturity = qlDate(maturity)
            self.s0 = spot
            self.rDcf = rdf
            self.qDcf = qdf
            self.t = ql.Actual365Fixed().yearFraction(qlDate(self.ref_date),
                                                      self.maturity)
            self.deltas = []
            self.smile = smile_section.copy()
            self.delta_type = ql.DeltaVolQuote.Spot

            for ss, delta in zip(smile_section, deltas):
                self.deltas.append(self.toSpotDelta(ss, delta, delta_type))

            sd = math.sqrt(self.t) * atm_vol
            calc = ql.BlackDeltaCalculator(ql.Option.Put, delta_type, spot,
                                           rdf, qdf, sd)
            atm_k = calc.atmStrike(atm_type)
            calc = ql.BlackDeltaCalculator(ql.Option.Put,
                                           ql.DeltaVolQuote.Spot, spot, rdf,
                                           qdf, sd)
            self.smile.insert(2, atm_vol)
            self.deltas.insert(2, calc.deltaFromStrike(atm_k))
            self.interp = ql.LinearInterpolation(self.deltas, self.smile)

        def __call__(self, v0):
            opt_type = ql.Option.Put
            sd = math.sqrt(self.t) * v0
            calc = ql.BlackDeltaCalculator(opt_type, self.delta_type, self.s0,
                                           self.rDcf, self.qDcf, sd)
            d = calc.deltaFromStrike(self.strike)
            v = self.interp(d, allowExtrapolation=True)
            if abs(v - v0) > 1e-8:
                return self.__call__(v)
            else:
                return v

    def __init__(self, *args, **kwargs) -> None:
        self.rts = None
        self.qts = None
        self.spot = None
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"{self.ccy_pair} as of {self.ref_date}"

    def vol_dict(self):
        vols = list()
        for q in self.quotes.filter(is_atm=True).order_by('maturity'):
            vols.append({'tenor': q.tenor, 'atm': q.value * 100})
        for q in self.quotes.exclude(is_atm=True):
            for v in vols:
                if v['tenor'] == q.tenor:
                    v[str(q.delta * -1)] = q.value * 100
        return vols

    def type_dict(self):
        x = self.quotes.filter(is_atm=True).first()
        y = self.quotes.filter(is_atm=False).first()
        return x.atm_type, y.delta_type

    def surface_matrix(self):
        maturities = []
        volx = []
        delta, delta_type = [], []
        atm_vols, atm_types = [], []
        prev_t = None  # datetime.date
        row = -1
        for q in self.quotes.exclude(is_atm=True).order_by(
                'maturity', 'delta'):
            if q.maturity == prev_t:
                volx[row].append(q.value)
                delta[row].append(q.delta * 0.01)
                delta_type[row].append(QL_DELTA_TYPE[q.delta_type])
            else:
                volx.append([q.value])
                delta.append([q.delta * 0.01])
                delta_type.append([QL_DELTA_TYPE[q.delta_type]])
                maturities.append(q.maturity)
                row += 1
            prev_t = q.maturity
        for q in self.quotes.filter(is_atm=True).order_by('maturity'):
            atm_vols.append(q.value)
            atm_types.append(QL_ATM_TYPE[q.atm_type])
        obj = volx, delta, delta_type, atm_vols, atm_types, maturities
        return obj

    def set_yts(self, rts, qts):
        if rts:
            self.rts = rts
        if qts:
            self.qts = qts

    def set_spot(self, spot: FxSpotRateQuote):
        self.spot = spot  # FxSpotRateQuote

    def handle(self, strike, spread=None):

        volx, deltax, delta_typex, atm_vols, atm_types, mats = self.surface_matrix(
        )

        if self.mktdataset == None:
            self.mktdataset = MktDataSet(self.ref_date)

        volatilities = []

        if self.spot == None:
            self.spot = self.mktdataset.get_fxspot(self.ccy_pair.name)
        s0 = self.spot.today_rate()

        if self.rts == None:
            ccy = self.ccy_pair.quote_ccy.code
            cvname = self.mktdataset.get_fxyts_name(ccy)
            self.rts = self.mktdataset.get_yts(ccy, cvname)
        if self.qts == None:
            ccy = self.ccy_pair.base_ccy.code
            cvname = self.mktdataset.get_fxyts_name(ccy)
            self.qts = self.mktdataset.get_yts(ccy, cvname)

        spread = spread if spread else 0.

        for i, smile in enumerate(volx):
            mat = qlDate(mats[i])
            target = self.TargetFun(self.ref_date, s0, self.rts.discount(mat),
                                    self.qts.discount(mat), strike, mats[i],
                                    deltax[i], delta_typex[i][0], atm_vols[i],
                                    atm_types[i],
                                    [sm + spread for sm in smile])
            guess = atm_vols[i]
            volatilities.append(target(guess))
            #volatilities.append(solver.solve(target, accuracy, guess, step))
        #print(volatilities)
        vts = ql.BlackVarianceCurve(qlDate(self.ref_date), qlDate(mats),
                                    volatilities, ql.Actual365Fixed(), False)
        vts.enableExtrapolation()
        return ql.BlackVolTermStructureHandle(vts)

    def surface_dataframe(self):
        volx, deltax, _, atm_vols, atm_types, maturities = self.surface_matrix(
        )
        smiles_temp = [
            pd.DataFrame([smile], columns=deltax[i], index=[maturities[i]])
            for i, smile in enumerate(volx)
        ]
        return pd.concat(smiles_temp)


class FXVolatilityQuote(models.Model):
    ref_date = models.DateField()
    tenor = CharField(max_length=6)
    delta = models.IntegerField(null=True, blank=True)
    value = models.FloatField(validators=[validate_positive])
    surface = ForeignKey(FXVolatility, CASCADE, related_name='quotes')
    delta_type = CharField(choices=CHOICE_DELTA_TYPE.choices,
                           max_length=8,
                           null=True,
                           blank=True)
    maturity = models.DateField(null=True, blank=True)
    is_atm = models.BooleanField(default=True)
    atm_type = CharField(choices=CHOICE_ATM_TYPE.choices,
                         max_length=12,
                         null=True,
                         blank=True)

    def save(self, *args, **kwargs):
        cal = self.surface.ccy_pair.calendar()
        self.maturity = cal.advance(qlDate(self.ref_date),
                                    ql.Period(self.tenor)).ISO()
        self.tenor = self.tenor.upper()
        if self.is_atm:
            self.delta = None
            self.delta_type = None
        else:
            self.atm_type = None
            if self.delta > 0:
                self.delta = round(self.delta - 100)
        super().save(*args, **kwargs)

    def __str__(self):
        if self.is_atm:
            return f'{self.surface}, {self.tenor}, ATM, {self.atm_type}'
        else:
            return f'{self.surface}, {self.tenor}, {self.delta}, {self.delta_type}'


class Portfolio(models.Model):
    name = CharField(max_length=16, primary_key=True)

    def __str__(self) -> str:
        return self.name


class Book(models.Model):
    name = CharField(max_length=16, primary_key=True)
    portfolio = ForeignKey(Portfolio, DO_NOTHING, related_name="books")
    owner = ForeignKey(User, DO_NOTHING, null=True, related_name="books")

    def __str__(self) -> str:
        return self.name


class Counterparty(models.Model):
    code = CharField(max_length=16, primary_key=True)
    name = CharField(max_length=64)
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
    # trade = ForeignKey(FXO, CASCADE, related_name="detail")
    # def __str__(self) -> str:
    #     return f"ID: {self.trade.id}"
    pass


class TradeMarkToMarket(models.Model):
    as_of = models.DateField()
    trade_d = ForeignKey(TradeDetail, CASCADE, null=True, related_name="mtms")
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
    pl_ccy = ForeignKey(Ccy, CASCADE, null=True, blank=True)
    detail = models.OneToOneField(TradeDetail, CASCADE, null=True)
    book = ForeignKey(Book,
                      SET_NULL,
                      null=True,
                      blank=True,
                      related_name="trades")
    input_user = ForeignKey(User,
                            SET_NULL,
                            null=True,
                            related_name='input_trades')
    counterparty = ForeignKey(Counterparty,
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
    trade = ForeignKey(Trade,
                       CASCADE,
                       related_name='cashflows',
                       editable=False)
    ccy = ForeignKey(Ccy, CASCADE, null=True, blank=True)
    amount = models.DecimalField(max_digits=32,
                                 decimal_places=2,
                                 null=True,
                                 blank=True)
    value_date = models.DateField(default=datetime.date.today)
    cashflow_type = CharField(max_length=10, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.trade.id}: {self.ccy} {self.amount} on {self.value_date}"

    def cashflow(self):
        return ql.SimpleCashFlow(float(self.amount), qlDate(self.value_date))


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
    # barrier_start = models.DateField(null=True, blank=True)
    # barrier_end = models.DateField(null=True, blank=True)
    barrier = models.FloatField(validators=[validate_positive],
                                null=True,
                                blank=True)
    knock = CharField(max_length=3, choices=KIKO, blank=True)
    rebate = models.DecimalField(max_digits=24, decimal_places=2, default=0.)
    rebate_ccy = ForeignKey("Ccy",
                            CASCADE,
                            null=True,
                            blank=True,
                            related_name='+')
    rebate_at_hit = models.BooleanField(default=False)
    payoff_at_hit = models.BooleanField(default=False)

    class Meta:
        abstract = True


class FXOUpperBarrierDetail(FXOBarrierDetail):
    trade = models.OneToOneField("FXO",
                                 CASCADE,
                                 primary_key=True,
                                 editable=False,
                                 related_name="upper_barrier_detail")


class FXOLowerBarrierDetail(FXOBarrierDetail):
    trade = models.OneToOneField("FXO",
                                 CASCADE,
                                 primary_key=True,
                                 editable=False,
                                 related_name="lower_barrier_detail")


@with_mktdataset
class FXO(Trade):
    product_type = CharField(max_length=12, default="FXO")
    maturity_date = models.DateField(null=False)
    buy_sell = CharField(max_length=1, choices=BUY_SELL, default='B')
    ccy_pair = ForeignKey(CcyPair,
                          models.DO_NOTHING,
                          null=False,
                          related_name='+')
    strike_price = models.FloatField(validators=[validate_positive])
    notional_1 = models.FloatField(default=1e6, validators=[validate_positive])
    notional_2 = models.FloatField(validators=[validate_positive])
    payoff_type = CharField(max_length=5, choices=PAYOFF_TYPE)
    exercise_type = CharField(max_length=5, choices=EXERCISE_TYPE)
    exercise_start = models.DateField(null=True, blank=True)
    exercise_end = models.DateField(null=True, blank=True)
    cp = CharField(max_length=1, choices=FXO_CP)
    barrier = models.BooleanField(default=False)
    subtype = CharField(max_length=8,
                        editable=False,
                        choices=FXO_SUBTYPE,
                        blank=True,
                        null=True)

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
        if self.payoff_type == 'PLA':
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

        if self.barrier:
            _up = False
            _low = False
            if hasattr(self, 'upper_barrier_detail'):
                up_bar = self.upper_barrier_detail
                _up = True
            if hasattr(self, 'lower_barrier_detail'):
                low_bar = self.lower_barrier_detail
                _low = True

            if _up and _low:
                if up_bar.knock == "IN" and low_bar.knock == "OUT":
                    kiko = ql.DoubleBarrier.KIKO
                elif up_bar.knock == "OUT" and low_bar.knock == "IN":
                    kiko = ql.DoubleBarrier.KOKI
                elif up_bar.knock == "OUT" and low_bar.knock == "OUT":
                    kiko = ql.DoubleBarrier.KnockOut
                elif up_bar.knock == "IN" and low_bar.knock == "IN":
                    kiko = ql.DoubleBarrier.KnockIn
                reb = float(up_bar.rebate) / self.notional_1
                self.inst = ql.DoubleBarrierOption(kiko, low_bar.barrier,
                                                   up_bar.barrier, reb, payoff,
                                                   exercise)
            elif _up:
                kiko = ql.Barrier.UpIn if up_bar.knock == "IN" else ql.Barrier.UpOut
                self.inst = ql.BarrierOption(
                    kiko, up_bar.barrier,
                    float(up_bar.rebate) / self.notional_1, payoff, exercise)
            elif _low:
                kiko = ql.Barrier.DownIn if low_bar.knock == "IN" else ql.Barrier.DownOut
                self.inst = ql.BarrierOption(
                    kiko, low_bar.barrier,
                    float(low_bar.rebate) / self.notional_1, payoff, exercise)
        else:
            self.inst = ql.VanillaOption(payoff, exercise)
        return self.inst

    def make_process(self,
                     spot_ptc_chg=None,
                     vol_spread=None,
                     q_spread=None,
                     r_spread=None):
        if self.mktdataset:
            mkt = self.mktdataset.fxo_mkt_data(self.ccy_pair.name)
            spot = mkt.get('spot')
            if spot_ptc_chg:
                spot.setQuote(spot.today_rate() * (spot_ptc_chg + 1.))
            spot0 = spot.spot0_handle()
            ytsh = ql.YieldTermStructureHandle
            zsts = ql.ZeroSpreadedTermStructure
            qts = ytsh(mkt.get('qts'))
            rts = ytsh(mkt.get('rts'))
            if q_spread:
                qts = ytsh(zsts(qts, ql.QuoteHandle(ql.SimpleQuote(q_spread))))
            if r_spread:
                rts = ytsh(zsts(rts, ql.QuoteHandle(ql.SimpleQuote(r_spread))))
            vol = mkt.get('vol').handle(self.strike_price, spread=vol_spread)
            process = ql.BlackScholesMertonProcess(spot0, qts, rts, vol)
            return process

    def make_pricing_engine(self, process=None):
        if process == None and self.mktdataset:
            process = self.make_process()

        if isinstance(self.inst, ql.DoubleBarrierOption):
            return ql.BinomialDoubleBarrierEngine(process, 'tian', 200)
        elif self.barrier:
            return ql.BinomialBarrierEngine(process, 'tian', 200)
        if self.exercise_type == "EUR":
            return ql.AnalyticEuropeanEngine(process)
        elif self.exercise_type == "AME":
            return ql.BinomialVanillaEngine(process, 'crr', 200)

    def self_inst(self):
        self.inst = self.instrument()
        self.inst.setPricingEngine(self.make_pricing_engine())

    def NPV(self):
        side = 1. if self.buy_sell == "B" else -1.
        return self.inst.NPV() * self.notional_1 * side

    def delta(self):
        """ in ccy2 """
        side = 1. if self.buy_sell == "B" else -1.
        spot0 = self.mktdataset.get_fxspot(self.ccy_pair_id).today_rate()
        #if isinstance(self.inst, ql.DoubleBarrierOption):
        #    return 0.
        return self.inst.delta() * self.notional_1 * side * spot0

    def gamma(self):
        """ Delta sensitivity respect to 1% change of spot rate 
         this Delta is in ccy2 """
        side = 1. if self.buy_sell == "B" else -1.
        spot_quote = self.mktdataset.get_fxspot(self.ccy_pair_id)
        spot0 = spot_quote.today_rate()
        if isinstance(self.inst, ql.DoubleBarrierOption):
            d0 = self.inst.delta()
            process = self.make_process(spot_ptc_chg=0.001)
            eng = self.make_pricing_engine(process)
            inst1 = self.instrument()
            inst1.setPricingEngine(eng)
            d1 = inst1.delta()
            spot_quote.resetQuote()
            return 0.01 * (d1 - d0) / (
                spot0 * 0.001) * self.notional_1 * side * spot0 * spot0
        gamma = self.inst.gamma()
        return gamma * self.notional_1 * side * 0.01 * spot0 * spot0

    def vega(self):
        side = 1. if self.buy_sell == "B" else -1.
        if isinstance(self.inst, ql.DoubleBarrierOption
                      ) or self.barrier or self.exercise_type == "AME":
            npv = self.inst.NPV()
            process = self.make_process(vol_spread=0.01)
            eng = self.make_pricing_engine(process)
            inst1 = self.instrument()
            inst1.setPricingEngine(eng)
            return side * self.notional_1 * (inst1.NPV() - npv)
        elif self.exercise_type == "EUR":
            return self.inst.vega() * self.notional_1 * side * 0.01

    def thetaPerDay(self):
        side = 1. if self.buy_sell == "B" else -1.
        if self.barrier:
            return 0.
        elif self.exercise_type == "EUR":
            return side * self.notional_1 * self.inst.thetaPerDay()
        else:
            return side * self.notional_1 * self.inst.theta() / 365

    def rho(self):
        """ 1% sensitivity """
        side = 1. if self.buy_sell == "B" else -1.
        if self.barrier:
            return 0.
        elif self.exercise_type == "EUR":
            return self.inst.rho() * self.notional_1 * side * 0.01
        else:
            npv = self.inst.NPV()
            process = self.make_process(r_spread=0.0001)
            eng = self.make_pricing_engine(process)
            inst1 = self.instrument()
            inst1.setPricingEngine(eng)
            return side * self.notional_1 * (inst1.NPV() - npv) * 100.

    def dividendRho(self):
        """ 1% sensitivity """
        side = 1. if self.buy_sell == "B" else -1.
        if self.barrier:
            return 0.
        elif self.exercise_type == "EUR":
            return self.inst.dividendRho() * self.notional_1 * side * 0.01
        else:
            npv = self.inst.NPV()
            process = self.make_process(q_spread=0.0001)
            eng = self.make_pricing_engine(process)
            inst1 = self.instrument()
            inst1.setPricingEngine(eng)
            return side * self.notional_1 * (inst1.NPV() - npv) * 100.


# class SwapManager():
#    pass


@with_mktdataset
class VanillaSwap(Trade):
    # objects = SwapManager()
    product_type = CharField(max_length=12, default="SWAP")
    start_date = models.DateField(null=True, blank=True)
    maturity_date = models.DateField(null=True, blank=True)
    notional = models.DecimalField(max_digits=24,
                                   decimal_places=2,
                                   default=1e6,
                                   validators=[validate_positive])

    def __str__(self):
        return f"SWAP ID: {self.id}"

    def instrument(self):
        self.inst = ql.MakeVanillaSwap()
        return self.inst

    def make_pricing_engine(self):
        return ql.DiscountingSwapEngine()

    def self_inst(self) -> None:
        self.inst = self.instrument()
        self.inst.setPricingEngine(self.make_pricing_engine())


@with_mktdataset
class Swap(Trade):
    product_type = CharField(max_length=12, default="SWAP")
    maturity_date = models.DateField(null=True, blank=True)

    def instrument(self):
        legs = [x.leg() for x in self.legs.all()]
        is_pay = [leg.pay_rec > 0 for leg in self.legs.all()]
        return ql.Swap(legs, is_pay)

    def make_pricing_engine(self):
        if self.mktdataset:
            ccy = self.legs.values('ccy')[0]['ccy']
            name = self.mktdataset.get_rfyts_name(ccy)
            yts = self.mktdataset.get_yts(ccy, name)
        return ql.DiscountingSwapEngine(ql.YieldTermStructureHandle(yts))

    def self_inst(self):
        self.inst = self.instrument()
        self.inst.setPricingEngine(self.make_pricing_engine())

    def __str__(self):
        return f"Swap ID: {self.id}"

    def delete(self, *args, **kwargs):
        if self.detail:
            self.detail.delete()
        for leg in self.legs.all():
            leg.delete()
        super().delete(*args, **kwargs)


class SchedulePeriod(models.Model):
    start = models.DateField()
    end = models.DateField()

    def __str__(self):
        return f"{self.start}~{self.end}"


class Schedule(models.Model):
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    tenor = CharField(max_length=8,
                      null=True,
                      blank=True,
                      validators=[validate_period])
    freq = CharField(max_length=16,
                     validators=[validate_period],
                     null=True,
                     blank=True)
    day_rule = CharField(max_length=24,
                         choices=CHOICE_DAY_RULE.choices,
                         default='ModifiedFollowing')
    calendar = ForeignKey(Calendar,
                          SET_NULL,
                          null=True,
                          blank=True,
                          default=None)

    def __str__(self):
        return f"{self.start_date}~{self.end_date}"

    def schedule(self):
        cdr = self.calendar.calendar()
        return ql.MakeSchedule(qlDate(self.start_date),
                               qlDate(self.end_date),
                               ql.Period(self.freq),
                               rule=QL_DAY_RULE[self.day_rule],
                               calendar=cdr)


@with_mktdataset
class SwapLeg(models.Model):
    trade = ForeignKey(Swap, CASCADE, related_name="legs")
    ccy = ForeignKey(Ccy, CASCADE, related_name='+')
    notional = DecimalField(max_digits=16,
                            decimal_places=2,
                            validators=[validate_positive])
    pay_rec = models.IntegerField(choices=SWAP_PAY_REC)
    gearing = DecimalField(default=1., max_digits=8, decimal_places=4)
    fixed_rate = DecimalField(max_digits=10, decimal_places=8, blank=True)
    index = ForeignKey(RateIndex,
                       SET_NULL,
                       blank=True,
                       null=True,
                       related_name='+')
    spread = DecimalField(max_digits=10, decimal_places=8, default=0.0)
    day_counter = CharField(max_length=16, choices=CHOICE_DAY_COUNTER.choices)
    schedule = ForeignKey(Schedule, CASCADE)

    def save(self, *args, **kwargs):
        if self.day_counter is None:
            self.day_counter = self.ccy.rate_day_counter
        super(SwapLeg, self).save(*args, **kwargs)

    def leg(self):  # need as_of??
        schd = self.schedule.schedule()
        dc = QL_DAY_COUNTER[self.day_counter]
        ntl = float(self.notional)
        if self.index:
            legIndex = self.mktdataset.get_irindex(self.index_id)
            return ql.IborLeg(schd, legIndex).withNotionals(ntl)
            if 'IBOR' in self.index.name:
                leg = ql.IborLeg([self.notional],
                                 schd,
                                 leg_idx,
                                 dc,
                                 fixingDays=[leg_idx.fixingDays()],
                                 spreads=[float(self.spread or 0.0)])
            elif 'OIS' in self.index.name:
                leg = ql.OvernightLeg([ntl],
                                      schd,
                                      leg_idx,
                                      dc,
                                      BusinessDayConvention=self.day_rule,
                                      gearing=[1],
                                      spread=self.spread,
                                      TelescopicValueDates=True)
            elif 'SOFR' in self.index.name:
                pass
            else:
                pass  # other floating leg
        else:  # self.index==None
            leg = ql.FixedRateLeg(schd, QL_DAY_COUNTER[self.day_counter],
                                  [ntl], [float(self.fixed_rate)])
        return leg

    def make_pricing_engine(self):
        if self.mktdataset:
            ccy = self.ccy.code
            name = self.mktdataset.get_rfyts_name(ccy)
            yts = self.mktdataset.get_yts(ccy, name)
        ytsh = ql.YieldTermStructureHandle
        return ql.DiscountingSwapEngine(ytsh(yts))

    # def discounting_curve(self, as_of):
    #     # return self.ccy.rf_curve.filter(ref_date=as_of).term_structure()
    #     return IRTermStructure.objects.filter(
    #         ref_date=as_of,
    #         name=self.ccy.risk_free_curve).first().term_structure()

    def NPV(self, as_of, discounting_curve=None):
        if discounting_curve:
            yts = discounting_curve
        else:
            yts = self.discounting_curve(as_of)
        return ql.CashFlows.npv(self.leg(as_of),
                                ql.YieldTermStructureHandle(yts))


@with_mktdataset
class Swaption(Trade):
    product_type = CharField(max_length=12, default="SWAPTION")
    exercise_date = models.DateField(null=False)
    buy_sell = CharField(max_length=1, choices=BUY_SELL, default='B')


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
        self.rfytss = dict()
        self.ytss = dict()
        self.spots = dict()  # FxSpotRateQuote
        self.fxvols = dict()
        self.irindexs = dict()
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

    def get_rfyts_name(self, ccy: str) -> str:
        name = self.rfytss.get(ccy)
        if name == None:
            yts = Ccy.objects.get(code=ccy).rf_curve.get(ref_date=self.date)
            yts.link_mktdataset(self)
            name = yts.name
            self.rfytss[ccy] = name
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

    def get_irindex(self, name):
        try:
            irindex = self.irindexs.get(name)
            if irindex == None:
                irindex = RateIndex.objects.get(name=name)
                self.irindexs[name] = irindex
            return irindex.index(ref_date=self.date, eff_date=self.date)
        except RuntimeError as error:
            raise error

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
