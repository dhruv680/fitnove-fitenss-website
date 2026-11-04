import datetime
from django.db import transaction
from django.utils import timezone
from .models import MembershipPlan, Membership
from apps.members.models import Member

class MembershipService:
    @staticmethod
    def get_scoped_plans(user):
        if user.is_super_admin:
            return MembershipPlan.objects.all()
        return MembershipPlan.objects.filter(organization=user.organization)

    @staticmethod
    def get_scoped_memberships(user):
        if user.is_super_admin:
            return Membership.objects.select_related('member__user', 'plan').all()
        return Membership.objects.select_related('member__user', 'plan').filter(member__organization=user.organization)

    @staticmethod
    @transaction.atomic
    def assign_membership(member, plan, start_date=None, notes=''):
        start_date = start_date or timezone.now().date()
        end_date = start_date + datetime.timedelta(days=plan.duration_days)

        # Deactivate any existing active subscriptions
        member.memberships.filter(status=Membership.Status.ACTIVE).update(status=Membership.Status.EXPIRED)

        membership = Membership.objects.create(
            member=member,
            plan=plan,
            start_date=start_date,
            end_date=end_date,
            status=Membership.Status.ACTIVE,
            notes=notes
        )

        member.status = Member.Status.ACTIVE
        member.save(update_fields=['status'])
        return membership

    @staticmethod
    @transaction.atomic
    def renew_membership(member, plan=None, extra_days=None, notes=''):
        today = timezone.now().date()
        current = member.current_membership
        
        # Calculate start date: if currently active and not expired, add from current end_date, else from today
        if current and current.end_date >= today:
            start_date = current.end_date + datetime.timedelta(days=1)
        else:
            start_date = today

        selected_plan = plan or (current.plan if current else None)
        if not selected_plan:
            raise ValueError("No membership plan specified for renewal.")

        duration = extra_days if extra_days else selected_plan.duration_days
        end_date = start_date + datetime.timedelta(days=duration)

        membership = Membership.objects.create(
            member=member,
            plan=selected_plan,
            start_date=start_date,
            end_date=end_date,
            status=Membership.Status.ACTIVE,
            notes=notes or f"Renewed on {today}"
        )

        member.status = Member.Status.ACTIVE
        member.save(update_fields=['status'])
        return membership

    @staticmethod
    def check_and_update_expiries(organization=None):
        """
        Scans subscriptions and marks past end-date memberships as EXPIRED.
        Also updates member status if no active subscription remains.
        """
        today = timezone.now().date()
        qs = Membership.objects.filter(status=Membership.Status.ACTIVE, end_date__lt=today)
        if organization:
            qs = qs.filter(member__organization=organization)

        expired_count = qs.update(status=Membership.Status.EXPIRED)

        # Check members who no longer have an active membership
        members_to_expire = Member.objects.filter(status=Member.Status.ACTIVE).exclude(
            memberships__status=Membership.Status.ACTIVE,
            memberships__end_date__gte=today
        )
        if organization:
            members_to_expire = members_to_expire.filter(organization=organization)
        
        members_to_expire.update(status=Member.Status.EXPIRED)
        return expired_count

