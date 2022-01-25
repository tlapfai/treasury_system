from weakref import ref
from QuantLib.QuantLib import as_fixed_rate_coupon
from django.contrib.auth import REDIRECT_FIELD_NAME, authenticate, login, logout
from django.db.models.query import RawQuerySet
from django.shortcuts import redirect, render
from django.db import IntegrityError
from django.http import *
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.core.serializers import serialize
from django.core.exceptions import ValidationError
from django.template import Context
from django.forms import modelformset_factory
from django.views import View
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.list import ListView

from django_plotly_dash import DjangoDash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.express as px

from django.shortcuts import get_object_or_404
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView

from .models import *
from .forms import *
from .serializers import *
from rest_framework import viewsets
import datetime
import json
import pandas as pd


def str2date(s):
    if len(s) == 10:
        return datetime.datetime.strptime(s, '%Y-%m-%d')
    elif len(str(s)) == 8:
        return datetime.datetime.strptime(str(s), '%Y%m%d')


# def tenor2date(request):
#     if request.is_ajax():
#         effective_date = request.POST.get('effective_date', None)
#         tenor = request.POST.get('tenor', None)
#         calendar = request.POST.get('calendar', None)
#         day_rule = request.POST.get('day_rule', None)
#         try:
#             d = to_qlDate(effective_date)
#             tnr = ql.Period(tenor)
#             cdr = Calendar.objects.get(name=calendar).calendar()
#             maturity_date = cdr.advance(d, tnr, QL_DAY_RULE[day_rule])
#             return JsonResponse({ 'mat': maturity_date.ISO() })
#         except:
#             response = { 'mat': effective_date }
#             return JsonResponse(response)


def index(request):
    mytime = timezone.now()
    myform = CcyPairForm()
    myFXOform = FXOForm(initial={'trade_date': datetime.date.today()})
    #trade_detail_form = TradeDetailForm()
    as_of_form = AsOfForm(initial={'as_of': datetime.date.today()})
    return render(request, "swpm/index.html", locals())


def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
            # return redirect(request.POST.get('next'))
        else:
            return render(request, "swpm/login.html",
                          {"message": "Invalid username and/or password."})
    else:
        return render(request, "swpm/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "swpm/register.html",
                          {"message": "Passwords must match."})

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "swpm/register.html",
                          {"message": "Username already taken."})
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "swpm/register.html")


class FXOCreateView(CreateView):
    # the rendering form must be named as "form"
    form_class = FXOForm
    model = FXO
    template_name = "swpm/fxo_create.html"
    make_models_forms = ("FX Option", FXO, FXOForm, None, None,
                         FXOValuationForm)


class FXOUpdateView(UpdateView):
    # the rendering form must be named as "form"
    form_class = FXOForm
    model = FXO
    template_name = "swpm/fxo_create.html"
    make_models_forms = ("FX Option", FXO, FXOForm, None, None,
                         FXOValuationForm)


class TradeView(CreateView):

    def make_models_forms(self, inst):
        if inst == 'FXO':
            return ("FX Option", FXO, FXOForm, None, None, FXOValuationForm)
        elif inst == 'SWAP':
            return ("Swap", Swap, SwapForm, SwapLeg, SwapLegForm,
                    SwapValuationForm)

    def get(self, request, **kwargs):
        try:
            inst = kwargs['inst'].upper()
        except KeyError:
            return HttpResponseNotFound('<h1>Product type not found</h1>')
        else:
            trade_id = kwargs.get('id')
            trade_type, inst_model, inst_form, leg_model, leg_form, val_form_ = self.make_models_forms(
                inst)
            # common forms --- start
            val_form = val_form_()
            as_of_form = AsOfForm(initial={'as_of': datetime.date.today()})
            # common forms --- end
            if trade_id:
                try:
                    loaded_trade = inst_model.objects.get(id=trade_id)
                except KeyError:
                    return HttpResponseNotFound('<h1>Trade not found</h1>')
                else:
                    trade_id_form = TradeIDForm(
                        initial={'loaded_id': trade_id})
                    trade_form = inst_form(instance=loaded_trade)
                    if leg_model:
                        leg_form_set = modelformset_factory(leg_model,
                                                            leg_form,
                                                            extra=2)
                        trade_form = inst_form(
                            initial={'trade_date': datetime.date.today()})
                        trade_forms = leg_form_set(
                            queryset=leg_model.objects.none(),
                            initial=[{
                                'maturity_date':
                                datetime.date.today() +
                                datetime.timedelta(days=365)
                            }])
            else:
                trade_id_form = TradeIDForm()
                trade_form = inst_form()
                if leg_model:
                    leg_form_set = modelformset_factory(leg_model,
                                                        leg_form,
                                                        extra=2)
                    trade_form = inst_form(
                        initial={'trade_date': datetime.date.today()})
                    trade_forms = leg_form_set(
                        queryset=leg_model.objects.none(),
                        initial=[{
                            'maturity_date':
                            datetime.date.today() +
                            datetime.timedelta(days=365)
                        }])

        return render(request, "swpm/trade.html", locals())


