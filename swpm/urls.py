from django.urls import path, re_path
from django.urls.conf import include
from . import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'calendar', views.CalendarViewSet)
router.register(r'fxo', views.FXOViewSet)

urlpatterns = [
    path("", views.index, name="index"),

    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("register", views.register, name="register"),

    path('new_trade', views.new_trade),
    path('pricing', views.pricing, name='pricing'),
    path('pricing/do', views.pricing, {'commit': True}, name='pricing-do'),
    path('ccypair', views.save_ccypair, name='ccypair'),
    path('trade_list', views.trade_list, name='trade_list'),
    #path('trade/<str:inst>', views.trade, name='trade'),
    #path('trade/<str:inst>/<int:id>', views.trade, name='trade'),
    #path('trade/<str:inst>', views.TradeView.as_view(), name='trade'),
    #path('trade/<str:inst>/<int:id>', views.TradeView.as_view(), name='trade'),
    path('calendar', views.CalendarList.as_view(), name='calendar'),
    path('calendar/<str:name>', views.CalendarDetail.as_view(), name='calendar'),
    path('fxoapi/<int:id>', views.FXODetail.as_view(), name='fxoapi'),

    path('fxodetail', views.fxo_detail, name='fxodetail'),
    path('trade/fxo/create', views.FXOCreateView.as_view(), name='fxo_create'),
    path('trade/fxo/<int:pk>', views.FXOUpdateView.as_view(), name='fxo_update'),
    path('trade/fxo/price', views.fxo_price, name='fxo_price'),  # api

    path('fx_volatility_table', views.fx_volatility_table,
         name='fx_volatility_table'),  # api

    path('yield_curve/search', views.yield_curve, name='yield_curve_search'),
    re_path(
        r'^yield_curve/(?P<curve>[-\w\s]+)/(?P<ref_date>\d{4}-\d{2}-\d{2})$', views.yield_curve, name='yield_curve'),
    # API
    path('reval', views.reval, name='reval'),
    path('market_data_import', views.market_data_import, name='market_data_import'),
    path('load_market_data', views.load_market_data, name='load_market_data'),
    #path('tenor2date', views.tenor2date, name='tenor2date'),
    re_path(r'api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('fxo_price', views.fxo_price, name='fxo_price'),
]
