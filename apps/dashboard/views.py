import json
import datetime
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from apps.accounts.permissions import admin_only, staff_or_admin
from apps.accounts.models import GymOrganization, GymBranch
from apps.members.models import Member
from apps.memberships.models import Membership, MembershipPlan
from apps.attendance.models import Attendance
from apps.payments.models import Payment, Invoice, Expense
from apps.trainers.models import Trainer
from apps.crm.models import Lead
from .services import DashboardService

@login_required
def dashboard_index(request):
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
