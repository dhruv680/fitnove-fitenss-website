from django.contrib import admin
from .models import Lead


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'email', 'source', 'status', 'interest', 'assigned_to', 'trial_date', 'created_at')
    list_filter = ('status', 'source', 'branch', 'created_at')
    search_fields = ('full_name', 'phone', 'email', 'notes')
    date_hierarchy = 'created_at'
