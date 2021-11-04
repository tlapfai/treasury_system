from django.forms import ModelForm, modelformset_factory, SelectDateWidget, DateInput, NumberInput
from django import forms
import datetime
from .models import *

class CcyPairForm(ModelForm):
    class Meta:
        model = CcyPair
        fields = '__all__'
        
class FXOForm(ModelForm):
    class Meta:
        model = FXO
        fields = ['trade_date', 'maturity_date', 'ccy_pair', 'type', 'cp', 'buy_sell', 'strike_price', 'notional_1', 'notional_2', 'book', 'counterparty']
        #exclude = ['id', 'create_time', 'detail', 'input_user']
        widgets = {
            'trade_date': DateInput(attrs={'type': 'date'}),
            'maturity_date': DateInput(attrs={'type': 'date'}),
            'strike_price': NumberInput(attrs={'step': '0.0001'}), 
            }
        labels = {
            'buy_sell': 'Buy/Sell',
            'cp': 'Call/Put',
            }
        help_texts = {
            #'ccy_pair': 'Choose a pair'
            }
    #def __init__(self, *args, **kwargs):
    #    super().__init__(*args, **kwargs)
    #    self.fields['trade_date'].widget.attrs.update({'type': 'date'})

class FXOValuationForm(forms.Form):
    npv = forms.FloatField(label="NPV", disabled=True)
    delta = forms.FloatField(label="Delta", disabled=True)
    gamma = forms.FloatField(disabled=True)
    vega = forms.FloatField(disabled=True)
    theta = forms.FloatField(disabled=True)
    dividendRho = forms.FloatField(disabled=True, label="Ccy1 Rho")
    rho = forms.FloatField(disabled=True, label="Ccy2 Rho")
    itmCashProbability = forms.FloatField(disabled=True, label="ITM Cash Probability")

class SwapLegForm(ModelForm):
    class Meta:
        model = SwapLeg
        fields = ['ccy', 'effective_date', 'maturity_date', 'notional', 'pay_rec', 'fixed_rate', 
            'index', 'spread', 'reset_freq', 'payment_freq', 'day_counter']
        widgets = {
            'effective_date': DateInput(attrs={'type': 'date'}),
            'maturity_date': DateInput(attrs={'type': 'date'}),
            }
        labels = {
            'pay_rec': 'Pay/Receive', 
        }

class SwapForm(ModelForm):
    class Meta:
        model = Swap
        fields = ['trade_date', 'book', 'counterparty']
        widgets = {
            'trade_date': DateInput(attrs={'type': 'date'}),
        }

class TradeDetailForm(ModelForm):
    pass
    #class Meta:
    #    model = TradeDetail
    #    fields = ['book']

class AsOfForm(forms.Form):
    as_of = forms.DateField(widget=DateInput(attrs={'type': 'date'}))

class RevalForm(forms.Form):
    reval_date = forms.DateField(widget=DateInput(attrs={'type': 'date'}))
    books = forms.ModelMultipleChoiceField(Book.objects.all())
    
