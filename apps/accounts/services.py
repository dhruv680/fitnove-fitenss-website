from django.contrib.auth import authenticate, login
from django.db import transaction
from django.utils.text import slugify
from .models import User, GymOrganization, GymBranch

class AccountService:
    @staticmethod
    def get_user_scope_queryset(user, queryset):
        """
        Filters any queryset by the user's organization and branch (if applicable).
        Super admins see all.
        """
        if not user or not user.is_authenticated:
            return queryset.none()
        if user.is_super_admin:
            return queryset

        if hasattr(queryset.model, 'organization'):
            return queryset.filter(organization=user.organization)
        elif hasattr(queryset.model, 'member'):
            return queryset.filter(member__organization=user.organization)
        return queryset

    @staticmethod
    @transaction.atomic
    def create_organization_with_branch(name, email, phone, city, address, currency='$'):
        slug = slugify(name)
        base_slug = slug
        count = 1
        while GymOrganization.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{count}"
            count += 1

        org = GymOrganization.objects.create(
            name=name,
            slug=slug,
            email=email,
            phone=phone,
            currency=currency
        )

        branch = GymBranch.objects.create(
            organization=org,
            name=f"{name} Main Center",
            code=f"{slug[:4].upper()}-01",
            address=address or 'Central Plaza, Suite 100',
            city=city or 'Metro City',
            state='State',
            zip_code='10001',
            phone=phone,
            email=email,
            is_main_branch=True
        )

        return org, branch

    @staticmethod
    @transaction.atomic
    def create_user(username, email, password, role=User.Role.MEMBER, organization=None, branch=None, **extra_fields):
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role=role,
            organization=organization,
            branch=branch,
            **extra_fields
        )
        return user

