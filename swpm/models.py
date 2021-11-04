import datetime
from QuantLib.QuantLib import PiecewiseLogLinearDiscount
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.deletion import CASCADE, DO_NOTHING, SET_NULL, SET_DEFAULT
from django.db.models.fields.related import ForeignKey
from django.utils import timezone
from django.core.exceptions import ValidationError
import QuantLib as ql

FXO_TYPE = [("EUR", "European"), 
        ("AME", "American"), 
        ("DIG", "Digital"), 
        ("BAR", "Barrier")]
    
FXO_CP = [("C","Call"), ("P","Put")]

SWAP_PAY_REC = [(1, "Receive"), (-1, "Pay")]

BUY_SELL = [("B", "Buy"), ("S", "Sell")]

DAY_COUNTER = [("A360", "A360"), ('A365Fixed', 'A365Fixed')]
QL_DAY_COUNTER = {"A360": ql.Actual360(), 'A365Fixed': ql.Actual365Fixed()}
# https://docs.djangoproject.com/en/3.2/ref/models/fields/#enumeration-types

CALENDAR_LIST = {'TARGET': ql.TARGET(), 'UnitedStates': ql.UnitedStates(), 'HongKong': ql.HongKong(), 'UnitedKingdom': ql.UnitedKingdom()}

def validate_positive(value):
    if value <= 0:
        raise ValidationError()

class User(AbstractUser):
    pass

class Calendar(models.Model):
    name = models.CharField(max_length=16)
    def __str__(self):
        return self.name
    def calendar(self):
        return CALENDAR_LIST[self.name]

class Ccy(models.Model):
    code = models.CharField(max_length=3, blank=False, primary_key=True)
    fixing_days = models.PositiveIntegerField(default=2)
    cdr = models.ForeignKey(Calendar, DO_NOTHING, related_name="ccys", null=True)
    def __str__(self):
        return self.code

class CcyPair(models.Model):
    name = models.CharField(max_length=7, primary_key=True)
    base_ccy = models.ForeignKey(Ccy, CASCADE, related_name="as_base_ccy")
    quote_ccy = models.ForeignKey(Ccy, CASCADE, related_name="as_quote_ccy")
    cdr = models.ForeignKey(Calendar, DO_NOTHING, related_name="ccy_pairs", null=True)
    fixing_days = models.PositiveIntegerField(default=2)
    def check_order():
        # check correct order
        return True
    def __str__(self):
        return f"{self.base_ccy}/{self.quote_ccy}"
    def get_rate(self, date):
        return self.rates.get(ref_date=date)
    def calendar(self):
        return self.cdr.calendar()

class FxSpotRateQuote(models.Model):
    ref_date = models.DateField()
    rate = models.FloatField()
    ccy_pair = models.ForeignKey(CcyPair, CASCADE, related_name="rates")
    class Meta:
        unique_together = ('ref_date', 'ccy_pair')
    def handle(self):
        return ql.QuoteHandle(ql.SimpleQuote(self.rate))
    def __str__(self):
        return f"{self.ccy_pair}: {self.rate} as of {self.ref_date}"
    
class RateIndex(models.Model):
    name = models.CharField(max_length=16, primary_key=True)
    ccy = models.ForeignKey(Ccy, CASCADE, related_name="rate_indexs")
    def __str__(self):
        return self.name

class RateQuote(models.Model):
    name = models.CharField(max_length=16)
    ref_date = models.DateField()
    rate = models.FloatField()
    tenor = models.CharField(max_length=5)
    instrument = models.CharField(max_length=5)
    ccy = models.ForeignKey(Ccy, CASCADE, related_name="rates")
    day_counter = models.CharField(max_length=16)
    def helper(self):
        if self.instrument == "DEPO":
            fixing_days = self.ccy.fixing_days
            convention = ql.ModifiedFollowing
            ccy = Ccy.objects.get(code=self.ccy)
            return ql.DepositRateHelper(self.rate, ql.Period(self.tenor), fixing_days, ql.TARGET(), convention, False, QL_DAY_COUNTER[self.day_counter])
    def __str__(self):
        return f"{self.name}: ({self.ccy}): {self.rate}"

class IRTermStructure(models.Model):
    name = models.CharField(max_length=16)
    ref_date = models.DateField()
    rates = models.ManyToManyField(RateQuote, related_name="ts")
    as_fx_curve = models.ForeignKey(Ccy, CASCADE, related_name="fx_curve", null=True)
    as_rf_curve = models.ForeignKey(Ccy, CASCADE, related_name="rf_curve", null=True)
    def term_structure(self):
        helpers = [rate.helper() for rate in self.rates.all()]
        return ql.YieldTermStructureHandle(ql.PiecewiseLogLinearDiscount(ql.Date(self.ref_date.isoformat(),'%Y-%m-%d'), helpers, ql.Actual360()))
    def ccy(self):
        return self.rates[0].ccy
    def __str__(self):
        return f"{self.name}"

class FXVolatility(models.Model):
    ref_date = models.DateField()
    ccy_pair = models.ForeignKey(CcyPair, CASCADE, related_name='vol')
    vol = models.FloatField()
    class Meta:
        verbose_name_plural = "FX volatilities"
    def handle(self):
        return ql.BlackVolTermStructureHandle(
            ql.BlackConstantVol(ql.Date(self.ref_date.isoformat(),'%Y-%m-%d'), self.ccy_pair.calendar(), self.vol, ql.Actual365Fixed()))
    def __str__(self):
        return f"{self.ccy_pair} as of {self.ref_date}"
    
