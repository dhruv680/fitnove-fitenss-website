from django.contrib import admin
from .models import Attendance, MemberFaceProfile


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('member', 'date', 'check_in_time', 'check_out_time', 'method', 'status', 'branch')
    list_filter = ('method', 'status', 'date', 'branch')
    search_fields = ('member__member_id', 'member__user__username', 'member__user__first_name', 'member__user__last_name')
    date_hierarchy = 'date'


@admin.register(MemberFaceProfile)
class MemberFaceProfileAdmin(admin.ModelAdmin):
    list_display = ('member', 'is_active', 'enrolled_at')
    list_filter = ('is_active', 'enrolled_at')
    search_fields = ('member__member_id', 'member__user__username', 'member__user__first_name', 'member__user__last_name')
    readonly_fields = ('enrolled_at',)
