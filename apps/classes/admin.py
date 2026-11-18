from django.contrib import admin
from .models import FitnessClass, ClassBooking


@admin.register(FitnessClass)
class FitnessClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'trainer', 'room', 'capacity', 'schedule_time', 'duration_minutes', 'days_of_week', 'is_active', 'branch')
    list_filter = ('is_active', 'branch', 'trainer')
    search_fields = ('name', 'room', 'description')


@admin.register(ClassBooking)
class ClassBookingAdmin(admin.ModelAdmin):
    list_display = ('fitness_class', 'member', 'booking_date', 'status', 'booked_at')
    list_filter = ('status', 'booking_date', 'fitness_class')
    search_fields = ('fitness_class__name', 'member__member_id', 'member__user__username')
