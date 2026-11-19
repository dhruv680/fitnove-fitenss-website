import json
import datetime
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.utils.text import slugify
from django.http import JsonResponse
from apps.accounts.permissions import admin_only, staff_or_admin
from apps.accounts.models import GymOrganization, GymBranch, User
from apps.members.models import Member
from apps.memberships.models import Membership, MembershipPlan
from apps.attendance.models import Attendance
from apps.payments.models import Payment, Invoice, Expense
from apps.trainers.models import Trainer
from apps.classes.models import FitnessClass
from apps.crm.models import Lead
from apps.notifications.models import Notification
from .services import DashboardService

def dashboard_index(request):
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    user = request.user

    # If the user is a gym member, redirect to member dashboard
    if user.is_member:
        member = getattr(user, 'member_profile', None)
        if not member:
            messages.warning(request, "Your member profile is being configured.")
            return render(request, 'dashboard/member_dashboard.html', {'member': None})
        
        attendances = member.attendances.order_by('-date')[:7]
        active_sub = member.current_membership
        workout = member.workout_plans.filter(is_active=True).first()
        diet = member.diet_plans.filter(is_active=True).first()

        return render(request, 'dashboard/member_dashboard.html', {
            'member': member,
            'attendances': attendances,
            'active_sub': active_sub,
            'workout': workout,
            'diet': diet
        })

    # If the user is a trainer, render Trainer dashboard
    if user.is_trainer:
        trainer = getattr(user, 'trainer_profile', None)
        assigned_members = trainer.assigned_members.all() if trainer else []
        classes = trainer.classes.filter(is_active=True) if trainer else []
        workouts = trainer.created_workout_plans.all()[:5] if trainer else []
        return render(request, 'dashboard/trainer_dashboard.html', {
            'trainer': trainer,
            'assigned_members': assigned_members,
            'classes': classes,
            'workouts': workouts
        })

    # Executive SaaS Dashboard (Super Admin, Gym Admin, Staff)
    data = DashboardService.get_dashboard_metrics(user)
    
    # JSON-encoded data for Chart.js
    chart_data = {
        'revenue_labels': data['revenue_labels'],
        'revenue_values': data['revenue_values'],
        'weekly_att_labels': data['weekly_att_labels'],
        'weekly_att_values': data['weekly_att_values'],
        'plan_labels': data['plan_labels'],
        'plan_counts': data['plan_counts'],
        'growth_labels': data['growth_labels'],
        'growth_values': data['growth_values'],
        'method_labels': data['method_labels'],
        'method_counts': data['method_counts'],
    }

    context = {
        **data,
        'chart_data_json': json.dumps(chart_data)
    }
    return render(request, 'dashboard/index.html', context)


@login_required
def global_search(request):
    query = request.GET.get('q', '').strip()
    org = request.user.organization

    members = []
    trainers = []
    plans = []
    invoices = []
    leads = []

    if query and len(query) >= 2:
        members_qs = Member.objects.all()
        trainers_qs = Trainer.objects.all()
        plans_qs = MembershipPlan.objects.all()
        invoices_qs = Invoice.objects.all()
        leads_qs = Lead.objects.all()

        if not request.user.is_super_admin:
            members_qs = members_qs.filter(organization=org)
            trainers_qs = trainers_qs.filter(organization=org)
            plans_qs = plans_qs.filter(organization=org)
            invoices_qs = invoices_qs.filter(payment__organization=org)
            leads_qs = leads_qs.filter(organization=org)

        members = members_qs.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__email__icontains=query) |
            Q(member_id__icontains=query) |
            Q(user__phone__icontains=query)
        )[:6]

        trainers = trainers_qs.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(specialization__icontains=query) |
            Q(employee_id__icontains=query)
        )[:5]

        plans = plans_qs.filter(name__icontains=query)[:5]

        invoices = invoices_qs.filter(
            Q(invoice_number__icontains=query) |
            Q(payment__member__user__first_name__icontains=query) |
            Q(payment__member__user__last_name__icontains=query)
        )[:5]

        leads = leads_qs.filter(
            Q(full_name__icontains=query) |
            Q(phone__icontains=query)
        )[:5]

    return render(request, 'dashboard/search_results.html', {
        'query': query,
        'members': members,
        'trainers': trainers,
        'plans': plans,
        'invoices': invoices,
        'leads': leads,
        'total_results': len(members) + len(trainers) + len(plans) + len(invoices) + len(leads)
    })


