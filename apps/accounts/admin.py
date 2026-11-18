from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, GymOrganization, GymBranch, UserFaceProfile


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
    list_display = ('user', 'is_active', 'enrolled_at')
    list_filter = ('is_active', 'enrolled_at')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('enrolled_at',)
