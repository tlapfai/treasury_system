from django.urls import path, re_path
from django.urls.conf import include
from . import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'calendar', views.CalendarViewSet)
router.register(r'fxo', views.FXOViewSet)

urlpatterns = [
    #path("", views.index, name="index"),
    path('', views.FXOView.as_view(), name='fxo_create'),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("register", views.register, name="register"),
    path('new_trade', views.new_trade),
    path('ccypair', views.save_ccypair, name='ccypair'),
    path('trade_list', views.trade_list, name='trade_list'),
    path('calendar', views.CalendarList.as_view(), name='calendar'),
    path('calendar/<str:name>',
         views.CalendarDetail.as_view(),
         name='calendar'),
    path('fxoapi/<int:id>', views.FXODetail.as_view(), name='fxoapi'),
    path('fxodetail', views.fxo_detail, name='fxodetail'),
    path('trade/fxo/create', views.FXOView.as_view(), name='fxo_create'),
    path('trade/fxo/<int:id>', views.FXOView.as_view(), name='fxo_update'),
    path('api/trade/fxo/price', views.api_fxo_price),  # api
    path('api/trade/fxo/scn', views.api_fxo_scn),
    path('api/trade/swap/price',
         views.api_swap_price,
         name='api_trade_swap_price'),  # api
    path('trade/swap/create', views.SwapView.as_view(), name='swap_create'),
    path('trade/fxo/scn', views.fxo_scn, name='fxo_scn'),
    path('mkt/fxv', views.FXVolView.as_view(), name='mkt_fxv'),
    path('mkt/curve', views.YieldCurveView.as_view(), name='mkt_curve'),
    path('api/mkt/curve/calc', views.api_curve_calc),
    re_path(r'^mkt/fxv/(?P<ccy_pair>[A-Z]+)/(?P<date>\d{4}-\d{2}-\d{2})$',
            views.FXVolView.as_view(),
            name='mkt_fxv_get'),
    path('api/mkt/fxv', views.api_fxv),
    re_path(
        r'^mkt/curve/(?P<ccy>[A-Z]+)/(?P<name>[A-Z]+)/(?P<date>\d{4}-\d{2}-\d{2})$',
        views.YieldCurveView.as_view(),
        name='mkt_curve_get'),
    path('api/mkt/curve', views.api_curve),
    path('api/day_counters', views.api_day_counters),
    path('load_fxo_mkt', views.load_fxo_mkt, name='load_fxo_mkt'),  # api
    path('api/tenor2date', views.tenor2date, name='tenor2date'),  # api
    path('yield_curve/search', views.yield_curve, name='yield_curve_search'),
    # \s is for whitespace
    re_path(
        r'^yield_curve/(?P<ccy>[-\w]+)/(?P<curve>[-\w]+)/(?P<ref_date>\d{4}-\d{2}-\d{2})$',
        views.yield_curve,
        name='yield_curve'),
    # API
    path('reval', views.reval, name='reval'),
    path('market_data_import',
         views.market_data_import,
         name='market_data_import'),
    #path('load_market_data', views.load_market_data, name='load_market_data'),
    #path('fxo_price', views.fxo_price, name='fxo_price'),
]