@login_required
@staff_or_admin
def reports_analytics(request):
    org = request.user.organization
    today = timezone.now().date()
    first_day_year = today.replace(month=1, day=1)

    payments_qs = Payment.objects.filter(status=Payment.Status.COMPLETED)
    expenses_qs = Expense.objects.all()
    attendance_qs = Attendance.objects.all()
    members_qs = Member.objects.all()

    if not request.user.is_super_admin:
        payments_qs = payments_qs.filter(organization=org)
        expenses_qs = expenses_qs.filter(organization=org)
        attendance_qs = attendance_qs.filter(member__organization=org)
        members_qs = members_qs.filter(organization=org)

    total_revenue = payments_qs.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
    total_expenses = expenses_qs.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    net_profit = total_revenue - total_expenses

    total_visits = attendance_qs.count()
    total_members = members_qs.count()
    retention_rate = round((members_qs.filter(status='ACTIVE').count() / max(1, total_members)) * 100, 1)

    # Monthly financial breakdown (last 6 months)
    monthly_financials = []
    for i in range(5, -1, -1):
        target = today - datetime.timedelta(days=i*30)
        m_start = target.replace(day=1)
        if m_start.month == 12:
            m_end = m_start.replace(year=m_start.year + 1, month=1, day=1)
        else:
            m_end = m_start.replace(month=m_start.month + 1, day=1)

        m_rev = payments_qs.filter(payment_date__date__gte=m_start, payment_date__date__lt=m_end).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
        m_exp = expenses_qs.filter(date__gte=m_start, date__lt=m_end).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        m_net = m_rev - m_exp

        monthly_financials.append({
            'month': m_start.strftime('%B %Y'),
            'revenue': m_rev,
            'expenses': m_exp,
            'net': m_net
        })

    return render(request, 'dashboard/reports.html', {
        'total_revenue': total_revenue,
        'total_expenses': total_expenses,
        'net_profit': net_profit,
        'total_visits': total_visits,
        'retention_rate': retention_rate,
        'monthly_financials': monthly_financials,
        'currency': org.currency if org else '$'
    })


@login_required
@admin_only
def settings_view(request):
    org = getattr(request.user, 'organization', None)
    if not org:
        org = GymOrganization.objects.first()
        if not org:
            org = GymOrganization.objects.create(
                name='FitNova Elite Fitness',
                slug='fitnova-metro',
                email='contact@fitnova.com',
                phone='+1 (555) 749-2000',
                website='https://fitnova.fitness',
                tax_id='GST-US-99824',
                currency='$',
                is_active=True
            )
        if request.user.organization != org:
            request.user.organization = org
            request.user.save(update_fields=['organization'])

    branch = getattr(request.user, 'branch', None)
    if not branch and org:
        branch = org.branches.filter(is_main_branch=True).first() or org.branches.first()
        if branch and request.user.branch != branch:
            request.user.branch = branch
            request.user.save(update_fields=['branch'])

    if request.method == 'POST':
        # Update Organization settings
        org.name = request.POST.get('org_name', org.name).strip()
        org.email = request.POST.get('org_email', org.email).strip()
        org.phone = request.POST.get('org_phone', org.phone).strip()
        org.website = request.POST.get('org_website', org.website).strip()
        org.tax_id = request.POST.get('tax_id', org.tax_id).strip()
        org.currency = request.POST.get('currency', org.currency).strip()
        if 'logo' in request.FILES:
            org.logo = request.FILES['logo']
        org.save()
        messages.success(request, "Organization profile updated successfully in PostgreSQL database!")
        return redirect('dashboard:settings')

    branches = org.branches.all().order_by('-is_main_branch', 'name')
    return render(request, 'dashboard/settings.html', {
        'org': org,
        'branch': branch,
        'branches': branches,
        'total_branches_count': branches.count(),
        'active_branches_count': branches.filter(is_active=True).count(),
    })


