from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'attendance'

router = DefaultRouter()
router.register(r'logs', views.AttendanceViewSet, basename='api-attendance')

urlpatterns = [
    path('', views.attendance_list, name='attendance_list'),
    path('scanner/', views.attendance_scanner, name='scanner'),
    path('api/scan/', views.api_scan_qr, name='api_scan'),
    path('api/', include(router.urls)),
]