def new_trade(request):
    return render(request, "swpm/new_trade.html")


def trade(request, **kwargs):

    def make_models_forms(inst):
        if inst == 'FXO':
            return ("FX Option", FXO, FXOForm, None, None, FXOValuationForm)
        elif inst == 'SWAP':
            return ("Swap", Swap, SwapForm, SwapLeg, SwapLegForm,
                    SwapValuationForm)

    if request.method == 'GET':
        try:
            inst = kwargs['inst'].upper()
        except KeyError:
            return HttpResponseNotFound('<h1>Product type not found</h1>')
        else:
            trade_id = kwargs.get('id')
            trade_type, inst_model, inst_form, leg_model, leg_form, val_form_ = make_models_forms(
                inst)
            # common forms
            val_form = val_form_()
            as_of_form = AsOfForm(initial={'as_of': datetime.date.today()})
            if trade_id:
                try:
                    loaded_trade = inst_model.objects.get(id=trade_id)
                except KeyError:
                    return HttpResponseNotFound('<h1>Trade not found</h1>')
                else:
                    trade_id_form = TradeIDForm(
                        initial={'loaded_id': trade_id})
                    trade_form = inst_form(instance=loaded_trade)
                    if leg_model:
                        leg_form_set = modelformset_factory(leg_model,
                                                            leg_form,
                                                            extra=2)
                        trade_form = SwapForm(
                            initial={'trade_date': datetime.date.today()})
                        trade_forms = leg_form_set(
                            queryset=leg_model.objects.none(),
                            initial=[{
                                'maturity_date':
                                datetime.date.today() +
                                datetime.timedelta(days=365)
                            }])
            else:
                trade_id_form = TradeIDForm()
                trade_form = inst_form()
                if leg_model:
                    leg_form_set = modelformset_factory(leg_model,
                                                        leg_form,
                                                        extra=2)
                    trade_form = inst_form(
                        initial={'trade_date': datetime.date.today()})
                    trade_forms = leg_form_set(
                        queryset=leg_model.objects.none(),
                        initial=[{
                            'maturity_date':
                            datetime.date.today() +
                            datetime.timedelta(days=365)
                        }])

        return render(request, "swpm/trade.html", locals())
    elif request.method == 'POST':  # from clicked price key
        inst = kwargs['inst'].upper()
        as_of_form = request.POST.get('as_of_form')
        valuation_message = kwargs.get('valuation_message')
        trade_id = kwargs.get('id')
        trade_type, inst_model, inst_form, leg_model, leg_form, val_form_ = make_models_forms(
            inst)
        trade_id_form = TradeIDForm(initial={'loaded_id': trade_id})
        val_form = val_form_()
        if kwargs.get('trade_form'):  # trade_from comes from def pricing()
            trade_form = kwargs['trade_form']
            as_of_form = kwargs['as_of_form']
            val_form = kwargs.get('val_form')
            market_data_form = kwargs.get('market_data_form')
            trade_id_form = kwargs.get('trade_id_form')
            if leg_model:
                trade_forms = kwargs.get('trade_forms')
                leg_tables = kwargs.get('leg_tables')

        if inst == "FXO":
            pass
            # else:
            #     trade_id = kwargs.get('id')
            #     if trade_id:
            #         try:
            #             loaded_trade = inst_model.objects.get(id=trade_id)
            #         except KeyError:
            #             return HttpResponseNotFound('<h1>Trade not found</h1>')
            #         else:
            #             trade_id_form = TradeIDForm(initial={'loaded_id': trade_id})
            #             trade_form = inst_form(instance=loaded_trade)
            #     else:
            #         trade_form = inst_form(initial={'trade_date': datetime.date.today()})
        elif inst == 'SWAP':
            trade_type = "Swap"
            if kwargs.get('trade_form'):
                pass
                # trade_form = kwargs.get('trade_form')
                # as_of_form = kwargs.get('as_of_form')
                # trade_forms= kwargs.get('trade_forms')
                # val_form = kwargs.get('val_form')
                # leg_tables = kwargs.get('leg_tables')
                # trade_id_form = kwargs.get('trade_id_form')
            else:
                val_form = SwapValuationForm()
                trade_id = kwargs.get('id')
                if trade_id:
                    try:
                        loaded_trade = Swap.objects.get(id=trade_id)
                    except KeyError:
                        return HttpResponseNotFound('<h1>Trade not found</h1>')
                    else:
                        trade_id_form = TradeIDForm(initial={'id': trade_id})
                        trade_form = SwapForm(instance=loaded_trade)
                        SwapLegFormSet = modelformset_factory(SwapLeg,
                                                              SwapLegForm,
                                                              extra=0)
                        trade_forms = SwapLegFormSet(
                            queryset=SwapLeg.objects.filter(
                                trade=loaded_trade))  # to be fixed
                else:
                    SwapLegFormSet = modelformset_factory(SwapLeg,
                                                          SwapLegForm,
                                                          extra=2)
                    trade_form = SwapForm(
                        initial={'trade_date': datetime.date.today()})
                    trade_forms = SwapLegFormSet(
                        queryset=SwapLeg.objects.none(),
                        initial=[{
                            'maturity_date':
                            datetime.date.today() +
                            datetime.timedelta(days=365)
                        }])
        else:
            return HttpResponseNotFound('<h1>Page not found</h1>')
        return render(request, "swpm/trade.html", locals())


