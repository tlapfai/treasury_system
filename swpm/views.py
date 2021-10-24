from django.shortcuts import render
from django.http import *
from django.utils import timezone

# Create your views here.
def index(request):
    mytime = timezone.now()
    return render(request, "swpm/index.html", locals())
