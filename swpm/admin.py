from django.contrib import admin
from .models import *

admin.site.register(User)
admin.site.register(Calendar)
admin.site.register(Ccy)
admin.site.register(RateIndex)
admin.site.register(RateIndexFixing)
admin.site.register(RateQuote)
admin.site.register(IRTermStructure)
admin.site.register(FXVolatility)
admin.site.register(FxSpotRateQuote)

admin.site.register(Trade)
admin.site.register(CashFlow)
admin.site.register(FXO)
admin.site.register(Swap)
admin.site.register(SwapLeg)

admin.site.register(Portfolio)
admin.site.register(Book)
admin.site.register(Counterparty)
admin.site.register(TradeDetail)
admin.site.register(TradeMarkToMarket)

class CcyPairAdmin(admin.ModelAdmin):
    fields = ('name', 'base_ccy', 'quote_ccy', 'calendar', 'fixing_days')
    #list of fields to display in django admin
    list_display = ['name', 'base_ccy', 'quote_ccy', 'calendar', 'fixing_days']
    #if you want django admin to show the search bar, just add this line
    search_fields = ['name', 'base_ccy', 'quote_ccy', 'calendar', 'fixing_days']
    #to define model data list ordering
    ordering = ['name', 'base_ccy', 'quote_ccy', 'calendar', 'fixing_days']
admin.site.register(CcyPair, CcyPairAdmin)

# @admin.register(IRTermStructure)
# class IRTermStructureAdmin(admin.ModelAdmin):
#     #fields = ['name', 'ref_date', 'ccy', 'rates', 'as_fx_curve', 'as_rf_curve']
#     list_display = ['name', 'ref_date', 'ccy', 'as_fx_curve', 'as_rf_curve']
#     #search_fields = ['name', 'ref_date', 'ccy', 'rates', 'as_fx_curve', 'as_rf_curve']
#     ordering = ['name', 'ref_date', 'ccy', 'rates', 'as_fx_curve', 'as_rf_curve']
    


#@admin.register(FXO)
#class FXOAdmin(admin.ModelAdmin):
#    pass
