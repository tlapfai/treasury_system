from django.shortcuts import render
from django.http import *
from django.utils import timezone
from .models import *
import datetime

def index(request):
    mytime = timezone.now()
    myform = CcyPairForm()
    myFXOform = FXOForm()
    return render(request, "swpm/index.html", locals())

def pricing(request):
    opt_class = FXO()
    opt = FXOForm(request.POST, instance=opt_class)
    opt_inst = opt.instrument()
    engine = opt.make_pricing_engine(datetime.date.today())
    
