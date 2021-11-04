from django.urls import path
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
    path('trade/<str:inst>', views.trade, name='trade'),
    # API
    path('reval', views.reval, name='reval'), 
]