def trade_list(request):
    if request.method == 'POST':
        form = TradeSearchForm(request.POST)
        form_ = dict([(x[0], x[1]) for x in form.data.dict().items()
                      if len(x[1]) > 0])
        form_.pop('csrfmiddlewaretoken')
        trades1 = list(FXO.objects.filter(**form_).values())
        trades2 = list(Swap.objects.filter(**form_).values())
        search_result = trades1 + trades2
        return render(request, 'swpm/trade-list.html', {
            'form': TradeSearchForm(),
            "search_result": search_result
        })
    else:
        return render(request, 'swpm/trade-list.html',
                      {'form': TradeSearchForm()})


def load_market_data(request, pricing=False):
    if request.method == 'POST':
        as_of = request.POST['as_of']
        trade_id_form = TradeIDForm(request.POST)
        as_of_form = AsOfForm(request.POST)
        ql.Settings.instance().evaluationDate = ql.Date(as_of, '%Y-%m-%d')
        val_form = FXOValuationForm()
        market_data = {}
        if request.POST['trade_type'] == 'FX Option':
            inst = 'fxo'
            trade_form = FXOForm(request.POST, instance=FXO())
            try:
                ccy_pair = CcyPair.objects.get(
                    name=trade_form.data['ccy_pair'])
                fx_spot_quote = FxSpotRateQuote.objects.get(ref_date=as_of,
                                                            ccy_pair=ccy_pair)
            except AttributeError:
                valuation_message = 'Cannot find market data'
                if pricing:
                    return None
                else:
                    return trade(request,
                                 as_of_form=as_of_form,
                                 inst=inst,
                                 trade_form=trade_form,
                                 trade_id_form=trade_id_form,
                                 val_form=val_form,
                                 valuation_message=valuation_message)
            else:
                market_data['fx_spot'] = FxSpotRateQuoteForm(
                    instance=fx_spot_quote)
        if pricing:
            return market_data
        else:
            return trade(request,
                         as_of_form=as_of_form,
                         inst=inst,
                         trade_form=trade_form,
                         trade_id_form=trade_id_form,
                         val_form=val_form,
                         market_data_form=market_data)


