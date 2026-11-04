from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'accounts'

router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='api-users')
router.register(r'organizations', views.GymOrganizationViewSet, basename='api-organizations')
router.register(r'branches', views.GymBranchViewSet, basename='api-branches')

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/change-password/', views.change_password_view, name='change_password'),
    path('api/', include(router.urls)),
]
