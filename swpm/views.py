from django.shortcuts import render
from django.http import *
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from .models import *
import datetime

def index(request):
    mytime = timezone.now()
    myform = CcyPairForm()
    myFXOform = FXOForm()
    return render(request, "swpm/index.html", locals())

@csrf_exempt
def pricing(request):
    if request.method == 'POST':
        opt_class = FXO()
        opt_form = FXOForm(request.POST, instance=opt_class)
        #print(opt_class)
        opt = opt_class.instrument()
        engine = opt_form.make_pricing_engine(datetime.date.today())
        opt.setPricingEngine(engine)
        return render(request, 'swpm/index.html', {
            'market_data': {'spot': 0}, 
            'result': {'npv': opt.NPV(), 
                    'delta': opt.delta(),
                    'gamma': opt.gamma()}})
    