def pricing(request, commit=False):
    if request.method == 'POST':
        # 2 forms for single leg product
        # 3 forms for multi leg product
        as_of = request.POST['as_of']
        trade_id_form = TradeIDForm(request.POST)
        as_of_form = AsOfForm(request.POST)  # for render back to page
        ql.Settings.instance().evaluationDate = to_qlDate(as_of)
        valuation_message = None
        if request.POST['trade_type'] == 'FX Option':
            fxo_form = FXOForm(request.POST, instance=FXO())
            market_data_form = load_market_data(request, pricing=True)
            if fxo_form.is_valid():
                tr = fxo_form.save(commit=False)
                inst = tr.instrument()
                engine = tr.make_pricing_engine(as_of)
                inst.setPricingEngine(engine)
                side = 1.0 if tr.buy_sell == "B" else -1.0
                # will get full market data
                spot = tr.ccy_pair.rates.get(ref_date=as_of).rate

                if commit and request.POST.get('book') and request.POST.get(
                        'counterparty'):
                    # need to check market data
                    tr.input_user = request.user
                    tr.detail = TradeDetail.objects.create()
                    tr.save()
                    valuation_message = f"Trade is done, ID is {tr.id}."
                    trade_id_form = TradeIDForm(
                        initial={'loaded_id': str(tr.id)})

                result = {
                    'npv':
                    inst.NPV(),
                    'delta':
                    inst.delta(),
                    'gamma':
                    inst.gamma() * 0.01 / spot,
                    'vega':
                    inst.vega() * 0.01,
                    'theta':
                    inst.thetaPerDay(),
                    'rho':
                    inst.rho() * 0.01,
                    'dividendRho':
                    inst.dividendRho() * 0.01,
                    'itmCashProbability':
                    inst.itmCashProbability() / side / tr.notional_1,
                }
                result = dict([(x, round(y * side * tr.notional_1, 2))
                               for x, y in result.items()])
                valuation_form = FXOValuationForm(initial=result)
            else:
                valuation_form = FXOValuationForm()

            return trade(request,
                         inst='fxo',
                         trade_form=fxo_form,
                         trade_id_form=trade_id_form,
                         as_of_form=as_of_form,
                         val_form=valuation_form,
                         market_data_form=market_data_form,
                         valuation_message=valuation_message)
        elif request.POST.get('trade_type') == 'Swap':
            SwapLegFormSet = modelformset_factory(SwapLeg,
                                                  SwapLegForm,
                                                  extra=2)
            swap_leg_form_set = SwapLegFormSet(request.POST)
            swap_form = SwapForm(request.POST, instance=Swap())
            if swap_form.is_valid() and swap_leg_form_set.is_valid():
                tr = swap_form.save(commit=False)
                legs = swap_leg_form_set.save(commit=False)
                leg_tables = []
                leg_npv = []
                for leg in legs:  # here leg is SwapLeg
                    leg_cf = []
                    leg.trade = tr
                    sch = leg.get_schedule()
                    ql_leg = leg.leg(as_of)
                    dc = QL_DAY_COUNTER[leg.day_counter]
                    yts = leg.discounting_curve(as_of)
                    for k in range(len(leg.leg(as_of))):
                        d2, d1 = sch[k + 1], sch[k]
                        leg_cf.append(
                            (d1.ISO(), d2.ISO(), dc.dayCount(d1, d2),
                             dc.yearFraction(d1, d2),
                             ql_leg[k].date().ISO(), ql_leg[k].amount(),
                             yts.discount(ql_leg[k].date()),
                             yts.discount(ql_leg[k].date()) *
                             ql_leg[k].amount(), leg.ccy.code))
                    leg_tables.append(leg_cf)
                    leg_npv.append(
                        ql.CashFlows.npv(ql_leg,
                                         ql.YieldTermStructureHandle(yts),
                                         False))
                if commit and request.POST.get('book') and request.POST.get(
                        'counterparty'):
                    tr.input_user = request.user
                    tr.detail = TradeDetail.objects.create()
                    tr.maturity_date = max([leg.maturity_date for leg in legs])
                    tr.save()
                    for leg in legs:
                        leg.save()
                    valuation_message = f"Trade is done, ID is {tr.id}."
                    trade_id_form = TradeIDForm(initial={'loaded_id': tr.id})
                    inst = tr.instrument(as_of)
                    engine = tr.make_pricing_engine(as_of)
                    inst.setPricingEngine(engine)
                else:
                    leg_inst = [x.leg(as_of=as_of) for x in legs]
                    is_pay = [leg.pay_rec > 0 for leg in legs]
                    inst = ql.Swap(leg_inst, is_pay)
                    #yts1 = legs[0].ccy.rf_curve.get(ref_date=as_of).term_structure()
                    yts1 = IRTermStructure.objects.filter(
                        ref_date=as_of, name=legs[0].ccy.risk_free_curve
                    ).first().term_structure()
                    inst.setPricingEngine(
                        ql.DiscountingSwapEngine(
                            ql.YieldTermStructureHandle(yts1)))
                    valuation_message = None
                result = {
                    'npv': inst.NPV(),
                    'leg1npv': leg_npv[0],
                    'leg2npv': leg_npv[1],
                    'leg1bpv': inst.legBPS(0),
                    'leg2bpv': inst.legBPS(1)
                }
                result = dict([(x, round(y, 2)) for x, y in result.items()])
                valuation_form = SwapValuationForm(initial=result)
            else:  # invalid swap_form or invalid swap_leg_form_set, return empty valuation_form
                return trade(request,
                             inst='swap',
                             trade_form=swap_form,
                             as_of_form=as_of_form,
                             trade_forms=swap_leg_form_set,
                             val_form=SwapValuationForm())
            return trade(request,
                         inst='swap',
                         trade_form=swap_form,
                         as_of_form=as_of_form,
                         trade_forms=swap_leg_form_set,
                         trade_id_form=trade_id_form,
                         val_form=valuation_form,
                         valuation_message=valuation_message,
                         leg_tables=leg_tables)