@login_required
@admin_only
def branch_create_view(request):
    if request.method != 'POST':
        return redirect('dashboard:settings')

    org = getattr(request.user, 'organization', None) or GymOrganization.objects.first()
    if not org:
        messages.error(request, "Gym Organization record not found. Please save organization profile first.")
        return redirect('dashboard:settings')

    name = request.POST.get('name', '').strip()
    code = request.POST.get('code', '').strip().upper()
    address = request.POST.get('address', '').strip()
    city = request.POST.get('city', '').strip()
    state = request.POST.get('state', '').strip()
    zip_code = request.POST.get('zip_code', '').strip()
    phone = request.POST.get('phone', '').strip()
    email = request.POST.get('email', '').strip()
    manager_name = request.POST.get('manager_name', '').strip()
    is_main_branch = request.POST.get('is_main_branch') in ('on', 'true', '1')
    is_active = request.POST.get('is_active', 'on') in ('on', 'true', '1')

    if not name or not address or not city:
        messages.error(request, "Branch Name, Address, and City are required fields.")
        return redirect('dashboard:settings')

    # Auto-generate unique branch code if blank
    if not code:
        city_slug = slugify(city[:3]).upper() if city else 'BR'
        code = f"FN-{city_slug}-{org.branches.count() + 1:02d}"

    orig_code = code
    counter = 1
    while GymBranch.objects.filter(code=code).exists():
        code = f"{orig_code}-{counter}"
        counter += 1

    # If new branch is designated as main branch, unmark existing main branches
    if is_main_branch:
        org.branches.filter(is_main_branch=True).update(is_main_branch=False)

    branch = GymBranch.objects.create(
        organization=org,
        name=name,
        code=code,
        address=address,
        city=city,
        state=state or 'NY',
        zip_code=zip_code or '10001',
        phone=phone or org.phone or '+1 (555) 000-0000',
        email=email or org.email or 'branch@fitnova.com',
        manager_name=manager_name,
        is_main_branch=is_main_branch or (org.branches.count() == 0),
        is_active=is_active
    )

    if not request.user.branch:
        request.user.branch = branch
        request.user.save(update_fields=['branch'])

    messages.success(request, f"New Gym Branch '{branch.name}' ({branch.code}) successfully created in PostgreSQL database!")
    return redirect('dashboard:settings')


@login_required
@admin_only
def branch_update_view(request, branch_id):
    if request.method != 'POST':
        return redirect('dashboard:settings')

    org = getattr(request.user, 'organization', None) or GymOrganization.objects.first()
    branch = get_object_or_404(GymBranch, id=branch_id, organization=org)

    name = request.POST.get('name', branch.name).strip()
    code = request.POST.get('code', branch.code).strip().upper()
    address = request.POST.get('address', branch.address).strip()
    city = request.POST.get('city', branch.city).strip()
    state = request.POST.get('state', branch.state).strip()
    zip_code = request.POST.get('zip_code', branch.zip_code).strip()
    phone = request.POST.get('phone', branch.phone).strip()
    email = request.POST.get('email', branch.email).strip()
    manager_name = request.POST.get('manager_name', branch.manager_name).strip()
    is_main_branch = request.POST.get('is_main_branch') in ('on', 'true', '1')
    is_active = request.POST.get('is_active') in ('on', 'true', '1')

    if not name or not address or not city:
        messages.error(request, "Branch Name, Address, and City are required fields.")
        return redirect('dashboard:settings')

    # Code uniqueness verification excluding self
    if code != branch.code and GymBranch.objects.filter(code=code).exclude(id=branch.id).exists():
        messages.error(request, f"Branch Code '{code}' is already assigned to another location.")
        return redirect('dashboard:settings')

    if is_main_branch and not branch.is_main_branch:
        org.branches.filter(is_main_branch=True).exclude(id=branch.id).update(is_main_branch=False)

    branch.name = name
    branch.code = code
    branch.address = address
    branch.city = city
    branch.state = state
    branch.zip_code = zip_code
    branch.phone = phone
    branch.email = email
    branch.manager_name = manager_name
    branch.is_main_branch = is_main_branch
    branch.is_active = is_active
    branch.save()

    messages.success(request, f"Branch '{branch.name}' ({branch.code}) updated successfully in PostgreSQL database!")
    return redirect('dashboard:settings')


