from django.shortcuts import render
from django.http import *
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.core.serializers import serialize

from .models import *
import datetime
import json

def index(request):
    mytime = timezone.now()
    myform = CcyPairForm()
    myFXOform = FXOForm()
    return render(request, "swpm/index.html", locals())

@csrf_exempt
def trade_list(request):
    #return JsonResponse([email.serialize() for email in emails], safe=False)
    trades = FXO.objects.all()
    return render(request, 'swpm/trade-list.html', json.loads(serialize('json', trades)), safe=False)


@csrf_exempt
def pricing(request, commit=False):
    if request.method == 'POST':
        #fxo_class = FXO()
        fxo_form = FXOForm(request.POST, instance=FXO())#fxo_class)
        fxo_class = fxo_form.save(commit=commit)
        #print(opt_class)
        opt = fxo_class.instrument()
        engine = fxo_class.make_pricing_engine(datetime.date.today())
        opt.setPricingEngine(engine)
        return render(request, 'swpm/index.html', {
            'myform': CcyPairForm(),
            'myFXOform': fxo_form, 
            'market_data': {'spot': fxo_class.ccy_pair.get_rate(datetime.date.today()).rate}, 
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
    