class FXOManager(models.Manager):
    def create_fxo(self, trade_date, maturity_date, ccy_pair, strike_price, type, cp, notional_1):
        fxo = self.create(
            trade_date = trade_date, 
            maturity_date = maturity_date, 
            ccy_pair = ccy_pair, 
            strike_price = strike_price, 
            type = type, 
            cp = cp, 
            notional_1 = notional_1, 
            notional_2 = notional_1 * strike_price
        )
        return fxo

class Portfolio(models.Model):
    name = models.CharField(max_length=16, primary_key=True)
    def __str__(self) -> str:
        return self.name


class Book(models.Model):
    name = models.CharField(max_length=16, primary_key=True)
    portfolio = models.ForeignKey(Portfolio, DO_NOTHING, related_name="books")
    owner = models.ForeignKey(User, DO_NOTHING, null=True, related_name="books")
    def __str__(self) -> str:
        return self.name

class Counterparty(models.Model):
    code = models.CharField(max_length=16, primary_key=True)
    name = models.CharField(max_length=64)
    is_internal = models.OneToOneField(Book, DO_NOTHING, null=True, blank=True, related_name="internal_cpty")
    class Meta:
        verbose_name_plural = "Counterparties"
    def __str__(self) -> str:
        return self.name
    
class TradeDetail(models.Model):
    #trade = models.ForeignKey(FXO, CASCADE, related_name="detail")
    pass
    #def __str__(self) -> str:
    #    return f"ID: {self.trade.first().id} in book [{self.book}]"

class TradeMarkToMarket(models.Model):
    as_of = models.DateField()
    trade_d = models.ForeignKey(TradeDetail, CASCADE, null=True, related_name="mtms")
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
    trade_date = models.DateField(null=False)
    detail = models.OneToOneField(TradeDetail, CASCADE, null=True, related_name="trade")
    
    book = models.ForeignKey(Book, SET_NULL, null=True, blank=True, related_name="trades")
    input_user = models.ForeignKey(User, SET_NULL, null=True, related_name='input_trades')
    counterparty = models.ForeignKey(Counterparty, DO_NOTHING, related_name="trade_set", null=True, blank=True)
    def delete(self, *args, **kwargs):
         if self.detail:
             self.detail.delete()
         super().delete(*args, **kwargs)
    #class Meta:
        #abstract = True
        #ordering = ['id']
    # def save(self, *args, **kwargs):
    #     if self.detail == None:
    #         d = TradeDetail.objects.create()
    #         d.save()
    #         self.detail = d
    #     super().save(*args, **kwargs)

        

class FXO(Trade):
    maturity_date = models.DateField(null=False, default=datetime.date.today())
    buy_sell = models.CharField(max_length=1, choices=BUY_SELL)
    ccy_pair = models.ForeignKey(CcyPair, models.DO_NOTHING, null=False, related_name='options')
    strike_price = models.FloatField(validators=[validate_positive])
    notional_1 = models.FloatField(validators=[validate_positive])
    notional_2 = models.FloatField(validators=[validate_positive])
    type = models.CharField(max_length=5, choices=FXO_TYPE)
    cp = models.CharField(max_length=1, choices=FXO_CP)
    objects = FXOManager()

    def __str__(self):
        return f"FXO ID: {self.id}, {self.ccy_pair}, Notional={self.notional_1:.0f}, K={self.strike_price}"
    
    def save(self, *args, **kwargs):
        if self.notional_2 == None:
            self.notional_2 = self.notional_1 * self.strike_price
        super().save(*args, **kwargs)
    
    def instrument(self):
        cp = ql.Option.Call if self.cp=="C" else ql.Option.Put
        if self.type == 'EUR':
            payoff = ql.PlainVanillaPayoff(cp, self.strike_price)
        elif self.type == 'DIG':
            payoff = ql.CashOrNothingPayoff(cp, self.strike_price, 1.0)
        else:
            payoff = ql.PlainVanillaPayoff(cp, self.strike_price)
        exercise = ql.EuropeanExercise(ql.Date(self.maturity_date.isoformat(), '%Y-%m-%d'))
        inst = ql.VanillaOption(payoff, exercise)
        return inst

    def make_pricing_engine(self, as_of):
        if self.active:
            spot_rate = self.ccy_pair.rates.get(ref_date=as_of)
            v = self.ccy_pair.vol.get(ref_date=as_of).handle()
            q = IRTermStructure.objects.get(ref_date=as_of, as_fx_curve=self.ccy_pair.base_ccy).term_structure()
            r = IRTermStructure.objects.get(ref_date=as_of, as_fx_curve=self.ccy_pair.quote_ccy).term_structure()
            process = ql.BlackScholesMertonProcess(spot_rate.handle(), q, r, v)
            return ql.AnalyticEuropeanEngine(process)


class SwapManager():
    pass

class Swap(Trade):
    objects = SwapManager()


class SwapLeg(models.Model):
    trade = models.ForeignKey(Swap, DO_NOTHING, related_name="legs")
    ccy = models.ForeignKey(Ccy, CASCADE, related_name="swap_legs")
    effective_date = models.DateField(default=datetime.date.today())
    maturity_date = models.DateField(default=datetime.date.today())
    notional = models.FloatField()
    pay_rec = models.IntegerField(choices=SWAP_PAY_REC)
    fixed_rate = models.FloatField(default=0, null=True, blank=True)
    index = models.ForeignKey(RateIndex, SET_NULL, null=True, blank=True)
    spread = models.FloatField(default=0, null=True)
    reset_freq = models.CharField(max_length=10, null=True, blank=True)
    payment_freq = models.CharField(max_length=16)
    day_counter = models.CharField(max_length=16, choices=DAY_COUNTER)
    def instrument(self):
        pass
    

