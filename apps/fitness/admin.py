from django.contrib import admin
from .models import Exercise, WorkoutPlan, WorkoutDay, WorkoutExercise, DietPlan, DietMeal, MemberProgress


class WorkoutDayInline(admin.TabularInline):
    model = WorkoutDay
    extra = 1


class WorkoutExerciseInline(admin.TabularInline):
    model = WorkoutExercise
    extra = 1


class DietMealInline(admin.TabularInline):
    model = DietMeal
    extra = 1


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'difficulty', 'equipment')
    list_filter = ('category', 'difficulty')
    search_fields = ('name', 'equipment', 'instructions')


@admin.register(WorkoutPlan)
class WorkoutPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'member', 'trainer', 'goal', 'level', 'start_date', 'end_date', 'is_active')
    list_filter = ('level', 'is_active', 'start_date', 'end_date')
    search_fields = ('name', 'goal', 'member__member_id', 'member__user__username')
    inlines = [WorkoutDayInline]


@admin.register(DietPlan)
class DietPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'member', 'trainer', 'daily_calories', 'protein_grams', 'carbs_grams', 'fats_grams', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'member__member_id', 'member__user__username')
    inlines = [DietMealInline]


@admin.register(MemberProgress)
class MemberProgressAdmin(admin.ModelAdmin):
    list_display = ('member', 'date', 'weight_kg', 'body_fat_percentage', 'created_at')
    list_filter = ('date',)
    search_fields = ('member__member_id', 'member__user__username')
