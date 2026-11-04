from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'notifications'

router = DefaultRouter()
router.register(r'user-notifications', views.NotificationViewSet, basename='api-notifications')

urlpatterns = [
    path('', views.notification_list, name='list'),
    path('<int:pk>/read/', views.mark_read, name='mark_read'),
    path('read-all/', views.mark_all_read, name='mark_all_read'),
    path('api/', include(router.urls)),
]
