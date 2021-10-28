from django.shortcuts import render
from django.http import *
from django.utils import timezone
from .models import *

# Create your views here.
def index(request):
    mytime = timezone.now()
    myform = CcyPairForm()
    myFXOform = FXOForm()
    return render(request, "swpm/index.html", locals())