@login_required
@admin_only
def branch_delete_view(request, branch_id):
    if request.method != 'POST':
        return redirect('dashboard:settings')

    org = getattr(request.user, 'organization', None) or GymOrganization.objects.first()
    branch = get_object_or_404(GymBranch, id=branch_id, organization=org)

    # Protect against deleting the only remaining branch
    if org.branches.count() <= 1:
        messages.error(request, "Cannot delete the sole operating branch. Add another location first.")
        return redirect('dashboard:settings')

    branch_name = branch.name
    branch_code = branch.code
    was_main = branch.is_main_branch

    # Reassign users and members to a fallback branch to prevent data loss
    fallback_branch = org.branches.exclude(id=branch.id).first()
    if request.user.branch_id == branch.id:
        request.user.branch = fallback_branch
        request.user.save(update_fields=['branch'])

    branch.members.all().update(branch=fallback_branch)
    branch.branch_users.all().update(branch=fallback_branch)

    branch.delete()

    if was_main and fallback_branch:
        fallback_branch.is_main_branch = True
        fallback_branch.save(update_fields=['is_main_branch'])

    messages.success(request, f"Gym Branch '{branch_name}' ({branch_code}) safely removed from PostgreSQL database.")
    return redirect('dashboard:settings')


@login_required
@admin_only
def branch_toggle_status_view(request, branch_id):
    if request.method != 'POST':
        return redirect('dashboard:settings')

    org = getattr(request.user, 'organization', None) or GymOrganization.objects.first()
    branch = get_object_or_404(GymBranch, id=branch_id, organization=org)
    branch.is_active = not branch.is_active
    branch.save(update_fields=['is_active'])

    status_str = "activated" if branch.is_active else "deactivated"
    messages.success(request, f"Gym Branch '{branch.name}' has been {status_str} in PostgreSQL database.")
    return redirect('dashboard:settings')



def about_view(request):
    org = getattr(request.user, 'organization', None) if request.user.is_authenticated else None
    if not org:
        org = GymOrganization.objects.first()

    trainers = Trainer.objects.filter(status='ACTIVE')
    if org:
        trainers = trainers.filter(organization=org)

    classes_count = FitnessClass.objects.filter(is_active=True).count()
    members_count = Member.objects.filter(status='ACTIVE').count()

    return render(request, 'dashboard/about.html', {
        'org': org,
        'trainers': trainers[:4],
        'classes_count': classes_count or 12,
        'members_count': members_count or 250,
    })


def services_view(request):
    org = getattr(request.user, 'organization', None) if request.user.is_authenticated else None
    if not org:
        org = GymOrganization.objects.first()

    plans = MembershipPlan.objects.filter(is_active=True)
    if org:
        plans = plans.filter(organization=org)

    classes = FitnessClass.objects.filter(is_active=True).select_related('trainer')
    if org:
        classes = classes.filter(organization=org)

    return render(request, 'dashboard/services.html', {
        'org': org,
        'plans': plans,
        'classes': classes[:6],
    })


def contact_view(request):
    org = getattr(request.user, 'organization', None) if request.user.is_authenticated else None
    if not org:
        org = GymOrganization.objects.first()
    branch = getattr(request.user, 'branch', None) if request.user.is_authenticated else None
    if not branch and org:
        branch = org.branches.first()

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        subject = request.POST.get('subject', 'General Inquiry').strip()
        message = request.POST.get('message', '').strip()

        if not name or not email or not message:
            messages.error(request, "Please fill in your name, email address, and message.")
            return render(request, 'dashboard/contact.html', {
                'org': org,
                'branch': branch,
                'form_data': request.POST
            })

        try:
            lead = Lead.objects.create(
                organization=org,
                branch=branch,
                full_name=name,
                email=email,
                phone=phone or 'N/A',
                source=Lead.Source.WEBSITE,
                interest=subject or 'General Inquiry',
                status=Lead.Status.NEW,
                notes=f"[Website Contact Form]\nSubject: {subject}\nMessage: {message}"
            )

            admin_users = User.objects.filter(role__in=[User.Role.SUPER_ADMIN, User.Role.GYM_ADMIN])
            if org:
                admin_users = admin_users.filter(organization=org)
            for admin_u in admin_users:
                Notification.objects.create(
                    recipient=admin_u,
                    title=f"New Contact Inquiry: {name}",
                    message=f"{name} ({email}) asked about '{subject}'. Check CRM pipeline.",
                    notification_type=Notification.NotificationType.INFO,
                    action_url='/crm/'
                )

            messages.success(request, f"Thank you, {name}! Your message has been sent successfully. Our team will contact you shortly.")
            return redirect('dashboard:contact')
        except Exception as e:
            messages.error(request, f"Could not submit inquiry: {str(e)}")

    return render(request, 'dashboard/contact.html', {
        'org': org,
        'branch': branch
    })