def fx_volatility_table(request):  # for API
    if request.method == 'POST':
        try:
            as_of = request.POST['as_of']
            ccy_pair = request.POST['ccy_pair']
            fxv = FXVolatility.objects.filter(ref_date=as_of,
                                              ccy_pair=ccy_pair).first()
            #ql.Settings.instance().evaluationDate = to_qlDate(as_of)
            market_data_message = None
            return JsonResponse(
                {
                    'result':
                    fxv.surface_dataframe().to_html(
                        classes='table fx-vol table-striped',
                        na_rep='',
                        border='1px',
                        col_space='5em'),
                    'message':
                    market_data_message
                }, )
        except RuntimeError as error:
            return JsonResponse({'errors': [error.args]}, status=500)


class MktDataSet():
    ccy_pairs = dict()
    fx_quotes = dict()
    ytss = dict()
    spots = dict()
    vols = dict()

    def __init__(self, ref_date) -> None:
        self.ref_date = ref_date

    def add_ccy_pair(self, ccy_pair, ref_date):
        """ return 0 if ref_date is not match, 1 if anything added, 2 if nothing added """
        if ref_date == self.ref_date:
            result = 2
            ccy1, ccy2 = ccy_pair.split('/')
            if self.ytss.get(ccy1) == None:
                self.ytss[ccy1] = Ccy.objects.get(code=ccy1).fx_curve.get(
                    ref_date=ref_date).term_structure()
                result = 1

            if self.ytss.get(ccy2) == None:
                self.ytss[ccy2] = Ccy.objects.get(code=ccy2).fx_curve.get(
                    ref_date=ref_date).term_structure()
                result = 1

            if self.ccy_pairs.get(ccy_pair) == None:
                cp = CcyPair.objects.get(name=ccy_pair)
                self.ccy_pairs[ccy_pair] = cp
                fxq = cp.rates.get(ref_date=ref_date)
                fxq.set_yts(self.ytss[ccy2], self.ytss[ccy1])
                self.spots[ccy_pair] = fxq  # fxq is FxSpotRateQuote
                # fxv
                fxv = FXVolatility.objects.get(ccy_pair=ccy_pair,
                                               ref_date=ref_date)
                fxv.set_yts(self.ytss[ccy2], self.ytss[ccy1])
                fxv.set_spot(fxq)  # fxq is FXSpotRateQuote
                self.vols[ccy_pair] = fxv  # fxv is a Django object
                result = 1
            return result
        else:
            return 0

    def add_ccy_pair_with_trades(self, trades):
        if isinstance(trades, list):
            tradelist = trades
        else:
            tradelist = [trades]
        for t in tradelist:
            self.add_ccy_pair(t.ccy_pair, self.ref_date)

    def fxo_mkt_data(self, ccy_pair):
        """ instrument should call corresponding _mkt_data """
        if self.ccy_pairs.get(ccy_pair, None):
            ccy1, ccy2 = ccy_pair.split('/')
            spot = self.spots.get(ccy_pair)
            qts = self.yts.get(ccy1)  # is yts, not handle
            rts = self.yts.get(ccy2)
            vol = self.vols[ccy_pair]
            # fxv is a Django object, invoke vol.hendle(strike)
            return {
                'ccy_pair': ccy_pair,
                'spot': spot,
                'qts': qts,
                'rts': rts,
                'vol': vol
            }
        else:
            return None


def fxo_price2(request):  # for API
    if request.method == 'POST':
        try:
            as_of = request.POST['as_of']
            ql.Settings.instance().evaluationDate = to_qlDate(as_of)
            valuation_message = None
            fxo_form = FXOForm(request.POST, instance=FXO())
            if fxo_form.is_valid():
                tr = fxo_form.save(commit=False)
                mktset = MktDataSet(as_of)
                mktset.add_ccy_pair_with_trades(tr)
                inst = tr.instrument()
                eng = tr.make_pricing_engine()
                inst.setPricingEngine(eng['engine'])
                result = {'npv': inst.NPV(), 'delta': inst.delta()}
            return JsonResponse({
                'result': result,
                'message': valuation_message
            })
        except RuntimeError as error:
            return JsonResponse({'errors': [error.args]}, status=500)


