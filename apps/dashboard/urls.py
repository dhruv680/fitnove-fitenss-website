from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_index, name='index'),
    path('search/', views.global_search, name='search'),
    path('reports/', views.reports_analytics, name='reports'),
    path('settings/', views.settings_view, name='settings'),
]

