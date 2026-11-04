from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from rest_framework import viewsets
from apps.accounts.permissions import staff_or_admin, IsStaffOrAdminUser
from apps.trainers.models import Trainer
from apps.memberships.models import MembershipPlan
from apps.memberships.services import MembershipService
from .models import Member
from .services import MemberService
from .serializers import MemberSerializer

@login_required
@staff_or_admin
def member_list(request):
    members = MemberService.get_scoped_members(request.user)

    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    plan_filter = request.GET.get('plan', '').strip()

    if search_query:
        members = members.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__phone__icontains=search_query) |
            Q(member_id__icontains=search_query)
        )

    if status_filter:
        members = members.filter(status=status_filter)

    if plan_filter:
        members = members.filter(memberships__plan_id=plan_filter, memberships__status='ACTIVE')

    paginator = Paginator(members, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    plans = MembershipPlan.objects.filter(is_active=True)
    if not request.user.is_super_admin:
        plans = plans.filter(organization=request.user.organization)

    return render(request, 'members/member_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'plan_filter': plan_filter,
        'plans': plans,
        'total_members': members.count(),
        'active_count': members.filter(status='ACTIVE').count(),
        'expired_count': members.filter(status='EXPIRED').count(),
    })


@login_required
@staff_or_admin
def member_create(request):
    organization = request.user.organization
    branch = request.user.branch

    trainers = Trainer.objects.filter(status='ACTIVE')
    plans = MembershipPlan.objects.filter(is_active=True)
    if not request.user.is_super_admin:
        trainers = trainers.filter(organization=organization)
        plans = plans.filter(organization=organization)

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        gender = request.POST.get('gender', 'MALE')
        dob = request.POST.get('dob') or None
        blood_group = request.POST.get('blood_group', '').strip()
        emergency_name = request.POST.get('emergency_name', '').strip()
        emergency_phone = request.POST.get('emergency_phone', '').strip()
        medical_history = request.POST.get('medical_history', '').strip()
        fitness_goals = request.POST.get('fitness_goals', '').strip()
        address = request.POST.get('address', '').strip()
        trainer_id = request.POST.get('trainer')
        plan_id = request.POST.get('plan')

        # Validation
        if not first_name or not last_name or not email or not phone:
            messages.error(request, 'First name, last name, email, and phone are required.')
            return render(request, 'members/member_form.html', {'trainers': trainers, 'plans': plans, 'is_edit': False})

        assigned_trainer = None
        if trainer_id:
            assigned_trainer = trainers.filter(id=trainer_id).first()

        try:
            member = MemberService.create_member(
                organization=organization,
                branch=branch,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                gender=gender,
                dob=dob,
                address=address,
                blood_group=blood_group,
                emergency_name=emergency_name,
                emergency_phone=emergency_phone,
                medical_history=medical_history,
                fitness_goals=fitness_goals,
                assigned_trainer=assigned_trainer
            )

            # Assign membership plan if chosen
            if plan_id:
                plan = plans.filter(id=plan_id).first()
                if plan:
                    MembershipService.assign_membership(member=member, plan=plan)

            messages.success(request, f"Member {member.full_name} ({member.member_id}) registered successfully!")
            return redirect('members:member_detail', pk=member.pk)
        except Exception as e:
            messages.error(request, f"Error registering member: {str(e)}")

    return render(request, 'members/member_form.html', {
        'trainers': trainers,
        'plans': plans,
        'is_edit': False
    })


@login_required
def member_detail(request, pk):
    members = MemberService.get_scoped_members(request.user)
    # If the user is a member, they can only view their own profile
    if request.user.is_member:
        member = get_object_or_404(members, user=request.user)
    else:
        member = get_object_or_404(members, pk=pk)

    subscriptions = member.memberships.select_related('plan').order_by('-start_date')
    attendances = member.attendances.order_by('-date')[:15]
    payments = member.payments.select_related('membership__plan').order_by('-payment_date')[:10]
    progress_logs = member.progress_logs.order_by('-date')[:5]

    return render(request, 'members/member_detail.html', {
        'member': member,
        'subscriptions': subscriptions,
        'attendances': attendances,
        'payments': payments,
        'progress_logs': progress_logs
    })


@login_required
@staff_or_admin
def member_edit(request, pk):
    members = MemberService.get_scoped_members(request.user)
    member = get_object_or_404(members, pk=pk)

    trainers = Trainer.objects.filter(status='ACTIVE')
    if not request.user.is_super_admin:
        trainers = trainers.filter(organization=request.user.organization)

    if request.method == 'POST':
        member.user.first_name = request.POST.get('first_name', '').strip()
        member.user.last_name = request.POST.get('last_name', '').strip()
        member.user.phone = request.POST.get('phone', '').strip()
        member.user.gender = request.POST.get('gender', member.user.gender)
        dob = request.POST.get('dob')
        if dob:
            member.user.date_of_birth = dob
        member.user.address = request.POST.get('address', '').strip()
        member.user.save()

        member.emergency_contact_name = request.POST.get('emergency_name', '').strip()
        member.emergency_contact_phone = request.POST.get('emergency_phone', '').strip()
        member.blood_group = request.POST.get('blood_group', '').strip()
        member.medical_history = request.POST.get('medical_history', '').strip()
        member.fitness_goals = request.POST.get('fitness_goals', '').strip()
        member.status = request.POST.get('status', member.status)

        trainer_id = request.POST.get('trainer')
        member.assigned_trainer = trainers.filter(id=trainer_id).first() if trainer_id else None

        member.save()
        messages.success(request, f"Member {member.full_name} updated successfully.")
        return redirect('members:member_detail', pk=member.pk)

    return render(request, 'members/member_form.html', {
        'member': member,
        'trainers': trainers,
        'is_edit': True
    })


@login_required
@staff_or_admin
def member_delete(request, pk):
    members = MemberService.get_scoped_members(request.user)
    member = get_object_or_404(members, pk=pk)

    if request.method == 'POST':
        name = member.full_name
        user_to_delete = member.user
        member.delete()
        user_to_delete.delete()
        messages.success(request, f"Member {name} was permanently removed.")
        return redirect('members:member_list')

    return render(request, 'members/member_confirm_delete.html', {'member': member})


# DRF ViewSet
class MemberViewSet(viewsets.ModelViewSet):
    serializer_class = MemberSerializer
    permission_classes = [IsStaffOrAdminUser]

    def get_queryset(self):
        return MemberService.get_scoped_members(self.request.user)

