from django.contrib import admin
from .models import Trainer


@admin.register(Trainer)
class TrainerAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'get_full_name', 'specialization', 'experience_years', 'hourly_rate', 'status', 'branch')
    list_filter = ('status', 'specialization', 'branch', 'organization')
    search_fields = ('employee_id', 'user__username', 'user__email', 'user__first_name', 'user__last_name', 'specialization')
    readonly_fields = ('joined_date',)

    @admin.display(description='Trainer Name', ordering='user__first_name')
    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
