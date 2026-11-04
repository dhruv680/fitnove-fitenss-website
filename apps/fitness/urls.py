from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'fitness'

router = DefaultRouter()
router.register(r'workouts', views.WorkoutPlanViewSet, basename='api-workouts')
router.register(r'diets', views.DietPlanViewSet, basename='api-diets')

urlpatterns = [
    path('workouts/', views.workout_list, name='workout_list'),
    path('workouts/add/', views.workout_create, name='workout_create'),
    path('workouts/<int:pk>/', views.workout_detail, name='workout_detail'),
    path('diets/', views.diet_list, name='diet_list'),
    path('diets/add/', views.diet_create, name='diet_create'),
    path('diets/<int:pk>/', views.diet_detail, name='diet_detail'),
    path('exercises/', views.exercise_library, name='exercise_library'),
    path('progress/', views.progress_log, name='progress_log'),
    path('api/', include(router.urls)),
]
