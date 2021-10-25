from django.db import models
from django.db.models.deletion import CASCADE, DO_NOTHING
from django.db.models.fields.related import ForeignKey
from django.utils import timezone
import QuantLib as ql

FXO_TYPE = [("EUR","European"), 
        ("AME", "American"), 
        ("DIG", "Digital"), 
        ("BAR", "Barrier")]
    
FXO_CP = [("C","Call"), ("P","Put")]

DAY_COUNTER = {"A360": ql.Actual360()}

class Calendar(models.Model):
    name = models.CharField(max_length=16)
    def calendar(self):
        return ql.TARGET()

class Ccy(models.Model):
    code = models.CharField(max_length=3, blank=False)
    fixing_days = models.PositiveIntegerField()
    def __str__(self):
        return self.code

class CcyPair(models.Model):
    base_ccy = models.ForeignKey(Ccy, CASCADE, related_name="as_base_ccy")
    quote_ccy = models.ForeignKey(Ccy, CASCADE, related_name="as_quote_ccy")
    cdr = models.ForeignKey(Calendar, DO_NOTHING, related_name="ccy_pair")
    def check_order():
        # check correct order
        return True
    def __str__(self):
        return f"{self.base_ccy}/{self.quote_ccy}"
    def calendar(self):
        return cdr.calendar()
    
class RateIndex(models.Model):
    name = models.CharField(max_length=16)

class RateQuote(models.Model):
    name = models.CharField(max_length=16)
    rate = models.FloatField()
    tenor = models.CharField(max_length=5)
    type = models.CharField(max_length=5)
    ccy = models.ForeignKey(Ccy, CASCADE, related_name="rates")
    day_counter = models.CharField(max_length=5)
    def helper(self):
        if type == "DEP":
            fixing_days = self.ccy.fixing_days
            convention = ql.ModifiedFollowing
            ccy = Ccy.objects.get(code=self.ccy)
            return ql.DepositRateHelper(self.rate, ql.Period(self.tenor), ccy.fixing_days, ql.TARGET(), convention, False, DAY_COUNTER[self.day_counter])
    def __str__(self):
        return f"{self.name}: {self.ccy}: {self.rate}"

class IRTermStructure(models.Model):
    name = models.CharField(max_length=16)
    ref_date = models.DateField()
    rates = models.ManyToManyField(RateQuote, related_name="ts")
    def term_structure(self):
        helpers = [rate.helper() for rate in rates]
        return ql.PiecewiseLogLinearDiscount(ql.Date(self.ref_date.isoformat(),'%Y-%m-%d'), helpers, ql.Actual360())
    def ccy(self):
        return rates[0].ccy

class FXVolatility(models.Model):
    ref_date = models.DateField()
    ccy_pair = models.ForeignKey(CcyPair, related_name='vol')
    vol = models.FloatField()
    def black_vol(self):
        return ql.BlackConstantVol(ql.Date(self.ref_date.isoformat(),'%Y-%m-%d'), ccy_pair.calendar(), vol, ql.Actual365Fixed)
    
class FXOManager(models.Manager):
    def create_fxo(self, trade_date, maturity_date, ccypair, strike_price, type, cp, notional_1):
        fxo = self.create(
            trade_date = trade_date, 
            maturity_date = maturity_date, 
            ccypair = ccypair, 
            strike_price = strike_price, 
            type = type, 
            cp = cp, 
            notional_1 = notional_1, 
            notional_2 = notional_1 * strike_price
        )
        return fxo


class FXO(models.Model):
    active = models.BooleanField(default=True)
    create_time = models.DateTimeField(auto_now_add=True)
    trade_date = models.DateField(null=False)
    maturity_date = models.DateField(null=False)
    ccypair = models.ForeignKey(CcyPair, models.DO_NOTHING, null=False, related_name='options')
    strike_price = models.FloatField()
    notional_1 = models.FloatField()
    notional_2 = models.FloatField()
    type = models.CharField(max_length=5, choices=FXO_TYPE)
    cp = models.CharField(max_length=1, choices=FXO_CP)
    objects = FXOManager()

    def __str__(self):
        return f"FXO ID: {self.id}, {self.ccypair}, K={self.strike_price}"
    
    def instrument(self):
        if self.active:
            cp = ql.Option.Call if self.cp=="C" else ql.Option.Put 
            payoff = ql.PlainVanillaPayoff(cp, self.strike_price)
            exercise = ql.EuropeanExercise(ql.Date(self.maturity_date.isoformat(), '%Y-%m-%d'))
            european_option = ql.VanillaOption(payoff, exercise)
            return european_option


