import datetime
from django.utils import timezone
from .models import Exercise, WorkoutPlan, WorkoutDay, WorkoutExercise, DietPlan, DietMeal, MemberProgress

class FitnessService:
    @staticmethod
    def get_scoped_workouts(user):
        if user.is_super_admin:
            return WorkoutPlan.objects.select_related('member__user', 'trainer__user').prefetch_related('days__exercises__exercise').all()
        if user.is_trainer:
            return WorkoutPlan.objects.select_related('member__user', 'trainer__user').prefetch_related('days__exercises__exercise').filter(trainer__user=user)
        if user.is_member:
            return WorkoutPlan.objects.select_related('member__user', 'trainer__user').prefetch_related('days__exercises__exercise').filter(member__user=user)
        return WorkoutPlan.objects.select_related('member__user', 'trainer__user').prefetch_related('days__exercises__exercise').filter(member__organization=user.organization)

    @staticmethod
    def get_scoped_diets(user):
        if user.is_super_admin:
            return DietPlan.objects.select_related('member__user', 'trainer__user').prefetch_related('meals').all()
        if user.is_trainer:
            return DietPlan.objects.select_related('member__user', 'trainer__user').prefetch_related('meals').filter(trainer__user=user)
        if user.is_member:
            return DietPlan.objects.select_related('member__user', 'trainer__user').prefetch_related('meals').filter(member__user=user)
        return DietPlan.objects.select_related('member__user', 'trainer__user').prefetch_related('meals').filter(member__organization=user.organization)
