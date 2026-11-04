from django.db import transaction
from django.utils import timezone
from apps.accounts.models import User
from .models import Trainer

class TrainerService:
    @staticmethod
    def get_scoped_trainers(user):
        if user.is_super_admin:
            return Trainer.objects.select_related('user', 'branch', 'organization').all()
        return Trainer.objects.select_related('user', 'branch', 'organization').filter(organization=user.organization)

    @staticmethod
    @transaction.atomic
    def create_trainer(organization, branch, first_name, last_name, email, phone, specialization, experience_years, hourly_rate, bio='', certifications=''):
        username = email.split('@')[0]
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        user = User.objects.create_user(
            username=username,
            email=email,
            password='Trainer@FitNova2026',
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            role=User.Role.TRAINER,
            organization=organization,
            branch=branch
        )

        emp_count = Trainer.objects.filter(organization=organization).count() + 1
        emp_id = f"TRN-{emp_count:04d}"

        trainer = Trainer.objects.create(
            user=user,
            organization=organization,
            branch=branch,
            employee_id=emp_id,
            specialization=specialization,
            experience_years=experience_years,
            hourly_rate=hourly_rate,
            bio=bio,
            certifications=certifications
        )
        return trainer

