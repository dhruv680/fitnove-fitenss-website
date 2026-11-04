from rest_framework import serializers
from .models import FitnessClass, ClassBooking

class FitnessClassSerializer(serializers.ModelSerializer):
    trainer_name = serializers.ReadOnlyField(source='trainer.full_name')
    active_bookings = serializers.SerializerMethodField()
    available_slots = serializers.SerializerMethodField()

    class Meta:
        model = FitnessClass
        fields = [
            'id', 'organization', 'branch', 'name', 'trainer', 'trainer_name',
            'capacity', 'room', 'schedule_time', 'duration_minutes', 'days_of_week',
            'description', 'is_active', 'active_bookings', 'available_slots'
        ]

    def get_active_bookings(self, obj):
        return obj.active_bookings_count()

    def get_available_slots(self, obj):
        return obj.available_slots()


class ClassBookingSerializer(serializers.ModelSerializer):
    class_name = serializers.ReadOnlyField(source='fitness_class.name')
    member_name = serializers.ReadOnlyField(source='member.full_name')

    class Meta:
        model = ClassBooking
        fields = ['id', 'fitness_class', 'class_name', 'member', 'member_name', 'booking_date', 'status', 'booked_at']

