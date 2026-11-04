from rest_framework import serializers
from .models import MembershipPlan, Membership

class MembershipPlanSerializer(serializers.ModelSerializer):
    duration_type_display = serializers.CharField(source='get_duration_type_display', read_only=True)
    feature_list = serializers.ReadOnlyField()

    class Meta:
        model = MembershipPlan
        fields = [
            'id', 'organization', 'name', 'slug', 'duration_type',
            'duration_type_display', 'duration_days', 'price', 'signup_fee',
            'features', 'feature_list', 'has_trainer_included', 'has_locker_included',
            'has_classes_included', 'is_popular', 'is_active', 'created_at'
        ]


class MembershipSerializer(serializers.ModelSerializer):
    plan_name = serializers.ReadOnlyField(source='plan.name')
    member_name = serializers.ReadOnlyField(source='member.full_name')
    days_remaining = serializers.ReadOnlyField()
    is_currently_active = serializers.ReadOnlyField()

    class Meta:
        model = Membership
        fields = [
            'id', 'member', 'member_name', 'plan', 'plan_name',
            'start_date', 'end_date', 'status', 'auto_renew',
            'days_remaining', 'is_currently_active', 'notes', 'created_at'
        ]

