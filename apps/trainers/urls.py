from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'trainers'

router = DefaultRouter()
router.register(r'trainers', views.TrainerViewSet, basename='api-trainers')

urlpatterns = [
    path('', views.trainer_list, name='trainer_list'),
    path('add/', views.trainer_create, name='trainer_create'),
    path('<int:pk>/', views.trainer_detail, name='trainer_detail'),
    path('<int:pk>/edit/', views.trainer_edit, name='trainer_edit'),
    path('api/', include(router.urls)),
]
