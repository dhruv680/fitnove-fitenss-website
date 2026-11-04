from rest_framework import serializers
from .models import Exercise, WorkoutPlan, WorkoutDay, WorkoutExercise, DietPlan, DietMeal, MemberProgress

class ExerciseSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Exercise
        fields = ['id', 'name', 'category', 'category_display', 'difficulty', 'equipment', 'instructions']


class WorkoutExerciseSerializer(serializers.ModelSerializer):
    exercise_name = serializers.ReadOnlyField(source='exercise.name')
    category = serializers.ReadOnlyField(source='exercise.get_category_display')

    class Meta:
        model = WorkoutExercise
        fields = ['id', 'exercise', 'exercise_name', 'category', 'sets', 'reps', 'rest_seconds', 'notes']


class WorkoutDaySerializer(serializers.ModelSerializer):
    exercises = WorkoutExerciseSerializer(many=True, read_only=True)

    class Meta:
        model = WorkoutDay
        fields = ['id', 'day_name', 'day_number', 'focus_area', 'exercises']


class WorkoutPlanSerializer(serializers.ModelSerializer):
    member_name = serializers.ReadOnlyField(source='member.full_name')
    trainer_name = serializers.ReadOnlyField(source='trainer.full_name')
    days = WorkoutDaySerializer(many=True, read_only=True)

    class Meta:
        model = WorkoutPlan
        fields = ['id', 'member', 'member_name', 'trainer', 'trainer_name', 'name', 'goal', 'level', 'start_date', 'end_date', 'is_active', 'notes', 'days']


class DietMealSerializer(serializers.ModelSerializer):
    meal_type_display = serializers.CharField(source='get_meal_type_display', read_only=True)

    class Meta:
        model = DietMeal
        fields = ['id', 'meal_type', 'meal_type_display', 'time_slot', 'items', 'calories']


class DietPlanSerializer(serializers.ModelSerializer):
    member_name = serializers.ReadOnlyField(source='member.full_name')
    trainer_name = serializers.ReadOnlyField(source='trainer.full_name')
    meals = DietMealSerializer(many=True, read_only=True)

    class Meta:
        model = DietPlan
        fields = ['id', 'member', 'member_name', 'trainer', 'trainer_name', 'name', 'daily_calories', 'protein_grams', 'carbs_grams', 'fats_grams', 'water_liters', 'is_active', 'notes', 'meals']


class MemberProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = MemberProgress
        fields = ['id', 'member', 'date', 'weight_kg', 'body_fat_percentage', 'chest_cm', 'waist_cm', 'arms_cm', 'notes']