def fxo_price(request):  # for API
    if request.method == 'POST':
        try:
            as_of = request.POST['as_of']
            ql.Settings.instance().evaluationDate = to_qlDate(as_of)
            valuation_message = None
            fxo_form = FXOForm(request.POST, instance=FXO())
            if fxo_form.is_valid():
                tr = fxo_form.save(commit=False)
                inst = tr.instrument()
                engine, process = tr.make_pricing_engine(
                    as_of, strike=tr.strike_price)
                inst.setPricingEngine(engine)
                side = 1.0 if tr.buy_sell == "B" else -1.0
                spot_0 = tr.ccy_pair.rates.get(ref_date=as_of).today_rate()
                spot = tr.ccy_pair.rates.get(ref_date=as_of).rate
                vol = process.blackVolatility().blackVol(
                    to_qlDate(tr.maturity_date), float(tr.strike_price), True)
            else:
                return JsonResponse({'errors': fxo_form.errors}, status=500)
                # try try fxo_form.errors.as_json()
            result = {
                'npv': inst.NPV(),
                'delta': inst.delta(),
                'gamma': inst.gamma() * 0.01 / spot_0,
                'vega': inst.vega() * 0.01,
                'theta': inst.thetaPerDay(),
                'rho': inst.rho() * 0.01,
                'dividendRho': inst.dividendRho() * 0.01,
                'strikeSensitivity': inst.strikeSensitivity(),
                'itmCashProbability': inst.itmCashProbability(),
                # 'impliedVolatility': inst.impliedVolatility(),
            }
            result = dict([
                (x, round(y * side *
                          tr.notional_1, 2)) if x != 'itmCashProbability' else
                (x, round(y, 6)) for x, y in result.items()
            ])
            parameters = {
                #'spot_0': spot_0,
                'spot': spot,
                'vol': vol * 100,
            }
            return JsonResponse(
                {
                    'result': result,
                    'parameters': parameters,
                    'valuation_message': valuation_message
                }, )
        except RuntimeError as error:
            return JsonResponse({'errors': [error.args]}, status=500)


@csrf_exempt
def load_fxo_mkt(request):
    # request.POST is only for form-encoded data.
    # If you are posting JSON, then you should use request.body instead.
    if request.method == "POST":
        data = json.loads(request.body.decode('utf-8'))
        ref_date = data.get('as_of')
        cp = data.get('ccy_pair')
        maturity = data.get('maturity_date')
        strike_price = float(data.get('strike_price'))
        ccy_pair = CcyPair.objects.get(name=cp)
        rts, qts = ccy_pair.fx_curves(ref_date)
        fx_quote = ccy_pair.rates.get(ref_date=ref_date)  # FxSpotRateQuote
        fx_quote.set_yts(rts, qts)
        spot = fx_quote.today_rate()
        fwd = fx_quote.forward_rate(maturity)
        fx_vol = FXVolatility.objects.get(ccy_pair=ccy_pair, ref_date=ref_date)
        fx_vol.set_yts(rts, qts)
        fx_vol.set_spot(spot)
        fx_vol_h = fx_vol.handle(strike_price)
        vol = fx_vol_h.blackVol(to_qlDate(maturity), strike_price)
        return JsonResponse({'spot': spot, 'fwd': fwd, 'vol': vol})


@csrf_exempt
def save_ccypair(request):
    if request.method == 'POST':
        ccypair_obj = CcyPair()
        ccypair_form = CcyPairForm(request.POST, instance=ccypair_obj)
        if ccypair_form.is_valid():
            ccypair_form.save()
            return render(request, 'swpm/index.html', {
                "message": "saved successfully.",
                'myform': ccypair_form
            })


@csrf_exempt
def reval(request):
    if request.method == 'POST':
        reval_date = request.POST['reval_date']
        books = request.POST['books']
        if books:
            trades = TradeDetail.objects.none()
            for book in books:
                b = Book.objects.get(pk=book)
                trades = trades.union(b.trades.all())
        else:
            trades = TradeDetail.objects.all()

        for t in trades:
            inst = t.trade.first().instrument()
            engine = t.trade.first().make_pricing_engine(reval_date)
            inst.setPricingEngine(engine)
            side = 1.0 if t.trade.first().buy_sell == "B" else -1.0
            mtm, _ = TradeMarkToMarket.objects.get_or_create(
                as_of=reval_date,
                trade_d=t,
                defaults={
                    'npv': side * inst.NPV() * t.trade.first().notional_1
                })
        return render(
            request, 'swpm/reval.html', {
                'reval_form':
                RevalForm(request.POST),
                'result':
                "Reval completed: \n" +
                str(TradeMarkToMarket.objects.filter(as_of=reval_date))
            })
    else:
        return render(request, 'swpm/reval.html', {
            'reval_form':
            RevalForm(initial={'reval_date': datetime.date.today()})
        })


