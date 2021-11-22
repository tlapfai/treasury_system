from django.urls import path, re_path
from . import views

urlpatterns = [
    path("", views.index, name="index"),

    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("register", views.register, name="register"),
    
    path('pricing', views.pricing, name='pricing'),
    path('pricing/do', views.pricing, {'commit': True}, name='pricing-do'),
    path('ccypair', views.save_ccypair, name='ccypair'), 
    path('trade_list', views.trade_list, name='trade_list'),
    #path('trade/<str:inst>', views.trade, name='trade'),
    #path('trade/<str:inst>/<int:id>', views.trade, name='trade'),
    path('trade/<str:inst>', views.TradeView.as_view(), name='trade'),
    path('trade/<str:inst>/<int:id>', views.TradeView.as_view(), name='trade'),

    path('yield_curve/search', views.yield_curve, name='yield_curve_search'), 
    re_path(r'^yield_curve/(?P<curve>[-\w\s]+)/(?P<ref_date>\d{4}-\d{2}-\d{2})$', views.yield_curve, name='yield_curve'), 
    # API
    path('reval', views.reval, name='reval'), 
    path('market_data_import', views.market_data_import, name='market_data_import'), 
    path('load_market_data', views.load_market_data, name='load_market_data'),
    #path('tenor2date', views.tenor2date, name='tenor2date'), 
]
