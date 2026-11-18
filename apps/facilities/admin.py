from django.contrib import admin
from .models import (
    GymEquipment, CardioProgram, SprintTurfSession, TurfBooking,
    RecoveryFacility, RecoveryBooking, FuelBarItem, FuelBarOrder
)


@admin.register(GymEquipment)
class GymEquipmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'zone', 'category', 'brand', 'quantity', 'status', 'location_bay')
    list_filter = ('zone', 'status', 'category', 'brand')
    search_fields = ('name', 'brand', 'category', 'specs', 'description')
    list_editable = ('status',)


@admin.register(CardioProgram)
class CardioProgramAdmin(admin.ModelAdmin):
    list_display = ('title', 'target_hr_zone', 'duration_minutes', 'calories_burn', 'difficulty', 'trainer', 'is_active')
    list_filter = ('difficulty', 'is_active', 'duration_minutes')
    search_fields = ('title', 'equipment_used', 'description')


@admin.register(SprintTurfSession)
class SprintTurfSessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'trainer', 'schedule_info', 'capacity', 'intensity', 'is_active')
    list_filter = ('intensity', 'is_active', 'trainer')
    search_fields = ('title', 'focus', 'description')


@admin.register(TurfBooking)
class TurfBookingAdmin(admin.ModelAdmin):
    list_display = ('session', 'member', 'booking_date', 'status', 'created_at')
    list_filter = ('status', 'booking_date')
    search_fields = ('session__title', 'member__member_id', 'member__user__username')


@admin.register(RecoveryFacility)
class RecoveryFacilityAdmin(admin.ModelAdmin):
    list_display = ('name', 'facility_type', 'duration_minutes', 'temperature', 'capacity_per_slot', 'is_available')
    list_filter = ('facility_type', 'is_available')
    search_fields = ('name', 'description', 'benefits')


@admin.register(RecoveryBooking)
class RecoveryBookingAdmin(admin.ModelAdmin):
    list_display = ('facility', 'member', 'booking_date', 'time_slot', 'status', 'created_at')
    list_filter = ('status', 'booking_date', 'facility')
    search_fields = ('facility__name', 'member__member_id', 'member__user__username')
    list_editable = ('status',)


@admin.register(FuelBarItem)
class FuelBarItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'calories', 'protein_grams', 'is_available')
    list_filter = ('category', 'is_available')
    search_fields = ('name', 'description', 'ingredients')
    list_editable = ('price', 'is_available')


@admin.register(FuelBarOrder)
class FuelBarOrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'member', 'total_price', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order_number', 'member__member_id', 'member__user__username', 'notes')
    list_editable = ('status',)
