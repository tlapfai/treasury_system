from django.forms import ModelForm, SelectDateWidget, DateInput
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
        fields = ['trade_date', 'maturity_date', 'ccy_pair', 'type', 'cp', 'buy_sell', 'strike_price', 'notional_1', 'notional_2']
        widgets = {
            'trade_date': DateInput(attrs={'type': 'date'}),
            'maturity_date': DateInput(attrs={'type': 'date'}),
            }
        labels = {
            'buy_sell': 'Buy/Sell',
            'cp': 'Call or Put',
            }
        help_texts = {
            #'ccy_pair': 'Choose a pair'
            }
    #def __init__(self, *args, **kwargs):
    #    super().__init__(*args, **kwargs)
    #    self.fields['trade_date'].widget.attrs.update({'type': 'date'})

class TradeDetailForm(ModelForm):
    class Meta:
        model = TradeDetail
        fields = ['book']

class AsOfForm(forms.Form):
    as_of = forms.DateField(widget=DateInput(attrs={'type': 'date'}))

class RevalForm(forms.Form):
    reval_date = forms.DateField(widget=DateInput(attrs={'type': 'date'}))
    books = forms.ModelMultipleChoiceField(Book.objects.all())
    