def handle_uploaded_file(f=None, text=None):
    # assume all dates are same
    msg = []
    if f:
        df = pd.read_csv(f)
    elif text:
        lines = text.split('\r\n')
        temp = [line.split(',') for line in lines if len(line) > 0]
        df = pd.DataFrame(temp[1:], columns=temp[0])

    if {
            'Instrument', 'Ccy', 'Date', 'Market Rate', 'Curve', 'Term',
            'Day Counter'
    }.issubset(set(df.columns)):
        for idx, row in df.iterrows():
            #arg_ = {'name': row['Curve'], 'ref_date': str2date(row['Date']), 'ccy': Ccy.objects.get(code=row['Ccy'])}
            arg_upd = {}
            try:
                ccy_ = Ccy.objects.get(code=row['Ccy'])
                if ccy_.foreign_exchange_curve == row['Curve']:
                    arg_upd['as_fx_curve'] = ccy_
                if ccy_.risk_free_curve == row['Curve']:
                    arg_upd['as_rf_curve'] = ccy_
                yts, created_ = IRTermStructure.objects.update_or_create(
                    name=row['Curve'],
                    ref_date=str2date(row['Date']),
                    ccy=ccy_,
                    defaults=arg_upd)
                if created_:
                    msg.append(f'{yts.name} ({yts.ref_date}) created.')
                if row['Term'][:2] == 'ED':
                    row['Term'] = row['Term'][:4]
                    row['Market Rate'] = 100.0 * float(row['Market Rate'])
                r, temp_ = RateQuote.objects.update_or_create(
                    name=row['Ccy'] + '' + row['Curve'] + ' ' + row['Term'],
                    ref_date=str2date(row['Date']),
                    defaults={
                        'tenor': row['Term'],
                        'instrument': row['Instrument'],
                        'ccy': ccy_,
                        'day_counter': row['Day Counter'],
                        'rate': float(row['Market Rate']) * 0.01
                    })
                yts.rates.add(r)
            except KeyError as e:
                msg.append(str(e))
            else:
                msg.append(f'{str(r)} is created.')
    elif {
            'Instrument', 'Ccy', 'Date', 'Market Rate', 'Curve', 'Term',
            'Ref Curve', 'Ref Ccy', 'Ccy Pair'
    }.issubset(set(df.columns)):
        for idx, row in df.iterrows():
            arg_upd = {}
            try:
                ccy_ = Ccy.objects.get(code=row['Ccy'])
                if ccy_.foreign_exchange_curve == row['Curve']:
                    arg_upd['as_fx_curve'] = ccy_
                arg_upd['ref_curve'] = row['Ref Curve']
                arg_upd['ref_ccy'] = Ccy.objects.get(code=row['Ref Ccy'])
                yts, created_ = IRTermStructure.objects.update_or_create(
                    name=row['Curve'],
                    ref_date=str2date(row['Date']),
                    ccy=ccy_,
                    defaults=arg_upd)
                if created_:
                    msg.append(
                        f'{yts.ccy} {yts.name} {yts.ref_date} is created.')
                r, temp_ = RateQuote.objects.update_or_create(
                    name=row['Ccy'] + ' ' + row['Curve'] + ' ' + row['Term'],
                    ref_date=str2date(row['Date']),
                    defaults={
                        'tenor': row['Term'],
                        'instrument': row['Instrument'],
                        'ccy': ccy_,
                        'rate': float(row['Market Rate']),
                        'ccy_pair': CcyPair.objects.get(name=row['Ccy Pair'])
                    })
                yts.rates.add(r)
            except KeyError as e:
                msg.append(str(e))
            else:
                msg.append(f'{str(r.name)} is created.')
    elif {'Date', 'Ccy Pair', 'Delta', 'Tenor', 'Volatility',
          'Delta Type'}.issubset(set(df.columns)):
        for idx, row in df.iterrows():
            arg_upd = {}
            try:
                ccy_pair_ = CcyPair.objects.get(name=row['Ccy Pair'])
                fxv, created_ = FXVolatility.objects.update_or_create(
                    ref_date=str2date(row['Date']), ccy_pair=ccy_pair_)
                if created_:
                    msg.append(
                        f'{fxv.ccy_pair.name} ({fxv.ref_date}) FXVolatility created.'
                    )
                v, temp_ = FXVolatilityQuote.objects.update_or_create(
                    ref_date=str2date(row['Date']),
                    tenor=row['Tenor'],
                    delta=float(row['Delta']),
                    defaults={
                        'delta_type': row['Delta Type'],
                        'vol': float(row['Volatility']),
                        'surface': fxv
                    })
            except KeyError as e:
                msg.append(str(e))
            else:
                msg.append(str(v))
    else:
        msg = ['Header is wrong']
    return msg


@csrf_exempt
def market_data_import(request):
    if request.method == 'POST':
        if request.FILES.get('file'):
            message = handle_uploaded_file(request.FILES['file'])
        elif request.POST.get('text'):
            message = handle_uploaded_file(text=request.POST['text'])
        return render(request, 'swpm/market_data_import.html', {
            'upload_file_form': UploadFileForm(),
            'message': message
        })
    else:
        form = UploadFileForm()
    return render(request, 'swpm/market_data_import.html',
                  {'upload_file_form': form})


