from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'crm'

router = DefaultRouter()
router.register(r'leads', views.LeadViewSet, basename='api-leads')

urlpatterns = [
    path('', views.lead_list, name='lead_list'),
    path('add/', views.lead_create, name='lead_create'),
    path('<int:pk>/status/', views.lead_update_status, name='lead_update_status'),
    path('api/', include(router.urls)),
]
