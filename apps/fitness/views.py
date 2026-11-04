import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from rest_framework import viewsets
from apps.accounts.permissions import staff_or_admin, IsStaffOrAdminUser
from apps.members.models import Member
from apps.trainers.models import Trainer
from .models import Exercise, WorkoutPlan, WorkoutDay, WorkoutExercise, DietPlan, DietMeal, MemberProgress
from .services import FitnessService
from .serializers import WorkoutPlanSerializer, DietPlanSerializer, ExerciseSerializer, MemberProgressSerializer

@login_required
def workout_list(request):
    workouts = FitnessService.get_scoped_workouts(request.user)
    paginator = Paginator(workouts, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'fitness/workout_list.html', {'page_obj': page_obj})


@login_required
def workout_detail(request, pk):
    workouts = FitnessService.get_scoped_workouts(request.user)
    workout = get_object_or_404(workouts, pk=pk)
    return render(request, 'fitness/workout_detail.html', {'workout': workout})


@login_required
def workout_create(request):
    org = request.user.organization
    members = Member.objects.filter(status='ACTIVE')
    trainers = Trainer.objects.filter(status='ACTIVE')
    exercises = Exercise.objects.all()

    if not request.user.is_super_admin:
        members = members.filter(organization=org)
        trainers = trainers.filter(organization=org)

    if request.method == 'POST':
        member_id = request.POST.get('member_id')
        name = request.POST.get('name', '').strip()
        goal = request.POST.get('goal', '').strip()
        level = request.POST.get('level', 'INTERMEDIATE')
        start_date = request.POST.get('start_date') or timezone.now().date()
        end_date = request.POST.get('end_date') or (timezone.now() + datetime.timedelta(days=30)).date()
        notes = request.POST.get('notes', '').strip()
        trainer_id = request.POST.get('trainer_id')

        member = get_object_or_404(members, id=member_id)
        trainer = trainers.filter(id=trainer_id).first() if trainer_id else None

        workout = WorkoutPlan.objects.create(
            member=member,
            trainer=trainer,
            name=name,
            goal=goal,
            level=level,
            start_date=start_date,
            end_date=end_date,
            notes=notes
        )

        # Create standard 3-day split by default
        day1 = WorkoutDay.objects.create(workout_plan=workout, day_name='Day 1 - Push (Chest & Triceps)', day_number=1, focus_area='Chest & Shoulders')
        day2 = WorkoutDay.objects.create(workout_plan=workout, day_name='Day 2 - Pull (Back & Biceps)', day_number=2, focus_area='Back & Arms')
        day3 = WorkoutDay.objects.create(workout_plan=workout, day_name='Day 3 - Legs & Core', day_number=3, focus_area='Quads, Hamstrings & Core')

        bench = Exercise.objects.filter(name__icontains='Bench Press').first() or exercises.first()
        squat = Exercise.objects.filter(name__icontains='Squat').first() or exercises.first()
        deadlift = Exercise.objects.filter(name__icontains='Deadlift').first() or exercises.first()

        if bench:
            WorkoutExercise.objects.create(workout_day=day1, exercise=bench, sets=4, reps='8-10 reps', rest_seconds=90)
        if deadlift:
            WorkoutExercise.objects.create(workout_day=day2, exercise=deadlift, sets=4, reps='6-8 reps', rest_seconds=120)
        if squat:
            WorkoutExercise.objects.create(workout_day=day3, exercise=squat, sets=4, reps='10-12 reps', rest_seconds=90)

        messages.success(request, f"Workout routine '{workout.name}' created for {member.full_name}!")
        return redirect('fitness:workout_detail', pk=workout.pk)

    return render(request, 'fitness/workout_form.html', {
        'members': members,
        'trainers': trainers
    })


@login_required
def diet_list(request):
    diets = FitnessService.get_scoped_diets(request.user)
    paginator = Paginator(diets, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'fitness/diet_list.html', {'page_obj': page_obj})


@login_required
def diet_detail(request, pk):
    diets = FitnessService.get_scoped_diets(request.user)
    diet = get_object_or_404(diets, pk=pk)
    return render(request, 'fitness/diet_detail.html', {'diet': diet})


