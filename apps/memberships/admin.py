from django.contrib import admin
from .models import MembershipPlan, Membership


@admin.register(MembershipPlan)
class MembershipPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'duration_type', 'duration_days', 'price', 'signup_fee', 'is_popular', 'is_active', 'organization')
    list_filter = ('duration_type', 'is_active', 'is_popular', 'organization')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ('member', 'plan', 'start_date', 'end_date', 'status', 'auto_renew', 'is_currently_active')
    list_filter = ('status', 'auto_renew', 'plan', 'start_date', 'end_date')
    search_fields = ('member__member_id', 'member__user__username', 'member__user__first_name', 'member__user__last_name', 'plan__name')
    readonly_fields = ('created_at', 'updated_at')
