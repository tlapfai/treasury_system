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
            return render(request, 'swpm/index.html', {
                'myform': CcyPairForm(),
                'myFXOform': fxo_form, 
                'as_of_form': as_of_form, 
                'market_data': {'spot': fxo_class.ccy_pair.get_rate(as_of).rate}, 
                'results': {'npv': opt.NPV(), 
                        'delta': opt.delta(),
                        'gamma': opt.gamma(),
                        'vega': opt.vega()
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
    

def reval(request):
    # ts = trades.all()
    # for t in ts: reval -> save()
    pass
