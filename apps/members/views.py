from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.utils import timezone
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
    all_scoped = MemberService.get_scoped_members(request.user)

    # Global KPI counts across all roster (unfiltered)
    total_roster = all_scoped.count()
    active_roster = all_scoped.filter(status='ACTIVE').count()
    expired_roster = all_scoped.filter(status='EXPIRED').count()
    pending_roster = all_scoped.filter(status='PENDING').count()

    # Real data percentage metrics
    active_pct = round((active_roster / total_roster * 100), 1) if total_roster > 0 else 0
    expired_pct = round((expired_roster / total_roster * 100), 1) if total_roster > 0 else 0
    pending_pct = round((pending_roster / total_roster * 100), 1) if total_roster > 0 else 0

    # New enrollments this calendar month
    month_start = timezone.now().date().replace(day=1)
    new_this_month = all_scoped.filter(joined_date__gte=month_start).count()

    members = all_scoped
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    plan_filter = request.GET.get('plan', '').strip()
    sort_by = request.GET.get('sort', 'newest').strip()

    if search_query:
        terms = search_query.split()
        q_obj = (
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__phone__icontains=search_query) |
            Q(member_id__icontains=search_query)
        )
        if len(terms) > 1:
            q_obj |= (Q(user__first_name__icontains=terms[0]) & Q(user__last_name__icontains=terms[-1]))
        members = members.filter(q_obj)

    if status_filter:
        members = members.filter(status=status_filter)

    if plan_filter:
        members = members.filter(memberships__plan_id=plan_filter, memberships__status='ACTIVE')

    # Sorting options
    if sort_by == 'name_asc':
        members = members.order_by('user__first_name', 'user__last_name')
    elif sort_by == 'name_desc':
        members = members.order_by('-user__first_name', '-user__last_name')
    elif sort_by == 'joined_asc':
        members = members.order_by('joined_date', 'id')
    else:  # newest default
        members = members.order_by('-joined_date', '-id')

    total_filtered = members.count()

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
        'sort_by': sort_by,
        'plans': plans,
        'total_filtered': total_filtered,
        'total_roster': total_roster,
        'active_roster': active_roster,
        'expired_roster': expired_roster,
        'pending_roster': pending_roster,
        'active_pct': active_pct,
        'expired_pct': expired_pct,
        'pending_pct': pending_pct,
        'new_this_month': new_this_month,
    })


@login_required
@staff_or_admin
def member_quick_view(request, pk):
    """Returns member profile, active plan, attendance & payment history for modal/drawer."""
    members = MemberService.get_scoped_members(request.user)
    member = get_object_or_404(members, pk=pk)

    recent_memberships = member.memberships.select_related('plan').order_by('-start_date')[:5]
    recent_payments = member.payments.select_related('membership__plan').order_by('-payment_date')[:5]
    recent_attendances = member.attendances.order_by('-date', '-check_in_time')[:5]

    curr_sub = member.current_membership
    curr_plan_data = None
    if curr_sub:
        curr_plan_data = {
            'id': curr_sub.id,
            'name': curr_sub.plan.name,
            'price': str(curr_sub.plan.price),
            'start_date': curr_sub.start_date.strftime('%b %d, %Y'),
            'end_date': curr_sub.end_date.strftime('%b %d, %Y'),
            'days_remaining': curr_sub.days_remaining,
            'is_active': curr_sub.is_currently_active,
            'status': curr_sub.status,
            'status_display': curr_sub.get_status_display(),
        }

    data = {
        'id': member.id,
        'member_id': member.member_id,
        'full_name': member.full_name,
        'first_name': member.user.first_name,
        'last_name': member.user.last_name,
        'initials': (member.user.first_name[:1] if member.user.first_name else member.user.username[:1]).upper(),
        'email': member.email,
        'phone': member.phone,
        'gender': member.user.get_gender_display() if hasattr(member.user, 'get_gender_display') else member.user.gender,
        'dob': member.user.date_of_birth.strftime('%b %d, %Y') if member.user.date_of_birth else '—',
        'address': member.user.address or '—',
        'blood_group': member.blood_group or '—',
        'emergency_name': member.emergency_contact_name or '—',
        'emergency_phone': member.emergency_contact_phone or '—',
        'medical_history': member.medical_history or 'None reported',
        'fitness_goals': member.fitness_goals or 'General fitness & strength',
        'status': member.status,
        'status_display': member.get_status_display(),
        'joined_date': member.joined_date.strftime('%b %d, %Y') if member.joined_date else '—',
        'branch_name': member.branch.name if member.branch else 'Main Facility',
        'trainer_name': member.assigned_trainer.full_name if member.assigned_trainer else 'None Assigned',
        'trainer_specialization': member.assigned_trainer.specialization if member.assigned_trainer else '',
        'qr_code_url': member.qr_code.url if member.qr_code else '',
        'currency': member.organization.currency if member.organization else '$',
        'current_plan': curr_plan_data,
        'memberships': [{
            'plan_name': m.plan.name,
            'start_date': m.start_date.strftime('%b %d, %Y'),
            'end_date': m.end_date.strftime('%b %d, %Y'),
            'status': m.status,
            'status_display': m.get_status_display(),
        } for m in recent_memberships],
        'payments': [{
            'transaction_id': p.transaction_id,
            'amount': str(p.total_amount),
            'method': p.get_payment_method_display(),
            'date': p.payment_date.strftime('%b %d, %Y'),
            'status': p.status,
            'status_display': p.get_status_display(),
        } for p in recent_payments],
        'attendances': [{
            'date': a.date.strftime('%b %d, %Y'),
            'check_in': a.check_in_time.strftime('%I:%M %p') if a.check_in_time else '—',
            'check_out': a.check_out_time.strftime('%I:%M %p') if a.check_out_time else '—',
            'status': a.status,
        } for a in recent_attendances],
        'urls': {
            'detail': reverse('members:member_detail', args=[member.id]),
            'edit': reverse('members:member_edit', args=[member.id]),
            'renew': reverse('memberships:membership_renew', args=[member.id]),
            'delete': reverse('members:member_delete', args=[member.id]),
        }
    }
    return JsonResponse(data)



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