def fx_volatility(request, ccy_pair=None, ref_date=None):
    if request.method == 'POST':
        pass
    elif request.method == 'GET':
        if ccy_pair and ref_date:
            # build a dataframe
            pass


def yield_curve(request, curve=None, ref_date=None, **kwargs):
    if request.method == 'POST':
        form = YieldCurveSearchForm(request.POST)
        form_ = dict([(x[0], x[1]) for x in form.data.dict().items()
                      if len(x[1]) > 0 and x[0] != 'csrfmiddlewaretoken'])
        search_result = list(
            IRTermStructure.objects.filter(
                **form_).order_by('-ref_date').values())
        return render(request, 'swpm/yield_curve.html', {
            'form': form,
            'search_result': search_result
        })
    elif request.method == 'GET':
        ccy = kwargs.get('ccy')
        if curve and ref_date:
            ql.Settings.instance().evaluationDate = to_qlDate(ref_date)
            yts_model = IRTermStructure.objects.get(
                ccy=ccy, name=curve, ref_date=str2date(ref_date))
            yts = yts_model.term_structure()
            dates = yts.dates()
            rates = []
            for i, r in enumerate(yts_model.rates.all()):
                if r.instrument in ['FUT', 'FXSW']:
                    adj_rate = r.rate
                else:
                    adj_rate = r.rate * 100.
                rates.append({
                    'id':
                    r.id,
                    'tenor':
                    r.tenor,
                    'rate':
                    adj_rate,
                    'date':
                    dates[i + 1].ISO(),
                    'zero_rate':
                    yts.zeroRate(dates[i + 1], ql.ActualActual(),
                                 ql.Continuous).rate() * 100
                })
                rates.sort(key=lambda r: r['date'])
            # need to fix: order wrong if the rates are not in chronological order, becoz dates comes from ql
            #plt_points = min(len(rates) - 1, 14)
            # https://plotly.com/python/px-arguments/
            dataPx = px.line(
                x=[rr['date'] for rr in rates],
                y=[rr['zero_rate'] for rr in rates],
                #range_x=[dates[0].ISO(), rates[plt_points]['date']],
                #range_y=[0, rates[plt_points]['zero_rate']*1.1],
                markers=True,
                labels={
                    'x': 'Date',
                    'y': 'Zero Rate'
                })
            # dataPx.update_layout(plot_bgcolor='#111111', paper_bgcolor='#111111', font_color='skyblue')
            app = DjangoDash('yts_plot')
            app.layout = html.Div([dcc.Graph(id="yts_plot_id", figure=dataPx)],
                                  className="yts_plot_class",
                                  style={"width": "100%"})
            data = {
                'name': ccy + ' ' + yts_model.name,
                'ref_date': str2date(ref_date),
                'rates': rates
            }
            return render(request, 'swpm/yield_curve.html', {
                'form': YieldCurveSearchForm(),
                'data': data
            })
        else:
            return render(request, 'swpm/yield_curve.html',
                          {'form': YieldCurveSearchForm()})
    else:
        return JsonResponse({"error": "GET or PUT request required."},
                            status=400)


class CalendarViewSet(viewsets.ModelViewSet):
    queryset = Calendar.objects.all()
    serializer_class = CalendarSerializer


class FXOViewSet(viewsets.ModelViewSet):
    queryset = FXO.objects.all()
    serializer_class = FXOSerializer


class CalendarDetail(APIView):
    renderer_classes = [TemplateHTMLRenderer]
    template_name = 'swpm/calendar.html'

    def get(self, request, name):
        calendar = get_object_or_404(Calendar, name=name)
        serializer = CalendarSerializer(calendar)
        return Response(locals())

    def post(self, request, name):
        calendar = get_object_or_404(Calendar, name=name)
        serializer = CalendarSerializer(calendar, data=request.data)
        if not serializer.is_valid():
            return Response({'serializer': serializer, 'profile': calendar})
        serializer.save()
        return redirect('profile-list')


class CalendarList(ListAPIView):  # only a API view
    serializer_class = CalendarSerializer
    queryset = Calendar.objects.all()


class FXODetail(APIView):
    renderer_classes = [TemplateHTMLRenderer]
    template_name = 'swpm/fxo.html'

    def get(self, request, id):
        trade = get_object_or_404(FXO, id=id)
        serializer = FXOSerializer(trade)
        return Response(locals())


def fxo_detail(request):
    if request.method == 'GET':
        return JsonResponse({'form': FXOForm().as_table()})


class FXODetailView(DetailView):
    model = FXO
    template_name = 'swpm/trade.html'
