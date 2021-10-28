from django.contrib import admin
from .models import *

admin.site.register(Calendar)
admin.site.register(Ccy)
admin.site.register(CcyPair)
admin.site.register(FXO)
admin.site.register(RateIndex)
admin.site.register(RateQuote)
admin.site.register(IRTermStructure)
admin.site.register(FXVolatility)
admin.site.register(FxSpotRateQuote)



