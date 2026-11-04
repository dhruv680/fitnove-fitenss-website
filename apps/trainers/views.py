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
        bio = request.POST.get('bio', '').strip()
        certifications = request.POST.get('certifications', '').strip()

        try:
            trainer = TrainerService.create_trainer(
                organization=request.user.organization,
                branch=request.user.branch,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                specialization=specialization,
                experience_years=int(experience_years),
                hourly_rate=float(hourly_rate),
                bio=bio,
                certifications=certifications
            )
            messages.success(request, f"Trainer {trainer.full_name} created successfully!")
            return redirect('trainers:trainer_detail', pk=trainer.pk)
        except Exception as e:
            messages.error(request, f"Error creating trainer: {str(e)}")

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
        trainer.user.first_name = request.POST.get('first_name', '').strip()
        trainer.user.last_name = request.POST.get('last_name', '').strip()
        trainer.user.phone = request.POST.get('phone', '').strip()
        trainer.user.save()

        trainer.specialization = request.POST.get('specialization', '').strip()
        trainer.experience_years = int(request.POST.get('experience_years', '1'))
        trainer.hourly_rate = float(request.POST.get('hourly_rate', '0.00'))
        trainer.status = request.POST.get('status', trainer.status)
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

