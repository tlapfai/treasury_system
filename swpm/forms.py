from bdb import effective
from email.policy import default
from random import choices
from select import select
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

CHOICE_TRADE_TYPE = [('FXO', 'FXO'), ('SWAP', 'SWAP')]
date_attrs = {'type': 'date', 'class': "form-control-sm"}
inline_date_attrs = {
    'type': 'date',
    'class': 'form-control-sm',
    'style': 'display: inline'
}
number_attrs = {'class': "form-control-sm", 'style': 'text-align: right'}
select_atts = {'class': "form-control-sm"}


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


class CashFlowForm(ModelForm):
    prefix = 'cashflow'

    class Meta:
        model = CashFlow
        fields = ['ccy', 'amount', 'value_date']
        widgets = {
            'value_date': DateInput(attrs=date_attrs),
            'amount': TextInput(attrs=number_attrs),
        }


class FXOUpperBarrierDetailForm(ModelForm):
    prefix = 'up-bar'
    effect = forms.BooleanField(required=False, label="Upper Barrier")

    class Meta:
        model = FXOUpperBarrierDetail
        fields = ['effect', 'barrier', 'knock', 'rebate', 'rebate_ccy']
        widgets = {
            'barrier': TextInput(attrs=number_attrs),
            'barrier_start': DateInput(attrs=date_attrs),
            'barrier_end': DateInput(attrs=date_attrs),
            'rebate': TextInput(attrs=number_attrs),
        }

    def clean(self):
        try:
            cd = super().clean()
            if cd.get('rebate') and (bool(cd.get('rebate_ccy')) == False):
                raise ValidationError(_('Missing rebate ccy.'),
                                      code='unmatch1')
        except KeyError:
            raise ValidationError(_('Fields not completed.'), code=KeyError)


class FXOLowerBarrierDetailForm(ModelForm):
    prefix = 'low-bar'
    effect = forms.BooleanField(required=False, label="Lower Barrier")

    class Meta:
        model = FXOLowerBarrierDetail
        fields = ['effect', 'barrier', 'knock', 'rebate', 'rebate_ccy']
        widgets = {
            'barrier': TextInput(attrs=number_attrs),
            'barrier_start': DateInput(attrs=date_attrs),
            'barrier_end': DateInput(attrs=date_attrs),
            'rebate': TextInput(attrs=number_attrs),
        }

    def clean(self):
        try:
            cd = super().clean()
            if cd.get('rebate') and (bool(cd.get('rebate_ccy')) == False):
                raise ValidationError(_('Missing rebate ccy.'),
                                      code='unmatch1')
        except KeyError:
            raise ValidationError(_('Fields not completed.'), code=KeyError)


class FXOForm(ModelForm):
    #tenor = forms.CharField(required=False, help_text='Use D, W, M and Y')
    tenor = forms.CharField(required=False, validators=[validate_period])

    class Meta:
        model = FXO
        fields = [
            'buy_sell', 'trade_date', 'tenor', 'maturity_date', 'ccy_pair',
            'payoff_type', 'exercise_type', 'cp', 'strike_price', 'notional_1',
            'notional_2', 'exercise_start', 'exercise_end', 'barrier', 'book',
            'counterparty'
        ]
        """ list all the necessary fields and put them in order
        https://stackoverflow.com/questions/43067707/why-doesnt-my-django-template-render-a-modelforms-id-or-pk-field
        The id field automatically has editable=False, which means by default it doesn't show up in any model forms."""
        widgets = {
            'buy_sell': forms.Select(attrs=select_atts),
            'ccy_pair': forms.Select(attrs=select_atts),
            'trade_date': DateInput(attrs=date_attrs),
            'maturity_date': DateInput(attrs=date_attrs),
            'strike_price': TextInput(attrs=number_attrs),
            'notional_1': TextInput(attrs=number_attrs),
            'notional_2': TextInput(attrs=number_attrs),
            'exercise_start': DateInput(attrs=date_attrs),
            'exercise_end': DateInput(attrs=date_attrs),
        }
        labels = {
            'buy_sell': 'Buy/Sell',
            'cp': 'Call/Put',
        }
        help_texts = {
            'ccy_pair': 'Choose a pair',
            'tenor': 'Use D, W, M and Y',
            'book': 'Book'
        }

    def clean(self):
        try:
            cd = super().clean()
            if cd.get('maturity_date') < cd.get('trade_date'):
                raise ValidationError(_(
                    'Maturity date must be not earlier than trade date. (form clean check)'
                ),
                                      code='unmatch1')
            exercise_type = cd.get('exercise_type')
            if exercise_type == "EUR":
                if abs(
                        cd.get('strike_price') * cd.get('notional_1') -
                        cd.get('notional_2')) > 0.1:
                    raise ValidationError(
                        _('Strike and notionals do not match.'),
                        code='unmatch1')
                cd.get('exercise_start') == None
                cd.get('exercise_end') == None
            elif exercise_type == "AME":
                if cd.get('exercise_start') == None:
                    cd['exercise_start'] = cd['trade_date']
                if cd.get('exercise_end') == None:
                    cd['exercise_end'] = cd['maturity_date']
                if cd['exercise_end'] < cd['exercise_start']:
                    raise ValidationError(_(
                        'Exercise End must be not earlier than Exercise Start. (form clean check)'
                    ),
                                          code='unmatch1')
            barrier = cd.get('barrier')
            if barrier:
                pass
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
        fields = '__all__'
        widgets = {
            #'effective_date': DateInput(attrs={'type': 'date'}),
            #'maturity_date': DateInput(attrs={'type': 'date'}),
        }
        #labels = {'pay_rec': 'Pay/Receive', 'calendar': 'Payment calendar'}

    # def clean(self):
    #     cleaned_data = super().clean()
    #     if cleaned_data.get('calendar') is None:
    #         cleaned_data['calendar'] = cleaned_data.get('ccy').calendar
    #     effective_date = cleaned_data.get('effective_date')
    #     maturity_date = cleaned_data.get('maturity_date')
    #     fixed_rate = cleaned_data.get('fixed_rate')
    #     spread = cleaned_data.get('spread')
    #     index = cleaned_data.get('index')
    #     reset_freq = cleaned_data.get('reset_freq')
    #     if fixed_rate and reset_freq:
    #         raise ValidationError(_('Fixed leg has no Reset Freq.'),
    #                               code='term_unmatch1')
    #     elif fixed_rate and spread:
    #         raise ValidationError(_('Fixed leg has no Spread'),
    #                               code='term_unmatch1')
    #     elif fixed_rate and index:
    #         raise ValidationError(_('Fixed Rate and Index cannot coexist'),
    #                               code='term_unmatch1')
    #     elif maturity_date <= effective_date:
    #         raise ValidationError(_('Maturity must later than Effective Date'),
    #                               code='term_unmatch1')


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
    trade_date__gte = forms.DateField(label="Traded from",
                                      widget=DateInput(inline_date_attrs),
                                      required=False)
    trade_date__lte = forms.DateField(label="Traded before",
                                      widget=DateInput(inline_date_attrs),
                                      required=False)
    book = forms.CharField(max_length=16, required=False)
    #trade_type = forms.MultipleChoiceField(choices=CHOICE_TRADE_TYPE,required=False)


class FXVolatilitySettingForm(forms.Form):
    atm_type = forms.ChoiceField(label="ATM Type",
                                 choices=CHOICE_ATM_TYPE.choices)
    delta_type = forms.ChoiceField(choices=CHOICE_DELTA_TYPE.choices)


class IRTermStructureSettingForm(forms.Form):
    pass
