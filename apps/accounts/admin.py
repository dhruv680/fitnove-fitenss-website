from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, GymOrganization, GymBranch, UserFaceProfile,
    FaceAuthenticationLog, FailedLoginAttempt, EmailVerificationOTP
)


@admin.register(GymOrganization)
class GymOrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'currency', 'email', 'phone', 'is_active', 'created_at')
    list_filter = ('is_active', 'currency')
    search_fields = ('name', 'email', 'phone', 'tax_id')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(GymBranch)
class GymBranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'code', 'city', 'phone', 'is_main_branch', 'is_active')
    list_filter = ('organization', 'is_main_branch', 'is_active', 'city')
    search_fields = ('name', 'code', 'city', 'address', 'phone')


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'organization', 'is_verified', 'is_active', 'is_staff')
    list_filter = ('role', 'is_verified', 'is_active', 'is_staff', 'organization')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone')
    ordering = ('-date_joined',)

    fieldsets = BaseUserAdmin.fieldsets + (
        ('FitNova Profile Details', {
            'fields': ('role', 'organization', 'branch', 'phone', 'gender', 'date_of_birth', 'address', 'profile_picture', 'is_verified')
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('FitNova Profile Details', {
            'fields': ('role', 'organization', 'branch', 'phone', 'gender', 'email')
        }),
    )


@admin.register(UserFaceProfile)
class UserFaceProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'sample_count', 'quality_score', 'liveness_verified', 'is_active', 'enrolled_at', 'last_authenticated_at')
    list_filter = ('is_active', 'liveness_verified', 'enrolled_at')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'face_hash')
    readonly_fields = ('enrolled_at', 'face_hash', 'encrypted_template')


@admin.register(FaceAuthenticationLog)
class FaceAuthenticationLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'event_type', 'status', 'user', 'similarity_score', 'liveness_score', 'ip_address')
    list_filter = ('event_type', 'status', 'created_at')
    search_fields = ('user__username', 'user__email', 'ip_address', 'failure_reason')
    readonly_fields = ('created_at',)


@admin.register(FailedLoginAttempt)
class FailedLoginAttemptAdmin(admin.ModelAdmin):
    list_display = ('identifier', 'ip_address', 'attempt_count', 'is_locked', 'locked_until', 'last_attempt_at')
    list_filter = ('is_locked', 'last_attempt_at')
    search_fields = ('identifier', 'ip_address')


@admin.register(EmailVerificationOTP)
class EmailVerificationOTPAdmin(admin.ModelAdmin):
    list_display = ('email', 'otp_code', 'is_verified', 'created_at', 'expires_at')
    list_filter = ('is_verified', 'created_at')
    search_fields = ('email', 'otp_code')