def apply_view(request):
    org = getattr(request.user, 'organization', None) if request.user.is_authenticated else None
    if not org:
        org = GymOrganization.objects.first()
    branch = getattr(request.user, 'branch', None) if request.user.is_authenticated else None
    if not branch and org:
        branch = org.branches.first()

    plans = MembershipPlan.objects.filter(is_active=True)
    if org:
        plans = plans.filter(organization=org)

    preselected_plan_id = request.GET.get('plan')

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        gender = request.POST.get('gender', 'OTHER')
        dob = request.POST.get('date_of_birth') or None
        plan_id = request.POST.get('plan_id')
        fitness_goals = request.POST.get('fitness_goals', '').strip()
        emergency_name = request.POST.get('emergency_name', '').strip()
        emergency_phone = request.POST.get('emergency_phone', '').strip()
        medical_history = request.POST.get('medical_history', '').strip()

        if not full_name or not email or not phone:
            messages.error(request, "Full name, email address, and phone number are required to submit an application.")
            return render(request, 'dashboard/apply.html', {
                'org': org,
                'plans': plans,
                'preselected_plan_id': plan_id or preselected_plan_id,
                'form_data': request.POST
            })

        chosen_plan = plans.filter(id=plan_id).first() if plan_id else None
        plan_name = chosen_plan.name if chosen_plan else "General Membership"

        try:
            lead = Lead.objects.create(
                organization=org,
                branch=branch,
                full_name=full_name,
                email=email,
                phone=phone,
                source=Lead.Source.WEBSITE,
                interest=f"Membership: {plan_name}",
                status=Lead.Status.NEW,
                notes=(
                    f"[Official Membership Application]\n"
                    f"Selected Plan: {plan_name}\n"
                    f"Gender: {gender} | DOB: {dob}\n"
                    f"Fitness Goals: {fitness_goals}\n"
                    f"Emergency: {emergency_name} ({emergency_phone})\n"
                    f"Medical: {medical_history or 'None reported'}"
                )
            )

            admin_users = User.objects.filter(role__in=[User.Role.SUPER_ADMIN, User.Role.GYM_ADMIN])
            if org:
                admin_users = admin_users.filter(organization=org)
            for admin_u in admin_users:
                Notification.objects.create(
                    recipient=admin_u,
                    title=f"Membership Application: {full_name}",
                    message=f"{full_name} submitted a membership application for {plan_name}. Phone: {phone}",
                    notification_type=Notification.NotificationType.SUCCESS,
                    action_url='/crm/'
                )

            return render(request, 'dashboard/apply.html', {
                'org': org,
                'plans': plans,
                'success': True,
                'applicant_name': full_name,
                'plan_name': plan_name,
                'application_id': f"APP-{lead.id:05d}"
            })
        except Exception as e:
            messages.error(request, f"Error submitting membership application: {str(e)}")

    return render(request, 'dashboard/apply.html', {
        'org': org,
        'plans': plans,
        'preselected_plan_id': preselected_plan_id
    })


def help_center_view(request):
    org = getattr(request.user, 'organization', None) if request.user.is_authenticated else None
    if not org:
        org = GymOrganization.objects.first()
    return render(request, 'dashboard/help_center.html', {'org': org})


def privacy_policy_view(request):
    org = getattr(request.user, 'organization', None) if request.user.is_authenticated else None
    if not org:
        org = GymOrganization.objects.first()
    return render(request, 'dashboard/privacy_policy.html', {'org': org})


def terms_conditions_view(request):
    org = getattr(request.user, 'organization', None) if request.user.is_authenticated else None
    if not org:
        org = GymOrganization.objects.first()
    return render(request, 'dashboard/terms_conditions.html', {'org': org})

