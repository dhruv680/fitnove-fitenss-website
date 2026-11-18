import json
import datetime
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
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
        return redirect('accounts:register')

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
    org = request.user.organization
    branch = request.user.branch

    if request.method == 'POST':
        if org:
            org.name = request.POST.get('org_name', org.name).strip()
            org.email = request.POST.get('org_email', org.email).strip()
            org.phone = request.POST.get('org_phone', org.phone).strip()
            org.website = request.POST.get('org_website', org.website).strip()
            org.tax_id = request.POST.get('tax_id', org.tax_id).strip()
            org.currency = request.POST.get('currency', org.currency).strip()
            if 'logo' in request.FILES:
                org.logo = request.FILES['logo']
            org.save()

        if branch:
            branch.name = request.POST.get('branch_name', branch.name).strip()
            branch.address = request.POST.get('branch_address', branch.address).strip()
            branch.city = request.POST.get('branch_city', branch.city).strip()
            branch.phone = request.POST.get('branch_phone', branch.phone).strip()
            branch.save()

        messages.success(request, "Organization and Gym Branch settings updated successfully!")
        return redirect('dashboard:settings')

    return render(request, 'dashboard/settings.html', {
        'org': org,
        'branch': branch
    })


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

