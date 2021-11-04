from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.db import IntegrityError
from django.http import *
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.core.serializers import serialize
from django.template import Context
from django.forms import modelformset_factory

from .models import *
from .forms import *
import datetime
import json

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
        else:
            return render(request, "swpm/login.html", {
                "message": "Invalid username and/or password."
            })
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
            return render(request, "swpm/register.html", {"message": "Passwords must match."})

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "swpm/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "swpm/register.html")


def trade(request, **kwargs):
    as_of_form = AsOfForm(initial={'as_of': datetime.date.today()})
    if kwargs['inst'] == "fxo":
        trade_type = "FX Option"
        val_form = FXOValuationForm()
        if kwargs.get('trade_form'):
            trade_form = kwargs['trade_form']
            as_of_form = kwargs['as_of_form']
            val_form = kwargs.get('val_form')
        else:
            trade_form = FXOForm(initial={'trade_date': datetime.date.today()})
    elif kwargs['inst'] == 'swap':
        trade_type = "Swap"
        SwapLegFormSet = modelformset_factory(SwapLeg, SwapLegForm, extra=2)
        trade_forms = SwapLegFormSet(initial=[{'maturity_date': datetime.date.today()+datetime.timedelta(days=365)}])
        swap_form = SwapForm(initial={'trade_date': datetime.date.today()})

    return render(request, "swpm/trade.html", locals())


@csrf_exempt
def trade_list(request):
    trades = FXO.objects.all()
    #temp = json.loads(serialize('json', trades))
    #return render(request, 
    #    'swpm/trade-list.html', 
    #    {"data": json.loads(serialize('json', trades))}
    #)
    return render(request, 
        'swpm/trade-list.html', 
        {"data": FXO.objects.values()}
    )


@csrf_exempt
def pricing(request, commit=False):
    if request.method == 'POST':
        as_of = request.POST['as_of']
        as_of_form = AsOfForm(request.POST) #for render back to page

        if request.POST['trade_type'] == 'FX Option':
            fxo_form = FXOForm(request.POST, instance=FXO())
            if fxo_form.is_valid():
                fxo = fxo_form.save(commit=False)
                if commit and request.POST.get('book') and request.POST.get('counterparty'):
                    fxo.input_user = request.user
                    fxo.detail = TradeDetail.objects.create()
                    fxo.save()
                    valuation_message = f"Trade is done, ID is {fxo.id}."
                else:
                    valuation_message = None

                inst = fxo.instrument()
                engine = fxo.make_pricing_engine(as_of)
                inst.setPricingEngine(engine)
                side = 1.0 if fxo.buy_sell=="B" else -1.0
                spot = fxo.ccy_pair.rates.get(as_of)
    
                result = {'npv': inst.NPV(), 
                            'delta': inst.delta(),
                            'gamma': inst.gamma()*0.01/spot,
                            'vega': inst.vega()*0.01, 
                            'theta': inst.thetaPerDay(), 
                            'rho': inst.rho()*0.01,
                            'dividendRho': inst.dividendRho()*0.01,
                            'itmCashProbability': inst.itmCashProbability(),
                            }
                result = dict([(x, round(y*side*fxo.notional_1,2)) for x, y in result.items()])
                valuation_form = FXOValuationForm(initial=result)
            return trade(request, inst='fxo', trade_form=fxo_form, as_of_form=as_of_form, val_form=valuation_form)
        elif request.POST.get('trade_type') == 'Swap':
            SwapLegFormSet = modelformset_factory(SwapLeg, SwapLegForm, extra=2)
            swap_leg_form_set = SwapLegFormSet(request.POST)
            swap_form = SwapForm(request.POST, instance=Swap())
            if swap_form.is_valid() and swap_leg_form_set.is_valid():
                tr = swap_form.save(commit=False)
                if commit and request.POST.get('book') and request.POST.get('counterparty'):
                    tr.input_user = request.user
                    tr.detail = TradeDetail.objects.create()
                    tr.save()
                    legs = swap_leg_form_set.save(commit=False)
                    for leg in legs:
                        leg.trade = tr
                        leg.save(commit=False)
                        # get pricing engine and calculate npv etc...
                    valuation_message = f"Trade is done, ID is {tr.id}."
                    return trade(request, inst='swap', trade_forms=swap_leg_form_set)
                else:
                    return HttpResponseNotAllowed()
            else:
                return HttpResponseNotAllowed()

@csrf_exempt                    
def save_ccypair(request):
    if request.method == 'POST':
        ccypair_obj = CcyPair()
        ccypair_form = CcyPairForm(request.POST, instance=ccypair_obj)
        if ccypair_form.is_valid():
            ccypair_form.save()
            return render(request, 'swpm/index.html', {"message": "saved successfully.", 'myform': ccypair_form})
    
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
            side = 1.0 if t.trade.first().buy_sell=="B" else -1.0
            mtm, _ = TradeMarkToMarket.objects.get_or_create(as_of = reval_date, trade_d = t, defaults={'npv': side * inst.NPV() * t.trade.first().notional_1})
        return render(request, 'swpm/reval.html', {'reval_form': RevalForm(request.POST), 
                                                    'result': "Reval completed: \n" + str(TradeMarkToMarket.objects.filter(as_of=reval_date))
                                                    }
                    )
    else:
        return render(request, 'swpm/reval.html', {'reval_form': RevalForm(initial={'reval_date': datetime.date.today()})})
