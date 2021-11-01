from django.shortcuts import render
from django.http import *
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.core.serializers import serialize
from django.template import Context

from .models import *
from .forms import *
import datetime
import json

def index(request):
    mytime = timezone.now()
    myform = CcyPairForm()
    myFXOform = FXOForm(initial={'trade_date': datetime.date.today()})
    as_of_form = AsOfForm(initial={'as_of': datetime.date.today()})
    return render(request, "swpm/index.html", locals())

@csrf_exempt
def trade_list(request):
    trades = FXO.objects.all()
    temp = json.loads(serialize('json', trades))
    return render(request, 
        'swpm/trade-list.html', 
        {"data": json.loads(serialize('json', trades))}
    )


@csrf_exempt
def pricing(request, commit=False):
    if request.method == 'POST':
        as_of = request.POST['as_of']
        as_of_form = AsOfForm(request.POST)
        fxo_form = FXOForm(request.POST, instance=FXO())
        if fxo_form.is_valid():
            fxo_class = fxo_form.save(commit=commit)
            opt = fxo_class.instrument()
            engine = fxo_class.make_pricing_engine(as_of)
            opt.setPricingEngine(engine)
            side = 1.0 if fxo_class.buy_sell=="B" else -1.0
            return render(request, 'swpm/index.html', {
                'myform': CcyPairForm(),
                'myFXOform': fxo_form, 
                'as_of_form': as_of_form, 
                'market_data': {'spot': fxo_class.ccy_pair.get_rate(as_of).rate}, 
                'results': {'npv': side*opt.NPV(), 
                        'delta': side*opt.delta(),
                        'gamma': side*opt.gamma(),
                        'vega': side*opt.vega()
                        }
                    }
                )

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
                trades_ = b.trades.all()
            trades.union(trades_)
        else:
            trades = TradeDetail.objects.all()

        for t in trades:
            inst = t.trade.instrument()
            engine = t.trade.make_pricing_engine(reval_date)
            inst.setPricingEngine(engine)
            side = 1.0 if t.trade.buy_sell=="B" else -1.0
            TradeMarkToMarket.objects.get_or_create(
                as_of = reval_date, 
                trade_d = t, 
                npv = side * t.trade.npv()
                )
        return render(request, 'swpm/reval.html', {'result': "Reval completed"})
    else:
        return render(request, 'swpm/reval.html', {'reval_form': RevalForm()})
