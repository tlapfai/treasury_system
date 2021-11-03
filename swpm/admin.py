from django.contrib import admin
from .models import *

admin.site.register(User)
admin.site.register(Calendar)
admin.site.register(Ccy)
admin.site.register(CcyPair)
admin.site.register(Trade)
admin.site.register(FXO)
admin.site.register(RateIndex)
admin.site.register(RateQuote)
admin.site.register(IRTermStructure)
admin.site.register(FXVolatility)
admin.site.register(FxSpotRateQuote)

admin.site.register(Portfolio)
admin.site.register(Book)
admin.site.register(Counterparty)
admin.site.register(TradeDetail)
admin.site.register(TradeMarkToMarket)


#@admin.register(FXO)
#class FXOAdmin(admin.ModelAdmin):
#    pass
