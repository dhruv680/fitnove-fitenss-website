from django.db import models
from django.utils import timezone
from apps.accounts.models import GymOrganization

class Exercise(models.Model):
    class Category(models.TextChoices):
        CHEST = 'CHEST', 'Chest'
        BACK = 'BACK', 'Back'
        LEGS = 'LEGS', 'Legs'
        SHOULDERS = 'SHOULDERS', 'Shoulders'
        ARMS = 'ARMS', 'Arms (Biceps & Triceps)'
        CORE = 'CORE', 'Core & Abs'
        CARDIO = 'CARDIO', 'Cardiovascular'
        FULL_BODY = 'FULL_BODY', 'Full Body & Functional'

    class Difficulty(models.TextChoices):
        BEGINNER = 'BEGINNER', 'Beginner'
        INTERMEDIATE = 'INTERMEDIATE', 'Intermediate'
        ADVANCED = 'ADVANCED', 'Advanced'

    organization = models.ForeignKey(
        GymOrganization,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='exercises'
    )
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=30, choices=Category.choices, default=Category.FULL_BODY)
    difficulty = models.CharField(max_length=20, choices=Difficulty.choices, default=Difficulty.BEGINNER)
    equipment = models.CharField(max_length=100, default='Bodyweight', help_text='e.g., Barbell, Dumbbell, Cable, Machine')
    instructions = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['category', 'name']
        verbose_name = 'Exercise'
        verbose_name_plural = 'Exercise Library'

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class WorkoutPlan(models.Model):
    class Level(models.TextChoices):
        BEGINNER = 'BEGINNER', 'Beginner'
        INTERMEDIATE = 'INTERMEDIATE', 'Intermediate'
        ADVANCED = 'ADVANCED', 'Advanced'

    member = models.ForeignKey(
        'members.Member',
        on_delete=models.CASCADE,
        related_name='workout_plans'
    )
    trainer = models.ForeignKey(
        'trainers.Trainer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_workout_plans'
    )
    name = models.CharField(max_length=150)
    goal = models.CharField(max_length=150, help_text='e.g., Hypertrophy, Fat Loss, Strength')
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.INTERMEDIATE)
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Workout Routine'
        verbose_name_plural = 'Workout Routines'

    def __str__(self):
        return f"{self.name} - {self.member.full_name}"


class WorkoutDay(models.Model):
    workout_plan = models.ForeignKey(WorkoutPlan, on_delete=models.CASCADE, related_name='days')
    day_name = models.CharField(max_length=100, help_text='e.g., Day 1 - Push, Monday')
    day_number = models.PositiveSmallIntegerField(default=1)
    focus_area = models.CharField(max_length=100, default='General Conditioning')

    class Meta:
        ordering = ['day_number']

    def __str__(self):
        return f"{self.workout_plan.name} - {self.day_name}"


class WorkoutExercise(models.Model):
    workout_day = models.ForeignKey(WorkoutDay, on_delete=models.CASCADE, related_name='exercises')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    sets = models.PositiveIntegerField(default=3)
    reps = models.CharField(max_length=50, default='10-12 reps')
    rest_seconds = models.PositiveIntegerField(default=60)
    notes = models.CharField(max_length=200, blank=True, default='')

    def __str__(self):
        return f"{self.exercise.name} - {self.sets} x {self.reps}"


class DietPlan(models.Model):
    member = models.ForeignKey(
        'members.Member',
        on_delete=models.CASCADE,
        related_name='diet_plans'
    )
    trainer = models.ForeignKey(
        'trainers.Trainer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_diet_plans'
    )
    name = models.CharField(max_length=150)
    daily_calories = models.PositiveIntegerField(default=2200)
    protein_grams = models.PositiveIntegerField(default=150)
    carbs_grams = models.PositiveIntegerField(default=200)
    fats_grams = models.PositiveIntegerField(default=60)
    water_liters = models.DecimalField(max_digits=4, decimal_places=1, default=3.0)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Diet Plan'
        verbose_name_plural = 'Diet Plans'

    def __str__(self):
        return f"{self.name} ({self.daily_calories} kcal) - {self.member.full_name}"


class DietMeal(models.Model):
    class MealType(models.TextChoices):
        BREAKFAST = 'BREAKFAST', 'Breakfast'
        MID_MORNING = 'MID_MORNING', 'Mid-Morning Snack'
        LUNCH = 'LUNCH', 'Lunch'
        PRE_WORKOUT = 'PRE_WORKOUT', 'Pre-Workout Fuel'
        POST_WORKOUT = 'POST_WORKOUT', 'Post-Workout Shake'
        DINNER = 'DINNER', 'Dinner'

    diet_plan = models.ForeignKey(DietPlan, on_delete=models.CASCADE, related_name='meals')
    meal_type = models.CharField(max_length=30, choices=MealType.choices, default=MealType.BREAKFAST)
    time_slot = models.CharField(max_length=50, default='08:00 AM')
    items = models.TextField(help_text='Foods and portions')
    calories = models.PositiveIntegerField(default=400)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.get_meal_type_display()} ({self.calories} kcal)"


class MemberProgress(models.Model):
    member = models.ForeignKey(
        'members.Member',
        on_delete=models.CASCADE,
        related_name='progress_logs'
    )
    date = models.DateField(default=timezone.now)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2)
    body_fat_percentage = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    chest_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    waist_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    arms_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = 'Progress Metric'
        verbose_name_plural = 'Progress Metrics'

    def __str__(self):
        return f"{self.member.full_name} - {self.weight_kg} kg on {self.date}"
