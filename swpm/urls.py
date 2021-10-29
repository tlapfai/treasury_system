from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path('pricing', views.pricing, name='pricing'),
    path('pricing/do', views.pricing, {'commit': True}, name='pricing-do'),
    path('ccypair', views.save_ccypair, name='ccypair'), 
    path('trade_list', views.trade_list, name='trade_list'),
]
