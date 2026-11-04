import datetime
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import User
from .models import Member

class MemberService:
    @staticmethod
    def get_scoped_members(user):
        if user.is_super_admin:
            return Member.objects.select_related('user', 'organization', 'branch', 'assigned_trainer__user').prefetch_related('memberships__plan').all()
        return Member.objects.select_related('user', 'organization', 'branch', 'assigned_trainer__user').prefetch_related('memberships__plan').filter(organization=user.organization)

    @staticmethod
    @transaction.atomic
    def create_member(organization, branch, first_name, last_name, email, phone, gender='MALE',
                      dob=None, address='', blood_group='', emergency_name='', emergency_phone='',
                      medical_history='', fitness_goals='', assigned_trainer=None, joined_date=None):
        username = email.split('@')[0]
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        user = User.objects.create_user(
            username=username,
            email=email,
            password='Member@FitNova2026',
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            gender=gender,
            date_of_birth=dob,
            address=address,
            role=User.Role.MEMBER,
            organization=organization,
            branch=branch
        )

        year = timezone.now().year
        count = Member.objects.filter(organization=organization).count() + 1
        member_id = f"FN-{year}-{count:04d}"

        member = Member.objects.create(
            user=user,
            organization=organization,
            branch=branch,
            member_id=member_id,
            emergency_contact_name=emergency_name,
            emergency_contact_phone=emergency_phone,
            blood_group=blood_group,
            medical_history=medical_history,
            fitness_goals=fitness_goals,
            assigned_trainer=assigned_trainer,
            joined_date=joined_date or timezone.now().date(),
            status=Member.Status.PENDING
        )
        return member

