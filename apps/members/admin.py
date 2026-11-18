from django.contrib import admin
from .models import Member


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('member_id', 'get_full_name', 'get_email', 'status', 'joined_date', 'branch', 'assigned_trainer')
    list_filter = ('status', 'branch', 'organization', 'joined_date')
    search_fields = ('member_id', 'user__username', 'user__email', 'user__first_name', 'user__last_name', 'user__phone')
    readonly_fields = ('qr_token', 'joined_date')

    @admin.display(description='Member Name', ordering='user__first_name')
    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    @admin.display(description='Email', ordering='user__email')
    def get_email(self, obj):
        return obj.user.email
