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
import pandas as pd
import math, time

FXO_TYPE = [("EUR", "European"), ("AME", "American"), ("DIG", "Digital"),
            ("BAR", "Barrier")]

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


def to_qlDate(d) -> ql.Date:
    if isinstance(d, str):
        return ql.DateParser.parseISO(d)
    elif isinstance(d, list):
        return [to_qlDate(dd) for dd in d]
    else:
        return ql.DateParser.parseISO(d.isoformat())


class User(AbstractUser):
    pass


class Calendar(models.Model):
    name = models.CharField(max_length=24, primary_key=True)

    def __str__(self):
        return self.name

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
        return self.cal.calendar()


class CcyPair(models.Model):
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

    def get_rate(self, date):
        return self.rates.get(ref_date=date)

    def calendar(self):
        if self.cal:
            return self.cal.calendar()
        else:
            ql.JointCalendar(self.base_ccy.cal.calendar(),
                             self.quote_ccy.cal.calendar())

    def fx_curves(self, ref_date):
        rts = self.quote_ccy.fx_curve.get(ref_date=ref_date).term_structure()
        qts = self.base_ccy.fx_curve.get(ref_date=ref_date).term_structure()
        return rts, qts


class FxSpotRateQuote(models.Model):
    ref_date = models.DateField()
    rate = models.FloatField()
    ccy_pair = models.ForeignKey(CcyPair, CASCADE, related_name="rates")

    class Meta:
        unique_together = ('ref_date', 'ccy_pair')

    def __init__(self, *args, **kwargs) -> None:
        self.rts = None
        self.qts = None
        super().__init__(*args, **kwargs)

    def set_yts(self, rts=None, qts=None):
        if rts:
            self.rts = rts
        if qts:
            self.qts = qts

    def handle(self):
        return ql.QuoteHandle(ql.SimpleQuote(self.rate))

    def spot_date(self):
        return self.ccy_pair.calendar().advance(
            to_qlDate(self.ref_date),
            ql.Period(self.ccy_pair.fixing_days, ql.Days))

    def forward_rate(self, maturity):
        sd = self.spot_date()
        if self.rts == None or self.qts == None:
            self.rts, self.qts = self.ccy_pair.fx_curves(self.ref_date)
        return self.rate / self.rts.discount(
            to_qlDate(maturity)) * self.rts.discount(sd) * self.qts.discount(
                to_qlDate(maturity)) / self.qts.discount(sd)

    def today_rate(self):
        return self.forward_rate(self.ref_date)

    def __str__(self):
        return f"{self.ccy_pair} as of {self.ref_date}"


class RateQuote(models.Model):
    name = models.CharField(max_length=16)  # e.g. USD OIS 12M
    ref_date = models.DateField()
    rate = models.FloatField()
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

        q = ql.QuoteHandle(ql.SimpleQuote(self.rate))
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
            if self.ccy.code == "USD":
                # https://quant.stackexchange.com/questions/32345/quantlib-python-dual-curve-bootstrapping-example
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
        elif self.instrument == "FXSW":
            # ql.FxSwapRateHelper(fwdPoint, spotFx, tenor, fixingDays, calendar, convention, endOfMonth, isFxBaseCurrencyCollateralCurrency, collateralCurve)
            if self.ccy_pair:
                ref_curve = kwargs.get('ref_curve')  # is a handle
                fixing_days = self.ccy_pair.fixing_days if fixing_days == None else fixing_days
                return ql.FxSwapRateHelper(
                    ql.QuoteHandle(ql.SimpleQuote(self.rate)),
                    ql.QuoteHandle(
                        ql.SimpleQuote(
                            self.ccy_pair.rates.get(
                                ref_date=self.ref_date).rate)), tenor_,
                    fixing_days, self.ccy_pair.calendar(), ql.Following, True,
                    self.ccy == self.ccy_pair.quote_ccy, ref_curve), q
            else:
                raise KeyError(
                    'CcyPair does not exist in FXSW type rate quote')

    def __str__(self):
        return f"{self.name} as of {self.ref_date.strftime('%Y-%m-%d')}: {self.rate}"


