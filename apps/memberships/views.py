from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.text import slugify
from rest_framework import viewsets
from apps.accounts.permissions import staff_or_admin, IsStaffOrAdminUser
from apps.members.models import Member
from .models import MembershipPlan, Membership
from .services import MembershipService
from .serializers import MembershipPlanSerializer, MembershipSerializer

@login_required
@staff_or_admin
def plan_list(request):
    plans = MembershipService.get_scoped_plans(request.user)
    return render(request, 'memberships/plan_list.html', {
        'plans': plans
    })


@login_required
@staff_or_admin
def plan_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        duration_type = request.POST.get('duration_type', 'MONTHLY')
        duration_days = request.POST.get('duration_days', '30')
        price = request.POST.get('price', '0.00')
        signup_fee = request.POST.get('signup_fee', '0.00')
        features = request.POST.get('features', '').strip()
        has_trainer_included = bool(request.POST.get('has_trainer_included'))
        has_locker_included = bool(request.POST.get('has_locker_included'))
        has_classes_included = bool(request.POST.get('has_classes_included'))
        is_popular = bool(request.POST.get('is_popular'))

        slug = slugify(name)
        base_slug = slug
        count = 1
        while MembershipPlan.objects.filter(organization=request.user.organization, slug=slug).exists():
            slug = f"{base_slug}-{count}"
            count += 1

        plan = MembershipPlan.objects.create(
            organization=request.user.organization,
            name=name,
            slug=slug,
            duration_type=duration_type,
            duration_days=int(duration_days),
            price=float(price),
            signup_fee=float(signup_fee),
            features=features,
            has_trainer_included=has_trainer_included,
            has_locker_included=has_locker_included,
            has_classes_included=has_classes_included,
            is_popular=is_popular
        )
        messages.success(request, f"Membership plan '{plan.name}' created successfully!")
        return redirect('memberships:plan_list')

    return render(request, 'memberships/plan_form.html', {'is_edit': False})


@login_required
@staff_or_admin
def plan_edit(request, pk):
    plans = MembershipService.get_scoped_plans(request.user)
    plan = get_object_or_404(plans, pk=pk)

    if request.method == 'POST':
        plan.name = request.POST.get('name', plan.name).strip()
        plan.duration_type = request.POST.get('duration_type', plan.duration_type)
        plan.duration_days = int(request.POST.get('duration_days', plan.duration_days))
        plan.price = float(request.POST.get('price', plan.price))
        plan.signup_fee = float(request.POST.get('signup_fee', plan.signup_fee))
        plan.features = request.POST.get('features', plan.features).strip()
        plan.has_trainer_included = bool(request.POST.get('has_trainer_included'))
        plan.has_locker_included = bool(request.POST.get('has_locker_included'))
        plan.has_classes_included = bool(request.POST.get('has_classes_included'))
        plan.is_popular = bool(request.POST.get('is_popular'))
        plan.is_active = bool(request.POST.get('is_active'))
        plan.save()

        messages.success(request, f"Membership plan '{plan.name}' updated successfully.")
        return redirect('memberships:plan_list')

    return render(request, 'memberships/plan_form.html', {'plan': plan, 'is_edit': True})


@login_required
@staff_or_admin
def membership_renew(request, member_id):
    if not request.user.is_super_admin:
        member = get_object_or_404(Member, pk=member_id, organization=request.user.organization)
    else:
        member = get_object_or_404(Member, pk=member_id)

    plans = MembershipPlan.objects.filter(organization=member.organization, is_active=True)

    if request.method == 'POST':
        plan_id = request.POST.get('plan_id')
        plan = get_object_or_404(plans, pk=plan_id)
        notes = request.POST.get('notes', 'Membership renewal')

        membership = MembershipService.renew_membership(member=member, plan=plan, notes=notes)
        messages.success(request, f"Membership for {member.full_name} renewed until {membership.end_date}!")
        return redirect('members:member_detail', pk=member.pk)

    return render(request, 'memberships/membership_renew.html', {
        'member': member,
        'plans': plans
    })


# DRF ViewSets
class MembershipPlanViewSet(viewsets.ModelViewSet):
    serializer_class = MembershipPlanSerializer
    permission_classes = [IsStaffOrAdminUser]

    def get_queryset(self):
        return MembershipService.get_scoped_plans(self.request.user)


class MembershipViewSet(viewsets.ModelViewSet):
    serializer_class = MembershipSerializer
    permission_classes = [IsStaffOrAdminUser]

    def get_queryset(self):
        return MembershipService.get_scoped_memberships(self.request.user)

