from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'members'

router = DefaultRouter()
router.register(r'members', views.MemberViewSet, basename='api-members')

urlpatterns = [
    path('', views.member_list, name='member_list'),
    path('add/', views.member_create, name='member_create'),
    path('<int:pk>/', views.member_detail, name='member_detail'),
    path('<int:pk>/edit/', views.member_edit, name='member_edit'),
    path('<int:pk>/delete/', views.member_delete, name='member_delete'),
    path('api/', include(router.urls)),
]

