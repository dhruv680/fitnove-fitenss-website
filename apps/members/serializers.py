from rest_framework import serializers
from .models import Member
from apps.accounts.serializers import UserSerializer
from apps.memberships.serializers import MembershipSerializer

class MemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    full_name = serializers.ReadOnlyField()
    email = serializers.ReadOnlyField()
    phone = serializers.ReadOnlyField()
    current_membership = MembershipSerializer(read_only=True)
    days_until_expiry = serializers.ReadOnlyField()
    is_membership_active = serializers.ReadOnlyField()
    assigned_trainer_name = serializers.ReadOnlyField(source='assigned_trainer.full_name')

    class Meta:
        model = Member
        fields = [
            'id', 'user', 'organization', 'branch', 'member_id',
            'full_name', 'email', 'phone', 'emergency_contact_name',
            'emergency_contact_phone', 'blood_group', 'medical_history',
            'fitness_goals', 'qr_token', 'qr_code', 'status',
            'joined_date', 'assigned_trainer', 'assigned_trainer_name',
            'current_membership', 'days_until_expiry', 'is_membership_active', 'notes'
        ]