class IRTermStructure(models.Model):
    name = models.CharField(max_length=16)
    ref_date = models.DateField()
    ccy = models.ForeignKey(Ccy,
                            CASCADE,
                            related_name="all_curves",
                            null=True,
                            blank=True)
    rates = models.ManyToManyField(RateQuote, related_name="ts")
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
        print(f'Called __init__ {self.name} {self.ref_date} {self.ccy}')

    def term_structure(self):
        if self.yts == None:
            dc = ql.Actual365Fixed()
            # change to helper(ccy.rf_curve.term_structure())
            ref_curve_ = None
            if self.ref_curve and self.ref_ccy:
                ref_curve_ = IRTermStructure.objects.get(
                    name=self.ref_curve,
                    ccy=self.ref_ccy,
                    ref_date=self.ref_date).term_structure()
            rates = cache.get(f'{self.ccy}-{self.name}-{self.ref_date}')
            if rates == None:
                rates = self.rates.all()
                cache.set(f'{self.ccy}-{self.name}-{self.ref_date}', rates, 60)
            helpers = [
                rate.helper(
                    ref_curve=ql.YieldTermStructureHandle(ref_curve_))[0]
                for rate in rates
            ]
            self.yts = ql.PiecewiseLogLinearDiscount(to_qlDate(self.ref_date),
                                                     helpers, dc)
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
            first_fixing_date = idx_obj.fixingDate(to_qlDate(eff_date))
            for f in self.fixings.filter(
                    ref_date__gte=first_fixing_date.ISO()):
                idx_obj.addFixings([to_qlDate(f.ref_date)], [f.value])

        return idx_obj


class RateIndexFixing(models.Model):
    value = models.FloatField()
    index = models.ForeignKey(RateIndex, CASCADE, related_name="fixings")
    ref_date = models.DateField()

    class Meta:
        unique_together = ('ref_date', 'index')

    def __str__(self):
        return f'{self.index} on {self.ref_date}'