@login_required
def diet_create(request):
    org = request.user.organization
    members = Member.objects.filter(status='ACTIVE')
    trainers = Trainer.objects.filter(status='ACTIVE')

    if not request.user.is_super_admin:
        members = members.filter(organization=org)
        trainers = trainers.filter(organization=org)

    if request.method == 'POST':
        member_id = request.POST.get('member_id')
        name = request.POST.get('name', '').strip()
        daily_calories = int(request.POST.get('calories', '2200'))
        protein = int(request.POST.get('protein', '150'))
        carbs = int(request.POST.get('carbs', '200'))
        fats = int(request.POST.get('fats', '60'))
        water = float(request.POST.get('water', '3.0'))
        trainer_id = request.POST.get('trainer_id')
        notes = request.POST.get('notes', '').strip()

        member = get_object_or_404(members, id=member_id)
        trainer = trainers.filter(id=trainer_id).first() if trainer_id else None

        diet = DietPlan.objects.create(
            member=member,
            trainer=trainer,
            name=name,
            daily_calories=daily_calories,
            protein_grams=protein,
            carbs_grams=carbs,
            fats_grams=fats,
            water_liters=water,
            notes=notes
        )

        DietMeal.objects.create(diet_plan=diet, meal_type='BREAKFAST', time_slot='08:30 AM', items='Oatmeal with whey protein, almonds, and sliced banana', calories=500)
        DietMeal.objects.create(diet_plan=diet, meal_type='LUNCH', time_slot='01:00 PM', items='Grilled chicken breast with brown rice and steamed broccoli', calories=650)
        DietMeal.objects.create(diet_plan=diet, meal_type='PRE_WORKOUT', time_slot='05:00 PM', items='Whole wheat toast with peanut butter and an apple', calories=350)
        DietMeal.objects.create(diet_plan=diet, meal_type='DINNER', time_slot='08:30 PM', items='Pan-seared salmon with quinoa and mixed greens salad', calories=600)

        messages.success(request, f"Diet plan '{diet.name}' prescribed to {member.full_name}!")
        return redirect('fitness:diet_detail', pk=diet.pk)

    return render(request, 'fitness/diet_form.html', {
        'members': members,
        'trainers': trainers
    })


@login_required
def exercise_library(request):
    exercises = Exercise.objects.all()
    category = request.GET.get('category', '').strip()
    search = request.GET.get('search', '').strip()

    if category:
        exercises = exercises.filter(category=category)
    if search:
        exercises = exercises.filter(name__icontains=search)

    paginator = Paginator(exercises, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'fitness/exercise_library.html', {
        'page_obj': page_obj,
        'category_filter': category,
        'search_query': search,
        'categories': Exercise.Category.choices
    })


@login_required
def progress_log(request):
    if request.user.is_member:
        member = request.user.member_profile
    else:
        member_id = request.GET.get('member_id')
        member = get_object_or_404(Member, id=member_id)

    if request.method == 'POST':
        weight = request.POST.get('weight_kg')
        body_fat = request.POST.get('body_fat') or None
        chest = request.POST.get('chest') or None
        waist = request.POST.get('waist') or None
        arms = request.POST.get('arms') or None
        notes = request.POST.get('notes', '').strip()

        MemberProgress.objects.create(
            member=member,
            weight_kg=float(weight),
            body_fat_percentage=float(body_fat) if body_fat else None,
            chest_cm=float(chest) if chest else None,
            waist_cm=float(waist) if waist else None,
            arms_cm=float(arms) if arms else None,
            notes=notes
        )
        messages.success(request, "Fitness progress metric logged!")
        return redirect('members:member_detail', pk=member.pk)

    logs = member.progress_logs.all()[:15]
    return render(request, 'fitness/progress_log.html', {'member': member, 'logs': logs})


class WorkoutPlanViewSet(viewsets.ModelViewSet):
    serializer_class = WorkoutPlanSerializer
    permission_classes = [IsStaffOrAdminUser]

    def get_queryset(self):
        return FitnessService.get_scoped_workouts(self.request.user)


class DietPlanViewSet(viewsets.ModelViewSet):
    serializer_class = DietPlanSerializer
    permission_classes = [IsStaffOrAdminUser]

    def get_queryset(self):
        return FitnessService.get_scoped_diets(self.request.user)
