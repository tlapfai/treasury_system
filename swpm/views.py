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
    trade_detail_form = TradeDetailForm()
    as_of_form = AsOfForm(initial={'as_of': datetime.date.today()})
    return render(request, "swpm/index.html", locals())

@csrf_exempt
def trade_list(request):
    trades = FXO.objects.all()
    temp = json.loads(serialize('json', trades))
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
        fxo_form = FXOForm(request.POST, instance=FXO())
        if fxo_form.is_valid():
            fxo = fxo_form.save(commit=commit)
            inst = fxo.instrument()
            engine = fxo.make_pricing_engine(as_of)
            inst.setPricingEngine(engine)
            side = 1.0 if fxo.buy_sell=="B" else -1.0
            if commit and request.POST['book']:
                trade_detail_form = TradeDetailForm(request.POST)
                trade_detail = trade_detail_form.save(commit=False)
                trade_detail.input_user = request.user
                trade_detail.save()
                fxo.detail = trade_detail
                fxo.save()
            else:
                trade_detail_form = TradeDetailForm(request.POST)
            return render(request, 'swpm/index.html', {
                'myform': CcyPairForm(),
                'myFXOform': fxo_form, 
                'as_of_form': as_of_form, 
                'trade_detail_form': trade_detail_form, 
                'market_data': {'spot': fxo.ccy_pair.get_rate(as_of).rate}, 
                'results': {'npv': side*inst.NPV()*fxo.notional_1, 
                        'delta': side*inst.delta()*fxo.notional_1,
                        'gamma': side*inst.gamma()*fxo.notional_1,
                        'vega': side*inst.vega()*fxo.notional_1
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
                trades = trades.union(b.trades.all())
        else:
            trades = TradeDetail.objects.all()

        for t in trades:
            inst = t.trade.first().instrument()
            engine = t.trade.first().make_pricing_engine(reval_date)
            inst.setPricingEngine(engine)
            side = 1.0 if t.trade.first().buy_sell=="B" else -1.0
            mtm, _ = TradeMarkToMarket.objects.get_or_create(as_of = reval_date, trade_d = t)
            mtm.npv = side * inst.NPV() * t.trade.first().notional_1
            mtm.save()
        return render(request, 'swpm/reval.html', {'reval_form': RevalForm(request.POST), 'result': "Reval completed: \n" + str(TradeMarkToMarket.objects.get(as_of=reval_date))})
    else:
        return render(request, 'swpm/reval.html', {'reval_form': RevalForm(initial={'reval_date': datetime.date.today()})})
