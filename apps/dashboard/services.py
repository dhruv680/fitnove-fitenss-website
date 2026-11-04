import datetime
from decimal import Decimal
from django.db.models import Sum, Count, Q
from django.utils import timezone
from apps.members.models import Member
from apps.memberships.models import Membership, MembershipPlan
from apps.attendance.models import Attendance
from apps.payments.models import Payment, Invoice, Expense
from apps.trainers.models import Trainer

class DashboardService:
    @staticmethod
    def get_dashboard_metrics(user):
        org = user.organization
        today = timezone.now().date()
        first_day_this_month = today.replace(day=1)
        
        # Calculate last month first and last day
        if first_day_this_month.month == 1:
            first_day_last_month = first_day_this_month.replace(year=first_day_this_month.year - 1, month=12, day=1)
        else:
            first_day_last_month = first_day_this_month.replace(month=first_day_this_month.month - 1, day=1)
        last_day_last_month = first_day_this_month - datetime.timedelta(days=1)

        # Scoped Querysets
        if user.is_super_admin:
            members_qs = Member.objects.all()
            memberships_qs = Membership.objects.all()
            attendance_qs = Attendance.objects.all()
            payments_qs = Payment.objects.all()
            expenses_qs = Expense.objects.all()
            trainers_qs = Trainer.objects.all()
        else:
            members_qs = Member.objects.filter(organization=org)
            memberships_qs = Membership.objects.filter(member__organization=org)
            attendance_qs = Attendance.objects.filter(member__organization=org)
            payments_qs = Payment.objects.filter(organization=org)
            expenses_qs = Expense.objects.filter(organization=org)
            trainers_qs = Trainer.objects.filter(organization=org)

        # 8 KPI Cards
        total_members = members_qs.count()
        active_members = members_qs.filter(status=Member.Status.ACTIVE).count()
        new_registrations = members_qs.filter(joined_date__gte=first_day_this_month).count()
        new_registrations_last_month = members_qs.filter(
            joined_date__gte=first_day_last_month,
            joined_date__lte=last_day_last_month
        ).count()

        # Growth %
        if new_registrations_last_month > 0:
            growth_pct = round(((new_registrations - new_registrations_last_month) / new_registrations_last_month) * 100, 1)
        else:
            growth_pct = 100.0 if new_registrations > 0 else 0.0

        total_revenue = payments_qs.filter(status=Payment.Status.COMPLETED).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
        this_month_revenue = payments_qs.filter(
            status=Payment.Status.COMPLETED,
            payment_date__date__gte=first_day_this_month
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')

        pending_payments = payments_qs.filter(status=Payment.Status.PENDING).count()

        # Expiring in next 14 days
        expiring_threshold = today + datetime.timedelta(days=14)
        expiring_memberships = memberships_qs.filter(
            status=Membership.Status.ACTIVE,
            end_date__gte=today,
            end_date__lte=expiring_threshold
        ).count()

        today_attendance = attendance_qs.filter(date=today).count()

        # Charts Data

        # 1. Monthly Revenue (Past 6 Months)
        revenue_labels = []
        revenue_values = []
        for i in range(5, -1, -1):
            target_date = today - datetime.timedelta(days=i*30)
            m_start = target_date.replace(day=1)
            # Find next month start
            if m_start.month == 12:
                m_end = m_start.replace(year=m_start.year + 1, month=1, day=1)
            else:
                m_end = m_start.replace(month=m_start.month + 1, day=1)

            month_rev = payments_qs.filter(
                status=Payment.Status.COMPLETED,
                payment_date__date__gte=m_start,
                payment_date__date__lt=m_end
            ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0

            revenue_labels.append(m_start.strftime('%b %Y'))
            revenue_values.append(float(month_rev))

        # 2. Weekly Attendance (Last 7 Days)
        weekly_att_labels = []
        weekly_att_values = []
        for i in range(6, -1, -1):
            d = today - datetime.timedelta(days=i)
            count = attendance_qs.filter(date=d).count()
            weekly_att_labels.append(d.strftime('%a (%d %b)'))
            weekly_att_values.append(count)

        # 3. Membership Distribution by Plan
        plan_distribution = memberships_qs.filter(status=Membership.Status.ACTIVE).values(
            'plan__name'
        ).annotate(count=Count('id')).order_by('-count')
        plan_labels = [p['plan__name'] for p in plan_distribution] or ['No Active Plans']
        plan_counts = [p['count'] for p in plan_distribution] or [0]

        # 4. Member Growth (Past 6 Months)
        growth_labels = []
        growth_values = []
        for i in range(5, -1, -1):
            target_date = today - datetime.timedelta(days=i*30)
            m_start = target_date.replace(day=1)
            if m_start.month == 12:
                m_end = m_start.replace(year=m_start.year + 1, month=1, day=1)
            else:
                m_end = m_start.replace(month=m_start.month + 1, day=1)

            reg_count = members_qs.filter(
                joined_date__gte=m_start,
                joined_date__lt=m_end
            ).count()
            growth_labels.append(m_start.strftime('%b %y'))
            growth_values.append(reg_count)

        # 5. Payment Methods Distribution
        method_distribution = payments_qs.filter(status=Payment.Status.COMPLETED).values(
            'payment_method'
        ).annotate(count=Count('id'), total=Sum('total_amount')).order_by('-count')
        method_labels = [m['payment_method'] for m in method_distribution] or ['None']
        method_counts = [float(m['total'] or 0) for m in method_distribution] or [0]

        # Additional Tables / Sections
        recent_members = members_qs.order_by('-joined_date', '-id')[:5]
        recent_payments = payments_qs.order_by('-payment_date')[:5]
        expiring_list = memberships_qs.filter(
            status=Membership.Status.ACTIVE,
            end_date__gte=today,
            end_date__lte=expiring_threshold
        ).select_related('member__user', 'plan').order_by('end_date')[:5]
        trainers_list = trainers_qs.filter(status=Trainer.Status.ACTIVE)[:5]

        currency = org.currency if org else '$'

        return {
            'total_members': total_members,
            'active_members': active_members,
            'new_registrations': new_registrations,
            'growth_pct': growth_pct,
            'total_revenue': total_revenue,
            'this_month_revenue': this_month_revenue,
            'pending_payments': pending_payments,
            'expiring_memberships': expiring_memberships,
            'today_attendance': today_attendance,
            'currency': currency,
            # Chart datasets (serialized for JSON)
            'revenue_labels': revenue_labels,
            'revenue_values': revenue_values,
            'weekly_att_labels': weekly_att_labels,
            'weekly_att_values': weekly_att_values,
            'plan_labels': plan_labels,
            'plan_counts': plan_counts,
            'growth_labels': growth_labels,
            'growth_values': growth_values,
            'method_labels': method_labels,
            'method_counts': method_counts,
            # Subsections
            'recent_members': recent_members,
            'recent_payments': recent_payments,
            'expiring_list': expiring_list,
            'trainers_list': trainers_list,
        }
