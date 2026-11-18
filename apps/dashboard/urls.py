from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_index, name='index'),
    path('about/', views.about_view, name='about'),
    path('services/', views.services_view, name='services'),
    path('contact/', views.contact_view, name='contact'),
    path('apply/', views.apply_view, name='apply'),
    path('help/', views.help_center_view, name='help_center'),
    path('privacy/', views.privacy_policy_view, name='privacy_policy'),
    path('terms/', views.terms_conditions_view, name='terms_conditions'),
    path('search/', views.global_search, name='search'),
    path('reports/', views.reports_analytics, name='reports'),
    path('settings/', views.settings_view, name='settings'),
    path('settings/branches/create/', views.branch_create_view, name='branch_create'),
    path('settings/branches/<int:branch_id>/update/', views.branch_update_view, name='branch_update'),
    path('settings/branches/<int:branch_id>/delete/', views.branch_delete_view, name='branch_delete'),
    path('settings/branches/<int:branch_id>/toggle-status/', views.branch_toggle_status_view, name='branch_toggle_status'),
]

