from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'accounts'

router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='api-users')
router.register(r'organizations', views.GymOrganizationViewSet, basename='api-organizations')
router.register(r'branches', views.GymBranchViewSet, basename='api-branches')

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('face-enroll/', views.face_enroll_view, name='face_enroll'),
    path('api/face-enroll/', views.api_face_enroll, name='api_face_enroll'),
    path('login/', views.login_view, name='login'),
    path('face-verify/', views.face_verify_view, name='face_verify'),
    path('api/face-verify/', views.api_face_verify, name='api_face_verify'),
    path('face-fallback/', views.face_fallback_view, name='face_fallback'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/change-password/', views.change_password_view, name='change_password'),
    path('api/', include(router.urls)),
]

