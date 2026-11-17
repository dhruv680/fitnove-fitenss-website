from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from rest_framework import viewsets
from apps.accounts.permissions import staff_or_admin, IsStaffOrAdminUser
from .models import Trainer
from .services import TrainerService
from .serializers import TrainerSerializer

@login_required
@staff_or_admin
def trainer_list(request):
    trainers = TrainerService.get_scoped_trainers(request.user)

    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()

    if search_query:
        trainers = trainers.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(specialization__icontains=search_query) |
            Q(employee_id__icontains=search_query)
        )

    if status_filter:
        trainers = trainers.filter(status=status_filter)

    paginator = Paginator(trainers, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'trainers/trainer_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'total_trainers': trainers.count()
    })


@login_required
@staff_or_admin
def trainer_create(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        specialization = request.POST.get('specialization', '').strip()
        experience_years = request.POST.get('experience_years', '1')
        hourly_rate = request.POST.get('hourly_rate', '0.00')
        rating = request.POST.get('rating', '5.0')
        bio = request.POST.get('bio', '').strip()
        certifications = request.POST.get('certifications', '').strip()

        if not first_name or not last_name or not email:
            messages.error(request, "First name, last name, and email address are required.")
            return render(request, 'trainers/trainer_form.html', {'is_edit': False})

        try:
            exp_yrs = max(0, int(experience_years))
        except (ValueError, TypeError):
            exp_yrs = 1

        try:
            rate = max(0.0, float(hourly_rate))
        except (ValueError, TypeError):
            rate = 0.0

        try:
            rat = min(5.0, max(1.0, float(rating)))
        except (ValueError, TypeError):
            rat = 5.0

        try:
            trainer = TrainerService.create_trainer(
                organization=request.user.organization,
                branch=request.user.branch,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                specialization=specialization or 'General Fitness',
                experience_years=exp_yrs,
                hourly_rate=rate,
                rating=rat,
                bio=bio,
                certifications=certifications
            )
            messages.success(request, f"Trainer {trainer.full_name} onboarded successfully!")
            return redirect('trainers:trainer_detail', pk=trainer.pk)
        except Exception as e:
            messages.error(request, f"Error onboarding trainer: {str(e)}")

    return render(request, 'trainers/trainer_form.html', {'is_edit': False})


@login_required
def trainer_detail(request, pk):
    trainers = TrainerService.get_scoped_trainers(request.user)
    trainer = get_object_or_404(trainers, pk=pk)
    assigned_members = trainer.assigned_members.select_related('user').all()

    return render(request, 'trainers/trainer_detail.html', {
        'trainer': trainer,
        'assigned_members': assigned_members
    })


@login_required
@staff_or_admin
def trainer_edit(request, pk):
    trainers = TrainerService.get_scoped_trainers(request.user)
    trainer = get_object_or_404(trainers, pk=pk)

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()

        if first_name:
            trainer.user.first_name = first_name
        if last_name:
            trainer.user.last_name = last_name
        if phone:
            trainer.user.phone = phone
        trainer.user.save()

        specialization = request.POST.get('specialization', '').strip()
        if specialization:
            trainer.specialization = specialization

        try:
            trainer.experience_years = max(0, int(request.POST.get('experience_years', trainer.experience_years)))
        except (ValueError, TypeError):
            pass

        try:
            trainer.hourly_rate = max(0.0, float(request.POST.get('hourly_rate', trainer.hourly_rate)))
        except (ValueError, TypeError):
            pass

        if request.POST.get('rating'):
            try:
                trainer.rating = min(5.0, max(1.0, float(request.POST.get('rating'))))
            except (ValueError, TypeError):
                pass

        new_status = request.POST.get('status')
        if new_status in Trainer.Status.values:
            trainer.status = new_status

        trainer.bio = request.POST.get('bio', '').strip()
        trainer.certifications = request.POST.get('certifications', '').strip()
        trainer.save()

        messages.success(request, f"Trainer {trainer.full_name} updated successfully.")
        return redirect('trainers:trainer_detail', pk=trainer.pk)

    return render(request, 'trainers/trainer_form.html', {
        'trainer': trainer,
        'is_edit': True
    })


class TrainerViewSet(viewsets.ModelViewSet):
    serializer_class = TrainerSerializer
    permission_classes = [IsStaffOrAdminUser]

    def get_queryset(self):
        return TrainerService.get_scoped_trainers(self.request.user)

