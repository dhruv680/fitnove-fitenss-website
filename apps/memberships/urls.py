from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'memberships'

router = DefaultRouter()
router.register(r'plans', views.MembershipPlanViewSet, basename='api-plans')
router.register(r'subscriptions', views.MembershipViewSet, basename='api-subscriptions')

urlpatterns = [
    path('plans/', views.plan_list, name='plan_list'),
    path('plans/add/', views.plan_create, name='plan_create'),
    path('plans/<int:pk>/edit/', views.plan_edit, name='plan_edit'),
    path('renew/<int:member_id>/', views.membership_renew, name='membership_renew'),
    path('api/', include(router.urls)),
]

