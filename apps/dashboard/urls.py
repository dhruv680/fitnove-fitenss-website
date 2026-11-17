from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_index, name='index'),
    path('about/', views.about_view, name='about'),
    path('services/', views.services_view, name='services'),
    path('contact/', views.contact_view, name='contact'),
    path('apply/', views.apply_view, name='apply'),
    path('search/', views.global_search, name='search'),
    path('reports/', views.reports_analytics, name='reports'),
    path('settings/', views.settings_view, name='settings'),
]

