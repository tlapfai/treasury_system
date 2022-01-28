from django.db.models import fields
from django.forms import ModelForm, modelformset_factory, SelectDateWidget, DateInput, NumberInput, RadioSelect, ModelMultipleChoiceField, widgets, TextInput
from django import forms
from django.forms.models import BaseModelFormSet, ModelChoiceField
from django.utils.translation import gettext as _
from django.utils.safestring import mark_safe
from django.forms import Widget
import datetime

from django_plotly_dash.dash_wrapper import wid2str
from .models import *


class HorizontalRadioSelect(RadioSelect):
    template_name = 'swpm/includes/horizontal_multiple_input.html'


class CcyPairForm(ModelForm):

    class Meta:
        model = CcyPair
        fields = '__all__'


class FxSpotRateQuoteForm(ModelForm):

    class Meta:
        model = FxSpotRateQuote
        fields = ['ccy_pair', 'rate']
        widgets = {'ccy_pair': TextInput(attrs={'readonly': 'readonly'})}


class IRTermStructureForm(ModelForm):

    class Meta:
        model = IRTermStructure
        fields = '__all__'

    #rates = ModelMultipleChoiceField(widget = forms.CheckboxSelectMultiple, queryset = RateQuote.objects.filter(XXXXXXX=ref_date))
    # https://medium.com/@alfarhanzahedi/customizing-modelmultiplechoicefield-in-a-django-form-96e3ae7e1a07
    # curve should be setup day-by-day, the page should hv some variable storing the date


class FXOForm(ModelForm):
    tenor = forms.CharField(required=False)

    class Meta:
        model = FXO
        fields = [
            'buy_sell', 'trade_date', 'maturity_date', 'ccy_pair', 'type',
            'cp', 'strike_price', 'notional_1', 'notional_2', 'book',
            'counterparty', 'tenor'
        ]
        """ list all the necessary fields and put them in order
        https://stackoverflow.com/questions/43067707/why-doesnt-my-django-template-render-a-modelforms-id-or-pk-field
        The id field automatically has editable=False, which means by default it doesn't show up in any model forms."""
        widgets = {
            'buy_sell':
            HorizontalRadioSelect(attrs={'class': "form-check-input"}),
            'trade_date':
            DateInput(attrs={
                'type': 'date',
                'class': "form-control"
            }),
            'maturity_date':
            DateInput(attrs={'type': 'date'}),
            'notional_1':
            NumberInput(attrs={'class': "form-control"})
        }
        labels = {
            'buy_sell': 'Buy/Sell',
            'cp': 'Call/Put',
        }
        help_texts = {
            # 'ccy_pair': 'Choose a pair'
        }

    def clean(self):
        try:
            cleaned_data = super().clean()
            option_type = cleaned_data.get('type')
            if option_type == "EUR" and abs(
                    cleaned_data.get('strike_price') *
                    cleaned_data.get('notional_1') -
                    cleaned_data.get('notional_2')) > 0.1:
                raise ValidationError(_('Strike and notionals do not match.'),
                                      code='unmatch1')
            if cleaned_data.get('maturity_date') < cleaned_data.get(
                    'trade_date'):
                raise ValidationError(
                    _('Maturity date must be not earlier than trade date.'),
                    code='unmatch1')
        except KeyError:
            raise ValidationError(_('Fields not completed.'), code=KeyError)

    # def __init__(self, *args, **kwargs):
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
    itmCashProbability = forms.FloatField(disabled=True,
                                          label="ITM Cash Probability")


