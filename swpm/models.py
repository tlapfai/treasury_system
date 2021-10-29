from django.db import models
from django.db.models.deletion import CASCADE, DO_NOTHING
from django.db.models.fields.related import ForeignKey
from django.utils import timezone
from django.forms import ModelForm, SelectDateWidget, DateInput
from django import forms
import QuantLib as ql

FXO_TYPE = [("EUR", "European"), 
        ("AME", "American"), 
        ("DIG", "Digital"), 
        ("BAR", "Barrier")]
    
FXO_CP = [("C","Call"), ("P","Put")]

DAY_COUNTER = {"A360": ql.Actual360(), 'A365Fixed': ql.Actual365Fixed()}

CALENDAR_LIST = {'TARGET': ql.TARGET(), 'UnitedStates': ql.UnitedStates(), 'HongKong': ql.HongKong(), 'UnitedKingdom': ql.UnitedKingdom()}

class Calendar(models.Model):
    name = models.CharField(max_length=16)
    def __str__(self):
        return self.name
    def calendar(self):
        return CALENDAR_LIST[self.name]

class Ccy(models.Model):
    code = models.CharField(max_length=3, blank=False)
    fixing_days = models.PositiveIntegerField(default=2)
    cdr = models.ForeignKey(Calendar, DO_NOTHING, related_name="ccys", null=True)
    def __str__(self):
        return self.code

class CcyPair(models.Model):
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
    def handle(self):
        return ql.QuoteHandle(ql.SimpleQuote(self.rate))
    def __str__(self):
        return f"{self.ccy_pair}: {self.rate} as of {self.ref_date}"
    
class RateIndex(models.Model):
    name = models.CharField(max_length=16)

class RateQuote(models.Model):
    name = models.CharField(max_length=16)
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
            return ql.DepositRateHelper(self.rate, ql.Period(self.tenor), fixing_days, ql.TARGET(), convention, False, DAY_COUNTER[self.day_counter])
    def __str__(self):
        return f"{self.name}: ({self.ccy}): {self.rate}"

class IRTermStructure(models.Model):
    name = models.CharField(max_length=16)
    ref_date = models.DateField()
    rates = models.ManyToManyField(RateQuote, related_name="ts")
    as_fx_curve = models.OneToOneField(Ccy, CASCADE, related_name="fx_curve", null=True)
    as_rf_curve = models.OneToOneField(Ccy, CASCADE, related_name="rf_curve", null=True)
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


class FXO(models.Model):
    active = models.BooleanField(default=True)
    create_time = models.DateTimeField(auto_now_add=True)
    trade_date = models.DateField(null=False)
    maturity_date = models.DateField(null=False)
    ccy_pair = models.ForeignKey(CcyPair, models.DO_NOTHING, null=False, related_name='options')
    strike_price = models.FloatField()
    notional_1 = models.FloatField()
    notional_2 = models.FloatField()
    type = models.CharField(max_length=5, choices=FXO_TYPE)
    cp = models.CharField(max_length=1, choices=FXO_CP)
    objects = FXOManager()
    
    def serialize(self):
        pass

    def __str__(self):
        return f"FXO ID: {self.id}, {self.ccy_pair}, K={self.strike_price}"
    
    def instrument(self):
        if self.active:
            cp = ql.Option.Call if self.cp=="C" else ql.Option.Put
            print(self.type)
            if self.type == 'EUR':
                payoff = ql.PlainVanillaPayoff(cp, self.strike_price)
            elif self.type == 'DIG':
                payoff = ql.CashOrNothingPayoff(cp, self.strike_price, 1.0)
            else:
                payoff = ql.PlainVanillaPayoff(cp, self.strike_price)
            exercise = ql.EuropeanExercise(ql.Date(self.maturity_date.isoformat(), '%Y-%m-%d'))
            inst = ql.VanillaOption(payoff, exercise)
            return inst

    def make_pricing_engine(self, as_of_date):
        if self.active:
            spot_rate = self.ccy_pair.rates.get(ref_date=as_of_date)
            v = self.ccy_pair.vol.get(ref_date=as_of_date).handle()
            q = self.ccy_pair.base_ccy.fx_curve.term_structure()
            r = self.ccy_pair.quote_ccy.fx_curve.term_structure()
            process = ql.BlackScholesMertonProcess(spot_rate.handle(), q, r, v)
            return ql.AnalyticEuropeanEngine(process)

class CcyPairForm(ModelForm):
    class Meta:
        model = CcyPair
        fields = '__all__'
        
class FXOForm(ModelForm):
    class Meta:
        model = FXO
        fields = ['trade_date', 'maturity_date', 'ccy_pair', 'strike_price', 'notional_1', 'notional_2', 'type', 'cp']
        widgets = {
            'trade_date': DateInput(attrs={'type': 'date'}),
            'maturity_date': DateInput(attrs={'type': 'date'}),
            }
        labels = {
            'cp': 'Call or Put',
            }
        help_texts = {
            'ccy_pair': 'Choose a pair'
            }
    #def __init__(self, *args, **kwargs):
    #    super().__init__(*args, **kwargs)
    #    self.fields['trade_date'].widget.attrs.update({'type': 'date'})
