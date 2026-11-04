from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'classes'

router = DefaultRouter()
router.register(r'classes', views.FitnessClassViewSet, basename='api-classes')

urlpatterns = [
    path('', views.class_list, name='class_list'),
    path('add/', views.class_create, name='class_create'),
    path('<int:pk>/', views.class_detail, name='class_detail'),
    path('<int:pk>/book/', views.book_class, name='book_class'),
    path('api/', include(router.urls)),
]