class SwapLegForm(ModelForm):

    class Meta:
        model = SwapLeg
        fields = [
            'ccy', 'effective_date', 'maturity_date', 'tenor', 'notional',
            'pay_rec', 'fixed_rate', 'index', 'spread', 'reset_freq',
            'payment_freq', 'day_rule', 'calendar', 'day_counter'
        ]
        widgets = {
            'effective_date': DateInput(attrs={'type': 'date'}),
            'maturity_date': DateInput(attrs={'type': 'date'}),
        }
        labels = {'pay_rec': 'Pay/Receive', 'calendar': 'Payment calendar'}

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('calendar') is None:
            cleaned_data['calendar'] = cleaned_data.get('ccy').calendar
        effective_date = cleaned_data.get('effective_date')
        maturity_date = cleaned_data.get('maturity_date')
        fixed_rate = cleaned_data.get('fixed_rate')
        spread = cleaned_data.get('spread')
        index = cleaned_data.get('index')
        reset_freq = cleaned_data.get('reset_freq')
        if fixed_rate and reset_freq:
            raise ValidationError(_('Fixed leg has no Reset Freq.'),
                                  code='term_unmatch1')
        elif fixed_rate and spread:
            raise ValidationError(_('Fixed leg has no Spread'),
                                  code='term_unmatch1')
        elif fixed_rate and index:
            raise ValidationError(_('Fixed Rate and Index cannot coexist'),
                                  code='term_unmatch1')
        elif maturity_date <= effective_date:
            raise ValidationError(_('Maturity must later than Effective Date'),
                                  code='term_unmatch1')


class SwapForm(ModelForm):

    class Meta:
        model = Swap
        fields = ['trade_date', 'book', 'counterparty']
        widgets = {
            'trade_date': DateInput(attrs={'type': 'date'}),
        }


# class SwapLegFormSet(BaseModelFormSet):
# def clean(self):
#     cleaned_data = super().clean()
#     forms_to_delete = self.deleted_forms
#     valid_forms = [form for form in self.forms if form.is_valid() and form not in forms_to_delete]

#     for form in valid_forms:
#         exclude = form._get_validation_exclusions()
#         unique_checks, date_checks = form.instance._get_unique_checks(exclude=exclude)
#         all_unique_checks.update(unique_checks)
#         all_date_checks.update(date_checks)


class SwapValuationForm(forms.Form):
    npv = forms.FloatField(label="NPV", disabled=True)
    leg1npv = forms.FloatField(label="Leg 1 NPV", disabled=True)
    leg2npv = forms.FloatField(label="Leg 2 NPV", disabled=True)
    leg1bpv = forms.FloatField(label="Leg 1 BPV", disabled=True)
    leg2bpv = forms.FloatField(label="Leg 2 BPV", disabled=True)


class TradeDetailForm(ModelForm):
    pass
    # class Meta:
    #    model = TradeDetail
    #    fields = ['book']


class AsOfForm(forms.Form):
    as_of = forms.DateField(widget=DateInput(attrs={
        'type': 'date',
        'default': datetime.date.today()
    }))


class TradeIDForm(forms.Form):
    loaded_id = forms.IntegerField(
        label="ID",
        required=False,
        widget=TextInput(attrs={'readonly': 'readonly'}))


class RevalForm(forms.Form):
    reval_date = forms.DateField(widget=DateInput(attrs={'type': 'date'}))
    books = forms.ModelMultipleChoiceField(Book.objects.all(), required=False)
    portfolios = forms.ModelMultipleChoiceField(Portfolio.objects.all(),
                                                required=False)


class UploadFileForm(forms.Form):
    file = forms.FileField(required=False)
    text = forms.CharField(widget=forms.Textarea(attrs={'width': '100%'}),
                           required=False)


class YieldCurveSearchForm(forms.Form):
    name__contains = forms.CharField(max_length=16,
                                     required=False,
                                     label='Name')
    ref_date = forms.DateField(widget=DateInput(attrs={'type': 'date'}),
                               required=False,
                               label='Date')
    ccy = forms.ModelChoiceField(Ccy.objects.all(),
                                 required=False,
                                 label='Ccy')


class TradeSearchForm(forms.Form):
    id = forms.IntegerField(required=False)
    trade_date = forms.DateField(widget=DateInput(attrs={'type': 'date'}),
                                 required=False)