class FXVolatility(models.Model):
    ref_date = models.DateField()
    ccy_pair = models.ForeignKey(CcyPair, CASCADE, related_name='vol')

    # use '.quotes to get quotes'

    class Meta:
        verbose_name_plural = "FX volatilities"
        unique_together = ('ref_date', 'ccy_pair')

    class TargetFun:

        def __init__(self, ref_date, spot, rdf, qdf, strike, maturity, deltas,
                     delta_types, smile_section):
            self.ref_date = ref_date
            self.strike = strike
            self.maturity = to_qlDate(maturity)
            self.delta_types = delta_types[0]
            self.interp = ql.LinearInterpolation(deltas, smile_section)
            self.spot = spot
            self.rDcf = rdf
            self.qDcf = qdf

        def __call__(self, v0):
            optionType = ql.Option.Call
            stdDev = math.sqrt(ql.Actual365Fixed().yearFraction(
                to_qlDate(self.ref_date), self.maturity)) * v0
            calc = ql.BlackDeltaCalculator(optionType, self.delta_types,
                                           self.spot, self.rDcf, self.qDcf,
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
                    surf_vol[row].append(q.vol)
                    surf_delta[row].append(q.delta)
                    surf_delta_type[row].append(QL_DELTA_TYPE[q.delta_type])
                else:
                    surf_vol.append([q.vol])
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

    def set_spot(self, spot):
        self.spot = spot  # FXSpotRateQuote

    def handle(self, strike, **kwargs):

        surf_vol, surf_delta, surf_delta_type, maturities = self.surface_matrix(
        )

        solver = ql.Brent()
        accuracy = 1e-12
        step = 1e-6
        volatilities = []
        """if kwargs.get('maturity'):
            mat = kwargs.get('maturity')
            ii = []
            ii.append(max([j for j, m in maturities if m <= to_qlDate(mat)]))
            ii.append(min([j for j, m in maturities if m >= to_qlDate(mat)]))
            surf_vol = [surf_vol[i_] for i_ in ii if i_]
            surf_delta = [surf_delta[i_] for i_ in ii if i_]
            surf_delta_type = [surf_delta_type[i_] for i_ in ii if i_]
            maturities = [maturities[i_] for i_ in ii if i_]"""

        if self.spot == None:
            self.spot = self.ccy_pair.rates.get(ref_date=self.ref_date)
        s0 = self.spot.today_rate()

        if self.rts == None:  # yts is the slowest part
            self.rts = self.ccy_pair.quote_ccy.fx_curve.filter(
                ref_date=self.ref_date).first().term_structure()
        if self.qts == None:
            self.qts = self.ccy_pair.base_ccy.fx_curve.filter(
                ref_date=self.ref_date).first().term_structure()

        for i, smile in enumerate(surf_vol):
            mat = to_qlDate(maturities[i])
            target = self.TargetFun(self.ref_date, s0, self.rts.discount(mat),
                                    self.qts.discount(mat), strike,
                                    maturities[i], surf_delta[i],
                                    surf_delta_type[i], smile)
            guess = smile[2]
            volatilities.append(solver.solve(target, accuracy, guess, step))
        vts = ql.BlackVarianceCurve(to_qlDate(self.ref_date),
                                    to_qlDate(maturities), volatilities,
                                    ql.Actual365Fixed(), False)
        vts.enableExtrapolation()

        if kwargs.get('maturity'):
            return (ql.BlackVolTermStructureHandle(vts),
                    vts.blackVol(to_qlDate(kwargs.get('maturity')), strike,
                                 True))
        else:
            return ql.BlackVolTermStructureHandle(vts)

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
    vol = models.FloatField(validators=[validate_positive])
    surface = models.ForeignKey(FXVolatility, CASCADE, related_name='quotes')
    delta_type = models.CharField(choices=CHOICE_DELTA_TYPE.choices,
                                  max_length=8,
                                  null=True)
    maturity = models.DateField(null=True, blank=True)

    def save(self, *args, **kwargs):
        self.maturity = (to_qlDate(self.ref_date) +
                         ql.Period(self.tenor)).ISO()
        if self.delta < 0:
            self.delta = round(1.0 + self.delta, 8)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'({self.ref_date}, {self.tenor}, {self.delta})'


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
    ccy_pairs = {}
    spot = {}  # dict
    yts = {}  # dict

    def __init__(self, ref_date) -> None:
        self.ref_date = ref_date

    def addCcyPair(self, ccy_pair):  # ccy_pair in XXX/YYY format
        self.ccy_pairs.add(ccy_pair)
        ccy1, ccy2 = ccy_pair[:2], ccy_pair[3:]
        if ccy1 not in self.yts:
            self.yts[ccy1] = IRTermStructure.objects.get(
                ref_date=self.ref_date, ccy=ccy1).term_structure()
        if ccy2 not in self.yts:
            self.yts[ccy2] = IRTermStructure.objects.get(
                ref_date=self.ref_date, ccy=ccy2).term_structure()
        if ccy_pair not in self.spot:
            self.spot[ccy_pair] = ql.QuoteHandle(
                ql.SimpleQuote(
                    CcyPair.objects.get(name=ccy_pair).get_rate(
                        self.ref_date)))

    def get_market_date(self, ref_date):
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


#@has_make_pricing_engine
class FXO(Trade):
    product_type = models.CharField(max_length=12, default="FXO")
    maturity_date = models.DateField(null=False, default=datetime.date.today)
    buy_sell = models.CharField(max_length=1, choices=BUY_SELL, default='B')
    ccy_pair = models.ForeignKey(CcyPair, models.DO_NOTHING, null=False)
    strike_price = models.FloatField(validators=[validate_positive])
    notional_1 = models.FloatField(default=1e6, validators=[validate_positive])
    notional_2 = models.FloatField(validators=[validate_positive])
    type = models.CharField(max_length=5, choices=FXO_TYPE)
    cp = models.CharField(max_length=1, choices=FXO_CP)
    objects = FXOManager()

    def __str__(self):
        return f"FXO ID: {self.id}, {self.ccy_pair}, Notional={self.notional_1:.0f}, K={self.strike_price}, {self.cp}"

    def save(self, *args, **kwargs):
        if self.notional_2 == None:
            self.notional_2 = self.notional_1 * self.strike_price
        super().save(*args, **kwargs)

    def instrument(self):
        cp = ql.Option.Call if self.cp == "C" else ql.Option.Put
        if self.type == 'EUR':
            payoff = ql.PlainVanillaPayoff(cp, self.strike_price)
        elif self.type == 'DIG':
            payoff = ql.CashOrNothingPayoff(cp, self.strike_price, 1.0)
        else:
            payoff = ql.PlainVanillaPayoff(cp, self.strike_price)
        exercise = ql.EuropeanExercise(to_qlDate(self.maturity_date))
        inst = ql.VanillaOption(payoff, exercise)
        return inst

    def link_mktset(self, mktset):
        """ check whether ccy_pair is in mktset """
        if self.ccy_pair.name in mktset.ccy_pair:
            self.mktset = mktset
            return True
        else:
            return False

    def make_pricing_engine(self):
        if self.mktset:
            mkt = self.mktset.fxo_mkt_data(self.ccy_pair.name)
            process = ql.BlackScholesMertonProcess(
                mkt.spot.rate, ql.YieldTermStructureHandle(mkt.qts),
                ql.YieldTermStructureHandle(mkt.rts),
                mkt.vol.handle(self.strike_price))
            return {
                'engine': ql.AnalyticEuropeanEngine(process),
                'process': process
            }


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
    trade = models.ForeignKey(Swap,
                              CASCADE,
                              null=True,
                              blank=True,
                              related_name="legs")
    ccy = models.ForeignKey(Ccy, CASCADE)
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
        return ql.MakeSchedule(to_qlDate(self.effective_date),
                               to_qlDate(self.maturity_date),
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
